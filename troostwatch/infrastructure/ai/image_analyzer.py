"""Image analysis using OpenAI Vision API.

This module provides functionality to analyze lot images and extract
product codes, model numbers, and EAN codes using GPT-4 Vision.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass, field
from typing import Literal

import httpx

from troostwatch.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractedCode:
    """A single extracted code from an image."""

    code_type: Literal["product_code", "model_number", "ean", "serial_number", "other"]
    value: str
    confidence: Literal["high", "medium", "low"]
    context: str | None = None  # Where on the image this was found


@dataclass
class ImageAnalysisResult:
    """Result of analyzing an image for product codes."""

    image_url: str
    codes: list[ExtractedCode] = field(default_factory=list)
    raw_text: str | None = None  # Any other text found in the image
    error: str | None = None


class ImageAnalyzer:
    """Analyzes images using OpenAI's GPT-4 Vision API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        timeout: float = 30.0,
    ) -> None:
        """Initialize the image analyzer.

        Args:
            api_key: OpenAI API key. Defaults to OPENAI_API_KEY env var.
            model: Model to use for vision analysis.
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

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

    async def analyze_image_url(self, image_url: str) -> ImageAnalysisResult:
        """Analyze an image URL for product codes.

        Args:
            image_url: URL of the image to analyze.

        Returns:
            ImageAnalysisResult with extracted codes.
        """
        if not self.api_key:
            return ImageAnalysisResult(
                image_url=image_url,
                error="OpenAI API key not configured",
            )

        prompt = """Analyseer deze afbeelding van een veilingitem en zoek naar:

1. **Productcodes** - Fabrikant artikelnummers (bijv. SM-G991B, WM75A)
2. **Modelnummers** - Model identificaties op labels of typeplaten
3. **EAN/barcode nummers** - 13-cijferige EAN codes of andere barcodes
4. **Serienummers** - Unieke apparaat identificaties

Let vooral op:
- Labels en stickers op het product
- Typeplaten met technische informatie
- Verpakkingen met barcodes
- Beeldschermen die codes tonen

Geef je antwoord in het volgende JSON formaat:
{
    "codes": [
        {
            "type": "product_code|model_number|ean|serial_number|other",
            "value": "de gevonden code",
            "confidence": "high|medium|low",
            "context": "waar op de afbeelding (bijv. 'label op achterkant', 'verpakking')"
        }
    ],
    "raw_text": "eventuele andere relevante tekst op de afbeelding"
}

Als je geen codes kunt vinden, geef dan een leeg codes array terug.
Wees nauwkeurig - alleen codes die je duidelijk kunt lezen."""

        try:
            client = await self._get_client()
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {"url": image_url, "detail": "high"},
                                },
                            ],
                        }
                    ],
                    "max_tokens": 1000,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            return self._parse_response(image_url, content)

        except httpx.HTTPStatusError as e:
            logger.error(
                "OpenAI API error: status_code=%s, detail=%s",
                e.response.status_code,
                e.response.text[:200],
            )
            return ImageAnalysisResult(
                image_url=image_url,
                error=f"API error: {e.response.status_code}",
            )
        except Exception as e:
            logger.error("Image analysis failed: %s", str(e))
            return ImageAnalysisResult(
                image_url=image_url,
                error=f"Analysis failed: {str(e)}",
            )

    async def analyze_image_bytes(
        self, image_data: bytes, mime_type: str = "image/jpeg"
    ) -> ImageAnalysisResult:
        """Analyze image bytes for product codes.

        Args:
            image_data: Raw image bytes.
            mime_type: MIME type of the image.

        Returns:
            ImageAnalysisResult with extracted codes.
        """
        base64_image = base64.b64encode(image_data).decode("utf-8")
        data_url = f"data:{mime_type};base64,{base64_image}"
        return await self.analyze_image_url(data_url)

    async def analyze_multiple(
        self, image_urls: list[str]
    ) -> list[ImageAnalysisResult]:
        """Analyze multiple images.

        Args:
            image_urls: List of image URLs to analyze.

        Returns:
            List of ImageAnalysisResult objects.
        """
        results = []
        for url in image_urls:
            result = await self.analyze_image_url(url)
            results.append(result)
        return results

    def _parse_response(self, image_url: str, content: str) -> ImageAnalysisResult:
        """Parse the GPT response into an ImageAnalysisResult."""
        import json

        try:
            data = json.loads(content)
            codes = []
            for code_data in data.get("codes", []):
                code_type = code_data.get("type", "other")
                if code_type not in (
                    "product_code",
                    "model_number",
                    "ean",
                    "serial_number",
                    "other",
                ):
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

            return ImageAnalysisResult(
                image_url=image_url,
                codes=codes,
                raw_text=data.get("raw_text"),
            )
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse GPT response: %s", str(e))
            return ImageAnalysisResult(
                image_url=image_url,
                error=f"Failed to parse response: {str(e)}",
            )
