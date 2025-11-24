"""CLI command to manually add or update a lot in the database."""

from __future__ import annotations

import click

from troostwatch.infrastructure.db import ensure_core_schema, ensure_schema, get_connection, iso_utcnow
from troostwatch.infrastructure.db.repositories import AuctionRepository, LotRepository
from troostwatch.parsers.lot_card import LotCardData
from troostwatch.parsers.lot_detail import LotDetailData
from troostwatch.sync.sync import _listing_detail_from_card, compute_detail_hash, compute_listing_hash


@click.command()
@click.option("--db", "db_path", default="troostwatch.db", help="Path to the SQLite database file.")
@click.option("--auction-code", required=True, help="Auction code for the lot (e.g. A1-12345).")
@click.option("--auction-title", help="Optional auction title to store or update.")
@click.option("--auction-url", help="Optional auction URL to store or update.")
@click.option("--lot-code", required=True, help="The lot code (e.g. A1-12345-1).")
@click.option("--title", required=True, help="Lot title.")
@click.option("--url", "lot_url", help="Lot detail URL.")
@click.option("--state", type=click.Choice(["running", "scheduled", "closed", ""], case_sensitive=False), default="", show_default=False, help="Lot state.")
@click.option("--opens-at", help="Opening timestamp (ISO format).")
@click.option("--closing-time", help="Closing timestamp (ISO format).")
@click.option("--bid-count", type=int, help="Number of bids.")
@click.option("--opening-bid", type=float, help="Opening bid in EUR.")
@click.option("--current-bid", type=float, help="Current bid in EUR.")
@click.option("--city", help="Location city.")
@click.option("--country", help="Location country.")
def add_lot(
    db_path: str,
    auction_code: str,
    auction_title: str | None,
    auction_url: str | None,
    lot_code: str,
    title: str,
    lot_url: str | None,
    state: str,
    opens_at: str | None,
    closing_time: str | None,
    bid_count: int | None,
    opening_bid: float | None,
    current_bid: float | None,
    city: str | None,
    country: str | None,
) -> None:
    """Manually insert or update a lot in the configured database."""

    normalized_state = state or None

    card = LotCardData(
        auction_code=auction_code,
        lot_code=lot_code,
        title=title,
        url=lot_url or "",
        state=normalized_state,
        opens_at=opens_at,
        closing_time_current=closing_time,
        location_city=city,
        location_country=country,
        bid_count=bid_count,
        price_eur=current_bid or opening_bid,
        is_price_opening_bid=opening_bid is not None and (current_bid is None or opening_bid == current_bid),
    )

    detail = LotDetailData(
        lot_code=lot_code,
        title=title,
        url=lot_url or "",
        state=normalized_state,
        opens_at=opens_at,
        closing_time_current=closing_time,
        bid_count=bid_count,
        opening_bid_eur=opening_bid,
        current_bid_eur=current_bid,
        location_city=city,
        location_country=country,
    )

    listing_hash = compute_listing_hash(card)
    detail_hash = compute_detail_hash(detail)
    seen_at = iso_utcnow()

    with get_connection(db_path) as conn:
        ensure_core_schema(conn)
        ensure_schema(conn)
        auction_repo = AuctionRepository(conn)
        lot_repo = LotRepository(conn)

        auction_id = auction_repo.upsert(
            auction_code,
            auction_url or auction_code,
            auction_title,
            pagination_pages=None,
        )

        # If there is no detail info at all, fall back to listing-only detail so the lot still persists.
        if not (opening_bid or current_bid or bid_count or city or country or lot_url):
            detail = _listing_detail_from_card(card)
            detail_hash = compute_detail_hash(detail)

        lot_repo.upsert_from_parsed(
            auction_id,
            card,
            detail,
            listing_hash=listing_hash,
            detail_hash=detail_hash,
            last_seen_at=seen_at,
            detail_last_seen_at=seen_at,
        )
        conn.commit()

    click.echo(f"Stored lot {lot_code} for auction {auction_code} in {db_path}")

