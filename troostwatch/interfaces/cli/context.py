"""Shared helpers for composing CLI command contexts.

This module centralises common CLI wiring such as resolving configuration
paths and building SQLite connections with the project defaults applied.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, ContextManager, Iterator, TypeVar

from troostwatch.infrastructure.http import TroostwatchHttpClient
from troostwatch.infrastructure.db import (
    ensure_schema,
    get_connection,
    get_path_config,
    iso_utcnow,
)
from troostwatch.infrastructure.db.repositories import (
    AuctionRepository,
    BuyerRepository,
    LotRepository,
)
from troostwatch.infrastructure.db.repositories.base import BaseRepository
from troostwatch.services.buyers import BuyerService
from troostwatch.services.lots import LotManagementService, LotViewService

from .auth import build_http_client

RepositoryT = TypeVar("RepositoryT", bound=BaseRepository)


@dataclass(frozen=True)
class CLIContext:
    """Container for CLI dependencies and configuration paths."""

    db_path: Path
    paths: dict[str, Path]
    connection_factory: Callable[[], ContextManager[sqlite3.Connection]]

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Open a configured SQLite connection and ensure the schema exists."""

        with self.connection_factory() as connection:
            ensure_schema(connection)
            yield connection

    @contextmanager
    def repository(self, repository_cls: type[RepositoryT]) -> Iterator[RepositoryT]:
        """Yield a repository instance wired to a managed connection."""

        with self.connect() as connection:
            yield repository_cls(connection)


@contextmanager
def lot_repository(cli_context: CLIContext) -> Iterator[LotRepository]:
    """Yield a LotRepository tied to the CLI context connection."""

    with cli_context.repository(LotRepository) as repository:
        yield repository


@contextmanager
def lot_view_service(cli_context: CLIContext) -> Iterator[LotViewService]:
    """Yield a LotViewService wired to the CLI context repository."""

    with lot_repository(cli_context) as repository:
        yield LotViewService(repository)


@contextmanager
def buyer_service(cli_context: CLIContext) -> Iterator[BuyerService]:
    """Yield a BuyerService wired to the CLI context repository."""

    with cli_context.repository(BuyerRepository) as repository:
        yield BuyerService(repository)


@contextmanager
def lot_management_service(cli_context: CLIContext) -> Iterator[LotManagementService]:
    """Yield a LotManagementService wired to the CLI context repositories."""

    with cli_context.connect() as conn:
        lot_repo = LotRepository(conn)
        auction_repo = AuctionRepository(conn)
        yield LotManagementService(lot_repo, auction_repo)
        conn.commit()


def get_current_timestamp() -> str:
    """Return the current UTC timestamp in ISO format."""
    return iso_utcnow()


def build_cli_context(db_path: str | Path | None = None) -> CLIContext:
    """Build the CLI context with resolved configuration paths and connection factory."""

    paths = get_path_config()
    resolved_db_path = (
        Path(db_path).expanduser() if db_path is not None else paths["db_path"]
    )

    def connection_factory() -> ContextManager[sqlite3.Connection]:
        return get_connection(resolved_db_path)

    return CLIContext(
        db_path=resolved_db_path, paths=paths, connection_factory=connection_factory
    )


@dataclass(frozen=True)
class SyncCommandContext:
    """Context container for sync commands including HTTP client wiring."""

    cli_context: CLIContext
    http_client: TroostwatchHttpClient | None


def build_sync_command_context(
    *,
    db_path: str | Path | None,
    base_url: str,
    login_path: str,
    username: str | None,
    password: str | None,
    token_path: str | None,
    session_timeout: float,
) -> SyncCommandContext:
    """Compose the CLI and HTTP context needed for sync commands."""

    cli_context = build_cli_context(db_path)
    http_client = build_http_client(
        base_url=base_url,
        login_path=login_path,
        username=username,
        password=password,
        token_path=token_path,
        session_timeout=session_timeout,
    )
    return SyncCommandContext(cli_context=cli_context, http_client=http_client)
