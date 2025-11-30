"""Repository for lot images, extracted codes, and OCR token data.

This module provides database access for the image analysis pipeline:
- LotImageRepository: Manage lot image URLs and local paths
- ExtractedCodeRepository: Store product codes extracted from images
- OcrTokenRepository: Store raw OCR token data for ML training
"""

# flake8: noqa: E501  # SQL-heavy repository; long SQL strings intentionally formatted for readability

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .base import BaseRepository


@dataclass
class LotImage:
    """A lot image record."""

    id: int
    lot_id: int
    url: str
    local_path: str | None
    position: int
    download_status: str
    analysis_status: str
    analysis_backend: str | None
    analyzed_at: str | None
    error_message: str | None
    phash: str | None
    created_at: str
    updated_at: str | None


@dataclass
class ExtractedCode:
    """An extracted product code from an image."""

    id: int
    lot_image_id: int
    code_type: str
    value: str
    confidence: str
    context: str | None
    created_at: str
    approved: bool = False
    approved_at: str | None = None
    approved_by: str | None = None  # 'auto', 'manual', 'openai'
    promoted_to_lot: bool = False


@dataclass
class OcrTokenData:
    """Raw OCR token data for ML training."""

    id: int
    lot_image_id: int
    tokens: dict[str, Any]  # Parsed from tokens_json
    token_count: int
    has_labels: bool
    created_at: str


class LotImageRepository(BaseRepository):
    """Repository for lot image records."""

    def insert_images(self, lot_id: int, image_urls: list[str]) -> list[int]:
        """Insert image URLs for a lot, returning the inserted IDs.

        Skips URLs that already exist for this lot (upsert behavior).

        Args:
            lot_id: The lot ID to associate images with
            image_urls: List of image URLs to insert

        Returns:
            List of inserted image IDs
        """
        inserted_ids: list[int] = []
        for position, url in enumerate(image_urls):
            cur = self.conn.execute(
                """
                INSERT INTO lot_images (lot_id, url, position)
                VALUES (?, ?, ?)
                ON CONFLICT (lot_id, url) DO UPDATE SET
                    position = excluded.position,
                    updated_at = datetime('now')
                RETURNING id
                """,
                (lot_id, url, position),
            )
            row = cur.fetchone()
            if row:
                inserted_ids.append(row[0])
        return inserted_ids

    def get_by_lot_id(self, lot_id: int) -> list[LotImage]:
        """Get all images for a lot, ordered by position."""
        rows = self._fetch_all_as_dicts(
            """
            SELECT * FROM lot_images
            WHERE lot_id = ?
            ORDER BY position
            """,
            (lot_id,),
        )
        return [self._row_to_image(row) for row in rows]

    def get_by_id(self, image_id: int) -> LotImage | None:
        """Get a single image by ID."""
        row = self._fetch_one_as_dict(
            "SELECT * FROM lot_images WHERE id = ?",
            (image_id,),
        )
        if not row or row.get("id") is None:
            return None
        return self._row_to_image(row)

    def get_pending_download(self, limit: int = 100) -> list[LotImage]:
        """Get images that need to be downloaded."""
        rows = self._fetch_all_as_dicts(
            """
            SELECT * FROM lot_images
            WHERE download_status = 'pending'
            ORDER BY created_at
            LIMIT ?
            """,
            (limit,),
        )
        return [self._row_to_image(row) for row in rows]

    def get_pending_analysis(self, limit: int = 100) -> list[LotImage]:
        """Get images that are downloaded but not yet analyzed."""
        rows = self._fetch_all_as_dicts(
            """
            SELECT * FROM lot_images
            WHERE download_status = 'downloaded'
              AND analysis_status = 'pending'
            ORDER BY created_at
            LIMIT ?
            """,
            (limit,),
        )
        return [self._row_to_image(row) for row in rows]

    def get_needs_review(self, limit: int = 100) -> list[LotImage]:
        """Get images that need manual review or OpenAI analysis."""
        rows = self._fetch_all_as_dicts(
            """
            SELECT * FROM lot_images
            WHERE analysis_status = 'needs_review'
            ORDER BY created_at
            LIMIT ?
            """,
            (limit,),
        )
        return [self._row_to_image(row) for row in rows]

    def get_failed(self, limit: int = 100) -> list[LotImage]:
        """Get images that failed download or analysis."""
        rows = self._fetch_all_as_dicts(
            """
            SELECT * FROM lot_images
            WHERE download_status = 'failed' OR analysis_status = 'failed'
            ORDER BY created_at
            LIMIT ?
            """,
            (limit,),
        )
        return [self._row_to_image(row) for row in rows]

    def mark_downloaded(self, image_id: int, local_path: str) -> None:
        """Mark an image as successfully downloaded."""
        self.conn.execute(
            """
            UPDATE lot_images
            SET download_status = 'downloaded',
                local_path = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (local_path, image_id),
        )

    def mark_download_failed(self, image_id: int, error: str) -> None:
        """Mark an image download as failed."""
        self.conn.execute(
            """
            UPDATE lot_images
            SET download_status = 'failed',
                error_message = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (error, image_id),
        )

    def mark_analyzed(
        self,
        image_id: int,
        backend: str,
        status: str = "analyzed",
    ) -> None:
        """Mark an image as analyzed.

        Args:
            image_id: The image ID
            backend: The analysis backend used ('local', 'openai', 'ml')
            status: The analysis status ('analyzed', 'needs_review')
        """
        self.conn.execute(
            """
            UPDATE lot_images
            SET analysis_status = ?,
                analysis_backend = ?,
                analyzed_at = datetime('now'),
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (status, backend, image_id),
        )

    def mark_analysis_failed(self, image_id: int, error: str) -> None:
        """Mark image analysis as failed."""
        self.conn.execute(
            """
            UPDATE lot_images
            SET analysis_status = 'failed',
                error_message = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (error, image_id),
        )

    def reset_for_reprocessing(self, image_id: int) -> None:
        """Reset an image for reprocessing (clears analysis status)."""
        self.conn.execute(
            """
            UPDATE lot_images
            SET analysis_status = 'pending',
                analyzed_at = NULL,
                error_message = NULL,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (image_id,),
        )

    def update_phash(self, image_id: int, phash: str) -> None:
        """Update the perceptual hash for an image."""
        self.conn.execute(
            """
            UPDATE lot_images
            SET phash = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (phash, image_id),
        )

    def get_by_phash(self, phash: str) -> list[LotImage]:
        """Get all images with a specific phash (exact match)."""
        rows = self._fetch_all_as_dicts(
            """
            SELECT * FROM lot_images
            WHERE phash = ?
            ORDER BY created_at
            """,
            (phash,),
        )
        return [self._row_to_image(row) for row in rows]

    def get_all_with_phash(self, limit: int | None = None) -> list[LotImage]:
        """Get all images that have a computed phash."""
        query = """
            SELECT * FROM lot_images
            WHERE phash IS NOT NULL
            ORDER BY created_at
        """
        params: tuple[Any, ...] = ()
        if limit:
            query += " LIMIT ?"
            params = (limit,)
        rows = self._fetch_all_as_dicts(query, params)
        return [self._row_to_image(row) for row in rows]

    def get_images_without_phash(self, limit: int = 100) -> list[LotImage]:
        """Get downloaded images that don't have a phash yet."""
        rows = self._fetch_all_as_dicts(
            """
            SELECT * FROM lot_images
            WHERE download_status = 'downloaded'
              AND phash IS NULL
            ORDER BY created_at
            LIMIT ?
            """,
            (limit,),
        )
        return [self._row_to_image(row) for row in rows]

    def find_duplicates_by_phash(self) -> list[tuple[str, list[LotImage]]]:
        """Find groups of images with the same phash (duplicates).

        Returns:
            List of tuples (phash, list of images with that phash)
            Only includes phashes that appear more than once.
        """
        # First get phashes that appear more than once
        dup_cursor = self.conn.execute(
            """
            SELECT phash, COUNT(*) as cnt
            FROM lot_images
            WHERE phash IS NOT NULL
            GROUP BY phash
            HAVING cnt > 1
            ORDER BY cnt DESC
            """
        )
        dup_phashes = [row[0] for row in dup_cursor.fetchall()]

        if not dup_phashes:
            return []

        # For each duplicate phash, get all images
        results: list[tuple[str, list[LotImage]]] = []
        for phash in dup_phashes:
            images = self.get_by_phash(phash)
            results.append((phash, images))

        return results

    def get_stats(self) -> dict[str, int]:
        """Get counts by status for dashboard display."""
        cur = self.conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN download_status = 'pending' THEN 1 ELSE 0 END) as pending_download,
                SUM(CASE WHEN download_status = 'downloaded' THEN 1 ELSE 0 END) as downloaded,
                SUM(CASE WHEN download_status = 'failed' THEN 1 ELSE 0 END) as download_failed,
                SUM(CASE WHEN analysis_status = 'pending' THEN 1 ELSE 0 END) as pending_analysis,
                SUM(CASE WHEN analysis_status = 'analyzed' THEN 1 ELSE 0 END) as analyzed,
                SUM(CASE WHEN analysis_status = 'needs_review' THEN 1 ELSE 0 END) as needs_review,
                SUM(CASE WHEN analysis_status = 'failed' THEN 1 ELSE 0 END) as analysis_failed
            FROM lot_images
            """
        )
        row = cur.fetchone()
        return {
            "total": row[0] or 0,
            "pending_download": row[1] or 0,
            "downloaded": row[2] or 0,
            "download_failed": row[3] or 0,
            "pending_analysis": row[4] or 0,
            "analyzed": row[5] or 0,
            "needs_review": row[6] or 0,
            "analysis_failed": row[7] or 0,
        }

    def _row_to_image(self, row: dict[str, Any]) -> LotImage:
        """Convert a database row to a LotImage dataclass."""
        return LotImage(
            id=row["id"],
            lot_id=row["lot_id"],
            url=row["url"],
            local_path=row["local_path"],
            position=row["position"],
            download_status=row["download_status"],
            analysis_status=row["analysis_status"],
            analysis_backend=row["analysis_backend"],
            analyzed_at=row["analyzed_at"],
            error_message=row["error_message"],
            phash=row.get("phash"),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


class ExtractedCodeRepository(BaseRepository):
    """Repository for extracted product codes."""

    def insert_code(
        self,
        lot_image_id: int,
        code_type: str,
        value: str,
        confidence: str = "medium",
        context: str | None = None,
    ) -> int:
        """Insert an extracted code and return its ID."""
        cur = self.conn.execute(
            """
            INSERT INTO extracted_codes (lot_image_id, code_type, value, confidence, context)
            VALUES (?, ?, ?, ?, ?)
            RETURNING id
            """,
            (lot_image_id, code_type, value, confidence, context),
        )
        row = cur.fetchone()
        return row[0] if row else 0

    def insert_codes(
        self,
        lot_image_id: int,
        codes: list[dict[str, Any]],
    ) -> list[int]:
        """Insert multiple extracted codes.

        Args:
            lot_image_id: The image ID
            codes: List of dicts with code_type, value, confidence, context

        Returns:
            List of inserted IDs
        """
        inserted_ids: list[int] = []
        for code in codes:
            code_id = self.insert_code(
                lot_image_id=lot_image_id,
                code_type=code.get("code_type", "other"),
                value=code.get("value", ""),
                confidence=code.get("confidence", "medium"),
                context=code.get("context"),
            )
            inserted_ids.append(code_id)
        return inserted_ids

    def bulk_insert_codes(
        self,
        codes: list[tuple[int, str, str, str, str | None]],
    ) -> int:
        """Bulk insert extracted codes for maximum performance.

        Uses executemany for efficient batch insertion.

        Args:
            codes: List of tuples (lot_image_id, code_type, value, confidence, context)

        Returns:
            Number of codes inserted
        """
        if not codes:
            return 0

        self.conn.executemany(
            """
            INSERT INTO extracted_codes (lot_image_id, code_type, value, confidence, context)
            VALUES (?, ?, ?, ?, ?)
            """,
            codes,
        )
        return len(codes)

    def get_by_image_id(self, lot_image_id: int) -> list[ExtractedCode]:
        """Get all codes extracted from an image."""
        rows = self._fetch_all_as_dicts(
            """
            SELECT * FROM extracted_codes
            WHERE lot_image_id = ?
            ORDER BY code_type, value
            """,
            (lot_image_id,),
        )
        return [self._row_to_code(row) for row in rows]

    def get_by_lot_id(self, lot_id: int) -> list[ExtractedCode]:
        """Get all codes for a lot (across all images)."""
        rows = self._fetch_all_as_dicts(
            """
            SELECT ec.* FROM extracted_codes ec
            JOIN lot_images li ON ec.lot_image_id = li.id
            WHERE li.lot_id = ?
            ORDER BY ec.code_type, ec.value
            """,
            (lot_id,),
        )
        return [self._row_to_code(row) for row in rows]

    def delete_by_image_id(self, lot_image_id: int) -> int:
        """Delete all codes for an image (before reprocessing)."""
        cur = self.conn.execute(
            "DELETE FROM extracted_codes WHERE lot_image_id = ?",
            (lot_image_id,),
        )
        return cur.rowcount

    def _row_to_code(self, row: dict[str, Any]) -> ExtractedCode:
        """Convert a database row to an ExtractedCode dataclass."""
        return ExtractedCode(
            id=row["id"],
            lot_image_id=row["lot_image_id"],
            code_type=row["code_type"],
            value=row["value"],
            confidence=row["confidence"],
            context=row["context"],
            created_at=row["created_at"],
            approved=bool(row.get("approved", 0)),
            approved_at=row.get("approved_at"),
            approved_by=row.get("approved_by"),
            promoted_to_lot=bool(row.get("promoted_to_lot", 0)),
        )

    def approve_code(
        self,
        code_id: int,
        approved_by: str = "manual",
    ) -> None:
        """Mark a code as approved."""
        self.conn.execute(
            """
            UPDATE extracted_codes
            SET approved = 1,
                approved_at = datetime('now'),
                approved_by = ?
            WHERE id = ?
            """,
            (approved_by, code_id),
        )

    def approve_codes_by_image(
        self,
        lot_image_id: int,
        approved_by: str = "auto",
    ) -> int:
        """Approve all codes for an image. Returns count of approved codes."""
        cur = self.conn.execute(
            """
            UPDATE extracted_codes
            SET approved = 1,
                approved_at = datetime('now'),
                approved_by = ?
            WHERE lot_image_id = ? AND approved = 0
            """,
            (approved_by, lot_image_id),
        )
        return cur.rowcount

    def get_unapproved(self, limit: int = 100) -> list[ExtractedCode]:
        """Get codes that need manual approval."""
        rows = self._fetch_all_as_dicts(
            """
            SELECT * FROM extracted_codes
            WHERE approved = 0
            ORDER BY created_at
            LIMIT ?
            """,
            (limit,),
        )
        return [self._row_to_code(row) for row in rows]

    def get_approved_for_promotion(self, limit: int = 100) -> list[ExtractedCode]:
        """Get approved codes that haven't been promoted to lots yet."""
        rows = self._fetch_all_as_dicts(
            """
            SELECT * FROM extracted_codes
            WHERE approved = 1 AND promoted_to_lot = 0
            ORDER BY created_at
            LIMIT ?
            """,
            (limit,),
        )
        return [self._row_to_code(row) for row in rows]

    def mark_promoted(self, code_id: int) -> None:
        """Mark a code as promoted to the lot record."""
        self.conn.execute(
            """
            UPDATE extracted_codes
            SET promoted_to_lot = 1
            WHERE id = ?
            """,
            (code_id,),
        )

    def get_approval_stats(self) -> dict[str, int]:
        """Get statistics about code approvals."""
        cur = self.conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN approved = 1 THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN approved = 0 THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN promoted_to_lot = 1 THEN 1 ELSE 0 END) as promoted,
                SUM(CASE WHEN approved_by = 'auto' THEN 1 ELSE 0 END) as auto_approved,
                SUM(CASE WHEN approved_by = 'manual' THEN 1 ELSE 0 END) as manually_approved
            FROM extracted_codes
            """
        )
        row = cur.fetchone()
        return {
            "total": row[0] or 0,
            "approved": row[1] or 0,
            "pending": row[2] or 0,
            "promoted": row[3] or 0,
            "auto_approved": row[4] or 0,
            "manually_approved": row[5] or 0,
            "approved_auto": row[4] or 0,
            "approved_manual": row[5] or 0,
            "rejected": 0,  # Not tracked separately yet
        }

    def get_by_id(self, code_id: int) -> ExtractedCode | None:
        """Get a single code by ID."""
        row = self._fetch_one_as_dict(
            "SELECT * FROM extracted_codes WHERE id = ?",
            (code_id,),
        )
        if not row or row.get("id") is None:
            return None
        return self._row_to_code(row)

    def get_pending_approval(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExtractedCode]:
        """Get codes pending approval with pagination."""
        rows = self._fetch_all_as_dicts(
            """
            SELECT * FROM extracted_codes
            WHERE approved = 0
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        return [self._row_to_code(row) for row in rows]

    def count_pending_approval(self) -> int:
        """Count total codes pending approval."""
        cur = self.conn.execute(
            "SELECT COUNT(*) FROM extracted_codes WHERE approved = 0"
        )
        row = cur.fetchone()
        return row[0] if row else 0

    def reject_code(self, code_id: int) -> None:
        """Reject a code by deleting it or marking it rejected.

        Currently we just leave it as not approved.
        Future: could add a rejected flag.
        """
        # For now, we don't delete - just ensure it stays unapproved
        # Could add a rejected_at column in future
        self.conn.execute(
            """
            UPDATE extracted_codes
            SET approved = 0,
                approved_by = NULL,
                approved_at = NULL
            WHERE id = ?
            """,
            (code_id,),
        )


class OcrTokenRepository(BaseRepository):
    """Repository for raw OCR token data (for ML training)."""

    def upsert_tokens(
        self,
        lot_image_id: int,
        tokens: dict[str, Any],
        has_labels: bool = False,
    ) -> int:
        """Insert or update OCR token data for an image.

        Args:
            lot_image_id: The image ID
            tokens: The pytesseract.image_to_data() output dict
            has_labels: Whether tokens have been manually labeled

        Returns:
            The record ID
        """
        tokens_json = json.dumps(tokens)
        token_count = len(tokens.get("text", []))

        cur = self.conn.execute(
            """
            INSERT INTO ocr_token_data (lot_image_id, tokens_json, token_count, has_labels)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (lot_image_id) DO UPDATE SET
                tokens_json = excluded.tokens_json,
                token_count = excluded.token_count,
                has_labels = CASE
                    WHEN excluded.has_labels = 1 THEN 1
                    ELSE ocr_token_data.has_labels
                END
            RETURNING id
            """,
            (lot_image_id, tokens_json, token_count, 1 if has_labels else 0),
        )
        row = cur.fetchone()
        return row[0] if row else 0

    def get_by_image_id(self, lot_image_id: int) -> OcrTokenData | None:
        """Get token data for an image."""
        row = self._fetch_one_as_dict(
            "SELECT * FROM ocr_token_data WHERE lot_image_id = ?",
            (lot_image_id,),
        )
        if not row or row.get("id") is None:
            return None
        return self._row_to_token_data(row)

    def get_for_training(self, limit: int = 1000) -> list[OcrTokenData]:
        """Get token data that has been labeled for training."""
        rows = self._fetch_all_as_dicts(
            """
            SELECT * FROM ocr_token_data
            WHERE has_labels = 1
            ORDER BY created_at
            LIMIT ?
            """,
            (limit,),
        )
        return [self._row_to_token_data(row) for row in rows]

    def get_all_for_export(self, limit: int | None = None) -> list[OcrTokenData]:
        """Get all token data for export (with or without labels)."""
        query = "SELECT * FROM ocr_token_data ORDER BY created_at"
        params: tuple[Any, ...] = ()
        if limit:
            query += " LIMIT ?"
            params = (limit,)
        rows = self._fetch_all_as_dicts(query, params)
        return [self._row_to_token_data(row) for row in rows]

    def mark_as_labeled(self, lot_image_id: int) -> None:
        """Mark token data as manually labeled."""
        self.conn.execute(
            "UPDATE ocr_token_data SET has_labels = 1 WHERE lot_image_id = ?",
            (lot_image_id,),
        )

    def get_stats(self) -> dict[str, int]:
        """Get statistics for token data."""
        cur = self.conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN has_labels = 1 THEN 1 ELSE 0 END) as labeled,
                SUM(token_count) as total_tokens
            FROM ocr_token_data
            """
        )
        row = cur.fetchone()
        return {
            "total": row[0] or 0,
            "labeled": row[1] or 0,
            "total_tokens": row[2] or 0,
        }

    def _row_to_token_data(self, row: dict[str, Any]) -> OcrTokenData:
        """Convert a database row to an OcrTokenData dataclass."""
        tokens_json = row.get("tokens_json", "{}")
        try:
            tokens = json.loads(tokens_json)
        except json.JSONDecodeError:
            tokens = {}

        return OcrTokenData(
            id=row["id"],
            lot_image_id=row["lot_image_id"],
            tokens=tokens,
            token_count=row["token_count"],
            has_labels=bool(row["has_labels"]),
            created_at=row["created_at"],
        )


__all__ = [
    "ExtractedCode",
    "ExtractedCodeRepository",
    "LotImage",
    "LotImageRepository",
    "OcrTokenData",
    "OcrTokenRepository",
]
