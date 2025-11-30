"""CLI helpers for constructing authenticated HTTP clients."""

from __future__ import annotations

from pathlib import Path

from troostwatch.infrastructure.http import (LoginCredentials,
                                             TroostwatchHttpClient)


def build_http_client(
    *,
    base_url: str,
    login_path: str,
    username: str | None,
    password: str | None,
    token_path: str | None,
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
