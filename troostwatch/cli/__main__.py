import click
from .buyer import buyer
from .sync import sync
from .sync_multi import sync_multi

@click.group()
def cli():
    pass

cli.add_command(buyer)
cli.add_command(sync)
cli.add_command(sync_multi)

if __name__ == "__main__":
    cli()