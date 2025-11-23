"""Buyer management CLI for Troostwatch.

Provides commands to add, list and remove buyers from the local database.
"""

from __future__ import annotations

import click

from ..db import get_connection, add_buyer, list_buyers, delete_buyer


@click.group()
@click.option(
    "--db", "db_path", default="troostwatch.db", show_default=True, help="Path to the SQLite database."
)
@click.pass_context
def buyer(ctx: click.Context, db_path: str) -> None:
    """Manage buyers stored in the database."""
    ctx.ensure_object(dict)
    ctx.obj["db_path"] = db_path


@buyer.command("add")
@click.argument("label")
@click.option("--name", default=None, help="Full name of the buyer.")
@click.option("--notes", default=None, help="Additional notes for the buyer.")
@click.pass_context
def add_cmd(ctx: click.Context, label: str, name: str | None, notes: str | None) -> None:
    """Add a new buyer with a unique LABEL."""
    db_path = ctx.obj["db_path"]
    with get_connection(db_path) as conn:
        add_buyer(conn, label, name, notes)
    click.echo(f"Added buyer {label}")


@buyer.command("list")
@click.pass_context
def list_cmd(ctx: click.Context) -> None:
    """List all buyers."""
    db_path = ctx.obj["db_path"]
    with get_connection(db_path) as conn:
        buyers = list_buyers(conn)
    if not buyers:
        click.echo("No buyers found.")
    else:
        for buyer in buyers:
            click.echo(f"{buyer['label']}: {buyer.get('name') or ''}")


@buyer.command("delete")
@click.argument("label")
@click.pass_context
def delete_cmd(ctx: click.Context, label: str) -> None:
    """Delete a buyer by LABEL."""
    db_path = ctx.obj["db_path"]
    with get_connection(db_path) as conn:
        delete_buyer(conn, label)
    click.echo(f"Deleted buyer {label}")