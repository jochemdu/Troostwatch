"""Live viewer CLI for Troostwatch.

This module defines the `view` subcommand that provides a live text-based dashboard
of tracked lots, winnings and exposure.

Currently, this is only a placeholder implementation. Actual functionality
should populate this function with logic to query the SQLite database and render
the results.
"""

import click


@click.command()
def view() -> None:
    """Placeholder for the live viewer. Prints a stub message."""
    click.echo("Live view is not yet implemented.")