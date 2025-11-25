"""Buyer management CLI for Troostwatch.

Provides commands to add, list and remove buyers from the local database.
"""

from __future__ import annotations

import click

from troostwatch.infrastructure.db import ensure_schema, get_connection
from troostwatch.infrastructure.db.repositories import BuyerRepository
from troostwatch.infrastructure.db.repositories.buyers import DuplicateBuyerError


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
        ensure_schema(conn)
        repo = BuyerRepository(conn)
        try:
            repo.add(label, name, notes)
        except DuplicateBuyerError:
            click.echo(f"Buyer with label '{label}' already exists.", err=True)
            ctx.exit(1)
    click.echo(f"Added buyer {label}")


@buyer.command("list")
@click.pass_context
def list_cmd(ctx: click.Context) -> None:
    """List all buyers."""
    db_path = ctx.obj["db_path"]
    with get_connection(db_path) as conn:
        ensure_schema(conn)
        buyers = BuyerRepository(conn).list()
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
        ensure_schema(conn)
        BuyerRepository(conn).delete(label)
    click.echo(f"Deleted buyer {label}")
