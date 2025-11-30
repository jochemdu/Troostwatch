#!/usr/bin/env python3
"""Fetch lot detail pages using authenticated Troostwijk client.

This script uses the TroostwatchHttpClient to fetch lot detail pages
with proper authentication, bypassing the 403 blocks.

Usage:
    # With credentials
    python scripts/fetch_lot_images.py --auction A1-39500 \
        --username YOUR_EMAIL --password YOUR_PASSWORD

    # With saved token
    python scripts/fetch_lot_images.py --auction A1-39500 \
        --token-path ~/.troostwatch/session.json

    # From environment variables
    export TROOSTWATCH_USERNAME=your@email.com
    export TROOSTWATCH_PASSWORD=yourpassword
    python scripts/fetch_lot_images.py --auction A1-39500
"""

import argparse
import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

import httpx

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from troostwatch.infrastructure.http import (  # noqa: E402
    LoginCredentials,
    TroostwatchHttpClient,
)
from troostwatch.infrastructure.web.parsers import (  # noqa: E402
    parse_auction_page,
    parse_lot_detail,
)

# OCR imports
try:
    import io

    import pytesseract
    from PIL import Image

    HAS_OCR = True
except ImportError:
    HAS_OCR = False


def classify_token(text: str) -> str:
    """Classify a token based on its content."""
    import re

    text = text.strip().upper()
    if not text:
        return "none"
    if re.match(r"^\d{13}$", text):
        return "ean"
    if re.match(r"^\d{8}$", text):
        return "ean"
    if re.match(r"^[A-Z]{1,4}\d{6,12}$", text):
        return "serial_number"
    if re.match(r"^[A-Z]{1,4}\d{2,4}[A-Z]?(-[A-Z0-9]+)?$", text):
        return "model_number"
    if re.match(r"^[A-Z]{2}\d{2}-\d{5}[A-Z]?$", text):
        return "part_number"
    return "none"


def extract_tokens(image_bytes: bytes) -> list[dict]:
    """Extract tokens from image using OCR."""
    if not HAS_OCR:
        return []
    try:
        image = Image.open(io.BytesIO(image_bytes))
        ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        tokens = []
        for i, text in enumerate(ocr_data["text"]):
            text = text.strip()
            if len(text) < 3 or ocr_data["conf"][i] < 30:
                continue
            tokens.append(
                {
                    "text": text,
                    "confidence": ocr_data["conf"][i],
                    "bbox": {
                        "x": ocr_data["left"][i],
                        "y": ocr_data["top"][i],
                        "width": ocr_data["width"][i],
                        "height": ocr_data["height"][i],
                    },
                }
            )
        return tokens
    except Exception as e:
        print(f"    OCR error: {e}")
        return []


async def download_image(url: str) -> bytes | None:
    """Download image from URL."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.content
        except Exception:
            pass
    return None


def main():
    parser = argparse.ArgumentParser(description="Fetch lot images with authentication")
    parser.add_argument(
        "--auction", required=True, help="Auction code (e.g., A1-39500)"
    )
    parser.add_argument("--username", default=os.environ.get("TROOSTWATCH_USERNAME"))
    parser.add_argument("--password", default=os.environ.get("TROOSTWATCH_PASSWORD"))
    parser.add_argument(
        "--token-path", default=os.environ.get("TROOSTWATCH_TOKEN_PATH")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("training_data/real_labels")
    )
    parser.add_argument("--limit", type=int, default=10, help="Max lots to process")
    parser.add_argument("--base-url", default="https://www.troostwijkauctions.com")

    args = parser.parse_args()

    if not args.username and not args.token_path:
        print("Error: Provide --username/--password or --token-path")
        print("\nOr set environment variables:")
        print("  export TROOSTWATCH_USERNAME=your@email.com")
        print("  export TROOSTWATCH_PASSWORD=yourpassword")
        return 1

    # Build authenticated client
    creds = LoginCredentials(
        username=args.username,
        password=args.password,
        token_path=Path(args.token_path) if args.token_path else None,
    )
    client = TroostwatchHttpClient(
        base_url=args.base_url,
        credentials=creds,
    )

    print(f"Authenticating as {args.username or 'cached session'}...")
    try:
        client.authenticate()
        print("  Authenticated successfully!")
    except Exception as e:
        print(f"  Authentication failed: {e}")
        return 1

    # Fetch auction page
    auction_url = f"{args.base_url}/nl/a/{args.auction}"
    print(f"\nFetching auction: {auction_url}")

    try:
        html = client.fetch_text(auction_url)
        print(f"  Got {len(html):,} bytes")
    except Exception as e:
        print(f"  Failed: {e}")
        return 1

    # Parse lots
    lots = list(parse_auction_page(html, base_url=args.base_url))
    print(f"  Found {len(lots)} lots")

    if not lots:
        print("No lots found in auction page")
        return 1

    # Process lots
    args.output.mkdir(parents=True, exist_ok=True)
    tokens_path = args.output / "tokens.jsonl"
    if tokens_path.exists():
        tokens_path.unlink()

    stats = {"images": 0, "tokens": 0}

    for idx, lot in enumerate(lots[: args.limit]):
        summary = (
            f"[{idx+1}/{min(len(lots), args.limit)}] {lot.lot_code}: "
            f"{lot.title[:50]}..."
        )
        print("\n" + summary)

        # Fetch lot detail
        try:
            detail_html = client.fetch_text(lot.url)
            detail = parse_lot_detail(detail_html, lot_code=lot.lot_code)
            print(f"  Images: {len(detail.image_urls)}")
        except Exception as e:
            print(f"  Failed to fetch detail: {e}")
            continue

        # Download images
        for i, img_url in enumerate(detail.image_urls):
            print(f"  [{i+1}/{len(detail.image_urls)}] Downloading...")

            image_bytes = asyncio.run(download_image(img_url))
            if not image_bytes:
                print("    Failed")
                continue

            # Save image
            img_hash = hashlib.md5(image_bytes).hexdigest()[:8]
            img_file = f"{lot.lot_code}_{i}_{img_hash}.jpg"
            img_path = args.output / "images" / img_file
            img_path.parent.mkdir(parents=True, exist_ok=True)

            with open(img_path, "wb") as f:
                f.write(image_bytes)

            print(f"    Saved: {img_file} ({len(image_bytes):,} bytes)")
            stats["images"] += 1

            # OCR
            tokens = extract_tokens(image_bytes)
            if tokens:
                print(f"    OCR: {len(tokens)} tokens")

            for token in tokens:
                token["label"] = classify_token(token["text"])
                token["image_file"] = img_file
                token["lot_code"] = lot.lot_code
                token["source_url"] = img_url

            with open(tokens_path, "a") as f:
                for token in tokens:
                    f.write(json.dumps(token) + "\n")
                    stats["tokens"] += 1

    print("\n" + "=" * 50)
    print(f"Images: {stats['images']}")
    print(f"Tokens: {stats['tokens']}")

    if stats["tokens"] > 0:
        labels = {}
        with open(tokens_path) as f:
            for line in f:
                label = json.loads(line).get("label", "none")
                labels[label] = labels.get(label, 0) + 1
        print("\nLabels:")
        for label, count in sorted(labels.items(), key=lambda x: -x[1]):
            print(f"  {label}: {count}")

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
