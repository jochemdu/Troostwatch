"""Helper functions for CLI context operations.

These functions provide a clean interface for CLI commands to access
database-related functionality without directly importing infrastructure modules.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from .context import build_cli_context
from troostwatch.infrastructure.db.repositories import (
    AuctionRepository,
    LotRepository,
    PreferenceRepository,
)


def load_auctions(db_path: str, active_only: bool = True) -> List[Dict]:
    """Load auctions from the database.
    
    Args:
        db_path: Path to the database file.
        active_only: If True, only return active auctions.
        
    Returns:
        List of auction dictionaries.
    """
    cli_context = build_cli_context(db_path)
    with cli_context.connect() as conn:
        return AuctionRepository(conn).list(only_active=active_only)


def load_lots_for_auction(db_path: str, auction_code: str) -> Sequence[str]:
    """Load lot codes for a specific auction.
    
    Args:
        db_path: Path to the database file.
        auction_code: The auction code to filter by.
        
    Returns:
        Sequence of lot code strings.
    """
    cli_context = build_cli_context(db_path)
    with cli_context.connect() as conn:
        return LotRepository(conn).list_lot_codes_by_auction(auction_code)


def get_preference(db_path: str, key: str) -> Optional[str]:
    """Get a preference value from the database.
    
    Args:
        db_path: Path to the database file.
        key: The preference key.
        
    Returns:
        The preference value or None if not set.
    """
    cli_context = build_cli_context(db_path)
    with cli_context.connect() as conn:
        return PreferenceRepository(conn).get(key)


def set_preference(db_path: str, key: str, value: Optional[str]) -> None:
    """Set a preference value in the database.

    Args:
        db_path: Path to the database file.
        key: The preference key.
        value: The preference value (or None to clear).
    """
    cli_context = build_cli_context(db_path)
    with cli_context.connect() as conn:
        PreferenceRepository(conn).set(key, value)
        conn.commit()
