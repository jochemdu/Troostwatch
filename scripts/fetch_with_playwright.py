#!/usr/bin/env python3
"""Fetch lot pages using Playwright browser automation.

This script uses Playwright to control a real browser, which can bypass
bot detection that blocks simple HTTP requests.

Usage:
    python scripts/fetch_with_playwright.py --auction A1-39500
    python scripts/fetch_with_playwright.py --auction A1-39500 --limit 20
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright  # noqa: E402

from troostwatch.infrastructure.web.parsers import (  # noqa: E402
    parse_auction_page, parse_lot_detail)


async def main():
    parser = argparse.ArgumentParser(description="Fetch lot pages with Playwright")
    parser.add_argument(
        "--auction", required=True, help="Auction code (e.g., A1-39500)"
    )
    parser.add_argument(
        "--output", type=Path, default=Path("training_data/playwright_fetch")
    )
    parser.add_argument("--limit", type=int, default=10, help="Max lots to fetch")
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    parser.add_argument("--base-url", default="https://www.troostwijkauctions.com")

    args = parser.parse_args()

    print("Starting Playwright browser...")

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=not args.headed,
        )

        # Create context with realistic settings
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="nl-NL",
        )

        page = await context.new_page()

        # Fetch auction page
        auction_url = f"{args.base_url}/nl/a/{args.auction}"
        print(f"\nFetching auction: {auction_url}")

        try:
            response = await page.goto(
                auction_url, wait_until="networkidle", timeout=30000
            )
            print(f"  Status: {response.status if response else 'unknown'}")
        except Exception as e:
            print(f"  Error: {e}")
            await browser.close()
            return 1

        # Get HTML
        html = await page.content()
        print(f"  Got {len(html):,} bytes")

        # Check for block
        if "Access Denied" in html or response.status == 403:
            print("  ❌ Blocked by Cloudflare/CDN")
            await browser.close()
            return 1

        # Save auction HTML
        args.output.mkdir(parents=True, exist_ok=True)
        auction_file = args.output / f"{args.auction}.html"
        with open(auction_file, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  Saved: {auction_file}")

        # Parse lots
        lots = list(parse_auction_page(html, base_url=args.base_url))
        print(f"  Found {len(lots)} lots")

        if not lots:
            await browser.close()
            return 1

        # Fetch lot detail pages
        all_image_urls = []

        for idx, lot in enumerate(lots[: args.limit]):
            summary = (
                f"[{idx+1}/{min(len(lots), args.limit)}] {lot.lot_code}: "
                f"{lot.title[:40]}..."
            )
            print("\n" + summary)

            try:
                response = await page.goto(
                    lot.url, wait_until="networkidle", timeout=30000
                )
                lot_html = await page.content()

                # Save HTML
                lot_file = args.output / f"{lot.lot_code}.html"
                with open(lot_file, "w", encoding="utf-8") as f:
                    f.write(lot_html)

                # Parse detail
                detail = parse_lot_detail(lot_html, lot_code=lot.lot_code)
                print(f"  Images: {len(detail.image_urls)}")

                for url in detail.image_urls:
                    all_image_urls.append(
                        {
                            "url": url,
                            "lot_code": lot.lot_code,
                            "lot_title": detail.title,
                        }
                    )

            except Exception as e:
                print(f"  Error: {e}")

            # Be nice
            await asyncio.sleep(1)

        await browser.close()

        # Save image URLs
        if all_image_urls:
            urls_file = args.output / "image_urls.json"
            with open(urls_file, "w") as f:
                json.dump(all_image_urls, f, indent=2)
            print(f"\n✓ Saved {len(all_image_urls)} image URLs to {urls_file}")

            print(f"\n✓ HTML files saved to: {args.output}")
            print("\nNext steps:")
            print("  1. Process HTML files:")
            print(
                "     python scripts/process_saved_lot_pages.py --html-dir "
                f"{args.output}"
            )
            print("  2. Or download images directly:")
            print(
                "     python scripts/download_images.py --urls "
                f"{args.output}/image_urls.json"
            )

        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)
