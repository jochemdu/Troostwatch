"""Entry point for running the Troostwatch CLI.

This module defines a top-level Click group that aggregates all subcommands
defined in the ``troostwatch.cli`` package. Executing ``python -m troostwatch.cli``
will invoke this group and present the available commands.
"""

import click

from .buyer import buyer
from .sync import sync
from .sync_multi import sync_multi
from .positions import positions
from .report import report
from .debug import debug
from .view import view
from .bid import bid


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli() -> None:
    """Troostwatch command-line interface."""
    pass


cli.add_command(buyer)
cli.add_command(sync)
cli.add_command(sync_multi)
cli.add_command(positions)
cli.add_command(report)
cli.add_command(debug)
cli.add_command(view)
cli.add_command(bid)


if __name__ == "__main__":
    cli()
