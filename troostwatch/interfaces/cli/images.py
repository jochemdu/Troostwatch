"""Image analysis CLI commands for Troostwatch.

Commands for downloading, analyzing, and managing lot images:
- download: Download pending images from URLs
- analyze: Run OCR analysis on downloaded images
- review: Handle images needing manual review
- export-tokens: Export OCR token data for ML training
- stats: Show image pipeline statistics
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TaskProgressColumn,
)
from rich.table import Table
import httpx

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
@click.option(
    "--parallel/--sequential",
    default=True,
    help="Use parallel downloads for better performance.",
    show_default=True,
)
@click.option(
    "--concurrency",
    type=int,
    default=10,
    help="Maximum concurrent downloads (only with --parallel).",
    show_default=True,
)
def download_images(
    db_path: str,
    limit: int,
    images_dir: str | None,
    parallel: bool,
    concurrency: int,
) -> None:
    """Download pending images from URLs to local storage.

    Downloads images that have been collected during sync but not yet
    stored locally. Images are saved to data/images/{lot_id}/{position}.jpg

    Use --parallel (default) for faster downloads with concurrent requests.
    """
    images_path = Path(images_dir) if images_dir else _get_images_dir()

    console.print(f"[bold]Downloading images to:[/bold] {images_path}")
    console.print(f"[bold]Database:[/bold] {db_path}")
    console.print(f"[bold]Limit:[/bold] {limit}")
    if parallel:
        console.print(f"[bold]Mode:[/bold] Parallel ({concurrency} concurrent)")
    else:
        console.print("[bold]Mode:[/bold] Sequential")
    console.print()

    service = ImageAnalysisService.from_sqlite_path(db_path, images_path)

    if parallel:
        # Use async parallel downloads with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("[cyan]{task.completed}/{task.total}"),
            console=console,
        ) as progress:
            task = progress.add_task("Downloading images...", total=None)

            def update_progress(done: int, total: int) -> None:
                progress.update(task, completed=done, total=total)

            stats = asyncio.run(
                service.download_pending_images_async(
                    limit=limit,
                    concurrency=concurrency,
                    progress_callback=update_progress,
                )
            )
    else:
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
    "--auto-approve-threshold",
    type=float,
    default=0.85,
    help="Threshold for auto-approving codes (0.0-1.0).",
    show_default=True,
)
@click.option(
    "--auto-approve/--no-auto-approve",
    default=True,
    help="Automatically approve high-confidence codes.",
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
    auto_approve_threshold: float,
    auto_approve: bool,
    limit: int,
    images_dir: str | None,
) -> None:
    """Analyze downloaded images with OCR.

    Runs OCR analysis on images that have been downloaded but not yet
    analyzed. Extracts product codes, EAN numbers, serial numbers, etc.

    Low-confidence results are marked as 'needs_review' for manual
    verification or OpenAI re-analysis.

    High-confidence codes can be auto-approved with --auto-approve.
    """
    images_path = Path(images_dir) if images_dir else _get_images_dir()

    console.print(f"[bold]Analyzing images with backend:[/bold] {backend}")
    console.print(f"[bold]Database:[/bold] {db_path}")
    console.print(f"[bold]Save tokens:[/bold] {save_tokens}")
    console.print(f"[bold]Confidence threshold:[/bold] {confidence_threshold}")
    console.print(
        f"[bold]Auto-approve:[/bold] {auto_approve} (threshold: {auto_approve_threshold})"
    )
    console.print(f"[bold]Limit:[/bold] {limit}")
    console.print()

    service = ImageAnalysisService.from_sqlite_path(db_path, images_path)
    stats = service.analyze_pending_images(
        backend=backend,  # type: ignore
        save_tokens=save_tokens,
        confidence_threshold=confidence_threshold,
        auto_approve_threshold=auto_approve_threshold,
        auto_approve=auto_approve,
        limit=limit,
    )

    console.print()
    console.print("[bold green]Analysis complete![/bold green]")
    console.print(f"  Processed: {stats.images_processed}")
    console.print(f"  Analyzed: {stats.images_analyzed}")
    console.print(f"  Needs review: {stats.images_needs_review}")
    console.print(f"  Failed: {stats.images_failed}")
    console.print(f"  Codes extracted: {stats.codes_extracted}")
    console.print(f"  [green]Codes auto-approved: {stats.codes_auto_approved}[/green]")
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


@images_cli.command(name="openai-analyze")
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
    default=50,
    help="Maximum number of images to analyze.",
    show_default=True,
)
@click.option(
    "--images-dir",
    type=click.Path(),
    default=None,
    help="Directory for stored images. Uses config.json if not specified.",
)
def openai_analyze(db_path: str, limit: int, images_dir: str | None) -> None:
    """Re-analyze needs_review images using OpenAI Vision.

    Takes images that were marked as 'needs_review' by local OCR
    (due to low confidence) and re-analyzes them using OpenAI's
    GPT-4 Vision API for better accuracy.

    Requires OPENAI_API_KEY environment variable to be set.

    This is more expensive than local OCR but provides better
    results for difficult images.

    Example:
        export OPENAI_API_KEY=sk-...
        troostwatch images openai-analyze --limit 20
    """
    import os

    if not os.environ.get("OPENAI_API_KEY"):
        console.print(
            "[bold red]Error:[/bold red] OPENAI_API_KEY environment variable not set."
        )
        console.print("Set it with: export OPENAI_API_KEY=sk-...")
        raise SystemExit(1)

    images_path = Path(images_dir) if images_dir else _get_images_dir()

    console.print("[bold]Re-analyzing with OpenAI Vision...[/bold]")
    console.print(f"[bold]Database:[/bold] {db_path}")
    console.print(f"[bold]Limit:[/bold] {limit}")
    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Analyzing...", total=None)

        service = ImageAnalysisService.from_sqlite_path(db_path, images_path)
        stats = service.promote_to_openai(limit=limit)

        progress.update(task, completed=True)

    console.print()
    console.print("[bold green]OpenAI analysis complete![/bold green]")
    console.print(f"  Processed: {stats.images_processed}")
    console.print(f"  Analyzed: {stats.images_analyzed}")
    console.print(f"  Still needs review: {stats.images_needs_review}")
    console.print(f"  Failed: {stats.images_failed}")
    console.print(f"  Codes extracted: {stats.codes_extracted}")
    console.print(f"  [green]Codes auto-approved: {stats.codes_auto_approved}[/green]")


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

    # Code statistics
    code_stats = stats.get("codes", {})
    code_table = Table(title="Extracted Codes Statistics")
    code_table.add_column("Metric", style="bold")
    code_table.add_column("Value", justify="right")

    code_table.add_row("Total Codes", str(code_stats.get("total", 0)))
    code_table.add_row("[green]Approved[/green]", str(code_stats.get("approved", 0)))
    code_table.add_row(
        "[yellow]Pending Approval[/yellow]", str(code_stats.get("pending", 0))
    )
    code_table.add_row(
        "[cyan]Auto-approved[/cyan]", str(code_stats.get("auto_approved", 0))
    )
    code_table.add_row(
        "[blue]Manually Approved[/blue]", str(code_stats.get("manually_approved", 0))
    )
    code_table.add_row("Promoted to Lots", str(code_stats.get("promoted", 0)))

    console.print(code_table)
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


@images_cli.command(name="promote")
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
    help="Maximum number of codes to promote.",
    show_default=True,
)
@click.option(
    "--images-dir",
    type=click.Path(),
    default=None,
    help="Directory for stored images. Uses config.json if not specified.",
)
def promote_codes(db_path: str, limit: int, images_dir: str | None) -> None:
    """Promote approved codes to lot records.

    Takes approved extracted codes (EAN, serial numbers, model numbers)
    and writes them to the product_specs table for the corresponding lots.

    Only codes that have been approved (auto or manual) and not yet
    promoted will be processed.
    """
    images_path = Path(images_dir) if images_dir else _get_images_dir()

    console.print("[bold]Promoting approved codes to lots...[/bold]")
    console.print(f"[bold]Database:[/bold] {db_path}")
    console.print(f"[bold]Limit:[/bold] {limit}")
    console.print()

    service = ImageAnalysisService.from_sqlite_path(db_path, images_path)
    result = service.promote_codes_to_lots(limit=limit)

    console.print()
    console.print("[bold green]Promotion complete![/bold green]")
    console.print(f"  Total promoted: {result.get('total', 0)}")
    console.print(f"  EAN codes: {result.get('ean', 0)}")
    console.print(f"  Serial numbers: {result.get('serial_number', 0)}")
    console.print(f"  Model numbers: {result.get('model_number', 0)}")
    console.print(f"  Product codes: {result.get('product_code', 0)}")


@images_cli.command(name="hash")
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
    help="Maximum number of images to hash.",
    show_default=True,
)
@click.option(
    "--images-dir",
    type=click.Path(),
    default=None,
    help="Directory for stored images. Uses config.json if not specified.",
)
def compute_hashes(db_path: str, limit: int, images_dir: str | None) -> None:
    """Compute perceptual hashes for downloaded images.

    Computes pHash values for images that have been downloaded but
    don't have a hash yet. These hashes are used for duplicate detection.

    Perceptual hashes are robust to minor image differences like
    resizing, compression artifacts, and small edits.
    """
    images_path = Path(images_dir) if images_dir else _get_images_dir()

    console.print("[bold]Computing image hashes...[/bold]")
    console.print(f"[bold]Database:[/bold] {db_path}")
    console.print(f"[bold]Limit:[/bold] {limit}")
    console.print()

    service = ImageAnalysisService.from_sqlite_path(db_path, images_path)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("[cyan]{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Computing hashes...", total=None)

        def update_progress(done: int, total: int) -> None:
            progress.update(task, completed=done, total=total)

        stats = service.compute_image_hashes(
            limit=limit,
            progress_callback=update_progress,
        )

    console.print()
    console.print("[bold green]Hashing complete![/bold green]")
    console.print(f"  Processed: {stats.images_processed}")
    console.print(f"  Hashed: {stats.images_hashed}")
    console.print(f"  Failed: {stats.images_failed}")


@images_cli.command(name="duplicates")
@click.option(
    "--db",
    "db_path",
    default="troostwatch.db",
    help="Path to the SQLite database file.",
    show_default=True,
)
@click.option(
    "--threshold",
    type=int,
    default=0,
    help="Hamming distance threshold (0=exact match, 10=similar).",
    show_default=True,
)
@click.option(
    "--images-dir",
    type=click.Path(),
    default=None,
    help="Directory for stored images. Uses config.json if not specified.",
)
@click.option(
    "--show-paths",
    is_flag=True,
    default=False,
    help="Show local file paths for each image.",
)
def find_duplicates_cmd(
    db_path: str,
    threshold: int,
    images_dir: str | None,
    show_paths: bool,
) -> None:
    """Find duplicate images using perceptual hashing.

    Groups images that are perceptually similar based on their pHash
    values. Use --threshold to control similarity sensitivity:

    \b
    - 0: Exact matches only (same hash)
    - 5: Very similar images
    - 10: Reasonably similar images
    - 15+: Loosely similar (may have false positives)

    Only images with computed hashes are considered. Run `images hash`
    first to compute hashes for downloaded images.
    """
    images_path = Path(images_dir) if images_dir else _get_images_dir()

    service = ImageAnalysisService.from_sqlite_path(db_path, images_path)

    console.print("[bold]Finding duplicate images...[/bold]")
    console.print(f"[bold]Threshold:[/bold] {threshold}")
    console.print()

    groups = service.find_duplicate_images(threshold=threshold)

    if not groups:
        console.print("[green]No duplicates found![/green]")
        return

    console.print(f"[bold]Found {len(groups)} groups of duplicates:[/bold]")
    console.print()

    for i, group in enumerate(groups, 1):
        console.print(f"[bold cyan]Group {i}[/bold cyan] ({group.count} images)")
        console.print(f"  Hash: {group.phash[:16]}...")
        console.print(f"  Lot IDs: {', '.join(str(lid) for lid in group.lot_ids)}")

        if show_paths:
            for img in group.images:
                console.print(f"    - Image {img.id}: {img.local_path or img.url}")

        console.print()

    # Summary
    total_duplicates = sum(g.count for g in groups)
    unique_lots = len(set(lid for g in groups for lid in g.lot_ids))
    console.print(f"[bold]Summary:[/bold]")
    console.print(f"  Total duplicate images: {total_duplicates}")
    console.print(f"  Unique lots affected: {unique_lots}")
    console.print(f"  Duplicate groups: {len(groups)}")


@images_cli.command(name="hash-stats")
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
def show_hash_stats(db_path: str, images_dir: str | None) -> None:
    """Show statistics about image hashing and duplicates.

    Displays counts of images with/without hashes, unique hashes,
    and detected duplicate groups.
    """
    images_path = Path(images_dir) if images_dir else _get_images_dir()

    service = ImageAnalysisService.from_sqlite_path(db_path, images_path)
    stats = service.get_duplicate_stats()

    table = Table(title="Image Hash Statistics")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Images with pHash", str(stats.get("with_phash", 0)))
    table.add_row("Images without pHash", str(stats.get("without_phash", 0)))
    table.add_row("Unique hashes", str(stats.get("unique_hashes", 0)))
    table.add_row("Duplicate groups", str(stats.get("duplicate_groups", 0)))
    table.add_row("Duplicate images", str(stats.get("duplicate_images", 0)))

    console.print(table)

    # Calculate duplication rate
    total = stats.get("with_phash", 0)
    duplicates = stats.get("duplicate_images", 0)
    if total > 0:
        rate = (duplicates / total) * 100
        console.print()
        console.print(f"[bold]Duplication rate:[/bold] {rate:.1f}%")


@images_cli.command(name="validate-codes")
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
    help="Maximum number of codes to validate.",
    show_default=True,
)
@click.option(
    "--images-dir",
    type=click.Path(),
    default=None,
    help="Directory for stored images. Uses config.json if not specified.",
)
def validate_codes_cmd(db_path: str, limit: int, images_dir: str | None) -> None:
    """Validate and normalize extracted product codes.

    Validates EAN codes using GS1 check digit, normalizes MAC addresses
    and UUIDs, and attempts to correct common OCR errors.

    Invalid codes are marked with low confidence. Valid codes that
    were corrected have their values updated.

    \b
    Validation includes:
    - EAN-13/EAN-8: GS1 check digit validation
    - MAC addresses: Format normalization
    - UUIDs: Format normalization
    - OCR error correction for EANs (O→0, I→1, etc.)
    """
    images_path = Path(images_dir) if images_dir else _get_images_dir()

    console.print("[bold]Validating extracted codes...[/bold]")
    console.print(f"[bold]Database:[/bold] {db_path}")
    console.print(f"[bold]Limit:[/bold] {limit}")
    console.print()

    service = ImageAnalysisService.from_sqlite_path(db_path, images_path)
    stats = service.validate_pending_codes(limit=limit)

    console.print()
    console.print("[bold green]Validation complete![/bold green]")
    console.print(f"  Processed: {stats.get('processed', 0)}")
    console.print(f"  [green]Valid: {stats.get('valid', 0)}[/green]")
    console.print(f"  [red]Invalid: {stats.get('invalid', 0)}[/red]")
    console.print(f"  [cyan]Corrected (OCR fixes): {stats.get('corrected', 0)}[/cyan]")


@images_cli.command(name="retrain-model")
@click.option(
    "--api-url",
    default="http://localhost:8000/ml/retrain",
    help="URL van het retraining API endpoint.",
    show_default=True,
)
@click.option(
    "--training-data-path",
    default=None,
    help="Pad naar training data JSON.",
)
@click.option(
    "--n-estimators",
    default=100,
    type=int,
    help="Aantal bomen in RandomForest.",
)
@click.option(
    "--max-depth",
    default=None,
    type=int,
    help="Maximale boomdiepte.",
)
def retrain_model_cli(api_url, training_data_path, n_estimators, max_depth):
    """Trigger ML model retraining via API."""
    console.print(f"[bold]Triggering ML retraining via:[/bold] {api_url}")
    payload = {
        "training_data_path": training_data_path,
        "n_estimators": n_estimators,
        "max_depth": max_depth,
    }
    try:
        response = httpx.post(api_url, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        console.print(f"[green]Retraining gestart:[/green] {result}")
    except Exception as e:
        console.print(f"[red]Fout bij retraining:[/red] {e}")


@images_cli.command(name="export-training-data")
@click.option(
    "--api-url",
    default="http://localhost:8000/ml/export-training-data",
    help="URL van het training data export API endpoint.",
    show_default=True,
)
@click.option(
    "--output",
    default="training_data.json",
    help="Pad voor het output JSON-bestand.",
    show_default=True,
)
@click.option(
    "--include-reviewed/--no-include-reviewed",
    default=False,
    help="Neem handmatig gelabelde data mee.",
)
@click.option(
    "--only-mismatches/--no-only-mismatches",
    default=False,
    help="Exporteer alleen records met token/label mismatch.",
)
@click.option(
    "--limit",
    default=1000,
    type=int,
    help="Maximaal aantal records.",
)
def export_training_data_cli(api_url, output, include_reviewed, only_mismatches, limit):
    """Exporteer training data via API en sla op als JSON."""
    console.print(f"[bold]Exporting training data via:[/bold] {api_url}")
    params = {
        "include_reviewed": include_reviewed,
        "only_mismatches": only_mismatches,
        "limit": limit,
    }
    try:
        response = httpx.get(api_url, params=params, timeout=60)
        response.raise_for_status()
        data = response.json()
        with open(output, "w", encoding="utf-8") as f:
            import json

            json.dump(data, f, indent=2, ensure_ascii=False)
        console.print(
            f"[green]Training data geëxporteerd:[/green] {output} ({data.get('count', 0)} records)"
        )
    except Exception as e:
        console.print(f"[red]Fout bij exporteren training data:[/red] {e}")


@images_cli.command(name="training-status")
@click.option(
    "--api-url",
    default="http://localhost:8000/ml/training-status",
    help="URL van het training status API endpoint.",
    show_default=True,
)
def training_status_cli(api_url):
    """Toon ML training status en model metrics via API."""
    console.print(f"[bold]Ophalen training status via:[/bold] {api_url}")
    try:
        response = httpx.get(api_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        console.print("\n[bold green]Training Status:[/bold green]")
        last_run = data.get("last_run", {})
        model_info = data.get("model_info", {})
        stats = data.get("stats", {})
        console.print(
            f"Laatste run: {last_run.get('started_at')} → {last_run.get('finished_at')}"
        )
        console.print(f"Status: {last_run.get('status')}")
        console.print(f"Metrics: {last_run.get('metrics')}")
        console.print(f"Model info: {model_info}")
        console.print(f"Stats: {stats}")
        console.print(f"Detail: {data.get('detail')}")
    except Exception as e:
        console.print(f"[red]Fout bij ophalen training status:[/red] {e}")


__all__ = ["images_cli"]
