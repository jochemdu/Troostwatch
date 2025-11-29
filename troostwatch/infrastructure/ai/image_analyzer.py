"""Image analysis with multiple backend options.

This module provides functionality to analyze lot images and extract
product codes, model numbers, and EAN codes using either:
- Local OCR (Tesseract) with regex-based code extraction
- OpenAI GPT-4 Vision API

The local OCR option is free and works offline, while OpenAI provides
more intelligent extraction but requires an API key.
"""

from __future__ import annotations

import base64
import io
import os
import re
from dataclasses import dataclass, field
from typing import Literal

import httpx

from troostwatch.infrastructure.observability.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractedCode:
    """A single extracted code from an image."""

    code_type: Literal["product_code", "model_number",
                       "ean", "serial_number", "other"]
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


# =============================================================================
# Code Extraction Patterns
# =============================================================================

# EAN-13: 13 digits, often starting with country code
EAN_PATTERN = re.compile(r"\b(\d{13})\b")

# EAN-8: 8 digits
EAN8_PATTERN = re.compile(r"\b(\d{8})\b")

# UPC-A: 12 digits
UPC_PATTERN = re.compile(r"\b(\d{12})\b")

# Common product code patterns (letters + numbers, hyphens allowed)
# Examples: SM-G991B, WM75A, A1-39500, HP-123ABC
PRODUCT_CODE_PATTERN = re.compile(
    r"\b([A-Z]{1,4}[-]?[A-Z0-9]{2,10}[-]?[A-Z0-9]{0,10})\b",
    re.IGNORECASE,
)

# Model number patterns (more specific formats)
# Examples: Model: ABC123, Type: XYZ-456
MODEL_PATTERN = re.compile(
    r"(?:model|type|art\.?(?:ikel)?(?:nr)?|p/?n|part\s*(?:no|number)?)"
    r"[:\s]*([A-Z0-9][-A-Z0-9./]{2,20})",
    re.IGNORECASE,
)

# Serial number patterns
# Examples: S/N: ABC123456, Serial: 12345678
SERIAL_PATTERN = re.compile(
    r"(?:s/?n|serial(?:\s*(?:no|number|nr))?)[:\s]*([A-Z0-9]{6,20})",
    re.IGNORECASE,
)


def _validate_ean13(code: str) -> bool:
    """Validate EAN-13 check digit."""
    if len(code) != 13 or not code.isdigit():
        return False
    total = sum(int(d) * (1 if i % 2 == 0 else 3)
                for i, d in enumerate(code[:12]))
    check = (10 - (total % 10)) % 10
    return int(code[12]) == check


def _validate_ean8(code: str) -> bool:
    """Validate EAN-8 check digit."""
    if len(code) != 8 or not code.isdigit():
        return False
    total = sum(int(d) * (3 if i % 2 == 0 else 1)
                for i, d in enumerate(code[:7]))
    check = (10 - (total % 10)) % 10
    return int(code[7]) == check


def _is_likely_product_code(code: str) -> bool:
    """Check if a string looks like a product code."""
    # Must have at least one letter and one digit
    has_letter = any(c.isalpha() for c in code)
    has_digit = any(c.isdigit() for c in code)
    # Not too long, not too short
    length_ok = 4 <= len(code) <= 20
    # Not all same character
    not_repetitive = len(set(code.replace("-", ""))) > 2
    return has_letter and has_digit and length_ok and not_repetitive


def extract_codes_from_text(text: str) -> list[ExtractedCode]:
    """Extract product codes, EANs, and other identifiers from text.

    Uses regex patterns to find various code formats in OCR'd text.
    """
    codes: list[ExtractedCode] = []
    seen: set[str] = set()

    # Extract EAN-13 codes
    for match in EAN_PATTERN.finditer(text):
        value = match.group(1)
        if value not in seen and _validate_ean13(value):
            seen.add(value)
            codes.append(
                ExtractedCode(
                    code_type="ean",
                    value=value,
                    confidence="high",
                    context="EAN-13 barcode",
                )
            )

    # Extract EAN-8 codes
    for match in EAN8_PATTERN.finditer(text):
        value = match.group(1)
        if value not in seen and _validate_ean8(value):
            seen.add(value)
            codes.append(
                ExtractedCode(
                    code_type="ean",
                    value=value,
                    confidence="high",
                    context="EAN-8 barcode",
                )
            )

    # Extract UPC codes (12 digits, less common in EU)
    for match in UPC_PATTERN.finditer(text):
        value = match.group(1)
        if value not in seen:
            # UPC validation is complex, mark as medium confidence
            seen.add(value)
            codes.append(
                ExtractedCode(
                    code_type="ean",
                    value=value,
                    confidence="medium",
                    context="UPC-A barcode",
                )
            )

    # Extract model numbers (with label)
    for match in MODEL_PATTERN.finditer(text):
        value = match.group(1).strip().upper()
        if value not in seen and len(value) >= 3:
            seen.add(value)
            codes.append(
                ExtractedCode(
                    code_type="model_number",
                    value=value,
                    confidence="high",
                    context="Labeled model number",
                )
            )

    # Extract serial numbers
    for match in SERIAL_PATTERN.finditer(text):
        value = match.group(1).strip().upper()
        if value not in seen and len(value) >= 6:
            seen.add(value)
            codes.append(
                ExtractedCode(
                    code_type="serial_number",
                    value=value,
                    confidence="high",
                    context="Labeled serial number",
                )
            )

    # Extract product codes (generic pattern)
    for match in PRODUCT_CODE_PATTERN.finditer(text):
        value = match.group(1).upper()
        if value not in seen and _is_likely_product_code(value):
            seen.add(value)
            codes.append(
                ExtractedCode(
                    code_type="product_code",
                    value=value,
                    confidence="medium",
                    context="Product code pattern",
                )
            )

    # Try vendor-specific extraction for higher accuracy
    try:
        from .vendor_profiles import extract_vendor_codes

        vendor_codes = extract_vendor_codes(text)
        for vc in vendor_codes:
            if vc.value not in seen:
                seen.add(vc.value)
                codes.append(vc)
    except ImportError:
        pass  # Vendor profiles not available

    return codes


# =============================================================================
# Local OCR Analyzer (Tesseract)
# =============================================================================


class LocalOCRAnalyzer:
    """Analyzes images using local Tesseract OCR."""

    def __init__(self, tesseract_cmd: str | None = None) -> None:
        """Initialize the local OCR analyzer.

        Args:
            tesseract_cmd: Path to tesseract executable. Auto-detected if None.
        """
        self.tesseract_cmd = tesseract_cmd
        self._tesseract_available: bool | None = None

    def _check_tesseract(self) -> bool:
        """Check if Tesseract is available."""
        if self._tesseract_available is not None:
            return self._tesseract_available

        try:
            import pytesseract

            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            # Test that tesseract works
            pytesseract.get_tesseract_version()
            self._tesseract_available = True
        except Exception as e:
            logger.warning("Tesseract not available: %s", str(e))
            self._tesseract_available = False

        return self._tesseract_available

    async def analyze_image_url(self, image_url: str) -> ImageAnalysisResult:
        """Analyze an image URL using local OCR.

        Args:
            image_url: URL of the image to analyze.

        Returns:
            ImageAnalysisResult with extracted codes.
        """
        if not self._check_tesseract():
            return ImageAnalysisResult(
                image_url=image_url,
                error="Tesseract OCR niet geïnstalleerd. "
                "Installeer met: pip install pytesseract && "
                "apt-get install tesseract-ocr tesseract-ocr-nld",
            )

        try:
            import pytesseract
            from PIL import Image

            # Download the image
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(image_url)
                response.raise_for_status()
                image_data = response.content

            # Load image
            image = Image.open(io.BytesIO(image_data))

            # Run OCR with English and Dutch language support
            try:
                text = pytesseract.image_to_string(image, lang="eng+nld")
            except pytesseract.TesseractError:
                # Fallback to English only if Dutch not available
                text = pytesseract.image_to_string(image, lang="eng")

            # Extract codes from text
            codes = extract_codes_from_text(text)

            return ImageAnalysisResult(
                image_url=image_url,
                codes=codes,
                raw_text=text.strip() if text.strip() else None,
            )

        except httpx.HTTPStatusError as e:
            logger.error("Failed to download image: %s", str(e))
            return ImageAnalysisResult(
                image_url=image_url,
                error=f"Afbeelding downloaden mislukt: {e.response.status_code}",
            )
        except Exception as e:
            logger.error("OCR analysis failed: %s", str(e))
            return ImageAnalysisResult(
                image_url=image_url,
                error=f"OCR mislukt: {str(e)}",
            )

    async def analyze_image_bytes(
        self, image_data: bytes, image_url: str = "bytes"
    ) -> ImageAnalysisResult:
        """Analyze image bytes using local OCR."""
        if not self._check_tesseract():
            return ImageAnalysisResult(
                image_url=image_url,
                error="Tesseract OCR niet geïnstalleerd",
            )

        try:
            import pytesseract
            from PIL import Image

            image = Image.open(io.BytesIO(image_data))
            try:
                text = pytesseract.image_to_string(image, lang="eng+nld")
            except pytesseract.TesseractError:
                text = pytesseract.image_to_string(image, lang="eng")
            codes = extract_codes_from_text(text)

            return ImageAnalysisResult(
                image_url=image_url,
                codes=codes,
                raw_text=text.strip() if text.strip() else None,
            )
        except Exception as e:
            logger.error("OCR analysis failed: %s", str(e))
            return ImageAnalysisResult(
                image_url=image_url,
                error=f"OCR mislukt: {str(e)}",
            )

    async def analyze_multiple(
        self, image_urls: list[str]
    ) -> list[ImageAnalysisResult]:
        """Analyze multiple images."""
        results = []
        for url in image_urls:
            result = await self.analyze_image_url(url)
            results.append(result)
        return results

    def get_token_data(self, image_path: str) -> dict | None:
        """Extract token-level OCR data for ML training.

        Uses pytesseract.image_to_data() to get detailed token information
        including bounding boxes, confidence scores, and text for each word.

        Args:
            image_path: Path to the local image file.

        Returns:
            Dictionary with token data suitable for ML training, or None on error.
            Format:
            {
                "text": ["word1", "word2", ...],
                "conf": [95, 80, ...],  # confidence scores
                "left": [10, 50, ...],  # x position
                "top": [100, 100, ...],  # y position
                "width": [40, 60, ...],
                "height": [20, 20, ...],
                "level": [5, 5, ...],  # hierarchy level
                "block_num": [1, 1, ...],
                "par_num": [1, 1, ...],
                "line_num": [1, 1, ...],
                "word_num": [1, 2, ...]
            }
        """
        if not self._check_tesseract():
            logger.warning("Tesseract not available for token extraction")
            return None

        try:
            import pytesseract
            from PIL import Image

            image = Image.open(image_path)

            try:
                data = pytesseract.image_to_data(
                    image,
                    lang="eng+nld",
                    output_type=pytesseract.Output.DICT,
                )
            except pytesseract.TesseractError:
                # Fallback to English only
                data = pytesseract.image_to_data(
                    image,
                    lang="eng",
                    output_type=pytesseract.Output.DICT,
                )

            # Filter out empty tokens and tokens with -1 confidence
            filtered_data: dict = {
                "text": [],
                "conf": [],
                "left": [],
                "top": [],
                "width": [],
                "height": [],
                "level": [],
                "block_num": [],
                "par_num": [],
                "line_num": [],
                "word_num": [],
            }

            for i, text in enumerate(data["text"]):
                # Skip empty tokens and low-confidence tokens
                if text.strip() and data["conf"][i] >= 0:
                    for key in filtered_data:
                        filtered_data[key].append(data[key][i])

            return filtered_data

        except Exception as e:
            logger.error("Token extraction failed: %s", str(e))
            return None

    def analyze_local_image(self, image_path: str) -> ImageAnalysisResult:
        """Analyze a local image file synchronously.

        Args:
            image_path: Path to the local image file.

        Returns:
            ImageAnalysisResult with extracted codes.
        """
        if not self._check_tesseract():
            return ImageAnalysisResult(
                image_url=image_path,
                error="Tesseract OCR niet geïnstalleerd",
            )

        try:
            import pytesseract
            from PIL import Image

            image = Image.open(image_path)

            try:
                text = pytesseract.image_to_string(image, lang="eng+nld")
            except pytesseract.TesseractError:
                text = pytesseract.image_to_string(image, lang="eng")

            codes = extract_codes_from_text(text)

            return ImageAnalysisResult(
                image_url=image_path,
                codes=codes,
                raw_text=text.strip() if text.strip() else None,
            )

        except Exception as e:
            logger.error("Local OCR analysis failed: %s", str(e))
            return ImageAnalysisResult(
                image_url=image_path,
                error=f"OCR mislukt: {str(e)}",
            )

    async def close(self) -> None:
        """No cleanup needed for local OCR."""


# =============================================================================
# OpenAI Vision Analyzer
# =============================================================================


class OpenAIAnalyzer:
    """Analyzes images using OpenAI's GPT-4 Vision API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        timeout: float = 30.0,
    ) -> None:
        """Initialize the OpenAI analyzer.

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
        """Analyze an image URL for product codes."""
        if not self.api_key:
            return ImageAnalysisResult(
                image_url=image_url,
                error="OpenAI API key niet geconfigureerd (set OPENAI_API_KEY)",
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
                error=f"API fout: {e.response.status_code}",
            )
        except Exception as e:
            logger.error("Image analysis failed: %s", str(e))
            return ImageAnalysisResult(
                image_url=image_url,
                error=f"Analyse mislukt: {str(e)}",
            )

    async def analyze_image_bytes(
        self, image_data: bytes, mime_type: str = "image/jpeg"
    ) -> ImageAnalysisResult:
        """Analyze image bytes for product codes."""
        base64_image = base64.b64encode(image_data).decode("utf-8")
        data_url = f"data:{mime_type};base64,{base64_image}"
        return await self.analyze_image_url(data_url)

    async def analyze_multiple(
        self, image_urls: list[str]
    ) -> list[ImageAnalysisResult]:
        """Analyze multiple images."""
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
                error=f"Response parsen mislukt: {str(e)}",
            )


# =============================================================================
# Unified Image Analyzer
# =============================================================================


class ImageAnalyzer:
    """Unified image analyzer with multiple backend options.

    Supports:
    - 'local': Tesseract OCR with regex extraction (free, offline)
    - 'openai': OpenAI GPT-4 Vision (requires API key)
    """

    def __init__(
        self,
        backend: Literal["local", "openai"] = "local",
        api_key: str | None = None,
        model: str = "gpt-4o",
        timeout: float = 30.0,
    ) -> None:
        """Initialize the image analyzer.

        Args:
            backend: Which backend to use ('local' or 'openai').
            api_key: OpenAI API key (only needed for 'openai' backend).
            model: OpenAI model to use (only for 'openai' backend).
            timeout: Request timeout in seconds.
        """
        self.backend = backend

        if backend == "openai":
            self._analyzer: LocalOCRAnalyzer | OpenAIAnalyzer = OpenAIAnalyzer(
                api_key=api_key,
                model=model,
                timeout=timeout,
            )
        else:
            self._analyzer = LocalOCRAnalyzer()

    async def analyze_image_url(self, image_url: str) -> ImageAnalysisResult:
        """Analyze an image URL for product codes."""
        return await self._analyzer.analyze_image_url(image_url)

    async def analyze_multiple(
        self, image_urls: list[str]
    ) -> list[ImageAnalysisResult]:
        """Analyze multiple images."""
        return await self._analyzer.analyze_multiple(image_urls)

    async def close(self) -> None:
        """Close any open connections."""
        await self._analyzer.close()


# Keep old name for backwards compatibility
__all__ = [
    "ExtractedCode",
    "ImageAnalysisResult",
    "ImageAnalyzer",
    "LocalOCRAnalyzer",
    "OpenAIAnalyzer",
    "extract_codes_from_text",
]
