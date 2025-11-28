"""Image analysis CLI commands for Troostwatch.

Commands for downloading, analyzing, and managing lot images:
- download: Download pending images from URLs
- analyze: Run OCR analysis on downloaded images
- review: Handle images needing manual review
- export-tokens: Export OCR token data for ML training
- stats: Show image pipeline statistics
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from troostwatch.app.config import load_config
from troostwatch.infrastructure.db import get_connection
from troostwatch.services.image_analysis import ImageAnalysisService

console = Console()


def _get_images_dir(config_path: str = "config.json") -> Path:
    """Get the images directory from config."""
    try:
        config = load_config(config_path)
        return Path(config.get("paths", {}).get("images_dir", "data/images"))
    except Exception:
        return Path("data/images")


@click.group(name="images")
def images_cli() -> None:
    """Commands for image download and analysis."""
    pass


@images_cli.command(name="download")
@click.option(
    "--db",
    "db_path",
    default="troostwatch.db",
    help="Path to the SQLite database file.",
    show_default=True,
)
@click.option(
    "--limit",
    type=int,
    default=100,
    help="Maximum number of images to download.",
    show_default=True,
)
@click.option(
    "--images-dir",
    type=click.Path(),
    default=None,
    help="Directory for storing downloaded images. Uses config.json if not specified.",
)
def download_images(db_path: str, limit: int, images_dir: str | None) -> None:
    """Download pending images from URLs to local storage.

    Downloads images that have been collected during sync but not yet
    stored locally. Images are saved to data/images/{lot_id}/{position}.jpg
    """
    images_path = Path(images_dir) if images_dir else _get_images_dir()

    console.print(f"[bold]Downloading images to:[/bold] {images_path}")
    console.print(f"[bold]Database:[/bold] {db_path}")
    console.print(f"[bold]Limit:[/bold] {limit}")
    console.print()

    service = ImageAnalysisService.from_sqlite_path(db_path, images_path)
    stats = service.download_pending_images(limit=limit)

    console.print()
    console.print("[bold green]Download complete![/bold green]")
    console.print(f"  Processed: {stats.images_processed}")
    console.print(f"  Downloaded: {stats.images_downloaded}")
    console.print(f"  Failed: {stats.images_failed}")
    console.print(f"  Bytes: {stats.bytes_downloaded:,}")


@images_cli.command(name="analyze")
@click.option(
    "--db",
    "db_path",
    default="troostwatch.db",
    help="Path to the SQLite database file.",
    show_default=True,
)
@click.option(
    "--backend",
    type=click.Choice(["local", "openai", "ml"]),
    default="local",
    help="OCR backend to use.",
    show_default=True,
)
@click.option(
    "--save-tokens/--no-save-tokens",
    default=True,
    help="Save raw OCR token data for ML training.",
    show_default=True,
)
@click.option(
    "--confidence-threshold",
    type=float,
    default=0.6,
    help="Threshold for needs_review status (0.0-1.0).",
    show_default=True,
)
@click.option(
    "--limit",
    type=int,
    default=100,
    help="Maximum number of images to analyze.",
    show_default=True,
)
@click.option(
    "--images-dir",
    type=click.Path(),
    default=None,
    help="Directory for stored images. Uses config.json if not specified.",
)
def analyze_images(
    db_path: str,
    backend: str,
    save_tokens: bool,
    confidence_threshold: float,
    limit: int,
    images_dir: str | None,
) -> None:
    """Analyze downloaded images with OCR.

    Runs OCR analysis on images that have been downloaded but not yet
    analyzed. Extracts product codes, EAN numbers, serial numbers, etc.

    Low-confidence results are marked as 'needs_review' for manual
    verification or OpenAI re-analysis.
    """
    images_path = Path(images_dir) if images_dir else _get_images_dir()

    console.print(f"[bold]Analyzing images with backend:[/bold] {backend}")
    console.print(f"[bold]Database:[/bold] {db_path}")
    console.print(f"[bold]Save tokens:[/bold] {save_tokens}")
    console.print(f"[bold]Confidence threshold:[/bold] {confidence_threshold}")
    console.print(f"[bold]Limit:[/bold] {limit}")
    console.print()

    service = ImageAnalysisService.from_sqlite_path(db_path, images_path)
    stats = service.analyze_pending_images(
        backend=backend,  # type: ignore
        save_tokens=save_tokens,
        confidence_threshold=confidence_threshold,
        limit=limit,
    )

    console.print()
    console.print("[bold green]Analysis complete![/bold green]")
    console.print(f"  Processed: {stats.images_processed}")
    console.print(f"  Analyzed: {stats.images_analyzed}")
    console.print(f"  Needs review: {stats.images_needs_review}")
    console.print(f"  Failed: {stats.images_failed}")
    console.print(f"  Codes extracted: {stats.codes_extracted}")
    console.print(f"  Tokens saved: {stats.tokens_saved}")


@images_cli.command(name="review")
@click.option(
    "--db",
    "db_path",
    default="troostwatch.db",
    help="Path to the SQLite database file.",
    show_default=True,
)
@click.option(
    "--promote-to-openai",
    is_flag=True,
    default=False,
    help="Re-analyze needs_review images with OpenAI Vision.",
)
@click.option(
    "--limit",
    type=int,
    default=50,
    help="Maximum number of images to process.",
    show_default=True,
)
@click.option(
    "--images-dir",
    type=click.Path(),
    default=None,
    help="Directory for stored images. Uses config.json if not specified.",
)
def review_images(
    db_path: str,
    promote_to_openai: bool,
    limit: int,
    images_dir: str | None,
) -> None:
    """Handle images that need manual review.

    Shows images marked as 'needs_review' due to low confidence.
    Optionally re-analyzes them with OpenAI Vision for better accuracy.
    """
    images_path = Path(images_dir) if images_dir else _get_images_dir()

    if promote_to_openai:
        console.print("[bold]Promoting images to OpenAI analysis...[/bold]")
        service = ImageAnalysisService.from_sqlite_path(db_path, images_path)
        stats = service.promote_to_openai(limit=limit)
        console.print(f"  Processed: {stats.images_processed}")
        console.print(f"  Analyzed: {stats.images_analyzed}")
    else:
        # Show review queue
        with get_connection(db_path) as conn:
            from troostwatch.infrastructure.db.repositories import LotImageRepository

            repo = LotImageRepository(conn)
            images = repo.get_needs_review(limit=limit)

            if not images:
                console.print("[green]No images need review.[/green]")
                return

            table = Table(title=f"Images Needing Review ({len(images)})")
            table.add_column("ID", style="cyan")
            table.add_column("Lot ID", style="magenta")
            table.add_column("Position")
            table.add_column("Local Path")
            table.add_column("Backend")

            for img in images:
                table.add_row(
                    str(img.id),
                    str(img.lot_id),
                    str(img.position),
                    img.local_path or "-",
                    img.analysis_backend or "-",
                )

            console.print(table)
            console.print()
            console.print(
                "Use [bold]--promote-to-openai[/bold] to re-analyze with OpenAI Vision."
            )


@images_cli.command(name="reprocess-failed")
@click.option(
    "--db",
    "db_path",
    default="troostwatch.db",
    help="Path to the SQLite database file.",
    show_default=True,
)
@click.option(
    "--limit",
    type=int,
    default=100,
    help="Maximum number of images to reprocess.",
    show_default=True,
)
@click.option(
    "--images-dir",
    type=click.Path(),
    default=None,
    help="Directory for stored images. Uses config.json if not specified.",
)
def reprocess_failed(db_path: str, limit: int, images_dir: str | None) -> None:
    """Retry analysis for previously failed images.

    Resets failed images and runs analysis again. Useful after
    fixing issues or updating the OCR engine.
    """
    images_path = Path(images_dir) if images_dir else _get_images_dir()

    console.print("[bold]Reprocessing failed images...[/bold]")

    service = ImageAnalysisService.from_sqlite_path(db_path, images_path)
    stats = service.reprocess_failed(limit=limit)

    console.print()
    console.print("[bold green]Reprocessing complete![/bold green]")
    console.print(f"  Processed: {stats.images_processed}")
    console.print(f"  Analyzed: {stats.images_analyzed}")
    console.print(f"  Needs review: {stats.images_needs_review}")
    console.print(f"  Failed: {stats.images_failed}")


@images_cli.command(name="export-tokens")
@click.option(
    "--db",
    "db_path",
    default="troostwatch.db",
    help="Path to the SQLite database file.",
    show_default=True,
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="training_data.json",
    help="Output file path for the JSON export.",
    show_default=True,
)
@click.option(
    "--include-reviewed",
    is_flag=True,
    default=False,
    help="Only include manually reviewed/labeled data.",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Maximum number of records to export.",
)
@click.option(
    "--images-dir",
    type=click.Path(),
    default=None,
    help="Directory for stored images. Uses config.json if not specified.",
)
def export_tokens(
    db_path: str,
    output: str,
    include_reviewed: bool,
    limit: int | None,
    images_dir: str | None,
) -> None:
    """Export OCR token data for ML training.

    Exports the raw token data (text, positions, confidence scores)
    collected during OCR analysis. This data can be used to train
    a custom ML model for better label recognition.
    """
    images_path = Path(images_dir) if images_dir else _get_images_dir()

    console.print(f"[bold]Exporting token data to:[/bold] {output}")
    console.print(f"[bold]Include reviewed only:[/bold] {include_reviewed}")

    service = ImageAnalysisService.from_sqlite_path(db_path, images_path)
    count = service.export_token_data(
        output_path=output,
        include_reviewed=include_reviewed,
        limit=limit,
    )

    console.print()
    console.print(f"[bold green]Exported {count} records![/bold green]")


@images_cli.command(name="stats")
@click.option(
    "--db",
    "db_path",
    default="troostwatch.db",
    help="Path to the SQLite database file.",
    show_default=True,
)
@click.option(
    "--images-dir",
    type=click.Path(),
    default=None,
    help="Directory for stored images. Uses config.json if not specified.",
)
def show_stats(db_path: str, images_dir: str | None) -> None:
    """Show statistics for the image analysis pipeline.

    Displays counts of images in each status (pending, downloaded,
    analyzed, needs_review, failed) and token data statistics.
    """
    images_path = Path(images_dir) if images_dir else _get_images_dir()

    service = ImageAnalysisService.from_sqlite_path(db_path, images_path)
    stats = service.get_stats()

    # Image statistics
    img_stats = stats.get("images", {})
    img_table = Table(title="Image Statistics")
    img_table.add_column("Status", style="bold")
    img_table.add_column("Count", justify="right")

    img_table.add_row("Total", str(img_stats.get("total", 0)))
    img_table.add_row("Pending Download", str(img_stats.get("pending_download", 0)))
    img_table.add_row("Downloaded", str(img_stats.get("downloaded", 0)))
    img_table.add_row("Download Failed", str(img_stats.get("download_failed", 0)))
    img_table.add_row("Pending Analysis", str(img_stats.get("pending_analysis", 0)))
    img_table.add_row("Analyzed", str(img_stats.get("analyzed", 0)))
    img_table.add_row("Needs Review", str(img_stats.get("needs_review", 0)))
    img_table.add_row("Analysis Failed", str(img_stats.get("analysis_failed", 0)))

    console.print(img_table)
    console.print()

    # Token statistics
    token_stats = stats.get("tokens", {})
    token_table = Table(title="Token Data Statistics")
    token_table.add_column("Metric", style="bold")
    token_table.add_column("Value", justify="right")

    token_table.add_row("Total Records", str(token_stats.get("total", 0)))
    token_table.add_row("Labeled for Training", str(token_stats.get("labeled", 0)))
    token_table.add_row("Total Tokens", f"{token_stats.get('total_tokens', 0):,}")

    console.print(token_table)


__all__ = ["images_cli"]
