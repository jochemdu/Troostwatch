"""Synchronization CLI for Troostwatch."""

from __future__ import annotations

import asyncio

import click
from rich.console import Console
from rich.prompt import IntPrompt, Prompt

from troostwatch.interfaces.cli.context import build_sync_command_context
from troostwatch.services.sync_service import SyncRunSummary, SyncService


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
    help=(
        "Auction code (e.g. A1-39499) identifying the auction to sync. "
        "When omitted and auctions exist in the DB, you will be prompted to choose."
    ),
)
@click.option(
    "--auction-url",
    required=False,
    help=(
        "URL of the auction listing page on Troostwijk. "
        "When omitted, it is taken from the selected auction if available."
    ),
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
    console = Console()
    if username and not password and token_path is None:
        password = Prompt.ask("Troostwijk password", password=True, console=console)

    command_context = build_sync_command_context(
        db_path=db_path,
        base_url=base_url,
        login_path=login_path,
        username=username,
        password=password,
        token_path=token_path,
        session_timeout=session_timeout,
    )

    service = SyncService(db_path=str(command_context.cli_context.db_path))
    selection = service.choose_auction(auction_code=auction_code, auction_url=auction_url)

    resolved_code = selection.resolved_code
    resolved_url = selection.resolved_url

    if not resolved_code and selection.available:
        console.print("Select an auction to sync:")
        for idx, auction in enumerate(selection.available, start=1):
            title = auction.get("title") or "(geen titel)"
            url = auction.get("url") or "(geen url bekend)"
            console.print(f"{idx}) {auction['auction_code']} - {title} - {url}")
        default_choice_num = selection.default_choice_number or 1
        console.print(
            "Standaard keuze: "
            f"{default_choice_num}) {selection.available[default_choice_num - 1]['auction_code']}"
        )
        choice = IntPrompt.ask(
            "Keuze",
            default=default_choice_num,
            console=console,
        )
        try:
            selected = selection.available[int(choice) - 1]
        except Exception:
            console.print("[red]Ongeldige keuze; aborting sync.[/red]")
            return
        resolved_code = selected.get("auction_code") or resolved_code
        resolved_url = selected.get("url") or resolved_url

    if not resolved_code:
        console.print(
            "[red]Auction code ontbreekt; geef --auction-code op of kies een bestaande.[/red]"
        )
        return

    if not resolved_url:
        resolved_url = Prompt.ask("Auction URL", console=console)

    console.print(
        f"[bold]Syncing auction {resolved_code}[/bold] from "
        f"[blue]{resolved_url}[/blue] into {command_context.cli_context.db_path}..."
    )
    if dry_run:
        console.print("[yellow]Dry-run enabled; no database writes will occur.[/yellow]")

    if command_context.http_client is not None:
        try:
            with console.status("Authenticating..."):
                command_context.http_client.authenticate()
        except Exception as exc:
            console.print(f"[red]Authentication failed: {exc}[/red]")
            return

    with console.status("Running sync..."):
        summary = asyncio.run(
            service.run_sync(
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
                http_client=command_context.http_client,
            )
        )

    if (
        not isinstance(summary, SyncRunSummary)
        or summary.result is None
        or summary.status != "success"
    ):
        console.print(f"[red]Error during sync: {getattr(summary, 'error', 'onbekende fout')}[/red]")
        return

    result = summary.result
    console.print(
        f"[green]Sync {result.status}[/green] (run #{result.run_id}): pages={result.pages_scanned}, "
        f"lots scanned={result.lots_scanned}, lots updated={result.lots_updated}, errors={result.error_count}"
    )
    if result.errors:
        console.print("[yellow]Errors:[/yellow]")
        for err in result.errors:
            console.print(f"  - {err}")
