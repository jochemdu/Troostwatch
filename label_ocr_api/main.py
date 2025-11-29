"""Label OCR API - FastAPI microservice for product label parsing.

This service provides endpoints for analyzing product images and
extracting product codes (EAN, serial numbers, model numbers, etc.)
using OCR with optional ML-based code classification.
"""

from __future__ import annotations

import io
import re
import time
from pathlib import Path
from typing import Annotated

import httpx
import pytesseract
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image
from pydantic import BaseModel, Field

# Try to load ML model if available
try:
    import joblib

    MODEL_PATH = Path(__file__).parent / "models" / "label_classifier.pkl"
    if MODEL_PATH.exists():
        label_classifier = joblib.load(MODEL_PATH)
    else:
        label_classifier = None
except Exception:
    label_classifier = None

app = FastAPI(
    title="Label OCR API",
    description="Microservice for extracting product codes from images",
    version="0.1.0",
)


class ExtractedCode(BaseModel):
    """A product code extracted from an image."""

    code_type: str = Field(
        description="Type of code: 'ean', 'serial_number', 'model_number', 'part_number', 'other'"
    )
    value: str = Field(description="The extracted code value")
    confidence: str = Field(
        description="Confidence level: 'high', 'medium', 'low'")
    context: str | None = Field(
        default=None, description="Context around the code")


class ParseLabelResponse(BaseModel):
    """Response from the /parse-label endpoint."""

    codes: list[ExtractedCode] = Field(default_factory=list)
    raw_text: str = Field(description="Full text extracted from the image")
    processing_time_ms: int = Field(
        description="Processing time in milliseconds")


class ImageURLRequest(BaseModel):
    """Request body for URL-based image analysis."""

    image_url: str = Field(description="URL of the image to analyze")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    model_loaded: bool
    tesseract_available: bool


# Pattern definitions for code detection
PATTERNS = {
    "ean": [
        (r"\b(\d{13})\b", "high"),  # EAN-13
        (r"\b(\d{8})\b(?!\d)", "medium"),  # EAN-8
    ],
    "serial_number": [
        (r"(?:S/?N|Serial)[:\s#]*([A-Z0-9-]{6,20})", "high"),
        (r"\b([A-Z]{2,3}\d{6,12})\b", "medium"),
    ],
    "model_number": [
        (r"(?:Model|Mod\.?|Type)[:\s#]*([A-Z0-9-]{4,20})", "high"),
        (r"\b([A-Z]{2,4}-?\d{3,6}[A-Z]?)\b", "medium"),
    ],
    "part_number": [
        (r"(?:P/?N|Part)[:\s#]*([A-Z0-9-]{6,20})", "high"),
    ],
}


def extract_codes_regex(text: str) -> list[ExtractedCode]:
    """Extract product codes using regex patterns."""
    codes: list[ExtractedCode] = []
    seen_values: set[str] = set()

    for code_type, patterns in PATTERNS.items():
        for pattern, confidence in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value = match.group(1).strip().upper()
                if value and value not in seen_values:
                    seen_values.add(value)
                    # Get context (20 chars before and after)
                    start = max(0, match.start() - 20)
                    end = min(len(text), match.end() + 20)
                    context = text[start:end].strip()

                    codes.append(
                        ExtractedCode(
                            code_type=code_type,
                            value=value,
                            confidence=confidence,
                            context=context,
                        )
                    )

    return codes


def extract_codes_ml(text: str, token_data: dict) -> list[ExtractedCode]:
    """Extract product codes using ML classifier.

    Uses the trained label_classifier model to identify tokens
    that are likely to be product codes.
    """
    if label_classifier is None:
        return extract_codes_regex(text)

    codes: list[ExtractedCode] = []
    tokens = token_data.get("text", [])
    confidences = token_data.get("conf", [])

    for i, token in enumerate(tokens):
        token = str(token).strip()
        if not token or token == "-1":
            continue

        # Prepare features for classification
        try:
            features = _prepare_token_features(token, i, tokens, confidences)
            prediction = label_classifier.predict([features])[0]
            proba = label_classifier.predict_proba([features])[0]

            if prediction != "none":
                max_proba = max(proba)
                confidence = (
                    "high"
                    if max_proba > 0.8
                    else "medium" if max_proba > 0.5 else "low"
                )
                codes.append(
                    ExtractedCode(
                        code_type=prediction,
                        value=token.upper(),
                        confidence=confidence,
                        context=None,
                    )
                )
        except Exception:
            # Fall back to regex on any error
            continue

    # If ML didn't find anything, fall back to regex
    if not codes:
        codes = extract_codes_regex(text)

    return codes


def _prepare_token_features(
    token: str,
    index: int,
    tokens: list,
    confidences: list,
) -> list[float]:
    """Prepare feature vector for a token.

    Features include:
    - Token length
    - Digit ratio
    - Uppercase ratio
    - Has common prefixes
    - OCR confidence
    - Position in document
    """
    features = []

    # Basic features
    features.append(len(token))
    features.append(sum(c.isdigit() for c in token) / max(len(token), 1))
    features.append(sum(c.isupper() for c in token) / max(len(token), 1))
    features.append(1.0 if re.match(r"^[A-Z]{2,3}\d+", token) else 0.0)
    features.append(1.0 if re.match(r"^\d{8,13}$", token) else 0.0)

    # Context features
    try:
        conf = float(confidences[index]) if index < len(confidences) else 0.0
        features.append(conf / 100.0)
    except (ValueError, TypeError):
        features.append(0.0)

    features.append(index / max(len(tokens), 1))

    return features


def analyze_image(image: Image.Image) -> ParseLabelResponse:
    """Analyze an image and extract product codes."""
    start_time = time.time()

    # Run OCR
    raw_text = pytesseract.image_to_string(image)
    token_data = pytesseract.image_to_data(
        image, output_type=pytesseract.Output.DICT)

    # Extract codes
    if label_classifier is not None:
        codes = extract_codes_ml(raw_text, token_data)
    else:
        codes = extract_codes_regex(raw_text)

    processing_time = int((time.time() - start_time) * 1000)

    return ParseLabelResponse(
        codes=codes,
        raw_text=raw_text,
        processing_time_ms=processing_time,
    )


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check the health status of the service."""
    # Check tesseract availability
    try:
        pytesseract.get_tesseract_version()
        tesseract_ok = True
    except Exception:
        tesseract_ok = False

    return HealthResponse(
        status="ok" if tesseract_ok else "degraded",
        model_loaded=label_classifier is not None,
        tesseract_available=tesseract_ok,
    )


@app.post("/parse-label", response_model=ParseLabelResponse)
async def parse_label_upload(
    file: Annotated[UploadFile, File(description="Image file to analyze")],
) -> ParseLabelResponse:
    """Parse a product label from an uploaded image file.

    Accepts JPG, PNG, or WebP images. Returns extracted product codes
    including EAN, serial numbers, model numbers, and part numbers.
    """
    # Validate content type
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported content type: {file.content_type}. Use JPEG, PNG, or WebP.",
        )

    try:
        content = await file.read()
        image = Image.open(io.BytesIO(content))
        return analyze_image(image)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process image: {e}")


@app.post("/parse-label/url", response_model=ParseLabelResponse)
async def parse_label_url(request: ImageURLRequest) -> ParseLabelResponse:
    """Parse a product label from an image URL.

    Downloads the image and extracts product codes.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(request.image_url)
            response.raise_for_status()

        image = Image.open(io.BytesIO(response.content))
        return analyze_image(image)
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=400, detail=f"Failed to download image: {e}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process image: {e}")


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    """Handle unexpected exceptions gracefully."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error",
                 "type": type(exc).__name__},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
