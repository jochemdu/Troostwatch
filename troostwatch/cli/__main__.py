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
from .menu import menu
from .bid import bid


@click.group(context_settings={"help_option_names": ["-h", "--help"]}, invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Troostwatch command-line interface."""
    if ctx.invoked_subcommand is None:
        click.echo("Launching interactive menu (use --help to see all commands).\n")
        ctx.invoke(menu)


cli.add_command(buyer)
cli.add_command(sync)
cli.add_command(sync_multi)
cli.add_command(positions)
cli.add_command(report)
cli.add_command(debug)
cli.add_command(view)
cli.add_command(bid)
cli.add_command(menu)


if __name__ == "__main__":
    cli()
