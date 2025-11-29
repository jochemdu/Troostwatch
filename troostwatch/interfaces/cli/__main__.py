"""Entry point for running the Troostwatch CLI.

This module defines a top-level Click group that aggregates all subcommands
defined in the ``troostwatch.interfaces.cli`` package. Executing
``python -m troostwatch.interfaces.cli`` will invoke this group and present the
available commands. The legacy ``troostwatch.cli`` namespace remains available
for compatibility but will be removed in a future release.
"""

import click

from .add_lot import add_lot
from .bid import bid
from .buyer import buyer
from .debug import debug
from .images import images_cli
from .menu import menu
from .positions import positions
from .report import report
from .sync import sync
from .sync_multi import sync_multi
from .view import view


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=True,
)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Troostwatch command-line interface."""
    if ctx.invoked_subcommand is None:
        click.echo(
            "Launching interactive menu (use --help to see all commands).\n")
        ctx.invoke(menu)


cli.add_command(buyer)
cli.add_command(sync)
cli.add_command(sync_multi)
cli.add_command(positions)
cli.add_command(report)
cli.add_command(debug)
cli.add_command(view)
cli.add_command(bid)
cli.add_command(add_lot)
cli.add_command(menu)
cli.add_command(images_cli, name="images")


if __name__ == "__main__":
    cli()
