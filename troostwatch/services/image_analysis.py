"""Image analysis service for OCR and product code extraction.

This service orchestrates the image analysis pipeline:
1. Download pending images from URLs to local storage
2. Analyze images with OCR (local or OpenAI)
3. Extract and store product codes
4. Store raw token data for ML training
5. Handle review queue for low-confidence results
6. Compute perceptual hashes for deduplication
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

from troostwatch.infrastructure.ai.image_analyzer import (
    ExtractedCode,
    ImageAnalysisResult,
    LocalOCRAnalyzer,
)
from troostwatch.infrastructure.ai.image_hashing import (
    compute_phash,
    hamming_distance,
    PIL_AVAILABLE as HASH_AVAILABLE,
)
from troostwatch.infrastructure.db import get_connection
from troostwatch.infrastructure.db.repositories import (
    ExtractedCodeRepository,
    LotImage,
    LotImageRepository,
    OcrTokenRepository,
)
from troostwatch.infrastructure.observability import get_logger
from troostwatch.infrastructure.observability.metrics import (
    record_image_download,
    record_image_analysis,
    record_code_approval,
    Timer,
)
from troostwatch.infrastructure.persistence.images import ImageDownloader

from .base import BaseService, ConnectionFactory

logger = get_logger(__name__)


@dataclass
class AnalysisStats:
    """Statistics from an analysis run."""

    images_processed: int = 0
    images_analyzed: int = 0
    images_needs_review: int = 0
    images_failed: int = 0
    codes_extracted: int = 0
    codes_auto_approved: int = 0
    tokens_saved: int = 0


@dataclass
class DownloadStats:
    """Statistics from a download run."""

    images_processed: int = 0
    images_downloaded: int = 0
    images_failed: int = 0
    bytes_downloaded: int = 0


@dataclass
class HashStats:
    """Statistics from a phash computation run."""

    images_processed: int = 0
    images_hashed: int = 0
    images_failed: int = 0
    duplicates_found: int = 0


@dataclass
class DuplicateGroup:
    """A group of images that are perceptually similar."""

    phash: str
    images: list[LotImage] = field(default_factory=list)
    lot_ids: list[int] = field(default_factory=list)

    @property
    def count(self) -> int:
        """Number of duplicate images in this group."""
        return len(self.images)


class ImageAnalysisService(BaseService):
    """Service for downloading and analyzing lot images.

    This service provides the main interface for the image analysis pipeline,
    coordinating between the image downloader, OCR analyzer, and repositories.
    """

    # Confidence threshold below which images go to needs_review
    DEFAULT_CONFIDENCE_THRESHOLD = 0.6
    # Confidence threshold above which codes are auto-approved
    DEFAULT_AUTO_APPROVE_THRESHOLD = 0.85

    def __init__(
        self,
        connection_factory: ConnectionFactory,
        images_dir: str | Path = "data/images",
    ) -> None:
        """Initialize the image analysis service.

        Args:
            connection_factory: Factory for database connections.
            images_dir: Directory for storing downloaded images.
        """
        super().__init__(connection_factory)
        self.images_dir = Path(images_dir)
        self._downloader = ImageDownloader(self.images_dir)
        self._ocr = LocalOCRAnalyzer()

    @classmethod
    def from_sqlite_path(
        cls,
        db_path: str,
        images_dir: str | Path = "data/images",
    ) -> "ImageAnalysisService":
        """Create service from a SQLite database path.

        Args:
            db_path: Path to the SQLite database.
            images_dir: Directory for storing downloaded images.

        Returns:
            Configured ImageAnalysisService instance.
        """
        return cls(
            connection_factory=lambda: get_connection(db_path),
            images_dir=images_dir,
        )

    def download_pending_images(self, limit: int = 100) -> DownloadStats:
        """Download images that haven't been downloaded yet.

        Args:
            limit: Maximum number of images to download.

        Returns:
            Statistics about the download operation.
        """
        import time

        stats = DownloadStats()

        with self._connection_factory() as conn:
            image_repo = LotImageRepository(conn)
            pending = image_repo.get_pending_download(limit=limit)
            stats.images_processed = len(pending)

            for image in pending:
                start_time = time.perf_counter()
                local_path, error = self._downloader.download_lot_image(image)
                duration = time.perf_counter() - start_time

                if local_path:
                    image_repo.mark_downloaded(image.id, local_path)
                    stats.images_downloaded += 1

                    # Track file size
                    try:
                        file_size = Path(local_path).stat().st_size
                        stats.bytes_downloaded += file_size
                        record_image_download("success", duration, file_size)
                    except Exception:
                        record_image_download("success", duration)
                else:
                    image_repo.mark_download_failed(image.id, error or "Unknown error")
                    stats.images_failed += 1
                    record_image_download("failed", duration)
                    logger.warning(
                        "Failed to download image",
                        extra={"image_id": image.id, "url": image.url, "error": error},
                    )

            conn.commit()

        logger.info(
            "Download batch complete",
            extra={
                "processed": stats.images_processed,
                "downloaded": stats.images_downloaded,
                "failed": stats.images_failed,
                "bytes": stats.bytes_downloaded,
            },
        )
        return stats

    async def download_pending_images_async(
        self,
        limit: int = 100,
        concurrency: int = 10,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> DownloadStats:
        """Download images concurrently with configurable parallelism.

        Uses asyncio for parallel downloads, significantly faster than
        sequential downloading for large batches.

        Args:
            limit: Maximum number of images to download.
            concurrency: Maximum concurrent downloads.
            progress_callback: Optional callback(done, total) for progress.

        Returns:
            Statistics about the download operation.
        """
        stats = DownloadStats()
        semaphore = asyncio.Semaphore(concurrency)

        # Get pending images
        with self._connection_factory() as conn:
            image_repo = LotImageRepository(conn)
            pending = image_repo.get_pending_download(limit=limit)
            stats.images_processed = len(pending)

        if not pending:
            return stats

        async def download_one(image: LotImage) -> tuple[int, str | None, str | None]:
            """Download a single image with semaphore."""
            async with semaphore:
                local_path, error = await self._downloader.download_lot_image_async(
                    image
                )
                return image.id, local_path, error

        # Download all concurrently
        tasks = [download_one(img) for img in pending]
        results = []
        done_count = 0

        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
            done_count += 1
            if progress_callback:
                progress_callback(done_count, len(tasks))

        # Update database with results
        with self._connection_factory() as conn:
            image_repo = LotImageRepository(conn)

            for image_id, local_path, error in results:
                if local_path:
                    image_repo.mark_downloaded(image_id, local_path)
                    stats.images_downloaded += 1
                    try:
                        stats.bytes_downloaded += Path(local_path).stat().st_size
                    except Exception:
                        pass
                else:
                    image_repo.mark_download_failed(image_id, error or "Unknown error")
                    stats.images_failed += 1
                    logger.warning(
                        "Failed to download image",
                        extra={"image_id": image_id, "error": error},
                    )

            conn.commit()

        logger.info(
            "Async download batch complete",
            extra={
                "processed": stats.images_processed,
                "downloaded": stats.images_downloaded,
                "failed": stats.images_failed,
                "bytes": stats.bytes_downloaded,
                "concurrency": concurrency,
            },
        )
        return stats

    def analyze_pending_images(
        self,
        backend: Literal["local", "openai", "ml"] = "local",
        save_tokens: bool = True,
        confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
        auto_approve_threshold: float = DEFAULT_AUTO_APPROVE_THRESHOLD,
        auto_approve: bool = True,
        limit: int = 100,
    ) -> AnalysisStats:
        """Analyze downloaded images that haven't been analyzed yet.

        Args:
            backend: Analysis backend to use.
            save_tokens: Whether to save raw OCR token data for ML training.
            confidence_threshold: Below this, mark as needs_review.
            auto_approve_threshold: Above this, auto-approve extracted codes.
            auto_approve: Whether to auto-approve high-confidence codes.
            limit: Maximum number of images to analyze.

        Returns:
            Statistics about the analysis operation.
        """
        import time

        stats = AnalysisStats()

        with self._connection_factory() as conn:
            image_repo = LotImageRepository(conn)
            code_repo = ExtractedCodeRepository(conn)
            token_repo = OcrTokenRepository(conn)

            pending = image_repo.get_pending_analysis(limit=limit)
            stats.images_processed = len(pending)

            for image in pending:
                start_time = time.perf_counter()

                if not image.local_path:
                    # Should not happen, but handle gracefully
                    image_repo.mark_analysis_failed(image.id, "No local path")
                    stats.images_failed += 1
                    record_image_analysis(backend, "failed", 0.0)
                    continue

                try:
                    # Analyze the image
                    result = self._ocr.analyze_local_image(image.local_path)
                    duration = time.perf_counter() - start_time

                    if result.error:
                        image_repo.mark_analysis_failed(image.id, result.error)
                        stats.images_failed += 1
                        record_image_analysis(backend, "failed", duration)
                        continue

                    # Calculate average confidence of extracted codes
                    avg_confidence = self._calculate_confidence(result.codes)

                    # Determine status based on confidence
                    if avg_confidence < confidence_threshold and result.codes:
                        status = "needs_review"
                        stats.images_needs_review += 1
                        record_image_analysis(
                            backend, "needs_review", duration, len(result.codes)
                        )
                    else:
                        status = "analyzed"
                        stats.images_analyzed += 1
                        record_image_analysis(
                            backend, "success", duration, len(result.codes)
                        )

                    # Mark image as analyzed
                    image_repo.mark_analyzed(image.id, backend, status)

                    # Store extracted codes
                    if result.codes:
                        code_repo.delete_by_image_id(image.id)  # Clear old codes
                        for code in result.codes:
                            code_repo.insert_code(
                                lot_image_id=image.id,
                                code_type=code.code_type,
                                value=code.value,
                                confidence=code.confidence,
                                context=code.context,
                            )
                            stats.codes_extracted += 1

                        # Auto-approve high-confidence codes
                        if auto_approve and avg_confidence >= auto_approve_threshold:
                            approved_count = code_repo.approve_codes_by_image(
                                image.id, approved_by="auto"
                            )
                            if approved_count > 0:
                                stats.codes_auto_approved += approved_count
                                # Record metrics for each approved code type
                                for code in result.codes:
                                    record_code_approval("auto", code.code_type)

                    # Save token data for ML training
                    if save_tokens:
                        token_data = self._ocr.get_token_data(image.local_path)
                        if token_data:
                            token_repo.upsert_tokens(image.id, token_data)
                            stats.tokens_saved += 1

                except Exception as e:
                    logger.error(
                        "Analysis failed",
                        extra={"image_id": image.id, "error": str(e)},
                    )
                    image_repo.mark_analysis_failed(image.id, str(e))
                    stats.images_failed += 1

            conn.commit()

        logger.info(
            "Analysis batch complete",
            extra={
                "processed": stats.images_processed,
                "analyzed": stats.images_analyzed,
                "needs_review": stats.images_needs_review,
                "failed": stats.images_failed,
                "codes_extracted": stats.codes_extracted,
            },
        )
        return stats

    def promote_to_openai(self, limit: int = 50) -> AnalysisStats:
        """Re-analyze needs_review images using OpenAI Vision.

        This is more expensive but more accurate for difficult images.

        Args:
            limit: Maximum number of images to process.

        Returns:
            Statistics about the operation.
        """
        # TODO: Implement OpenAI re-analysis
        # This would use the OpenAIAnalyzer class
        logger.warning("OpenAI promotion not yet implemented")
        return AnalysisStats()

    def reprocess_failed(self, limit: int = 100) -> AnalysisStats:
        """Retry analysis for previously failed images.

        Args:
            limit: Maximum number of images to reprocess.

        Returns:
            Statistics about the operation.
        """
        with self._connection_factory() as conn:
            image_repo = LotImageRepository(conn)
            failed = image_repo.get_failed(limit=limit)

            # Reset status for reprocessing
            for image in failed:
                image_repo.reset_for_reprocessing(image.id)

            conn.commit()

        # Now run normal analysis
        return self.analyze_pending_images(limit=limit)

    def export_token_data(
        self,
        output_path: str | Path,
        include_reviewed: bool = False,
        limit: int | None = None,
    ) -> int:
        """Export OCR token data for ML training.

        Args:
            output_path: Path for the output JSON file.
            include_reviewed: Include manually reviewed/labeled data.
            limit: Maximum number of records to export.

        Returns:
            Number of records exported.
        """
        with self._connection_factory() as conn:
            token_repo = OcrTokenRepository(conn)
            image_repo = LotImageRepository(conn)

            if include_reviewed:
                records = token_repo.get_for_training(limit=limit or 10000)
            else:
                records = token_repo.get_all_for_export(limit=limit)

            export_data: dict[str, Any] = {
                "version": "1.0",
                "images": [],
            }

            for record in records:
                # Get the corresponding image for lot_id
                image = self._fetch_one_as_dict(
                    conn,
                    "SELECT lot_id, local_path FROM lot_images WHERE id = ?",
                    (record.lot_image_id,),
                )
                if image:
                    export_data["images"].append({
                        "lot_image_id": record.lot_image_id,
                        "lot_id": image.get("lot_id"),
                        "local_path": image.get("local_path"),
                        "tokens": record.tokens,
                        "has_labels": record.has_labels,
                    })

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        logger.info(
            "Exported token data",
            extra={"path": str(output_path), "records": len(export_data["images"])},
        )
        return len(export_data["images"])

    def get_stats(self) -> dict:
        """Get current statistics for all image-related data.

        Returns:
            Dictionary with image, code, and token statistics.
        """
        with self._connection_factory() as conn:
            image_repo = LotImageRepository(conn)
            code_repo = ExtractedCodeRepository(conn)
            token_repo = OcrTokenRepository(conn)

            return {
                "images": image_repo.get_stats(),
                "codes": code_repo.get_approval_stats(),
                "tokens": token_repo.get_stats(),
            }

    def promote_codes_to_lots(self, limit: int = 100) -> dict[str, int]:
        """Promote approved codes to lot records.

        This updates the lots table with extracted EAN codes, serial numbers,
        and model numbers from approved extracted_codes.

        Args:
            limit: Maximum number of codes to process.

        Returns:
            Dictionary with counts of promoted codes by type.
        """
        promoted: dict[str, int] = {
            "ean": 0,
            "serial_number": 0,
            "model_number": 0,
            "product_code": 0,
            "total": 0,
        }

        with self._connection_factory() as conn:
            code_repo = ExtractedCodeRepository(conn)

            # Get approved codes that haven't been promoted
            codes = code_repo.get_approved_for_promotion(limit=limit)

            for code in codes:
                # Get the lot_id for this image
                lot_info = self._fetch_one_as_dict(
                    conn,
                    "SELECT lot_id FROM lot_images WHERE id = ?",
                    (code.lot_image_id,),
                )
                if not lot_info:
                    continue

                lot_id = lot_info["lot_id"]

                # Update the lot based on code type
                if code.code_type == "ean":
                    # Check if lot already has this EAN in specs
                    existing = self._fetch_one_as_dict(
                        conn,
                        "SELECT id FROM product_specs WHERE lot_id = ? AND key = 'ean' AND value = ?",
                        (lot_id, code.value),
                    )
                    if not existing:
                        conn.execute(
                            """
                            INSERT INTO product_specs (lot_id, key, value, source)
                            VALUES (?, 'ean', ?, 'ocr')
                            """,
                            (lot_id, code.value),
                        )
                        promoted["ean"] += 1

                elif code.code_type == "serial_number":
                    existing = self._fetch_one_as_dict(
                        conn,
                        "SELECT id FROM product_specs WHERE lot_id = ? AND key = 'serial_number' AND value = ?",
                        (lot_id, code.value),
                    )
                    if not existing:
                        conn.execute(
                            """
                            INSERT INTO product_specs (lot_id, key, value, source)
                            VALUES (?, 'serial_number', ?, 'ocr')
                            """,
                            (lot_id, code.value),
                        )
                        promoted["serial_number"] += 1

                elif code.code_type == "model_number":
                    existing = self._fetch_one_as_dict(
                        conn,
                        "SELECT id FROM product_specs WHERE lot_id = ? AND key = 'model_number' AND value = ?",
                        (lot_id, code.value),
                    )
                    if not existing:
                        conn.execute(
                            """
                            INSERT INTO product_specs (lot_id, key, value, source)
                            VALUES (?, 'model_number', ?, 'ocr')
                            """,
                            (lot_id, code.value),
                        )
                        promoted["model_number"] += 1

                elif code.code_type == "product_code":
                    existing = self._fetch_one_as_dict(
                        conn,
                        "SELECT id FROM product_specs WHERE lot_id = ? AND key = 'product_code' AND value = ?",
                        (lot_id, code.value),
                    )
                    if not existing:
                        conn.execute(
                            """
                            INSERT INTO product_specs (lot_id, key, value, source)
                            VALUES (?, 'product_code', ?, 'ocr')
                            """,
                            (lot_id, code.value),
                        )
                        promoted["product_code"] += 1

                # Mark code as promoted
                code_repo.mark_promoted(code.id)
                promoted["total"] += 1

            conn.commit()

        logger.info(
            "Promoted codes to lots",
            extra=promoted,
        )
        return promoted

    # -------------------------------------------------------------------------
    # Image Deduplication via Perceptual Hashing
    # -------------------------------------------------------------------------

    def compute_image_hashes(
        self,
        limit: int = 100,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> HashStats:
        """Compute perceptual hashes for downloaded images.

        This computes pHash values for images that don't have one yet,
        enabling later duplicate detection.

        Args:
            limit: Maximum number of images to process.
            progress_callback: Optional callback(done, total) for progress.

        Returns:
            Statistics about the hashing operation.
        """
        if not HASH_AVAILABLE:
            logger.warning("PIL not available, cannot compute image hashes")
            return HashStats()

        stats = HashStats()

        with self._connection_factory() as conn:
            image_repo = LotImageRepository(conn)
            pending = image_repo.get_images_without_phash(limit=limit)
            stats.images_processed = len(pending)

            for i, image in enumerate(pending):
                if not image.local_path:
                    stats.images_failed += 1
                    continue

                try:
                    phash = compute_phash(image.local_path)
                    if phash:
                        image_repo.update_phash(image.id, phash)
                        stats.images_hashed += 1
                    else:
                        stats.images_failed += 1
                        logger.warning(
                            "Failed to compute phash",
                            extra={"image_id": image.id, "path": image.local_path},
                        )
                except Exception as e:
                    stats.images_failed += 1
                    logger.error(
                        "Error computing phash",
                        extra={"image_id": image.id, "error": str(e)},
                    )

                if progress_callback:
                    progress_callback(i + 1, len(pending))

            conn.commit()

        logger.info(
            "Image hash batch complete",
            extra={
                "processed": stats.images_processed,
                "hashed": stats.images_hashed,
                "failed": stats.images_failed,
            },
        )
        return stats

    def find_duplicate_images(
        self,
        threshold: int = 10,
    ) -> list[DuplicateGroup]:
        """Find groups of perceptually similar images.

        Uses Hamming distance on pHash values to identify duplicates.
        Images within the threshold distance are considered duplicates.

        Args:
            threshold: Maximum Hamming distance to consider as duplicate.
                       0 = exact match only, 10 = fairly similar.

        Returns:
            List of DuplicateGroup objects containing similar images.
        """
        if not HASH_AVAILABLE:
            logger.warning("PIL not available, cannot find duplicates")
            return []

        with self._connection_factory() as conn:
            image_repo = LotImageRepository(conn)

            if threshold == 0:
                # Exact match - use database grouping
                db_duplicates = image_repo.find_duplicates_by_phash()
                groups = []
                for phash, images in db_duplicates:
                    lot_ids = list(set(img.lot_id for img in images))
                    groups.append(DuplicateGroup(
                        phash=phash,
                        images=images,
                        lot_ids=lot_ids,
                    ))
                return groups

            # Fuzzy matching - need to compare hashes using Hamming distance
            all_images = image_repo.get_all_with_phash()

            if not all_images:
                return []

            # Build hash-to-images mapping
            hash_map: dict[str, list[LotImage]] = {}
            for img in all_images:
                if img.phash:
                    if img.phash not in hash_map:
                        hash_map[img.phash] = []
                    hash_map[img.phash].append(img)

            # Find similar hashes using Hamming distance clustering
            # We use union-find to group similar hashes
            hashes = list(hash_map.keys())

            # Union-find for clustering
            parent: dict[str, str] = {h: h for h in hashes}

            def find(x: str) -> str:
                if parent[x] != x:
                    parent[x] = find(parent[x])
                return parent[x]

            def union(x: str, y: str) -> None:
                px, py = find(x), find(y)
                if px != py:
                    parent[px] = py

            # Compare all pairs and union similar ones
            for i, h1 in enumerate(hashes):
                for h2 in hashes[i + 1:]:
                    try:
                        dist = hamming_distance(h1, h2)
                        if dist <= threshold:
                            union(h1, h2)
                    except ValueError:
                        # Different length hashes, skip
                        continue

            # Group hashes by their root
            clusters: dict[str, list[str]] = {}
            for h in hashes:
                root = find(h)
                if root not in clusters:
                    clusters[root] = []
                clusters[root].append(h)

            # Build duplicate groups from clusters with multiple hashes
            groups = []
            for root, cluster_hashes in clusters.items():
                cluster_images = []
                for h in cluster_hashes:
                    cluster_images.extend(hash_map.get(h, []))

                if len(cluster_images) > 1:
                    lot_ids = list(set(img.lot_id for img in cluster_images))
                    groups.append(DuplicateGroup(
                        phash=cluster_hashes[0],  # Use first hash as representative
                        images=cluster_images,
                        lot_ids=lot_ids,
                    ))

            # Sort by number of duplicates (most first)
            groups.sort(key=lambda g: g.count, reverse=True)
            return groups

    def get_duplicate_stats(self) -> dict[str, int]:
        """Get statistics about duplicate images.

        Returns:
            Dictionary with duplicate-related counts.
        """
        with self._connection_factory() as conn:
            image_repo = LotImageRepository(conn)

            # Count images with phash
            cur = conn.execute(
                "SELECT COUNT(*) FROM lot_images WHERE phash IS NOT NULL"
            )
            with_phash = cur.fetchone()[0]

            # Count images without phash
            cur = conn.execute(
                """
                SELECT COUNT(*) FROM lot_images
                WHERE download_status = 'downloaded' AND phash IS NULL
                """
            )
            without_phash = cur.fetchone()[0]

            # Count unique hashes
            cur = conn.execute(
                "SELECT COUNT(DISTINCT phash) FROM lot_images WHERE phash IS NOT NULL"
            )
            unique_hashes = cur.fetchone()[0]

            # Count exact duplicates (same phash appears multiple times)
            cur = conn.execute(
                """
                SELECT COUNT(*) FROM (
                    SELECT phash, COUNT(*) as cnt
                    FROM lot_images
                    WHERE phash IS NOT NULL
                    GROUP BY phash
                    HAVING cnt > 1
                )
                """
            )
            duplicate_groups = cur.fetchone()[0]

            # Count images that are duplicates
            cur = conn.execute(
                """
                SELECT SUM(cnt) FROM (
                    SELECT phash, COUNT(*) as cnt
                    FROM lot_images
                    WHERE phash IS NOT NULL
                    GROUP BY phash
                    HAVING cnt > 1
                )
                """
            )
            row = cur.fetchone()
            duplicate_images = row[0] if row[0] else 0

        return {
            "with_phash": with_phash,
            "without_phash": without_phash,
            "unique_hashes": unique_hashes,
            "duplicate_groups": duplicate_groups,
            "duplicate_images": duplicate_images,
        }

    def _calculate_confidence(self, codes: list[ExtractedCode]) -> float:
        """Calculate average confidence score from extracted codes.

        Args:
            codes: List of extracted codes.

        Returns:
            Average confidence as a float (0.0 to 1.0).
        """
        if not codes:
            return 0.0

        confidence_map = {"high": 1.0, "medium": 0.6, "low": 0.3}
        total = sum(confidence_map.get(c.confidence, 0.5) for c in codes)
        return total / len(codes)

    def _fetch_one_as_dict(
        self,
        conn,
        query: str,
        params: tuple = (),
    ) -> dict | None:
        """Helper to fetch a single row as a dict."""
        cur = conn.execute(query, params)
        row = cur.fetchone()
        if not row:
            return None
        columns = [c[0] for c in cur.description]
        return dict(zip(columns, row))


__all__ = [
    "AnalysisStats",
    "DownloadStats",
    "DuplicateGroup",
    "HashStats",
    "ImageAnalysisService",
]
