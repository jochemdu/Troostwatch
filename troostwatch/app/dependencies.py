"""Shared FastAPI dependencies for Troostwatch application components."""

from __future__ import annotations

import sqlite3
from typing import Annotated, Iterator

from fastapi import Depends

from troostwatch.infrastructure.db import ensure_schema, get_connection
from troostwatch.infrastructure.db.repositories import (
    AuctionRepository,
    BidRepository,
    BuyerRepository,
    LotRepository,
    PositionRepository,
)
from troostwatch.infrastructure.db.repositories.images import (
    ExtractedCodeRepository,
    LotImageRepository,
)

# Re-export repository types for use in api.py type hints
# This keeps infrastructure imports centralized in the dependencies layer
__all__ = [
    # Connection and repository factory functions
    "get_db_connection",
    "get_auction_repository",
    "get_bid_repository",
    "get_lot_repository",
    "get_buyer_repository",
    "get_position_repository",
    "get_extracted_code_repository",
    "get_lot_image_repository",
    # Repository types (for re-export)
    "AuctionRepository",
    "BidRepository",
    "BuyerRepository",
    "LotRepository",
    "PositionRepository",
    "ExtractedCodeRepository",
    "LotImageRepository",
    # Annotated dependency types (modern FastAPI pattern)
    "LotRepositoryDep",
    "BuyerRepositoryDep",
    "PositionRepositoryDep",
    "AuctionRepositoryDep",
    "BidRepositoryDep",
    "ExtractedCodeRepositoryDep",
    "LotImageRepositoryDep",
]


def get_db_connection() -> Iterator[sqlite3.Connection]:
    """Provide a SQLite connection with the required schema ensured.

    Uses check_same_thread=False to allow FastAPI to use the connection
    across different threads (required for async request handling).
    """

    with get_connection(check_same_thread=False) as conn:
        ensure_schema(conn)
        yield conn


def get_lot_repository(
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> LotRepository:
    return LotRepository(conn)


def get_buyer_repository(
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> BuyerRepository:
    return BuyerRepository(conn)


def get_position_repository(
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> PositionRepository:
    return PositionRepository(conn)


def get_auction_repository(
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> AuctionRepository:
    return AuctionRepository(conn)


def get_bid_repository(
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> BidRepository:
    return BidRepository(conn)


def get_extracted_code_repository(
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> ExtractedCodeRepository:
    return ExtractedCodeRepository(conn)


def get_lot_image_repository(
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> LotImageRepository:
    return LotImageRepository(conn)


# Annotated dependency types for modern FastAPI (0.122+) patterns
# Use these instead of `param: Type = Depends(get_x)` repetition
LotRepositoryDep = Annotated[LotRepository, Depends(get_lot_repository)]
BuyerRepositoryDep = Annotated[BuyerRepository, Depends(get_buyer_repository)]
PositionRepositoryDep = Annotated[PositionRepository, Depends(get_position_repository)]
AuctionRepositoryDep = Annotated[AuctionRepository, Depends(get_auction_repository)]
BidRepositoryDep = Annotated[BidRepository, Depends(get_bid_repository)]
ExtractedCodeRepositoryDep = Annotated[
    ExtractedCodeRepository, Depends(get_extracted_code_repository)
]
LotImageRepositoryDep = Annotated[LotImageRepository, Depends(get_lot_image_repository)]
