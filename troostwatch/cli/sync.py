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
from troostwatch.infrastructure.db import ensure_schema, get_connection
from troostwatch.infrastructure.db.repositories import AuctionRepository, PreferenceRepository
from .auth import build_http_client
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
    required=False,
    help="Auction code (e.g. A1-39499) identifying the auction to sync. When omitted and auctions exist in the DB, you will be prompted to choose.",
)
@click.option(
    "--auction-url",
    required=False,
    help="URL of the auction listing page on Troostwijk. When omitted, it is taken from the selected auction if available.",
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
    default=0.0,
    help="Legacy delay between HTTP requests; superseded by --throttle-per-host.",
    show_default=True,
)
@click.option(
    "--max-concurrent-requests",
    type=int,
    default=5,
    show_default=True,
    help="Maximum simultaneous HTTP requests when fetching lot details.",
)
@click.option(
    "--throttle-per-host",
    type=float,
    default=None,
    help="Requests per second allowed per host. Overrides --delay when provided.",
)
@click.option(
    "--max-retries",
    type=int,
    default=3,
    show_default=True,
    help="Retry attempts for failed HTTP requests.",
)
@click.option(
    "--retry-backoff-base",
    type=float,
    default=0.5,
    show_default=True,
    help="Base delay (seconds) used for exponential backoff between retries.",
)
@click.option(
    "--concurrency-mode",
    type=click.Choice(["asyncio", "threadpool"], case_sensitive=False),
    default="asyncio",
    show_default=True,
    help="Concurrency backend used for HTTP requests.",
)
@click.option(
    "--force-detail-refetch/--skip-unchanged-details",
    default=False,
    help="Always refetch detail pages even when listing hashes are unchanged.",
)
@click.option(
    "--verbose/--no-verbose",
    default=True,
    show_default=True,
    help="Enable verbose logging during the sync run.",
)
@click.option(
    "--log-path",
    type=click.Path(path_type=str),
    help="Optional path to write verbose sync logs.",
)
@click.option(
    "--username",
    help="Account username/email for authenticated requests.",
)
@click.option(
    "--password",
    help="Account password for authenticated requests (prompted if omitted).",
)
@click.option(
    "--token-path",
    type=click.Path(path_type=str),
    help="Optional path to reuse/persist session tokens.",
)
@click.option(
    "--base-url",
    default="https://www.troostwijkauctions.com",
    show_default=True,
    help="Base URL for authenticated requests.",
)
@click.option(
    "--login-path",
    default="/login",
    show_default=True,
    help="Relative login path used to obtain session cookies/CSRF.",
)
@click.option(
    "--session-timeout",
    type=float,
    default=30 * 60,
    show_default=True,
    help="Seconds before an in-memory session is considered expired.",
)
def sync(
    db_path: str,
    auction_code: str | None,
    auction_url: str | None,
    max_pages: int | None,
    dry_run: bool,
    delay_seconds: float,
    max_concurrent_requests: int,
    throttle_per_host: float | None,
    max_retries: int,
    retry_backoff_base: float,
    concurrency_mode: str,
    force_detail_refetch: bool,
    verbose: bool,
    log_path: str | None,
    username: str | None,
    password: str | None,
    token_path: str | None,
    base_url: str,
    login_path: str,
    session_timeout: float,
) -> None:
    """Synchronize an auction into a local database.

    This command downloads the auction listing page (and subsequent pages if
    available and not limited by ``--max-pages``) and detail pages for each lot.
    Parsed data are then inserted into or updated in the local SQLite database.

    If ``--dry-run`` is specified, the command parses the pages but skips
    database writes.
    """
    from ..db import get_connection, get_preference, list_auctions

    resolved_code = auction_code
    resolved_url = auction_url

    if not resolved_code or not resolved_url:
        preferred_code = None
        with get_connection(db_path) as conn:
            ensure_schema(conn)
            repo = AuctionRepository(conn)
            available = repo.list(only_active=False)
            preferred_code = PreferenceRepository(conn).get("preferred_auction")

        if available and not resolved_code:
            click.echo("Select an auction to sync:")
            default_index = 0
            for idx, auction in enumerate(available, start=1):
                title = auction.get("title") or "(geen titel)"
                url = auction.get("url") or "(geen url bekend)"
                click.echo(f"{idx}) {auction['auction_code']} - {title} - {url}")
                if auction.get("auction_code") == preferred_code:
                    default_index = idx - 1
            default_choice_num = default_index + 1
            click.echo(
                "Standaard keuze: "
                f"{default_choice_num}) {available[default_index]['auction_code']}"
            )
            choice = click.prompt(
                "Keuze",
                type=click.IntRange(1, len(available)),
                show_choices=False,
                default=default_choice_num,
                show_default=True,
            )
            selected = available[choice - 1]
            resolved_code = selected.get("auction_code") or resolved_code
            resolved_url = selected.get("url") or resolved_url

        if available and resolved_code and not resolved_url:
            match = next(
                (a for a in available if a.get("auction_code") == resolved_code), None
            )
            if match:
                resolved_url = match.get("url") or resolved_url

    if not resolved_code:
        click.echo("Auction code ontbreekt; geef --auction-code op of kies een bestaande.")
        return

    if not resolved_url:
        resolved_url = click.prompt("Auction URL")

    click.echo(
        f"Syncing auction {resolved_code} from {resolved_url} into {db_path}..."
    )
    if username and not password and token_path is None:
        password = click.prompt("Troostwijk password", hide_input=True)

    http_client = build_http_client(
        base_url=base_url,
        login_path=login_path,
        username=username,
        password=password,
        token_path=token_path,
        session_timeout=session_timeout,
    )

    if http_client is not None:
        try:
            http_client.authenticate()
        except Exception as exc:
            click.echo(f"Authentication failed: {exc}")
            return

    try:
        result = sync_auction_to_db(
            db_path=db_path,
            auction_code=resolved_code,
            auction_url=resolved_url,
            max_pages=max_pages,
            dry_run=dry_run,
            delay_seconds=delay_seconds,
            max_concurrent_requests=max_concurrent_requests,
            throttle_per_host=throttle_per_host,
            max_retries=max_retries,
            retry_backoff_base=retry_backoff_base,
            concurrency_mode=concurrency_mode.lower(),
            force_detail_refetch=force_detail_refetch,
            verbose=verbose,
            log_path=log_path,
            http_client=http_client,
        )
    except Exception as exc:
        click.echo(f"Error during sync: {exc}")
        return

    click.echo(
        f"Sync {result.status} (run #{result.run_id}): pages={result.pages_scanned}, "
        f"lots scanned={result.lots_scanned}, lots updated={result.lots_updated}, errors={result.error_count}"
    )
    if result.errors:
        click.echo("Errors:")
        for err in result.errors:
            click.echo(f"  - {err}")