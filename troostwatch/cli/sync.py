"""Synchronization CLI for Troostwatch.

This module defines the ``sync`` subcommand that downloads auction data
from Troostwijk and stores it into a local SQLite database. It wraps the
``sync_auction_to_db`` function from :mod:`troostwatch.sync.sync`.

Example usage::

    python -m troostwatch.cli sync \
        --db troostwatch.db \
        --auction-code A1-39499 \
        --auction-url https://www.troostwijkauctions.com/auction/1234 \
        --max-pages 2

The command will fetch up to two pages of lot listings for auction ``A1-39499``
from the given URL and persist the lots and auction metadata into
``troostwatch.db``.
"""

import click
from ..sync.sync import sync_auction_to_db


@click.command(name="sync")
@click.option(
    "--db",
    "db_path",
    default="troostwatch.db",
    help="Path to the SQLite database file. Will be created if it does not exist.",
    show_default=True,
)
@click.option(
    "--auction-code",
    required=True,
    help="Auction code (e.g. A1-39499) identifying the auction to sync.",
)
@click.option(
    "--auction-url",
    required=True,
    help="URL of the auction listing page on Troostwijk.",
)
@click.option(
    "--max-pages",
    type=int,
    default=None,
    help="Optional maximum number of listing pages to fetch. If omitted, all pages are processed.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="If set, parse pages but do not write any changes to the database.",
)
@click.option(
    "--delay",
    "delay_seconds",
    type=float,
    default=0.5,
    help="Delay in seconds between HTTP requests to avoid hammering the site.",
    show_default=True,
)
def sync(db_path: str, auction_code: str, auction_url: str, max_pages: int | None, dry_run: bool, delay_seconds: float) -> None:
    """Synchronize an auction into a local database.

    This command downloads the auction listing page (and subsequent pages if
    available and not limited by ``--max-pages``) and detail pages for each lot.
    Parsed data are then inserted into or updated in the local SQLite database.

    If ``--dry-run`` is specified, the command parses the pages but skips
    database writes.
    """
    click.echo(
        f"Syncing auction {auction_code} from {auction_url} into {db_path}..."
    )
    try:
        sync_auction_to_db(
            db_path=db_path,
            auction_code=auction_code,
            auction_url=auction_url,
            max_pages=max_pages,
            dry_run=dry_run,
            delay_seconds=delay_seconds,
        )
        click.echo("Sync complete.")
    except Exception as exc:
        click.echo(f"Error during sync: {exc}")