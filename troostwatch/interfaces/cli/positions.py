"""CLI commands for managing lot positions.

This module defines a ``positions`` Click group with subcommands to add,
list and delete tracked positions. A position represents a buyer who is
tracking a specific lot in a specific auction, with an optional maximum
budget. Positions are stored in the ``my_lot_positions`` table.
"""

from __future__ import annotations

import click

from troostwatch.services.positions import PositionsService


@click.group()
def positions() -> None:
    """Manage tracked lot positions."""
    pass


@positions.command()
@click.option("--db", "db_path", required=True, help="Path to the SQLite database.")
@click.argument("buyer")
@click.argument("auction_code")
@click.argument("lot_code")
@click.option("--budget", type=float, default=None, help="Maximum total budget in EUR.")
@click.option(
    "--inactive", is_flag=True, help="Mark the position as inactive (not tracked)."
)
def add(
    db_path: str,
    buyer: str,
    auction_code: str,
    lot_code: str,
    budget: float | None,
    inactive: bool,
) -> None:
    """Add or update a tracked position for BUYER on AUCTION_CODE/LOT_CODE.

    If a position already exists for the buyer and lot, this command updates
    the tracking flag and budget fields. Use ``--inactive`` to mark the
    position as not tracked. Use ``--budget`` to set a maximum budget.
    """
    track_active = not inactive
    service = PositionsService.from_sqlite_path(db_path)
    try:
        service.add_position(
            buyer_label=buyer,
            lot_code=lot_code,
            auction_code=auction_code,
            track_active=track_active,
            max_budget_total_eur=budget,
        )
    except ValueError as exc:
        click.echo(str(exc))
        return
    status = "inactive" if not track_active else "active"
    click.echo(f"Position for {buyer} on {auction_code}/{lot_code} set to {status}.")


@positions.command(name="list")
@click.option("--db", "db_path", required=True, help="Path to the SQLite database.")
@click.option("--buyer", default=None, help="Only list positions for this buyer.")
def list_positions_cmd(db_path: str, buyer: str | None) -> None:
    """List tracked positions.

    Without arguments, lists all positions for all buyers. Use the
    ``--buyer`` option to filter by buyer label.
    """
    positions = PositionsService.from_sqlite_path(db_path).list_positions(
        buyer_label=buyer
    )
    if not positions:
        click.echo("No positions found.")
        return
    for pos in positions:
        active = "active" if pos.track_active else "inactive"
        budget = pos.max_budget_total_eur
        budget_str = f"budget €{budget:.2f}" if budget is not None else "no budget"
        click.echo(
            f"{pos.buyer_label} – {pos.auction_code}/{pos.lot_code} "
            f"({active}, {budget_str}, current €{pos.current_bid_eur or 0:.2f})"
        )


@positions.command()
@click.option("--db", "db_path", required=True, help="Path to the SQLite database.")
@click.argument("buyer")
@click.argument("auction_code")
@click.argument("lot_code")
def delete(db_path: str, buyer: str, auction_code: str, lot_code: str) -> None:
    """Delete a tracked position for BUYER on AUCTION_CODE/LOT_CODE."""
    service = PositionsService.from_sqlite_path(db_path)
    try:
        service.delete_position(
            buyer_label=buyer, lot_code=lot_code, auction_code=auction_code
        )
    except ValueError as exc:
        click.echo(str(exc))
        return
    click.echo(f"Removed position for {buyer} on {auction_code}/{lot_code}.")
