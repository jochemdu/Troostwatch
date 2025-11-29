#!/usr/bin/env python3
"""Generate training data from lot detail HTML snapshots.

This script uses the existing lot detail parser to extract image URLs
from HTML snapshots, downloads the images, runs OCR, and generates
training data for the label classifier.

Usage:
    python scripts/generate_training_from_snapshots.py --snapshot tests/snapshots/live_pages/lot.html
    python scripts/generate_training_from_snapshots.py --html-dir ./lot_pages/
    python scripts/generate_training_from_snapshots.py --output training_data/real_labels
"""

from troostwatch.infrastructure.web.parsers.lot_detail import parse_lot_detail
import argparse
import asyncio
import hashlib
import json
import re
import sys
from pathlib import Path

import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


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
        print(f"  Failed to download {url}: HTTP {response.status_code}")
        return None
    except Exception as e:
        print(f"  Error downloading {url}: {e}")
        return None


def extract_tokens_from_image(image_bytes: bytes) -> list[dict]:
    """Extract text tokens from an image using OCR."""
    if not HAS_OCR:
        return []

    try:
        image = Image.open(io.BytesIO(image_bytes))
        # Get detailed OCR data
        ocr_data = pytesseract.image_to_data(
            image, output_type=pytesseract.Output.DICT)

        tokens = []
        for i, text in enumerate(ocr_data["text"]):
            text = text.strip()
            if not text:
                continue

            # Get bounding box
            x, y, w, h = (
                ocr_data["left"][i],
                ocr_data["top"][i],
                ocr_data["width"][i],
                ocr_data["height"][i],
            )
            conf = ocr_data["conf"][i]

            tokens.append(
                {
                    "text": text,
                    "confidence": conf,
                    "bbox": {"x": x, "y": y, "width": w, "height": h},
                }
            )

        return tokens
    except Exception as e:
        print(f"  OCR error: {e}")
        return []


def classify_token(text: str) -> str:
    """Heuristically classify a token based on its content.

    Returns one of: 'ean', 'serial_number', 'model_number', 'part_number', 'none'
    """
    text = text.strip()
    if not text:
        return "none"

    # EAN-13 pattern: exactly 13 digits
    if re.match(r"^\d{13}$", text):
        return "ean"

    # EAN-8 pattern: exactly 8 digits
    if re.match(r"^\d{8}$", text):
        return "ean"

    # Serial number patterns (mixed alphanumeric, often longer)
    # Examples: "S/N: ABC123456", "SN12345678"
    if re.match(r"^[A-Z]{1,3}\d{6,12}$", text, re.IGNORECASE):
        return "serial_number"

    if re.match(r"^\d{6,12}[A-Z]{1,3}$", text, re.IGNORECASE):
        return "serial_number"

    # Model number patterns (letter-number combinations)
    # Examples: "VM55T-E", "LH55VMTEBGBXEN", "QM85R"
    if re.match(r"^[A-Z]{1,4}\d{2,4}[A-Z]?(-[A-Z0-9]+)?$", text, re.IGNORECASE):
        return "model_number"

    if re.match(r"^[A-Z]{2}\d{2}[A-Z]{3,}$", text, re.IGNORECASE):
        return "model_number"

    # Part number patterns (often with dashes or slashes)
    # Examples: "BN44-00123A", "DC93-00456B"
    if re.match(r"^[A-Z]{2}\d{2}-\d{5}[A-Z]?$", text, re.IGNORECASE):
        return "part_number"

    return "none"


async def process_snapshot(
    snapshot_path: Path, output_dir: Path, client: httpx.AsyncClient
) -> dict:
    """Process a single HTML snapshot and extract training data."""
    print(f"\nProcessing: {snapshot_path}")

    # Read and parse the HTML
    with open(snapshot_path, "r", encoding="utf-8") as f:
        html = f.read()

    try:
        lot_data = parse_lot_detail(html, lot_code="snapshot")
    except Exception as e:
        print(f"  Failed to parse: {e}")
        return {"images": 0, "tokens": 0}

    print(f"  Title: {lot_data.title}")
    print(f"  Found {len(lot_data.image_urls)} images")

    stats = {"images": 0, "tokens": 0}

    for i, image_url in enumerate(lot_data.image_urls):
        print(f"  Downloading image {i + 1}/{len(lot_data.image_urls)}...")

        image_bytes = await download_image(client, image_url)
        if not image_bytes:
            continue

        # Save the image
        image_hash = hashlib.md5(image_bytes).hexdigest()[:12]
        image_filename = f"{snapshot_path.stem}_{i}_{image_hash}.jpg"
        image_path = output_dir / "images" / image_filename
        image_path.parent.mkdir(parents=True, exist_ok=True)

        with open(image_path, "wb") as f:
            f.write(image_bytes)

        print(f"    Saved: {image_filename} ({len(image_bytes)} bytes)")
        stats["images"] += 1

        # Extract tokens with OCR
        tokens = extract_tokens_from_image(image_bytes)
        print(f"    Extracted {len(tokens)} tokens")

        # Classify and save tokens
        for token in tokens:
            label = classify_token(token["text"])
            token["label"] = label
            token["image_file"] = image_filename
            token["source_url"] = image_url
            token["lot_title"] = lot_data.title

        # Save tokens to JSONL
        tokens_path = output_dir / "tokens.jsonl"
        with open(tokens_path, "a", encoding="utf-8") as f:
            for token in tokens:
                f.write(json.dumps(token, ensure_ascii=False) + "\n")
                stats["tokens"] += 1

    return stats


async def main():
    parser = argparse.ArgumentParser(
        description="Generate training data from lot detail HTML snapshots"
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        help="Path to a single HTML snapshot file",
    )
    parser.add_argument(
        "--html-dir",
        type=Path,
        help="Directory containing HTML snapshot files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("training_data/real_labels"),
        help="Output directory for training data",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP timeout in seconds",
    )

    args = parser.parse_args()

    if not args.snapshot and not args.html_dir:
        # Default to using test snapshots
        args.html_dir = Path("tests/snapshots/live_pages")

    # Collect HTML files to process
    html_files: list[Path] = []
    if args.snapshot:
        html_files.append(args.snapshot)
    if args.html_dir:
        html_files.extend(args.html_dir.glob("*.html"))

    if not html_files:
        print("No HTML files found to process")
        return

    print(f"Found {len(html_files)} HTML files to process")
    print(f"Output directory: {args.output}")

    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)

    # Clear existing tokens file
    tokens_path = args.output / "tokens.jsonl"
    if tokens_path.exists():
        tokens_path.unlink()

    # Process all snapshots
    total_stats = {"images": 0, "tokens": 0}

    async with httpx.AsyncClient(follow_redirects=True) as client:
        for html_file in html_files:
            stats = await process_snapshot(html_file, args.output, client)
            total_stats["images"] += stats["images"]
            total_stats["tokens"] += stats["tokens"]

    print("\n" + "=" * 50)
    print("Summary:")
    print(f"  HTML files processed: {len(html_files)}")
    print(f"  Images downloaded: {total_stats['images']}")
    print(f"  Tokens extracted: {total_stats['tokens']}")
    print(f"  Output directory: {args.output}")

    if total_stats["tokens"] > 0:
        print(f"\nTraining data saved to: {tokens_path}")
        print("\nLabel distribution:")
        # Count labels
        labels: dict[str, int] = {}
        with open(tokens_path, "r") as f:
            for line in f:
                token = json.loads(line)
                label = token.get("label", "none")
                labels[label] = labels.get(label, 0) + 1
        for label, count in sorted(labels.items()):
            print(f"  {label}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
