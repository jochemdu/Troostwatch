"""CLI entry point for placing bids using the authenticated HTTP client."""

from __future__ import annotations

import click
from troostwatch.infrastructure.http import AuthenticationError
from troostwatch.services.bidding import BidError, BiddingService

from .auth import build_http_client


@click.command(name="bid")
@click.option(
    "--db",
    "db_path",
    default="troostwatch.db",
    show_default=True,
    help="Path to the SQLite database.",
)
@click.option("--buyer", "buyer_label", required=True, help="Buyer label to bid as.")
@click.option("--auction-code", required=True, help="Auction code for the lot.")
@click.option("--lot-code", required=True, help="Lot code to bid on.")
@click.option("--amount", required=True, type=float, help="Bid amount in EUR.")
@click.option("--note", default=None, help="Optional note to persist locally with the bid.")
@click.option("--username", help="Account username/email for authentication.")
@click.option("--password", help="Account password (prompted if omitted).")
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
    "--api-base-url",
    default="https://www.troostwijkauctions.com/api",
    show_default=True,
    help="Base API URL used for bid submissions.",
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
@click.option(
    "--quiet",
    is_flag=True,
    default=False,
    help="Only print fatal errors (suppress response payloads).",
)
def bid(
    db_path: str,
    buyer_label: str,
    auction_code: str,
    lot_code: str,
    amount: float,
    note: str | None,
    username: str | None,
    password: str | None,
    token_path: str | None,
    base_url: str,
    api_base_url: str,
    login_path: str,
    session_timeout: float,
    quiet: bool,
) -> None:
    if username and not password and token_path is None:
        password = click.prompt("Troostwijk password", hide_input=True)

    client = build_http_client(
        base_url=base_url,
        login_path=login_path,
        username=username,
        password=password,
        token_path=token_path,
        session_timeout=session_timeout,
    )
    if client is None:
        click.echo("Login credentials or a token path are required to submit bids.")
        return

    try:
        client.authenticate()
    except Exception as exc:
        click.echo(f"Authentication failed: {exc}")
        return

    if db_path:
        service = BiddingService.from_sqlite_path(client, db_path, api_base_url=api_base_url)
    else:
        service = BiddingService(client, api_base_url=api_base_url)
    try:
        result = service.submit_bid(
            buyer_label=buyer_label,
            auction_code=auction_code,
            lot_code=lot_code,
            amount_eur=amount,
            note=note,
        )
    except AuthenticationError as exc:
        click.echo(f"Authentication error while bidding: {exc}")
        return
    except BidError as exc:
        click.echo(str(exc))
        return
    except Exception as exc:  # pragma: no cover - runtime safety
        click.echo(f"Unexpected error while bidding: {exc}")
        return

    click.echo(
        f"Bid of €{amount:.2f} placed on lot {lot_code} in auction {auction_code} for buyer {buyer_label}."
    )
    if not quiet:
        click.echo(f"Response: {result.raw_response}")
