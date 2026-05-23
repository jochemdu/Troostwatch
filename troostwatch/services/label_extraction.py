"""Service for extracting and parsing product label data from images.

Follows Troostwatch architecture: services may import infrastructure and domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from troostwatch.infrastructure.ai import (
    preprocess_for_ocr,
    PreprocessingConfig,
    TesseractOCR,
    parse_label,
    ParsedLabel,
)


@dataclass
class LabelExtractionResult:
    text: str
    label: Optional[ParsedLabel]
    preprocessing_steps: list[str]
    ocr_confidence: Optional[float]


def extract_label_from_image(
    image_bytes: bytes,
    preprocessing_config: Optional[PreprocessingConfig] = None,
    ocr_language: str = "eng+nld",
) -> LabelExtractionResult:
    """
    Full pipeline: preprocess image, run OCR, parse vendor label.

    Args:
        image_bytes: Raw image bytes (PNG/JPEG).
        preprocessing_config: Optional preprocessing config.
        ocr_language: Tesseract language(s).

    Returns:
        LabelExtractionResult with OCR text, parsed label, and metadata.
    """
    # Preprocess image
    config = preprocessing_config or PreprocessingConfig.for_labels()
    processed_bytes = preprocess_for_ocr(image_bytes, config=config)

    # OCR
    ocr = TesseractOCR(language=ocr_language)
    ocr_result = ocr.extract_text(processed_bytes)

    # Parse label
    label = parse_label(ocr_result.text)

    # Preprocessing steps (from config, not from result)
    steps: list[str] = []
    if hasattr(config, "steps_applied"):
        steps = config.steps_applied

    return LabelExtractionResult(
        text=ocr_result.text,
        label=label,
        preprocessing_steps=steps,
        ocr_confidence=ocr_result.confidence,
    )
