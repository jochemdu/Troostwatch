"""Debug Click group for inspecting the Troostwatch database.

This module implements a ``debug`` Click group containing various helper
commands for inspecting the state of a Troostwatch SQLite database. Use
``python -m troostwatch.interfaces.cli debug`` to see the available
subcommands.

Available subcommands:

- ``stats`` – show row counts per table.
- ``integrity`` – run the SQLite integrity check.
- ``view`` – print a limited set of rows from a given table.

More commands can be added here in the future as needed.
"""

from __future__ import annotations

import click
from rich.console import Console

from troostwatch.infrastructure.diagnostics.debug_tools import (
    db_integrity,
    db_stats,
    db_view,
)
from troostwatch.interfaces.cli.context import build_cli_context

console = Console()


@click.group()
@click.option(
    "--db",
    "db_path",
    default="troostwatch.db",
    help="Path to the SQLite database file to inspect.",
    show_default=True,
)
@click.pass_context
def debug(ctx: click.Context, db_path: str) -> None:
    """Debugging tools for Troostwatch.

    This command groups together several utilities for inspecting the
    local database. Use the subcommands to view table counts, run the
    integrity checker or inspect specific tables.
    """
    ctx.obj = {"db_path": db_path}


@debug.command(name="stats")
@click.pass_context
def stats_cmd(ctx: click.Context) -> None:
    """Show row counts for all tables in the database."""
    db_path = ctx.obj["db_path"]
    cli_context = build_cli_context(db_path)
    with cli_context.connect() as conn:
        for entry in db_stats(conn):
            console.print(f"{entry['table']}: {entry['rows']}")


@debug.command(name="integrity")
@click.pass_context
def integrity_cmd(ctx: click.Context) -> None:
    """Run the SQLite integrity check and report problems."""
    db_path = ctx.obj["db_path"]
    cli_context = build_cli_context(db_path)
    with cli_context.connect() as conn:
        results = db_integrity(conn)
        for line in results:
            console.print(line)


@debug.command(name="view")
@click.argument("table")
@click.option(
    "--limit",
    default=10,
    show_default=True,
    help="Maximum number of rows to display from the table.",
)
@click.pass_context
def view_cmd(ctx: click.Context, table: str, limit: int) -> None:
    """Print up to ``limit`` rows from a specified table.

    Example::

        python -m troostwatch.interfaces.cli debug view buyers
    """
    db_path = ctx.obj["db_path"]
    cli_context = build_cli_context(db_path)
    with cli_context.connect() as conn:
        try:
            rows = db_view(conn, table, limit)
        except ValueError as exc:
            console.print(f"[red]{exc}[/red]")
            return
        if not rows:
            console.print(f"[yellow](No rows in table {table})[/yellow]")
            return
        # Print header
        headers = list(rows[0].keys())
        console.print("\t".join(headers))
        for row in rows:
            console.print(
                "\t".join(str(row[h]) if row[h] is not None else "" for h in headers)
            )
