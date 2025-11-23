"""Bid submission helpers built on top of the authenticated HTTP client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.parse import urljoin

from ..db import get_connection, ensure_schema, _get_buyer_id, _get_lot_id, iso_utcnow
from ..http_client import AuthenticationError, TroostwatchHttpClient


class BidError(Exception):
    """Raised when a bid cannot be submitted."""


@dataclass
class BidResult:
    """Structured response from the bidding API."""

    lot_code: str
    auction_code: str
    amount_eur: float
    raw_response: Dict[str, Any]


class BiddingService:
    """Service for submitting bids against the remote Troostwijk API."""

    def __init__(
        self,
        client: TroostwatchHttpClient,
        *,
        api_base_url: str = "https://www.troostwijkauctions.com/api",
    ) -> None:
        self.client = client
        self.api_base_url = api_base_url.rstrip("/")

    def _resolve(self, path: str) -> str:
        return urljoin(self.api_base_url + "/", path.lstrip("/"))

    def submit_bid(
        self,
        *,
        buyer_label: str,
        auction_code: str,
        lot_code: str,
        amount_eur: float,
        note: Optional[str] = None,
        db_path: str | None = None,
    ) -> BidResult:
        if amount_eur <= 0:
            raise ValueError("Bid amount must be positive")

        payload: Dict[str, Any] = {
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
            raise
        except Exception as exc:  # pragma: no cover - runtime safety
            raise BidError(f"Failed to submit bid: {exc}")

        self._persist_bid(db_path, buyer_label, auction_code, lot_code, amount_eur, note)

        return BidResult(
            lot_code=lot_code,
            auction_code=auction_code,
            amount_eur=amount_eur,
            raw_response=response,
        )

    def _persist_bid(
        self,
        db_path: str | None,
        buyer_label: str,
        auction_code: str,
        lot_code: str,
        amount_eur: float,
        note: Optional[str],
    ) -> None:
        if db_path is None:
            return
        with get_connection(db_path) as conn:
            ensure_schema(conn)
            buyer_id = _get_buyer_id(conn, buyer_label)
            lot_id = _get_lot_id(conn, lot_code, auction_code)
            if lot_id is None or buyer_id is None:
                # Do not fail the bid if the local DB is missing metadata
                return
            conn.execute(
                """
                INSERT INTO my_bids (lot_id, buyer_id, amount_eur, placed_at, note)
                VALUES (?, ?, ?, ?, ?)
                """,
                (lot_id, buyer_id, amount_eur, iso_utcnow(), note),
            )
            conn.commit()
