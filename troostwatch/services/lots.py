"""Service helpers for viewing, filtering, and managing lots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

from pydantic import BaseModel, Field

from troostwatch.infrastructure.db.repositories import AuctionRepository, LotRepository
from troostwatch.infrastructure.web.parsers import LotCardData, LotDetailData


class LotView(BaseModel):
    """DTO representing a lot summary suitable for API responses."""

    auction_code: str
    lot_code: str
    title: Optional[str] = None
    state: Optional[str] = None
    current_bid_eur: Optional[float] = None
    bid_count: Optional[int] = None
    current_bidder_label: Optional[str] = None
    closing_time_current: Optional[str] = Field(default=None, description="Current closing timestamp, if set.")
    closing_time_original: Optional[str] = Field(default=None, description="Original closing timestamp, if set.")

    model_config = {"from_attributes": True}

    @classmethod
    def from_record(cls, record: dict[str, object]) -> "LotView":
        return cls.model_validate({
            "auction_code": record["auction_code"],
            "lot_code": record["lot_code"],
            "title": record.get("title"),
            "state": record.get("state"),
            "current_bid_eur": record.get("current_bid_eur"),
            "bid_count": record.get("bid_count"),
            "current_bidder_label": record.get("current_bidder_label"),
            "closing_time_current": record.get("closing_time_current"),
            "closing_time_original": record.get("closing_time_original"),
        })


class LotViewService:
    """Service exposing read-only lot views for APIs and CLIs."""

    def __init__(self, lot_repository: LotRepository) -> None:
        self._lot_repository = lot_repository

    def list_lots(
        self,
        *,
        auction_code: Optional[str] = None,
        state: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[LotView]:
        effective_limit = None if limit is not None and limit <= 0 else limit
        rows = self._lot_repository.list_lots(
            auction_code=auction_code,
            state=state,
            limit=effective_limit,
        )
        return self._to_dtos(rows)

    def _to_dtos(self, rows: Iterable[dict[str, object]]) -> List[LotView]:
        return [LotView.from_record(row) for row in rows]


@dataclass
class LotInput:
    """Input data for adding/updating a lot."""

    auction_code: str
    lot_code: str
    title: str
    url: Optional[str] = None
    state: Optional[str] = None
    opens_at: Optional[str] = None
    closing_time: Optional[str] = None
    bid_count: Optional[int] = None
    opening_bid_eur: Optional[float] = None
    current_bid_eur: Optional[float] = None
    location_city: Optional[str] = None
    location_country: Optional[str] = None
    auction_title: Optional[str] = None
    auction_url: Optional[str] = None


class LotManagementService:
    """Service for adding and updating lots."""

    def __init__(
        self,
        lot_repository: LotRepository,
        auction_repository: AuctionRepository,
    ) -> None:
        self._lot_repository = lot_repository
        self._auction_repository = auction_repository

    def add_lot(self, lot_input: LotInput, seen_at: str) -> str:
        """Add or update a lot in the database.

        Returns the lot_code of the added/updated lot.
        """
        from troostwatch.services.sync import compute_detail_hash, compute_listing_hash
        from troostwatch.services.sync.sync import _listing_detail_from_card

        card = LotCardData(
            auction_code=lot_input.auction_code,
            lot_code=lot_input.lot_code,
            title=lot_input.title,
            url=lot_input.url or "",
            state=lot_input.state,
            opens_at=lot_input.opens_at,
            closing_time_current=lot_input.closing_time,
            location_city=lot_input.location_city,
            location_country=lot_input.location_country,
            bid_count=lot_input.bid_count,
            price_eur=lot_input.current_bid_eur or lot_input.opening_bid_eur,
            is_price_opening_bid=(
                lot_input.opening_bid_eur is not None
                and (lot_input.current_bid_eur is None or lot_input.opening_bid_eur == lot_input.current_bid_eur)
            ),
        )

        detail = LotDetailData(
            lot_code=lot_input.lot_code,
            title=lot_input.title,
            url=lot_input.url or "",
            state=lot_input.state,
            opens_at=lot_input.opens_at,
            closing_time_current=lot_input.closing_time,
            bid_count=lot_input.bid_count,
            opening_bid_eur=lot_input.opening_bid_eur,
            current_bid_eur=lot_input.current_bid_eur,
            location_city=lot_input.location_city,
            location_country=lot_input.location_country,
        )

        listing_hash = compute_listing_hash(card)
        detail_hash = compute_detail_hash(detail)

        # Upsert auction
        auction_id = self._auction_repository.upsert(
            lot_input.auction_code,
            lot_input.auction_url or lot_input.auction_code,
            lot_input.auction_title,
            pagination_pages=None,
        )

        # If no detail info, fall back to listing-only detail
        if not (
            lot_input.opening_bid_eur
            or lot_input.current_bid_eur
            or lot_input.bid_count
            or lot_input.location_city
            or lot_input.location_country
            or lot_input.url
        ):
            detail = _listing_detail_from_card(card)
            detail_hash = compute_detail_hash(detail)

        # Upsert lot
        self._lot_repository.upsert_from_parsed(
            auction_id,
            card,
            detail,
            listing_hash=listing_hash,
            detail_hash=detail_hash,
            last_seen_at=seen_at,
            detail_last_seen_at=seen_at,
        )

        return lot_input.lot_code
