"""Image download and storage utilities.

This module provides functionality for downloading lot images from URLs
and storing them locally for OCR analysis and ML training.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from troostwatch.infrastructure.observability.logging import get_logger

if TYPE_CHECKING:
    from troostwatch.infrastructure.db.repositories.images import LotImage

logger = get_logger(__name__)


class ImageDownloader:
    """Downloads and stores lot images locally.

    Images are stored in a directory structure:
        {images_dir}/{lot_id}/{position}.{ext}

    The downloader supports both synchronous and async downloads,
    with configurable timeouts and retries.
    """

    # Default image size to download (high quality, but not maximum)
    DEFAULT_IMAGE_SIZE = "1024x768"

    # Supported image extensions
    EXTENSIONS = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
        "image/gif": ".gif",
    }

    def __init__(
        self,
        images_dir: str | Path,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        """Initialize the image downloader.

        Args:
            images_dir: Base directory for storing images.
            timeout: HTTP request timeout in seconds.
            max_retries: Maximum number of retry attempts.
        """
        self.images_dir = Path(images_dir)
        self.timeout = timeout
        self.max_retries = max_retries

    def _get_download_url(self, url: str, size: str | None = None) -> str:
        """Get the download URL with optional size parameter.

        Troostwijk URLs support size parameters:
            https://media.tbauctions.com/image-media/{uuid}/file?imageSize=1024x768

        Args:
            url: Base image URL
            size: Image size (e.g., "1024x768"). If None, downloads full size.

        Returns:
            URL with size parameter appended if specified.
        """
        if size and "?" not in url:
            return f"{url}?imageSize={size}"
        elif size and "imageSize" not in url:
            return f"{url}&imageSize={size}"
        return url

    def _get_local_path(
        self,
        lot_id: int,
        position: int,
        content_type: str | None = None,
    ) -> Path:
        """Get the local file path for an image.

        Args:
            lot_id: The lot ID.
            position: Image position (0-indexed).
            content_type: MIME type to determine extension.

        Returns:
            Path object for the local file.
        """
        ext = self.EXTENSIONS.get(content_type or "", ".jpg")
        lot_dir = self.images_dir / str(lot_id)
        return lot_dir / f"{position}{ext}"

    def download_image(
        self,
        url: str,
        lot_id: int,
        position: int,
        size: str | None = None,
    ) -> tuple[str | None, str | None]:
        """Download an image synchronously.

        Args:
            url: Image URL to download.
            lot_id: The lot ID (for directory structure).
            position: Image position (for filename).
            size: Optional image size parameter.

        Returns:
            Tuple of (local_path, error_message).
            On success: (path_string, None)
            On failure: (None, error_message)
        """
        download_url = self._get_download_url(url, size or self.DEFAULT_IMAGE_SIZE)

        for attempt in range(self.max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(download_url)
                    response.raise_for_status()

                    content_type = response.headers.get("content-type", "image/jpeg")
                    # Handle content-type with charset
                    if ";" in content_type:
                        content_type = content_type.split(";")[0].strip()

                    local_path = self._get_local_path(lot_id, position, content_type)

                    # Create directory if needed
                    local_path.parent.mkdir(parents=True, exist_ok=True)

                    # Write image data
                    with open(local_path, "wb") as f:
                        f.write(response.content)

                    logger.debug(
                        "Downloaded image",
                        extra={
                            "url": url,
                            "local_path": str(local_path),
                            "size_bytes": len(response.content),
                        },
                    )
                    return str(local_path), None

            except httpx.HTTPStatusError as e:
                error = f"HTTP {e.response.status_code}"
                if attempt == self.max_retries - 1:
                    logger.error(
                        "Failed to download image after retries",
                        extra={"url": url, "error": error, "attempts": attempt + 1},
                    )
                    return None, error

            except httpx.RequestError as e:
                error = str(e)
                if attempt == self.max_retries - 1:
                    logger.error(
                        "Failed to download image after retries",
                        extra={"url": url, "error": error, "attempts": attempt + 1},
                    )
                    return None, error

            except Exception as e:
                error = str(e)
                logger.error(
                    "Unexpected error downloading image",
                    extra={"url": url, "error": error},
                )
                return None, error

        return None, "Max retries exceeded"

    async def download_image_async(
        self,
        url: str,
        lot_id: int,
        position: int,
        size: str | None = None,
    ) -> tuple[str | None, str | None]:
        """Download an image asynchronously.

        Args:
            url: Image URL to download.
            lot_id: The lot ID (for directory structure).
            position: Image position (for filename).
            size: Optional image size parameter.

        Returns:
            Tuple of (local_path, error_message).
        """
        download_url = self._get_download_url(url, size or self.DEFAULT_IMAGE_SIZE)

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(download_url)
                    response.raise_for_status()

                    content_type = response.headers.get("content-type", "image/jpeg")
                    if ";" in content_type:
                        content_type = content_type.split(";")[0].strip()

                    local_path = self._get_local_path(lot_id, position, content_type)
                    local_path.parent.mkdir(parents=True, exist_ok=True)

                    with open(local_path, "wb") as f:
                        f.write(response.content)

                    logger.debug(
                        "Downloaded image (async)",
                        extra={
                            "url": url,
                            "local_path": str(local_path),
                            "size_bytes": len(response.content),
                        },
                    )
                    return str(local_path), None

            except httpx.HTTPStatusError as e:
                error = f"HTTP {e.response.status_code}"
                if attempt == self.max_retries - 1:
                    return None, error

            except httpx.RequestError as e:
                error = str(e)
                if attempt == self.max_retries - 1:
                    return None, error

            except Exception as e:
                return None, str(e)

        return None, "Max retries exceeded"

    def download_lot_image(
        self,
        image: "LotImage",
        size: str | None = None,
    ) -> tuple[str | None, str | None]:
        """Download a LotImage record.

        Convenience method that extracts lot_id and position from the record.

        Args:
            image: LotImage record to download.
            size: Optional image size parameter.

        Returns:
            Tuple of (local_path, error_message).
        """
        return self.download_image(
            url=image.url,
            lot_id=image.lot_id,
            position=image.position,
            size=size,
        )

    async def download_lot_image_async(
        self,
        image: "LotImage",
        size: str | None = None,
    ) -> tuple[str | None, str | None]:
        """Download a LotImage record asynchronously.

        Args:
            image: LotImage record to download.
            size: Optional image size parameter.

        Returns:
            Tuple of (local_path, error_message).
        """
        return await self.download_image_async(
            url=image.url,
            lot_id=image.lot_id,
            position=image.position,
            size=size,
        )


def get_image_hash(file_path: str | Path) -> str:
    """Compute SHA-256 hash of an image file.

    Useful for detecting duplicate images or changes.

    Args:
        file_path: Path to the image file.

    Returns:
        Hex-encoded SHA-256 hash string.
    """
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


__all__ = ["ImageDownloader", "get_image_hash"]
