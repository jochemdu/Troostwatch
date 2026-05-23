#!/usr/bin/env python3
"""Generate real training data from Troostwijk auction images.

This script:
1. Fetches lot detail pages to get image URLs
2. Downloads images
3. Runs OCR with pytesseract
4. Saves token data for manual labeling

Usage:
    python scripts/generate_real_training_data.py --db troostwatch.db --limit 20 --output real_training_data.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sqlite3
from pathlib import Path

import httpx

# Check for optional dependencies
try:
    import pytesseract
    from PIL import Image
    import io

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("Warning: pytesseract or PIL not available. OCR will be skipped.")


async def fetch_lot_detail(client: httpx.AsyncClient, url: str) -> dict | None:
    """Fetch lot detail page and extract image URLs."""
    try:
        response = await client.get(url)
        if response.status_code != 200:
            return None

        html = response.text

        # Extract image URLs from the page
        # Look for patterns like https://cdn.troostwijkauctions.com/...
        image_pattern = (
            r'https://cdn\.troostwijkauctions\.com/[^"\'>\s]+\.(?:jpg|jpeg|png|webp)'
        )
        images = list(set(re.findall(image_pattern, html, re.IGNORECASE)))

        # Also look for NEXT.js data
        next_data_match = re.search(
            r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL
        )
        if next_data_match:
            try:
                next_data = json.loads(next_data_match.group(1))
                # Extract images from NEXT data structure
                props = next_data.get("props", {}).get("pageProps", {})
                lot_data = props.get("lot", {})
                media = lot_data.get("media", [])
                for item in media:
                    if isinstance(item, dict) and "url" in item:
                        images.append(item["url"])
                    elif isinstance(item, str):
                        images.append(item)
            except json.JSONDecodeError:
                pass

        return {"images": images[:5]}  # Limit to 5 images per lot

    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None


async def download_image(client: httpx.AsyncClient, url: str) -> bytes | None:
    """Download an image and return its bytes."""
    try:
        response = await client.get(url, timeout=30.0)
        if response.status_code == 200:
            return response.content
        return None
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None


def run_ocr(image_bytes: bytes) -> dict | None:
    """Run OCR on image bytes and return token data."""
    if not OCR_AVAILABLE:
        return None

    try:
        image = Image.open(io.BytesIO(image_bytes))

        # Get token-level data
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

        # Filter and clean tokens
        tokens = []
        confidences = []

        for i, text in enumerate(data["text"]):
            text = str(text).strip()
            conf = data["conf"][i]

            # Skip empty tokens and very low confidence
            if text and conf >= 0:
                tokens.append(text)
                confidences.append(int(conf))

        return {
            "text": tokens,
            "conf": confidences,
        }

    except Exception as e:
        print(f"OCR error: {e}")
        return None


def auto_label_tokens(tokens: list[str]) -> dict[str, str]:
    """Automatically label tokens using pattern matching.

    This provides initial labels that can be refined manually.
    """
    labels = {}

    for i, token in enumerate(tokens):
        token_upper = token.upper().strip()

        # EAN-13 pattern
        if re.match(r"^\d{13}$", token_upper):
            labels[str(i)] = "ean"
        # EAN-8 pattern
        elif re.match(r"^\d{8}$", token_upper):
            labels[str(i)] = "ean"
        # Serial number patterns
        elif re.match(r"^(CN|CND|MXL|5CG|2UA|PF|PC|MP|MJ)[A-Z0-9]{6,12}$", token_upper):
            labels[str(i)] = "serial_number"
        elif re.match(r"^S/?N[A-Z0-9]{6,}$", token_upper):
            labels[str(i)] = "serial_number"
        # Model number patterns
        elif re.match(r"^SM-[GANS]\d{3}[A-Z]?$", token_upper):  # Samsung
            labels[str(i)] = "model_number"
        elif re.match(r"^[A-Z]{2,4}-\d{4,}[A-Z]?$", token_upper):
            labels[str(i)] = "model_number"
        elif re.match(r"^WS-C\d{4}.*$", token_upper):  # Cisco
            labels[str(i)] = "model_number"
        # Part number patterns
        elif re.match(r"^P/?N\d{6,}$", token_upper):
            labels[str(i)] = "part_number"

    return labels


async def process_lots(
    db_path: str,
    limit: int,
    output_path: Path,
) -> None:
    """Process lots from database and generate training data."""

    # Get lot URLs from database
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        "SELECT id, title, url FROM lots WHERE url IS NOT NULL LIMIT ?", (limit,)
    )
    lots = cursor.fetchall()
    conn.close()

    print(f"Processing {len(lots)} lots...")

    images_data = []

    async with httpx.AsyncClient(
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        },
        follow_redirects=True,
        timeout=30.0,
    ) as client:

        for lot_id, title, url in lots:
            print(f"\nProcessing lot {lot_id}: {title[:50]}...")

            # Fetch lot detail page
            detail = await fetch_lot_detail(client, url)
            if not detail or not detail.get("images"):
                print("  No images found")
                continue

            print(f"  Found {len(detail['images'])} images")

            # Process each image
            for img_idx, img_url in enumerate(
                detail["images"][:3]
            ):  # Max 3 images per lot
                print(f"  Downloading image {img_idx + 1}...")

                image_bytes = await download_image(client, img_url)
                if not image_bytes:
                    continue

                # Run OCR
                token_data = run_ocr(image_bytes)
                if not token_data or not token_data["text"]:
                    print("    No OCR tokens extracted")
                    continue

                print(f"    Extracted {len(token_data['text'])} tokens")

                # Auto-label tokens
                auto_labels = auto_label_tokens(token_data["text"])
                if auto_labels:
                    print(f"    Auto-labeled {len(auto_labels)} tokens")

                images_data.append(
                    {
                        "lot_id": lot_id,
                        "lot_title": title,
                        "image_url": img_url,
                        "tokens": token_data,
                        "labels": auto_labels,  # Can be refined manually
                    }
                )

            # Small delay between lots
            await asyncio.sleep(0.5)

    # Save training data
    output = {"images": images_data}

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Print summary
    total_tokens = sum(len(img["tokens"]["text"]) for img in images_data)
    labeled_tokens = sum(len(img["labels"]) for img in images_data)

    print(f"\n{'='*50}")
    print(f"Training data saved to: {output_path}")
    print(f"Images processed: {len(images_data)}")
    print(f"Total tokens: {total_tokens}")
    print(f"Auto-labeled tokens: {labeled_tokens}")
    print("\nNext steps:")
    print(f"1. Review and refine labels in {output_path}")
    print(f"2. Train model: python scripts/train_label_classifier.py -i {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate training data from real Troostwijk auction images"
    )
    parser.add_argument(
        "--db",
        type=str,
        default="troostwatch.db",
        help="Path to SQLite database with lot data",
    )
    parser.add_argument(
        "--limit",
        "-n",
        type=int,
        default=20,
        help="Number of lots to process",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("real_training_data.json"),
        help="Output path for training data",
    )
    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"Error: Database not found: {args.db}")
        return

    asyncio.run(process_lots(args.db, args.limit, args.output))


if __name__ == "__main__":
    main()
