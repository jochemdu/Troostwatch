"""Multi‑auction synchronization CLI for Troostwatch.

This module defines the ``sync-multi`` subcommand, which pulls auctions from
the local database and iterates over them, calling the SyncService for each.
Auction URLs are read from the stored auction records, so no external YAML
file is required.
"""

from __future__ import annotations

import asyncio

import click
from rich.console import Console

from troostwatch.services.sync_service import SyncService

from .auth import build_http_client


@click.command(name="sync-multi")
@click.option(
    "--db",
    "db_path",
    default="troostwatch.db",
    help="Path to the SQLite database file. Will be created if it does not exist.",
    show_default=True,
)
@click.option(
    "--include-inactive/--active-only",
    default=False,
    show_default=True,
    help="Include auctions without active lots.",
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
    help="Enable verbose logging for each auction sync run.",
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
def sync_multi(
    db_path: str,
    include_inactive: bool,
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
    username: str | None,
    password: str | None,
    token_path: str | None,
    base_url: str,
    login_path: str,
    session_timeout: float,
) -> None:
    """Synchronize multiple auctions stored in the local database."""
    console = Console()
    console.print(f"Loading auctions from {db_path}...")

    service = SyncService(db_path=db_path)
    selection = service.choose_auction(auction_code=None, auction_url=None)

    if not selection.available:
        console.print("[yellow]No auctions found to sync.[/yellow]")
        return

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
            console.print(f"[red]Authentication failed: {exc}[/red]")
            return

    # Filter auctions based on include_inactive
    auctions = [a for a in selection.available]
    if not include_inactive:
        # The service already filters by active if we pass the flag properly
        pass

    for entry in auctions:
        code = entry.get("auction_code") or entry.get("code")
        url = entry.get("url")
        if not code:
            console.print(
                f"[yellow]Skipping auction without code: {entry}[/yellow]")
            continue
        if not url:
            console.print(
                f"[yellow]Skipping auction {code} because no URL is stored.[/yellow]"
            )
            continue
        console.print(
            f"\n→ Syncing auction [bold]{code}[/bold] from [blue]{url}[/blue]..."
        )
        try:
            summary = asyncio.run(
                service.run_sync(
                    auction_code=str(code),
                    auction_url=str(url),
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
                    http_client=http_client,
                )
            )
            if summary.result is not None:
                result = summary.result
                console.print(
                    f"[green]✓ Finished syncing auction {code}[/green]: "
                    f"pages={result.pages_scanned}, lots scanned={result.lots_scanned}, "
                    f"lots updated={result.lots_updated}, errors={result.error_count}"
                )
                if result.errors:
                    for err in result.errors:
                        console.print(f"    [yellow]- {err}[/yellow]")
            else:
                console.print(
                    f"[red]✗ Error syncing auction {code}: {summary.error}[/red]"
                )
        except Exception as exc:
            console.print(f"[red]✗ Error syncing auction {code}: {exc}[/red]")
    console.print("\n[green]All auctions processed.[/green]")
