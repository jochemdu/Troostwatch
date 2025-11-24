"""CLI helpers for constructing authenticated HTTP clients."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from troostwatch.http_client import LoginCredentials, TroostwatchHttpClient


def build_http_client(
    *,
    base_url: str,
    login_path: str,
    username: Optional[str],
    password: Optional[str],
    token_path: Optional[str],
    session_timeout: float,
) -> TroostwatchHttpClient | None:
    """Return a configured :class:`TroostwatchHttpClient` or ``None``.

    The helper only constructs a client when either credentials or a token path
    are provided. Callers can then decide whether authentication is mandatory
    for their workflow.
    """

    if not username and not token_path:
        return None

    creds = LoginCredentials(
        username=username,
        password=password,
        token_path=Path(token_path) if token_path else None,
    )
    return TroostwatchHttpClient(
        base_url=base_url,
        login_path=login_path,
        credentials=creds,
        session_timeout_seconds=session_timeout,
    )
