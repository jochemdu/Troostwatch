"""Service helpers for viewing, filtering, and managing lots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Mapping, Optional

from pydantic import BaseModel, Field

from troostwatch.domain.models import Lot
from troostwatch.infrastructure.db.repositories import AuctionRepository, LotRepository
from troostwatch.infrastructure.observability import get_logger
from troostwatch.infrastructure.web.parsers import LotCardData, LotDetailData
from troostwatch.services.dto import LotInputDTO


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
    brand: Optional[str] = Field(default=None, description="Brand/manufacturer of the lot item.")
    is_active: bool = False
    effective_price: Optional[float] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> "LotView":
        """Create a LotView from a database record."""
        # Use domain model for business logic
        lot = Lot.from_dict(dict(record))

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
            "brand": record.get("brand"),
            "is_active": lot.is_active,
            "effective_price": lot.effective_price,
        })

    @classmethod
    def from_domain(cls, lot: Lot) -> "LotView":
        """Create a LotView from a domain Lot model."""
        return cls.model_validate({
            "auction_code": lot.auction_code,
            "lot_code": lot.lot_code,
            "title": lot.title,
            "state": lot.state.value,
            "current_bid_eur": lot.current_bid_eur,
            "bid_count": lot.bid_count,
            "current_bidder_label": lot.current_bidder_label,
            "closing_time_current": lot.closing_time_current.isoformat() if lot.closing_time_current else None,
            "closing_time_original": lot.closing_time_original.isoformat() if lot.closing_time_original else None,
            "is_active": lot.is_active,
            "effective_price": lot.effective_price,
        })


class LotViewService:
    """Service exposing read-only lot views for APIs and CLIs.

    Uses repository injection pattern - caller manages connection lifecycle.
    """

    def __init__(self, lot_repository: LotRepository) -> None:
        self._lot_repository = lot_repository
        self._logger = get_logger(__name__)

    def list_lots(
        self,
        *,
        auction_code: Optional[str] = None,
        state: Optional[str] = None,
        brand: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[LotView]:
        """List lots as LotView DTOs for presentation."""
        self._logger.debug(
            "Listing lots: auction=%s state=%s brand=%s limit=%s",
            auction_code, state, brand, limit
        )
        effective_limit = None if limit is not None and limit <= 0 else limit
        rows = self._lot_repository.list_lots(
            auction_code=auction_code,
            state=state,
            brand=brand,
            limit=effective_limit,
        )
        result = self._to_dtos(rows)
        self._logger.debug("Found %d lots", len(result))
        return result

    def list_domain_lots(
        self,
        *,
        auction_code: Optional[str] = None,
        state: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Lot]:
        """List lots as domain models for business logic."""
        effective_limit = None if limit is not None and limit <= 0 else limit
        rows = self._lot_repository.list_lots(
            auction_code=auction_code,
            state=state,
            limit=effective_limit,
        )
        return [Lot.from_dict(row) for row in rows]

    def get_active_lots(
        self,
        *,
        auction_code: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Lot]:
        """Get only active (running or scheduled) lots as domain models."""
        lots = self.list_domain_lots(auction_code=auction_code, limit=limit)
        return [lot for lot in lots if lot.is_active]

    def _to_dtos(self, rows: Iterable[Mapping[str, object]]) -> List[LotView]:
        return [LotView.from_record(row) for row in rows]


# Alias for backwards compatibility - prefer LotInputDTO in new code
LotInput = LotInputDTO


class LotManagementService:
    """Service for adding and updating lots using DTOs.

    Uses repository injection pattern - caller manages connection lifecycle.
    """

    def __init__(
        self,
        lot_repository: LotRepository,
        auction_repository: AuctionRepository,
    ) -> None:
        self._lot_repository = lot_repository
        self._auction_repository = auction_repository
        self._logger = get_logger(__name__)

    def add_lot(self, lot_input: LotInputDTO, seen_at: str) -> str:
        """Add or update a lot in the database.

        Returns the lot_code of the added/updated lot.
        """
        self._logger.debug(
            "Adding lot %s in auction %s",
            lot_input.lot_code, lot_input.auction_code
        )
        from troostwatch.services.sync import (
            _listing_detail_from_card,
            compute_detail_hash,
            compute_listing_hash,
        )

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

        self._logger.debug("Lot %s added/updated successfully", lot_input.lot_code)
        return lot_input.lot_code
