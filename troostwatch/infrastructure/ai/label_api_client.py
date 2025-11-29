"""Client for the Label OCR API microservice.

This module provides a client for communicating with the separate
label_ocr_api FastAPI service that performs ML-based product code
extraction from images.

The service should be running at http://localhost:8001 (configurable).

Usage:
    client = LabelAPIClient()
    async with client:
        result = await client.parse_label_url("https://example.com/image.jpg")
        for code in result.codes:
            print(f"{code.code_type}: {code.value}")
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import httpx

from troostwatch.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)

# Default service URL (can be overridden via environment variable)
DEFAULT_SERVICE_URL = os.environ.get(
    "LABEL_OCR_API_URL", "http://localhost:8001")


@dataclass
class ExtractedCode:
    """A product code extracted from an image by the ML service."""

    code_type: Literal["ean", "serial_number",
                       "model_number", "part_number", "other"]
    value: str
    confidence: Literal["high", "medium", "low"]
    context: str | None = None


@dataclass
class ParseLabelResult:
    """Result from the Label OCR API."""

    codes: list[ExtractedCode] = field(default_factory=list)
    raw_text: str = ""
    processing_time_ms: int = 0
    error: str | None = None


@dataclass
class HealthStatus:
    """Health status of the Label OCR API service."""

    status: str
    model_loaded: bool
    tesseract_available: bool


class LabelAPIClient:
    """Async client for the Label OCR API microservice.

    This client communicates with the separate label_ocr_api service
    that provides ML-based product code extraction.

    The service must be running separately:
        cd label_ocr_api && uvicorn main:app --port 8001

    Attributes:
        base_url: The base URL of the Label OCR API service.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_SERVICE_URL,
        timeout: float = 30.0,
    ) -> None:
        """Initialize the Label API client.

        Args:
            base_url: Base URL of the service. Defaults to LABEL_OCR_API_URL
                     environment variable or http://localhost:8001.
            timeout: Request timeout in seconds.
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "LabelAPIClient":
        """Enter async context, creating HTTP client."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit async context, closing HTTP client."""
        await self.close()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> HealthStatus:
        """Check the health of the Label OCR API service.

        Returns:
            HealthStatus with service status information.

        Raises:
            httpx.HTTPError: If the service is not reachable.
        """
        client = await self._get_client()
        response = await client.get(f"{self.base_url}/health")
        response.raise_for_status()
        data = response.json()
        return HealthStatus(
            status=data.get("status", "unknown"),
            model_loaded=data.get("model_loaded", False),
            tesseract_available=data.get("tesseract_available", False),
        )

    async def is_available(self) -> bool:
        """Check if the Label OCR API service is available.

        Returns:
            True if the service is reachable and healthy.
        """
        try:
            status = await self.health_check()
            return status.status in ("ok", "degraded")
        except Exception as e:
            logger.debug("Label OCR API not available: %s", str(e))
            return False

    async def parse_label_url(self, image_url: str) -> ParseLabelResult:
        """Parse a product label from an image URL.

        Args:
            image_url: URL of the image to analyze.

        Returns:
            ParseLabelResult with extracted codes.
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/parse-label/url",
                json={"image_url": image_url},
            )
            response.raise_for_status()
            return self._parse_response(response.json())

        except httpx.HTTPStatusError as e:
            logger.error(
                "Label API error: status=%d, url=%s",
                e.response.status_code,
                image_url,
            )
            return ParseLabelResult(
                error=f"API error: {e.response.status_code}",
            )
        except httpx.ConnectError:
            logger.error("Label OCR API not reachable at %s", self.base_url)
            return ParseLabelResult(
                error=f"Service not reachable at {self.base_url}",
            )
        except Exception as e:
            logger.error("Label API request failed: %s", str(e))
            return ParseLabelResult(error=str(e))

    async def parse_label_file(self, image_path: str | Path) -> ParseLabelResult:
        """Parse a product label from a local image file.

        Args:
            image_path: Path to the local image file.

        Returns:
            ParseLabelResult with extracted codes.
        """
        path = Path(image_path)
        if not path.exists():
            return ParseLabelResult(error=f"File not found: {path}")

        # Determine MIME type
        suffix = path.suffix.lower()
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }
        mime_type = mime_types.get(suffix, "image/jpeg")

        try:
            client = await self._get_client()
            with open(path, "rb") as f:
                files = {"file": (path.name, f, mime_type)}
                response = await client.post(
                    f"{self.base_url}/parse-label",
                    files=files,
                )
            response.raise_for_status()
            return self._parse_response(response.json())

        except httpx.HTTPStatusError as e:
            logger.error(
                "Label API error: status=%d, path=%s",
                e.response.status_code,
                path,
            )
            return ParseLabelResult(
                error=f"API error: {e.response.status_code}",
            )
        except httpx.ConnectError:
            logger.error("Label OCR API not reachable at %s", self.base_url)
            return ParseLabelResult(
                error=f"Service not reachable at {self.base_url}",
            )
        except Exception as e:
            logger.error("Label API request failed: %s", str(e))
            return ParseLabelResult(error=str(e))

    async def parse_label_bytes(
        self,
        image_data: bytes,
        filename: str = "image.jpg",
        mime_type: str = "image/jpeg",
    ) -> ParseLabelResult:
        """Parse a product label from image bytes.

        Args:
            image_data: Raw image bytes.
            filename: Filename to use in the upload.
            mime_type: MIME type of the image.

        Returns:
            ParseLabelResult with extracted codes.
        """
        try:
            client = await self._get_client()
            files = {"file": (filename, image_data, mime_type)}
            response = await client.post(
                f"{self.base_url}/parse-label",
                files=files,
            )
            response.raise_for_status()
            return self._parse_response(response.json())

        except httpx.HTTPStatusError as e:
            logger.error("Label API error: status=%d", e.response.status_code)
            return ParseLabelResult(
                error=f"API error: {e.response.status_code}",
            )
        except httpx.ConnectError:
            logger.error("Label OCR API not reachable at %s", self.base_url)
            return ParseLabelResult(
                error=f"Service not reachable at {self.base_url}",
            )
        except Exception as e:
            logger.error("Label API request failed: %s", str(e))
            return ParseLabelResult(error=str(e))

    def _parse_response(self, data: dict) -> ParseLabelResult:
        """Parse the API response into a ParseLabelResult."""
        codes = []
        for code_data in data.get("codes", []):
            code_type = code_data.get("code_type", "other")
            # Normalize code_type to expected values
            if code_type not in ("ean", "serial_number", "model_number", "part_number"):
                code_type = "other"

            confidence = code_data.get("confidence", "medium")
            if confidence not in ("high", "medium", "low"):
                confidence = "medium"

            codes.append(
                ExtractedCode(
                    code_type=code_type,
                    value=code_data.get("value", ""),
                    confidence=confidence,
                    context=code_data.get("context"),
                )
            )

        return ParseLabelResult(
            codes=codes,
            raw_text=data.get("raw_text", ""),
            processing_time_ms=data.get("processing_time_ms", 0),
        )


# Convenience function for one-off requests
async def parse_label(
    image_path_or_url: str,
    service_url: str = DEFAULT_SERVICE_URL,
) -> ParseLabelResult:
    """Parse a product label from an image path or URL.

    Convenience function for one-off requests. For multiple requests,
    use LabelAPIClient as a context manager.

    Args:
        image_path_or_url: Local file path or URL of the image.
        service_url: URL of the Label OCR API service.

    Returns:
        ParseLabelResult with extracted codes.
    """
    async with LabelAPIClient(base_url=service_url) as client:
        if image_path_or_url.startswith(("http://", "https://")):
            return await client.parse_label_url(image_path_or_url)
        else:
            return await client.parse_label_file(image_path_or_url)


__all__ = [
    "ExtractedCode",
    "HealthStatus",
    "LabelAPIClient",
    "ParseLabelResult",
    "parse_label",
]
