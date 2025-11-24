"""Text viewer for auctions and lots stored in the database."""

from __future__ import annotations

import json
from typing import Optional

import click

from troostwatch.infrastructure.db import ensure_schema, get_connection
from troostwatch.infrastructure.db.repositories import LotRepository


@click.command()
@click.option("--db", "db_path", required=True, help="Path to the SQLite database.")
@click.option("--auction-code", default=None, help="Filter lots to a specific auction code.")
@click.option("--state", default=None, help="Filter lots by state (e.g. open, closed).")
@click.option(
    "--limit",
    type=int,
    default=50,
    show_default=True,
    help="Maximum number of lots to display (0 for no limit).",
)
@click.option("--json-output", is_flag=True, help="Output the results as JSON.")
def view(
    db_path: str,
    auction_code: Optional[str],
    state: Optional[str],
    limit: Optional[int],
    json_output: bool,
) -> None:
    """Show lots stored in the Troostwatch database."""

    effective_limit = None if limit is not None and limit <= 0 else limit
    with get_connection(db_path) as conn:
        ensure_schema(conn)
        lots = LotRepository(conn).list_lots(
            auction_code=auction_code,
            state=state,
            limit=effective_limit,
        )

    if json_output:
        click.echo(json.dumps(lots, indent=2))
        return

    if not lots:
        click.echo("No lots found with the provided filters.")
        return

    click.echo(f"Showing {len(lots)} lot(s):")
    for lot in lots:
        current_bid = lot["current_bid_eur"]
        bid_str = f"€{current_bid:.2f}" if current_bid is not None else "n/a"
        bids = lot.get("bid_count") or 0
        closing = lot.get("closing_time_current") or lot.get("closing_time_original") or "-"
        bidder = lot.get("current_bidder_label")
        bidder_suffix = f" | bidder={bidder}" if bidder else ""
        click.echo(
            f"- [{lot['auction_code']}/{lot['lot_code']}] {lot.get('title') or '(no title)'} "
            f"| state={lot.get('state') or '?'} | current={bid_str} ({bids} bids) | closes={closing}{bidder_suffix}"
        )
