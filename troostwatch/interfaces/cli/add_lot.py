"""CLI command to manually add or update a lot in the database."""

from __future__ import annotations

import click
from rich.console import Console

from troostwatch.interfaces.cli.context import (
    build_cli_context,
    get_current_timestamp,
    lot_management_service,
)
from troostwatch.services.lots import LotInput

console = Console()


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
    cli_context = build_cli_context(db_path)

    lot_input = LotInput(
        auction_code=auction_code,
        lot_code=lot_code,
        title=title,
        url=lot_url,
        state=normalized_state,
        opens_at=opens_at,
        closing_time=closing_time,
        bid_count=bid_count,
        opening_bid_eur=opening_bid,
        current_bid_eur=current_bid,
        location_city=city,
        location_country=country,
        auction_title=auction_title,
        auction_url=auction_url,
    )

    seen_at = get_current_timestamp()

    with lot_management_service(cli_context) as service:
        service.add_lot(lot_input, seen_at)

    console.print(f"[green]Stored lot {lot_code} for auction {auction_code} in {db_path}[/green]")
