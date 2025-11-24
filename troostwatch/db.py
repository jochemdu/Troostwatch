"""Database utilities for Troostwatch.

This module now delegates to the infrastructure database layer found under
``troostwatch.infrastructure.db``. Schema management lives in
``troostwatch.infrastructure.db.schema`` and repositories encapsulate SQL for
individual aggregates under ``troostwatch.infrastructure.db.repositories``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Dict, Any

from troostwatch.infrastructure.db import (
    DEFAULT_DB_TIMEOUT,
    apply_pragmas,
    create_snapshot,
    get_config,
    get_connection,
    get_default_timeout,
    get_path_config,
    iso_utcnow,
    load_config,
    ensure_core_schema,
    ensure_schema,
    SchemaMigrator,
)
from troostwatch.infrastructure.db.repositories import (
    AuctionRepository,
    BidRepository,
    BuyerRepository,
    LotRepository,
    PositionRepository,
    PreferenceRepository,
)

__all__ = [
    "DEFAULT_DB_TIMEOUT",
    "apply_pragmas",
    "create_snapshot",
    "ensure_core_schema",
    "ensure_schema",
    "get_config",
    "get_connection",
    "get_default_timeout",
    "get_path_config",
    "iso_utcnow",
    "load_config",
    "run_migrations",
    "add_buyer",
    "list_buyers",
    "delete_buyer",
    "add_position",
    "list_positions",
    "delete_position",
    "list_auctions",
    "list_lot_codes_by_auction",
    "list_lots",
    "get_preference",
    "set_preference",
]


def run_migrations(conn, migrations: Iterable[str] | None = None) -> None:
    migrator = SchemaMigrator(conn)
    migrator.run_migrations(migrations)


def add_buyer(conn, label: str, name: Optional[str] = None, notes: Optional[str] = None) -> None:
    BuyerRepository(conn).add(label, name, notes)


def list_buyers(conn) -> List[Dict[str, Optional[str]]]:
    return BuyerRepository(conn).list()


def delete_buyer(conn, label: str) -> None:
    BuyerRepository(conn).delete(label)


def _get_buyer_id(conn, label: str) -> Optional[int]:
    return BuyerRepository(conn).get_id(label)


def _get_lot_id(conn, lot_code: str, auction_code: Optional[str] = None) -> Optional[int]:
    return LotRepository(conn).get_id(lot_code, auction_code)


def add_position(
    conn,
    buyer_label: str,
    lot_code: str,
    auction_code: Optional[str] = None,
    *,
    track_active: bool = True,
    max_budget_total_eur: Optional[float] = None,
    my_highest_bid_eur: Optional[float] = None,
) -> None:
    PositionRepository(conn).upsert(
        buyer_label,
        lot_code,
        auction_code,
        track_active=track_active,
        max_budget_total_eur=max_budget_total_eur,
        my_highest_bid_eur=my_highest_bid_eur,
    )


def list_positions(conn, buyer_label: Optional[str] = None) -> List[Dict[str, Optional[str]]]:
    return PositionRepository(conn).list(buyer_label)


def delete_position(conn, buyer_label: str, lot_code: str, auction_code: Optional[str] = None) -> None:
    PositionRepository(conn).delete(buyer_label, lot_code, auction_code)


def list_auctions(conn, only_active: bool = True) -> List[Dict[str, Optional[str]]]:
    return AuctionRepository(conn).list(only_active=only_active)


def list_lot_codes_by_auction(conn, auction_code: str) -> List[str]:
    return LotRepository(conn).list_lot_codes_by_auction(auction_code)


def list_lots(
    conn,
    *,
    auction_code: Optional[str] = None,
    state: Optional[str] = None,
    limit: Optional[int] = None,
) -> List[Dict[str, Optional[str]]]:
    return LotRepository(conn).list_lots(auction_code=auction_code, state=state, limit=limit)


def get_preference(conn, key: str) -> Optional[str]:
    return PreferenceRepository(conn).get(key)


def set_preference(conn, key: str, value: Optional[str]) -> None:
    PreferenceRepository(conn).set(key, value)


def record_bid(conn, buyer_label: str, auction_code: str, lot_code: str, amount_eur: float, note: Optional[str]) -> None:
    BidRepository(conn).record_bid(
        buyer_label=buyer_label,
        auction_code=auction_code,
        lot_code=lot_code,
        amount_eur=amount_eur,
        note=note,
    )
