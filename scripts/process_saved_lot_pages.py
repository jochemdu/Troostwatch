#!/usr/bin/env python3
"""Process manually saved lot detail HTML pages for training data.

Since Troostwijk blocks automated requests, this script processes
HTML files that you save manually from your browser.

Instructions:
1. Open lot detail pages in your browser
2. Right-click -> "Save Page As" -> "Webpage, Complete" or just the HTML
3. Save to a directory (e.g., ./saved_lots/)
4. Run this script:
   
   python scripts/process_saved_lot_pages.py --html-dir ./saved_lots/

The script will:
- Parse each HTML file using the lot detail parser
- Extract image URLs from the JSON data
- Download images that are still accessible
- Run OCR to extract text tokens
- Generate training data with labels

Usage:
    python scripts/process_saved_lot_pages.py --html-dir ./saved_lots/
    python scripts/process_saved_lot_pages.py --html-dir ./saved_lots/ --output training_data/real
"""

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from troostwatch.infrastructure.web.parsers import parse_lot_detail

# Try to import OCR dependencies
try:
    import pytesseract
    from PIL import Image
    import io

    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    print("Warning: pytesseract or PIL not available, OCR will be skipped")


async def download_image(
    client: httpx.AsyncClient, url: str, timeout: float = 30.0
) -> bytes | None:
    """Download an image from URL."""
    try:
        response = await client.get(url, timeout=timeout)
        if response.status_code == 200:
            return response.content
        return None
    except Exception:
        return None


def extract_tokens_from_image(image_bytes: bytes) -> list[dict]:
    """Extract text tokens from an image using OCR."""
    if not HAS_OCR:
        return []

    try:
        image = Image.open(io.BytesIO(image_bytes))
        # Get detailed OCR data
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        tokens = []
        for i, text in enumerate(ocr_data["text"]):
            text = text.strip()
            if not text or len(text) < 3:  # Skip very short tokens
                continue

            conf = ocr_data["conf"][i]
            if conf < 30:  # Skip low confidence
                continue

            x, y, w, h = (
                ocr_data["left"][i],
                ocr_data["top"][i],
                ocr_data["width"][i],
                ocr_data["height"][i],
            )

            tokens.append(
                {
                    "text": text,
                    "confidence": conf,
                    "bbox": {"x": x, "y": y, "width": w, "height": h},
                }
            )

        return tokens
    except Exception as e:
        print(f"    OCR error: {e}")
        return []


def classify_token(text: str) -> str:
    """Classify a token based on its content.

    Returns one of: 'ean', 'serial_number', 'model_number', 'part_number', 'none'
    """
    text = text.strip().upper()
    if not text:
        return "none"

    # EAN-13: exactly 13 digits
    if re.match(r"^\d{13}$", text):
        return "ean"

    # EAN-8: exactly 8 digits
    if re.match(r"^\d{8}$", text):
        return "ean"

    # Serial patterns: mixed alphanumeric, 8+ chars
    if re.match(r"^[A-Z]{1,4}\d{6,12}$", text):
        return "serial_number"
    if re.match(r"^\d{6,12}[A-Z]{1,4}$", text):
        return "serial_number"
    if re.match(r"^S/?N[:\s]?\w+", text):
        return "serial_number"

    # Model patterns: letter-number combos, often with dashes
    if re.match(r"^[A-Z]{1,4}\d{2,4}[A-Z]?(-[A-Z0-9]+)?$", text):
        return "model_number"
    if re.match(r"^[A-Z]{2}\d{2}[A-Z]{3,}$", text):
        return "model_number"

    # Part number patterns: XX##-#####X format
    if re.match(r"^[A-Z]{2}\d{2}-\d{5}[A-Z]?$", text):
        return "part_number"

    return "none"


async def process_html_file(
    html_path: Path, output_dir: Path, client: httpx.AsyncClient
) -> dict:
    """Process a single HTML file and extract training data."""
    print(f"\nProcessing: {html_path.name}")

    with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
        html = f.read()

    try:
        lot_data = parse_lot_detail(html, lot_code=html_path.stem)
    except Exception as e:
        print(f"  Parse error: {e}")
        return {"images": 0, "tokens": 0}

    print(f"  Lot: {lot_data.lot_code}")
    print(f"  Title: {lot_data.title[:60]}...")
    print(f"  Images: {len(lot_data.image_urls)}")

    stats = {"images": 0, "tokens": 0}

    for i, image_url in enumerate(lot_data.image_urls):
        print(f"  [{i+1}/{len(lot_data.image_urls)}] Downloading...")

        image_bytes = await download_image(client, image_url)
        if not image_bytes:
            print(f"    Failed to download")
            continue

        # Save image
        image_hash = hashlib.md5(image_bytes).hexdigest()[:8]
        image_filename = f"{lot_data.lot_code}_{i}_{image_hash}.jpg"
        image_path = output_dir / "images" / image_filename
        image_path.parent.mkdir(parents=True, exist_ok=True)

        with open(image_path, "wb") as f:
            f.write(image_bytes)

        print(f"    Saved: {image_filename} ({len(image_bytes):,} bytes)")
        stats["images"] += 1

        # OCR
        tokens = extract_tokens_from_image(image_bytes)
        if tokens:
            print(f"    OCR: {len(tokens)} tokens")

        # Classify and save
        for token in tokens:
            token["label"] = classify_token(token["text"])
            token["image_file"] = image_filename
            token["lot_code"] = lot_data.lot_code
            token["lot_title"] = lot_data.title
            token["source_url"] = image_url

        tokens_path = output_dir / "tokens.jsonl"
        with open(tokens_path, "a", encoding="utf-8") as f:
            for token in tokens:
                f.write(json.dumps(token, ensure_ascii=False) + "\n")
                stats["tokens"] += 1

    return stats


async def main():
    parser = argparse.ArgumentParser(
        description="Process manually saved lot detail HTML pages"
    )
    parser.add_argument(
        "--html-dir",
        type=Path,
        required=True,
        help="Directory containing saved HTML files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("training_data/real_labels"),
        help="Output directory",
    )

    args = parser.parse_args()

    if not args.html_dir.exists():
        print(f"Error: Directory not found: {args.html_dir}")
        print("\nTo use this script:")
        print("1. Open lot pages in your browser")
        print("2. Save the HTML (Ctrl+S or Right-click -> Save As)")
        print(f"3. Put the HTML files in: {args.html_dir}")
        print("4. Run this script again")
        return

    html_files = list(args.html_dir.glob("*.html")) + list(args.html_dir.glob("*.htm"))
    if not html_files:
        print(f"No HTML files found in: {args.html_dir}")
        return

    print(f"Found {len(html_files)} HTML files")
    print(f"Output: {args.output}")

    args.output.mkdir(parents=True, exist_ok=True)

    # Clear tokens file
    tokens_path = args.output / "tokens.jsonl"
    if tokens_path.exists():
        tokens_path.unlink()

    total = {"images": 0, "tokens": 0}

    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        for html_file in html_files:
            stats = await process_html_file(html_file, args.output, client)
            total["images"] += stats["images"]
            total["tokens"] += stats["tokens"]

    print("\n" + "=" * 50)
    print("Summary:")
    print(f"  Files processed: {len(html_files)}")
    print(f"  Images downloaded: {total['images']}")
    print(f"  Tokens extracted: {total['tokens']}")

    if total["tokens"] > 0:
        print(f"\nTraining data: {tokens_path}")
        # Show label distribution
        labels: dict[str, int] = {}
        with open(tokens_path) as f:
            for line in f:
                label = json.loads(line).get("label", "none")
                labels[label] = labels.get(label, 0) + 1
        print("\nLabel distribution:")
        for label, count in sorted(labels.items(), key=lambda x: -x[1]):
            print(f"  {label}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
