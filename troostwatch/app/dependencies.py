"""Shared FastAPI dependencies for Troostwatch application components."""

from __future__ import annotations

import sqlite3
from typing import Iterator

from fastapi import Depends

from troostwatch.infrastructure.db import ensure_schema, get_connection
from troostwatch.infrastructure.db.repositories import (
    AuctionRepository,
    BidRepository,
    BuyerRepository,
    LotRepository,
    PositionRepository,
)

# Re-export repository types for use in api.py type hints
# This keeps infrastructure imports centralized in the dependencies layer
__all__ = [
    "get_db_connection",
    "get_auction_repository",
    "get_bid_repository",
    "get_lot_repository",
    "get_buyer_repository",
    "get_position_repository",
    "AuctionRepository",
    "BidRepository",
    "BuyerRepository",
    "LotRepository",
    "PositionRepository",
]


def get_db_connection() -> Iterator[sqlite3.Connection]:
    """Provide a SQLite connection with the required schema ensured.
    
    Uses check_same_thread=False to allow FastAPI to use the connection
    across different threads (required for async request handling).
    """

    with get_connection(check_same_thread=False) as conn:
        ensure_schema(conn)
        yield conn


def get_lot_repository(conn: sqlite3.Connection = Depends(get_db_connection)) -> LotRepository:
    return LotRepository(conn)


def get_buyer_repository(conn: sqlite3.Connection = Depends(get_db_connection)) -> BuyerRepository:
    return BuyerRepository(conn)


def get_position_repository(conn: sqlite3.Connection = Depends(get_db_connection)) -> PositionRepository:
    return PositionRepository(conn)


def get_auction_repository(conn: sqlite3.Connection = Depends(get_db_connection)) -> AuctionRepository:
    return AuctionRepository(conn)


def get_bid_repository(conn: sqlite3.Connection = Depends(get_db_connection)) -> BidRepository:
    return BidRepository(conn)
