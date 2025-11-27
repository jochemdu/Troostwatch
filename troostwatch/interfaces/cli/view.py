"""Text viewer for auctions and lots stored in the database."""

from __future__ import annotations

import json

import click
from rich.console import Console

from troostwatch.interfaces.cli.context import (
    CLIContext,
    build_cli_context,
    lot_view_service,
)
from troostwatch.services.lots import LotView

console = Console()
DEFAULT_CLI_CONTEXT = build_cli_context()


def _get_cli_context(db_path: str | None) -> CLIContext:
    return DEFAULT_CLI_CONTEXT if db_path is None else build_cli_context(db_path)


def _format_lot_line(lot: LotView) -> str:
    current_bid = lot.current_bid_eur
    bid_str = f"€{current_bid:.2f}" if current_bid is not None else "n/a"
    bids = lot.bid_count or 0
    closing = lot.closing_time_current or lot.closing_time_original or "-"
    bidder_suffix = (
        f" | bidder={lot.current_bidder_label}" if lot.current_bidder_label else ""
    )
    title = lot.title or "(no title)"
    state = lot.state or "?"
    return (
        f"- [{lot.auction_code}/{lot.lot_code}] {title} "
        f"| state={state} | current={bid_str} ({bids} bids) | closes={closing}{bidder_suffix}"
    )


@click.command()
@click.option(
    "--db",
    "db_path",
    default=None,
    show_default=str(DEFAULT_CLI_CONTEXT.db_path),
    help="Path to the SQLite database.",
)
@click.option(
    "--auction-code", default=None, help="Filter lots to a specific auction code."
)
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
    db_path: str | None,
    auction_code: str | None,
    state: str | None,
    limit: int | None,
    json_output: bool,
) -> None:
    """Show lots stored in the Troostwatch database."""

    cli_context = _get_cli_context(db_path)
    with lot_view_service(cli_context) as service:
        lots = service.list_lots(
            auction_code=auction_code,
            state=state,
            limit=limit,
        )

    if json_output:
        payload = [lot.model_dump(mode="json") for lot in lots]
        console.print(json.dumps(payload, indent=2))
        return

    if not lots:
        console.print("[yellow]No lots found with the provided filters.[/yellow]")
        return

    console.print(f"Showing {len(lots)} lot(s):")
    for lot in lots:
        console.print(_format_lot_line(lot))
