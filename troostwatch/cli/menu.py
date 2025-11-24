"""Interactive central menu for Troostwatch CLI commands.

This module exposes a ``menu`` command that lets users pick from the
available CLI functions and provides guided prompts for the most common
options of each command. It is intended as a friendly entry point for
users who prefer interactive choice lists over long command invocations.
"""

from __future__ import annotations

from typing import Optional

import click

from .bid import bid
from .buyer import buyer
from .debug import debug
from .positions import positions
from .report import report
from .sync import sync
from .sync_multi import sync_multi
from .view import view


def _prompt_optional_str(message: str) -> Optional[str]:
    value = click.prompt(message, default="", show_default=False)
    return value or None


def _prompt_optional_int(message: str, default: Optional[int] = None) -> Optional[int]:
    text_default = "" if default is None else default
    value = click.prompt(message, default=text_default, show_default=default is not None)
    if isinstance(value, str):
        value = value.strip()
        return int(value) if value else None
    return value


def _run_sync(ctx: click.Context) -> None:
    db_path = click.prompt("Database path", default="troostwatch.db")
    auction_code = click.prompt("Auction code (e.g. A1-39499)")
    auction_url = click.prompt("Auction URL")
    max_pages = _prompt_optional_int("Max pages to fetch (blank for all)")
    verbose = click.confirm("Enable verbose logging?", default=False)

    ctx.invoke(
        sync,
        db_path=db_path,
        auction_code=auction_code,
        auction_url=auction_url,
        max_pages=max_pages,
        dry_run=False,
        delay_seconds=0.0,
        max_concurrent_requests=5,
        throttle_per_host=None,
        max_retries=3,
        retry_backoff_base=0.5,
        concurrency_mode="asyncio",
        force_detail_refetch=False,
        verbose=verbose,
        username=None,
        password=None,
        token_path=None,
        base_url="https://www.troostwijkauctions.com",
        login_path="/login",
        session_timeout=30 * 60,
    )


def _run_sync_multi(ctx: click.Context) -> None:
    db_path = click.prompt("Database path", default="troostwatch.db")
    auctions_file = click.prompt("Path to YAML file with auctions")
    max_pages = _prompt_optional_int("Max pages to fetch per auction (blank for all)")
    verbose = click.confirm("Enable verbose logging?", default=False)

    ctx.invoke(
        sync_multi,
        db_path=db_path,
        auctions_file=auctions_file,
        max_pages=max_pages,
        dry_run=False,
        delay_seconds=0.0,
        max_concurrent_requests=5,
        throttle_per_host=None,
        max_retries=3,
        retry_backoff_base=0.5,
        concurrency_mode="asyncio",
        force_detail_refetch=False,
        verbose=verbose,
        username=None,
        password=None,
        token_path=None,
        base_url="https://www.troostwijkauctions.com",
        login_path="/login",
        session_timeout=30 * 60,
    )


def _run_view(ctx: click.Context) -> None:
    db_path = click.prompt("Database path", default="troostwatch.db")
    auction_code = _prompt_optional_str("Auction code filter (blank for all)")
    state = _prompt_optional_str("State filter (blank for all)")
    limit = click.prompt("Maximum lots to show (0 for no limit)", default=50, type=int)
    json_output = click.confirm("Show as JSON?", default=False)

    ctx.invoke(
        view,
        db_path=db_path,
        auction_code=auction_code,
        state=state,
        limit=limit,
        json_output=json_output,
    )


def _run_buyer(ctx: click.Context) -> None:
    db_path = click.prompt("Database path", default="troostwatch.db")
    action = click.prompt(
        "Buyer action",
        type=click.Choice(["list", "add", "delete", "back"], case_sensitive=False),
        show_choices=True,
    ).lower()
    if action == "back":
        return
    if action == "list":
        with click.Context(buyer) as buyer_ctx:
            buyer_ctx.obj = {"db_path": db_path}
            buyer_ctx.invoke(buyer.commands["list"])
        return

    label = click.prompt("Buyer label")
    if action == "add":
        name = _prompt_optional_str("Buyer name (optional)")
        notes = _prompt_optional_str("Notes (optional)")
        with click.Context(buyer) as buyer_ctx:
            buyer_ctx.obj = {"db_path": db_path}
            buyer_ctx.invoke(buyer.commands["add"], label=label, name=name, notes=notes)
    else:
        with click.Context(buyer) as buyer_ctx:
            buyer_ctx.obj = {"db_path": db_path}
            buyer_ctx.invoke(buyer.commands["delete"], label=label)


def _run_positions(ctx: click.Context) -> None:
    db_path = click.prompt("Database path", default="troostwatch.db")
    action = click.prompt(
        "Positions action",
        type=click.Choice(["list", "add", "delete", "back"], case_sensitive=False),
        show_choices=True,
    ).lower()
    if action == "back":
        return
    if action == "list":
        buyer_filter = _prompt_optional_str("Filter by buyer (blank for all)")
        ctx.invoke(positions.commands["list"], db_path=db_path, buyer=buyer_filter)
        return

    buyer_label = click.prompt("Buyer label")
    auction_code = click.prompt("Auction code")
    lot_code = click.prompt("Lot code")
    if action == "add":
        budget = _prompt_optional_int("Budget EUR (blank for none)")
        inactive = click.confirm("Mark as inactive?", default=False)
        ctx.invoke(
            positions.commands["add"],
            db_path=db_path,
            buyer=buyer_label,
            auction_code=auction_code,
            lot_code=lot_code,
            budget=budget,
            inactive=inactive,
        )
    else:
        ctx.invoke(
            positions.commands["delete"],
            db_path=db_path,
            buyer=buyer_label,
            auction_code=auction_code,
            lot_code=lot_code,
        )


def _run_report(ctx: click.Context) -> None:
    db_path = click.prompt("Database path", default="troostwatch.db")
    buyer_label = click.prompt("Buyer label to summarize")
    json_output = click.confirm("Show as JSON?", default=False)
    ctx.invoke(report.commands["buyer"], db_path=db_path, buyer=buyer_label, json_output=json_output)


def _run_bid(ctx: click.Context) -> None:
    db_path = click.prompt("Database path", default="troostwatch.db")
    buyer_label = click.prompt("Buyer label")
    auction_code = click.prompt("Auction code")
    lot_code = click.prompt("Lot code")
    amount = click.prompt("Bid amount (EUR)", type=float)
    note = _prompt_optional_str("Note (optional)")
    quiet = click.confirm("Quiet output?", default=False)

    ctx.invoke(
        bid,
        db_path=db_path,
        buyer_label=buyer_label,
        auction_code=auction_code,
        lot_code=lot_code,
        amount=amount,
        note=note,
        username=None,
        password=None,
        token_path=None,
        base_url="https://www.troostwijkauctions.com",
        api_base_url="https://www.troostwijkauctions.com/api",
        login_path="/login",
        session_timeout=30 * 60,
        quiet=quiet,
    )


def _run_debug(ctx: click.Context) -> None:
    db_path = click.prompt("Database path", default="troostwatch.db")
    action = click.prompt(
        "Debug action",
        type=click.Choice(["stats", "integrity", "view", "back"], case_sensitive=False),
        show_choices=True,
    ).lower()
    if action == "back":
        return
    if action == "view":
        table = click.prompt("Table name")
        limit = click.prompt("Row limit", default=10, type=int)
        with click.Context(debug) as debug_ctx:
            debug_ctx.obj = {"db_path": db_path}
            debug_ctx.invoke(debug.commands["view"], table=table, limit=limit)
        return

    with click.Context(debug) as debug_ctx:
        debug_ctx.obj = {"db_path": db_path}
        debug_ctx.invoke(debug.commands[action])


@click.command()
@click.pass_context
def menu(ctx: click.Context) -> None:
    """Show an interactive menu with choice lists for all commands."""

    choices = {
        "sync": ("Sync a single auction", _run_sync),
        "sync-multi": ("Sync multiple auctions from a YAML file", _run_sync_multi),
        "view": ("View lots stored in the database", _run_view),
        "buyers": ("Manage buyers", _run_buyer),
        "positions": ("Manage tracked positions", _run_positions),
        "report": ("Generate a buyer report", _run_report),
        "bid": ("Place a bid", _run_bid),
        "debug": ("Debug tools", _run_debug),
        "exit": ("Exit the menu", None),
    }

    click.echo("Troostwatch menu (choose a command):")
    while True:
        for key, (label, _) in choices.items():
            if key == "exit":
                click.echo(f"  - {key}: {label}")
            else:
                click.echo(f"  - {key}: {label}")

        selection = click.prompt(
            "Enter choice",
            type=click.Choice(list(choices.keys()), case_sensitive=False),
            show_choices=False,
        ).lower()
        if selection == "exit":
            click.echo("Goodbye!")
            break

        handler = choices[selection][1]
        if handler:
            handler(ctx)

