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

from troostwatch.infrastructure.db import ensure_schema, get_connection, get_path_config

RepositoryT = TypeVar("RepositoryT")


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


def build_cli_context(db_path: str | Path | None = None) -> CLIContext:
    """Build the CLI context with resolved configuration paths and connection factory."""

    paths = get_path_config()
    resolved_db_path = Path(db_path).expanduser() if db_path is not None else paths["db_path"]

    def connection_factory() -> ContextManager[sqlite3.Connection]:
        return get_connection(resolved_db_path)

    return CLIContext(db_path=resolved_db_path, paths=paths, connection_factory=connection_factory)
