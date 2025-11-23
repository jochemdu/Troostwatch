"""Multi‑auction synchronization CLI for Troostwatch.

This module defines the ``sync-multi`` subcommand, which reads a YAML file
containing a list of auctions to synchronize and iterates over them, calling
``sync_auction_to_db`` for each. The YAML file should have the following
structure::

    auctions:
      - code: A1-39499
        url: "https://www.troostwijkauctions.com/a/123"
      - code: B2-12345
        url: "https://www.troostwijkauctions.com/a/456"

Only the ``code`` and ``url`` fields are required for each auction entry.
Additional keys are ignored.
"""

from __future__ import annotations

import click
import yaml

from ..sync.sync import sync_auction_to_db


@click.command(name="sync-multi")
@click.option(
    "--db",
    "db_path",
    default="troostwatch.db",
    help="Path to the SQLite database file. Will be created if it does not exist.",
    show_default=True,
)
@click.option(
    "--auctions-file",
    required=True,
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Path to a YAML file describing auctions to sync.",
)
@click.option(
    "--max-pages",
    type=int,
    default=None,
    help="Optional maximum number of listing pages to fetch per auction.",
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
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Enable verbose logging for each auction sync run.",
)
def sync_multi(
    db_path: str,
    auctions_file: str,
    max_pages: int | None,
    dry_run: bool,
    delay_seconds: float,
    verbose: bool,
) -> None:
    """Synchronize multiple auctions defined in a YAML file.

    The YAML file must contain a top‑level ``auctions`` list with objects
    containing at least ``code`` and ``url`` fields. Each auction is synced in
    the order specified. Errors in one auction will be reported but will not
    prevent subsequent auctions from being processed.
    """
    click.echo(f"Loading auctions list from {auctions_file}...")
    # Read YAML file
    try:
        with open(auctions_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except Exception as exc:
        click.echo(f"Failed to read YAML file: {exc}")
        return
    auctions = data.get("auctions") if isinstance(data, dict) else None
    if not auctions or not isinstance(auctions, list):
        click.echo("The YAML file must define a list under the 'auctions' key.")
        return
    for entry in auctions:
        code = entry.get("code")
        url = entry.get("url")
        if not code or not url:
            click.echo(f"Skipping entry without 'code' or 'url': {entry}")
            continue
        click.echo(f"\n→ Syncing auction {code} from {url}...")
        try:
            result = sync_auction_to_db(
                db_path=db_path,
                auction_code=code,
                auction_url=url,
                max_pages=max_pages,
                dry_run=dry_run,
                delay_seconds=delay_seconds,
                verbose=verbose,
            )
            click.echo(
                f"✓ Finished syncing auction {code}: pages={result.pages_scanned}, "
                f"lots scanned={result.lots_scanned}, lots updated={result.lots_updated}, errors={result.error_count}"
            )
            if result.errors:
                for err in result.errors:
                    click.echo(f"    - {err}")
        except Exception as exc:
            click.echo(f"✗ Error syncing auction {code}: {exc}")
    click.echo("\nAll auctions processed.")