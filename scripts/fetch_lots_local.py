#!/usr/bin/env python3
"""Simple script to fetch Troostwijk lot pages - run this LOCALLY on your machine.

This script has minimal dependencies (just requests) and can be run on your
local machine where Troostwijk is not blocked.

Usage:
    # Copy this file to your local machine and run:
    python fetch_lots_local.py --auction A1-39500 --output ./lot_pages/
    
    # Then copy the lot_pages folder back to Codespaces and run:
    python scripts/process_saved_lot_pages.py --html-dir ./lot_pages/
"""

import argparse
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urljoin

try:
    import requests
except ImportError:
    print("Installing requests...")
    import subprocess
    import sys
    subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
    import requests


def extract_next_data(html: str) -> dict:
    """Extract __NEXT_DATA__ JSON from HTML."""
    match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    return {}


def parse_lots_from_html(html: str, base_url: str) -> list[dict]:
    """Extract lot info from auction page HTML."""
    data = extract_next_data(html)
    lots = []
    
    # Navigate to lots in the JSON structure
    page_props = data.get("props", {}).get("pageProps", {})
    items = page_props.get("items") or page_props.get("lots") or []
    
    for item in items:
        lot_code = item.get("displayId", "")
        slug = item.get("urlSlug", "")
        title = item.get("title", "")
        
        if lot_code and slug:
            lots.append({
                "lot_code": lot_code,
                "title": title,
                "url": f"{base_url}/l/{slug}",
            })
    
    return lots


def parse_images_from_html(html: str) -> list[str]:
    """Extract image URLs from lot detail HTML."""
    data = extract_next_data(html)
    
    lot = data.get("props", {}).get("pageProps", {}).get("lot", {})
    images = lot.get("images", [])
    
    return [img.get("url") for img in images if img.get("url")]


def main():
    parser = argparse.ArgumentParser(
        description="Fetch Troostwijk lot pages (run locally)"
    )
    parser.add_argument("--auction", required=True, help="Auction code")
    parser.add_argument("--output", type=Path, default=Path("./lot_pages"))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--base-url", default="https://www.troostwijkauctions.com")
    
    args = parser.parse_args()
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "nl-NL,nl;q=0.9",
    })
    
    # Fetch auction page
    auction_url = f"{args.base_url}/nl/a/{args.auction}"
    print(f"Fetching: {auction_url}")
    
    resp = session.get(auction_url)
    print(f"  Status: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"  Failed! Response: {resp.text[:200]}")
        return 1
    
    # Save auction HTML
    args.output.mkdir(parents=True, exist_ok=True)
    auction_file = args.output / f"{args.auction}.html"
    with open(auction_file, "w", encoding="utf-8") as f:
        f.write(resp.text)
    print(f"  Saved: {auction_file}")
    
    # Parse lots
    lots = parse_lots_from_html(resp.text, args.base_url)
    print(f"  Found {len(lots)} lots")
    
    # Fetch lot details
    all_images = []
    
    for idx, lot in enumerate(lots[:args.limit]):
        print(f"\n[{idx+1}/{min(len(lots), args.limit)}] {lot['lot_code']}")
        
        resp = session.get(lot["url"])
        if resp.status_code != 200:
            print(f"  Failed: {resp.status_code}")
            continue
        
        # Save HTML
        lot_file = args.output / f"{lot['lot_code']}.html"
        with open(lot_file, "w", encoding="utf-8") as f:
            f.write(resp.text)
        
        # Extract images
        images = parse_images_from_html(resp.text)
        print(f"  Images: {len(images)}")
        
        for url in images:
            all_images.append({
                "url": url,
                "lot_code": lot["lot_code"],
            })
        
        time.sleep(0.5)  # Be nice
    
    # Save image URLs
    if all_images:
        urls_file = args.output / "image_urls.json"
        with open(urls_file, "w") as f:
            json.dump(all_images, f, indent=2)
        print(f"\n✓ {len(all_images)} image URLs saved to {urls_file}")
    
    print(f"\n✓ Done! Files in: {args.output}")
    print(f"\nCopy this folder to Codespaces and run:")
    print(f"  python scripts/process_saved_lot_pages.py --html-dir {args.output}")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main() or 0)
