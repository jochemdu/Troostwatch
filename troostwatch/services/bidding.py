"""Bid submission helpers built on top of the authenticated HTTP client."""

from __future__ import annotations

import sqlite3
from contextlib import AbstractContextManager
from typing import Any, Callable
from urllib.parse import urljoin

from troostwatch.infrastructure.db import ensure_schema, get_connection
from troostwatch.infrastructure.db.repositories import BidRepository
from troostwatch.infrastructure.http import AuthenticationError, TroostwatchHttpClient
from troostwatch.infrastructure.observability import get_logger, log_context
from troostwatch.services.dto import BidResultDTO

ConnectionFactory = Callable[[], AbstractContextManager[sqlite3.Connection]]

# Re-export for backward compatibility
BidResult = BidResultDTO


class BidError(Exception):
    """Raised when a bid cannot be submitted."""


class BiddingService:
    """Service for submitting bids against the remote Troostwijk API.

    Uses connection factory pattern for optional bid persistence.
    """

    def __init__(
        self,
        client: TroostwatchHttpClient,
        *,
        api_base_url: str = "https://www.troostwijkauctions.com/api",
        connection_factory: ConnectionFactory | None = None,
    ) -> None:
        self.client = client
        self.api_base_url = api_base_url.rstrip("/")
        self._connection_factory = connection_factory
        self._logger = get_logger(__name__)

    @classmethod
    def from_sqlite_path(
        cls,
        client: TroostwatchHttpClient,
        db_path: str,
        *,
        api_base_url: str = "https://www.troostwijkauctions.com/api",
    ) -> "BiddingService":
        """Create a BiddingService with database persistence enabled.

        Args:
            client: Authenticated HTTP client for bid submission
            db_path: Path to the SQLite database file
            api_base_url: Base URL for the bidding API

        Returns:
            BiddingService instance with persistence enabled
        """

        def connection_factory() -> AbstractContextManager[sqlite3.Connection]:
            return get_connection(db_path)

        return cls(
            client, api_base_url=api_base_url, connection_factory=connection_factory
        )

    def _resolve(self, path: str) -> str:
        return urljoin(self.api_base_url + "/", path.lstrip("/"))

    def submit_bid(
        self,
        *,
        buyer_label: str,
        auction_code: str,
        lot_code: str,
        amount_eur: float,
        note: str | None = None,
    ) -> BidResult:
        if amount_eur <= 0:
            raise ValueError("Bid amount must be positive")

        with log_context(
            auction_code=auction_code, lot_code=lot_code, buyer=buyer_label
        ):
            self._logger.info("Submitting bid for %.2f EUR", amount_eur)

            payload: dict[str, Any] = {
                "auctionCode": auction_code,
                "lotCode": lot_code,
                "amountEur": amount_eur,
                "buyerLabel": buyer_label,
            }
            if note:
                payload["note"] = note

            try:
                response = self.client.post_json(self._resolve("bids"), payload)
            except AuthenticationError:
                self._logger.error("Authentication failed during bid submission")
                raise
            except Exception as exc:  # pragma: no cover - runtime safety
                self._logger.error("Bid submission failed: %s", exc)
                raise BidError(f"Failed to submit bid: {exc}")

            self._persist_bid(buyer_label, auction_code, lot_code, amount_eur, note)
            self._logger.info("Bid submitted successfully for %.2f EUR", amount_eur)

            return BidResult(
                lot_code=lot_code,
                auction_code=auction_code,
                amount_eur=amount_eur,
                raw_response=response,
            )

    def _persist_bid(
        self,
        buyer_label: str,
        auction_code: str,
        lot_code: str,
        amount_eur: float,
        note: str | None,
    ) -> None:
        if self._connection_factory is None:
            return
        with self._connection_factory() as conn:
            ensure_schema(conn)
            try:
                BidRepository(conn).record_bid(
                    buyer_label=buyer_label,
                    auction_code=auction_code,
                    lot_code=lot_code,
                    amount_eur=amount_eur,
                    note=note,
                )
            except ValueError as exc:
                raise BidError(f"Failed to persist bid locally: {exc}")
