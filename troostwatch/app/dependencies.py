"""Shared FastAPI dependencies for Troostwatch application components."""

from __future__ import annotations

import sqlite3
from typing import Iterator

from fastapi import Depends

from troostwatch.infrastructure.db import ensure_schema, get_connection
from troostwatch.infrastructure.db.repositories import BuyerRepository, LotRepository, PositionRepository


def get_db_connection() -> Iterator[sqlite3.Connection]:
    """Provide a SQLite connection with the required schema ensured."""

    with get_connection() as conn:
        ensure_schema(conn)
        yield conn


def get_lot_repository(conn: sqlite3.Connection = Depends(get_db_connection)) -> LotRepository:
    return LotRepository(conn)


def get_buyer_repository(conn: sqlite3.Connection = Depends(get_db_connection)) -> BuyerRepository:
    return BuyerRepository(conn)


def get_position_repository(conn: sqlite3.Connection = Depends(get_db_connection)) -> PositionRepository:
    return PositionRepository(conn)
