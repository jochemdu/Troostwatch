"""Synchronization CLI for Troostwatch.

This module defines the `sync` subcommand that downloads auction data
from Troostwijk and stores it into a local SQLite database.

Currently, this is only a placeholder implementation. In the future, it should
implement the logic described in the project roadmap.
"""

import click


@click.command()
def sync() -> None:
    """Placeholder sync command."""
    click.echo("Sync functionality is not yet implemented.")