"""Buyer management CLI for Troostwatch.

Provides commands to add, list and remove buyers from the local database.
"""

from __future__ import annotations

import asyncio

import click
from rich.console import Console
from rich.table import Table

from troostwatch.interfaces.cli.context import (CLIContext, build_cli_context,
                                                buyer_service)
from troostwatch.services.buyers import BuyerAlreadyExistsError

console = Console()
DEFAULT_CLI_CONTEXT = build_cli_context()


@click.group()
@click.option(
    "--db",
    "db_path",
    default=None,
    show_default=str(DEFAULT_CLI_CONTEXT.db_path),
    help="Path to the SQLite database.",
)
@click.pass_context
def buyer(ctx: click.Context, db_path: str | None) -> None:
    """Manage buyers stored in the database."""

    ctx.ensure_object(dict)
    ctx.obj["cli_context"] = (
        DEFAULT_CLI_CONTEXT if db_path is None else build_cli_context(db_path)
    )


@buyer.command("add")
@click.argument("label")
@click.option("--name", default=None, help="Full name of the buyer.")
@click.option("--notes", default=None, help="Additional notes for the buyer.")
@click.pass_context
def add_cmd(
    ctx: click.Context, label: str, name: str | None, notes: str | None
) -> None:
    """Add a new buyer with a unique LABEL."""

    cli_context: CLIContext = ctx.obj["cli_context"]
    with buyer_service(cli_context) as service:
        try:
            asyncio.run(service.create_buyer(label=label, name=name, notes=notes))
        except BuyerAlreadyExistsError:
            console.print(f"[red]Buyer with label '{label}' already exists.[/red]")
            ctx.exit(1)

    console.print(f"[green]Added buyer [bold]{label}[/bold]")


@buyer.command("list")
@click.pass_context
def list_cmd(ctx: click.Context) -> None:
    """List all buyers."""

    cli_context: CLIContext = ctx.obj["cli_context"]
    with buyer_service(cli_context) as service:
        buyers = service.list_buyers()

    if not buyers:
        console.print("[yellow]No buyers found.[/yellow]")
        return

    table = Table(title="Buyers")
    table.add_column("Label", style="bold")
    table.add_column("Name")
    table.add_column("Notes")
    for buyer_item in buyers:
        table.add_row(buyer_item.label, buyer_item.name or "", buyer_item.notes or "")
    console.print(table)


@buyer.command("delete")
@click.argument("label")
@click.pass_context
def delete_cmd(ctx: click.Context, label: str) -> None:
    """Delete a buyer by LABEL."""

    cli_context: CLIContext = ctx.obj["cli_context"]
    with buyer_service(cli_context) as service:
        asyncio.run(service.delete_buyer(label=label))
    console.print(f"[green]Deleted buyer [bold]{label}[/bold]")
