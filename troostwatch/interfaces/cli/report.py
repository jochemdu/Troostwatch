"""CLI commands for generating reports and summaries.

This module defines a ``report`` Click group with subcommands to produce
readable summaries from the database, such as the exposure overview for a
specific buyer.
"""

from __future__ import annotations

import click
import json

from troostwatch.services.reporting import ReportingService


@click.group()
def report() -> None:
    """Generate reports and summaries."""
    pass


@report.command(name="buyer")
@click.option("--db", "db_path", required=True, help="Path to the SQLite database.")
@click.argument("buyer")
@click.option(
    "--json-output",
    is_flag=True,
    help="Output the summary as JSON instead of plain text.",
)
def report_buyer(db_path: str, buyer: str, json_output: bool) -> None:
    """Show a summary of exposure and tracked lots for BUYER."""
    service = ReportingService.from_sqlite_path(db_path)
    summary = service.get_buyer_summary(buyer).to_dict()
    if json_output:
        click.echo(json.dumps(summary, indent=2))
        return
    click.echo(f"Summary for buyer '{buyer}':")
    click.echo(f"  Tracked positions: {summary['tracked_count']}")
    click.echo(f"  Open lots: {summary['open_count']}")
    click.echo(f"  Closed lots: {summary['closed_count']}")
    click.echo(f"  Minimum open exposure: €{summary['open_exposure_min_eur']:.2f}")
    click.echo(f"  Maximum open exposure: €{summary['open_exposure_max_eur']:.2f}")
    if summary["open_tracked_lots"]:
        click.echo("\nOpen tracked lots:")
        for lot in summary["open_tracked_lots"]:
            budget = lot["max_budget_total_eur"]
            budget_str = f"(max €{budget:.2f})" if budget is not None else "(no max)"
            click.echo(
                f"  {lot['lot_code']} – {lot['title']} – state={lot['state']} – "
                f"current €{lot['current_bid_eur'] or 0:.2f} {budget_str}"
            )
    if summary["won_lots"]:
        click.echo("\nClosed lots:")
        for lot in summary["won_lots"]:
            click.echo(
                f"  {lot['lot_code']} – {lot['title']} – state={lot['state']} – "
                f"final €{lot['current_bid_eur'] or 0:.2f}"
            )
