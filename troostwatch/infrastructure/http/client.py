"""HTTP client with login session handling for Troostwatch.

This module centralises HTTP access that requires authentication against the
Troostwijk website. It maintains a :class:`requests.Session`, performs
credential-based logins, extracts CSRF tokens, reuses cookies and enforces a
simple session timeout so long-running processes can refresh credentials when
needed.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from requests import Response, Session


class AuthenticationError(Exception):
    """Raised when login fails or responses indicate the user is unauthenticated."""


class SessionExpiredError(Exception):
    """Raised when an operation is attempted with an expired session."""


@dataclass
class LoginCredentials:
    """Simple container for login inputs and optional cached token path."""

    username: str | None = None
    password: str | None = None
    token_path: Path | None = None


@dataclass
class StoredSession:
    """Represents persisted session state on disk."""

    csrf_token: str | None
    cookies: dict[str, str]
    obtained_at: float

    def is_expired(self, timeout_seconds: float) -> bool:
        return (
            timeout_seconds > 0 and (
                time.time() - self.obtained_at) > timeout_seconds
        )


class TroostwatchHttpClient:
    """Authenticated HTTP helper with CSRF and cookie management."""

    def __init__(
        self,
        *,
        base_url: str = "https://www.troostwijkauctions.com",
        login_path: str = "/login",
        credentials: LoginCredentials | None = None,
        session_timeout_seconds: float = 30 * 60,
        session: Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.login_path = login_path
        self.credentials = credentials or LoginCredentials()
        self.session_timeout_seconds = session_timeout_seconds
        self.session = session or requests.Session()
        self.csrf_token: str | None = None
        self.last_authenticated: float | None = None

    # -------------------- token helpers --------------------
    def _extract_csrf(self, response: Response) -> str | None:
        header_token = response.headers.get("X-CSRFToken") or response.headers.get(
            "X-CSRF-Token"
        )
        if header_token:
            return header_token
        match = re.search(
            r'name=["\']csrf-token["\']\s+content=["\']([^"\']+)',
            response.text,
            re.IGNORECASE,
        )
        if match:
            return match.group(1)
        return None

    def _store_session(self, path: Path) -> None:
        data = {
            "csrf_token": self.csrf_token,
            "cookies": self.session.cookies.get_dict(),
            "obtained_at": self.last_authenticated or time.time(),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _load_session(self, path: Path) -> StoredSession | None:
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        try:
            return StoredSession(
                csrf_token=payload.get("csrf_token"),
                cookies=payload.get("cookies", {}),
                obtained_at=float(payload.get("obtained_at", 0)),
            )
        except Exception:
            return None

    def _restore_from_tokens(self, tokens: StoredSession) -> None:
        self.csrf_token = tokens.csrf_token
        self.session.cookies.update(tokens.cookies)
        self.last_authenticated = tokens.obtained_at

    # -------------------- auth workflow --------------------
    def _session_active(self) -> bool:
        if self.last_authenticated is None:
            return False
        return not StoredSession(None, {}, self.last_authenticated).is_expired(
            self.session_timeout_seconds
        )

    def authenticate(self, *, force: bool = False) -> None:
        """
        Ensure an authenticated session exists.
        Raises:
            SessionExpiredError: If credentials are missing or session cannot be refreshed.
        """
        import logging

        logger = logging.getLogger(__name__)

        if not force and self._session_active():
            return

        token_path = self.credentials.token_path
        if token_path is not None:
            cached = self._load_session(token_path)
            if cached and not cached.is_expired(self.session_timeout_seconds):
                self._restore_from_tokens(cached)
                return

        if not self.credentials.username or not self.credentials.password:
            logger.error(
                "Session expired and no credentials/token available to refresh."
            )
            raise SessionExpiredError(
                "Session expired and no credentials/token available to refresh."
            )

        try:
            self._login(self.credentials.username, self.credentials.password)
        except Exception as exc:
            logger.error(f"Login failed: {exc}")
            raise AuthenticationError(f"Login failed: {exc}") from exc
        if token_path is not None:
            self._store_session(token_path)

    def _login(self, username: str, password: str) -> None:
        """
        Perform login and update session tokens.
        Raises:
            AuthenticationError: If login fails.
        """
        import logging

        logger = logging.getLogger(__name__)
        login_url = urljoin(self.base_url + "/", self.login_path.lstrip("/"))
        try:
            page = self.session.get(login_url)
            page.raise_for_status()
            csrf = self._extract_csrf(page)
        except Exception as exc:
            logger.error(f"Failed to fetch login page: {exc}")
            raise AuthenticationError(
                f"Failed to fetch login page: {exc}") from exc

        payload = {"username": username,
                   "email": username, "password": password}
        headers: dict[str, str] = {}
        if csrf:
            headers["X-CSRFToken"] = csrf
        try:
            response = self.session.post(
                login_url, data=payload, headers=headers)
            if response.status_code >= 400:
                logger.error(
                    f"Login failed with status {response.status_code}: {response.text[:200]}"
                )
                raise AuthenticationError(
                    f"Login failed with status {response.status_code}: {response.text[:200]}"
                )
            self.csrf_token = self._extract_csrf(response) or csrf
            self.last_authenticated = time.time()
        except Exception as exc:
            logger.error(f"Login request failed: {exc}")
            raise AuthenticationError(f"Login request failed: {exc}") from exc

    # -------------------- request helpers --------------------
    def _prepare_headers(self, extra: dict[str, str | None]) -> dict[str, str]:
        from troostwatch import __version__

        headers = {"User-Agent": f"troostwatch-client/{__version__}"}
        if extra:
            headers.update(extra)
        if self.csrf_token:
            headers.setdefault("X-CSRFToken", self.csrf_token)
        return headers

    def authenticated_get(self, url: str, **kwargs: Any) -> Response:
        self.authenticate()
        headers = self._prepare_headers(kwargs.pop("headers", None))
        response = self.session.get(url, headers=headers, **kwargs)
        self._raise_for_status(response)
        return response

    def authenticated_post(self, url: str, **kwargs: Any) -> Response:
        self.authenticate()
        headers = self._prepare_headers(kwargs.pop("headers", None))
        response = self.session.post(url, headers=headers, **kwargs)
        self._raise_for_status(response)
        return response

    def _raise_for_status(self, response: Response) -> None:
        """
        Raise custom exceptions for HTTP error status codes.
        """
        import logging

        logger = logging.getLogger(__name__)
        if response.status_code == 401:
            logger.error("Unauthenticated request; please log in again.")
            raise AuthenticationError(
                "Unauthenticated request; please log in again.")
        if response.status_code == 403:
            logger.error("Permission denied for the requested operation.")
            raise AuthenticationError(
                "Permission denied for the requested operation.")
        try:
            response.raise_for_status()
        except Exception as exc:
            logger.error(f"HTTP request failed: {exc}")
            raise AuthenticationError(f"HTTP request failed: {exc}") from exc

    # -------------------- convenience --------------------
    def fetch_text(self, url: str) -> str:
        """Authenticated GET request that returns decoded text."""
        response = self.authenticated_get(url)
        response.encoding = response.encoding or "utf-8"
        return response.text

    def post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Authenticated POST returning parsed JSON."""
        response = self.authenticated_post(url, json=payload)
        try:
            return response.json()
        except Exception as exc:
            raise AuthenticationError(f"Failed to parse JSON response: {exc}")

    def _get(self, url, **kwargs):
        return DummyResponse(text=f"response for {url}")

    def _post_json(self, url, payload, **kwargs):
        return DummyResponse(json_data={"echo": payload, "url": url})


__all__ = [
    "AuthenticationError",
    "LoginCredentials",
    "SessionExpiredError",
    "StoredSession",
    "TroostwatchHttpClient",
]
