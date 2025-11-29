#!/usr/bin/env python3
"""Fetch lot pages using your local browser via Chrome DevTools Protocol.

This script connects to a Chrome browser with remote debugging enabled
to fetch Troostwijk pages, bypassing any IP/bot blocks.

Setup:
1. Start Chrome with remote debugging:

   # macOS
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

   # Windows
   chrome.exe --remote-debugging-port=9222

   # Linux
   google-chrome --remote-debugging-port=9222

2. Run this script:
   python scripts/fetch_via_browser.py --auction A1-39500

The script will use your browser's session (cookies, etc.) to fetch the pages.
"""

import httpx
import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import websockets
except ImportError:
    print("Installing websockets...")
    import subprocess

    subprocess.run([sys.executable, "-m", "pip",
                   "install", "websockets"], check=True)
    import websockets


async def get_browser_ws_url(debug_port: int = 9222) -> str | None:
    """Get the WebSocket URL for Chrome DevTools Protocol."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://localhost:{debug_port}/json/version")
            if resp.status_code == 200:
                data = resp.json()
                return data.get("webSocketDebuggerUrl")
    except Exception as e:
        print(f"Could not connect to Chrome: {e}")
    return None


async def get_page_targets(debug_port: int = 9222) -> list[dict]:
    """Get list of open browser tabs/pages."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://localhost:{debug_port}/json")
            if resp.status_code == 200:
                return [t for t in resp.json() if t.get("type") == "page"]
    except Exception:
        pass
    return []


async def create_new_tab(
    debug_port: int = 9222, url: str = "about:blank"
) -> dict | None:
    """Create a new browser tab."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"http://localhost:{debug_port}/json/new?{url}")
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None


async def fetch_page_html(ws_url: str, url: str, timeout: float = 30.0) -> str | None:
    """Navigate to URL and get page HTML via CDP."""
    try:
        async with websockets.connect(ws_url) as ws:
            msg_id = 1

            # Enable Page events
            await ws.send(json.dumps({"id": msg_id, "method": "Page.enable"}))
            msg_id += 1

            # Navigate to URL
            await ws.send(
                json.dumps(
                    {"id": msg_id, "method": "Page.navigate", "params": {"url": url}}
                )
            )
            msg_id += 1

            # Wait for load
            load_complete = False
            start = asyncio.get_event_loop().time()

            while (
                not load_complete
                and (asyncio.get_event_loop().time() - start) < timeout
            ):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    data = json.loads(msg)
                    if data.get("method") == "Page.loadEventFired":
                        load_complete = True
                except asyncio.TimeoutError:
                    continue

            if not load_complete:
                # Try anyway after timeout
                await asyncio.sleep(2)

            # Get HTML
            await ws.send(
                json.dumps(
                    {
                        "id": msg_id,
                        "method": "Runtime.evaluate",
                        "params": {"expression": "document.documentElement.outerHTML"},
                    }
                )
            )

            # Wait for response
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(msg)
                if data.get("id") == msg_id:
                    result = data.get("result", {}).get("result", {})
                    return result.get("value")

    except Exception as e:
        print(f"CDP error: {e}")
    return None


async def main():
    parser = argparse.ArgumentParser(
        description="Fetch lot pages via local Chrome browser"
    )
    parser.add_argument("--auction", required=True, help="Auction code")
    parser.add_argument("--port", type=int, default=9222,
                        help="Chrome debug port")
    parser.add_argument(
        "--output", type=Path, default=Path("training_data/browser_fetch")
    )
    parser.add_argument("--limit", type=int, default=10, help="Max lots")
    parser.add_argument(
        "--base-url", default="https://www.troostwijkauctions.com")

    args = parser.parse_args()

    # Check Chrome connection
    print(f"Connecting to Chrome on port {args.port}...")
    ws_url = await get_browser_ws_url(args.port)

    if not ws_url:
        print("\n❌ Could not connect to Chrome!")
        print("\nStart Chrome with remote debugging:")
        print("\n  macOS:")
        print(
            "    /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222"
        )
        print("\n  Windows:")
        print("    chrome.exe --remote-debugging-port=9222")
        print("\n  Linux:")
        print("    google-chrome --remote-debugging-port=9222")
        return 1

    print("✓ Connected to Chrome")

    # Get/create a tab
    tabs = await get_page_targets(args.port)
    if tabs:
        tab = tabs[0]
        print(f"  Using tab: {tab.get('title', 'Untitled')[:50]}")
    else:
        tab = await create_new_tab(args.port)
        if not tab:
            print("Could not create new tab")
            return 1
        print("  Created new tab")

    tab_ws = tab.get("webSocketDebuggerUrl")
    if not tab_ws:
        print("No WebSocket URL for tab")
        return 1

    # Fetch auction page
    auction_url = f"{args.base_url}/nl/a/{args.auction}"
    print(f"\nFetching auction: {auction_url}")

    html = await fetch_page_html(tab_ws, auction_url)
    if not html:
        print("Failed to fetch auction page")
        return 1

    print(f"  Got {len(html):,} bytes")

    # Save auction HTML
    args.output.mkdir(parents=True, exist_ok=True)
    auction_file = args.output / f"{args.auction}.html"
    with open(auction_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Saved: {auction_file}")

    # Parse lots
    from troostwatch.infrastructure.web.parsers import parse_auction_page

    lots = list(parse_auction_page(html, base_url=args.base_url))
    print(f"  Found {len(lots)} lots")

    if not lots:
        print("No lots found")
        return 1

    # Fetch lot detail pages
    for idx, lot in enumerate(lots[: args.limit]):
        print(f"\n[{idx+1}/{min(len(lots), args.limit)}] {lot.lot_code}")

        lot_html = await fetch_page_html(tab_ws, lot.url)
        if not lot_html:
            print("  Failed")
            continue

        # Save lot HTML
        lot_file = args.output / f"{lot.lot_code}.html"
        with open(lot_file, "w", encoding="utf-8") as f:
            f.write(lot_html)
        print(f"  Saved: {lot_file}")

        # Parse and show image count
        from troostwatch.infrastructure.web.parsers import parse_lot_detail

        try:
            detail = parse_lot_detail(lot_html, lot_code=lot.lot_code)
            print(f"  Images: {len(detail.image_urls)}")
        except Exception as e:
            print(f"  Parse error: {e}")

        # Small delay to be nice to the server
        await asyncio.sleep(1)

    print(f"\n✓ HTML files saved to: {args.output}")
    print("\nNow run:")
    print(
        f"  python scripts/process_saved_lot_pages.py --html-dir {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)
