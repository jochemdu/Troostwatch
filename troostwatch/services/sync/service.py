from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Optional

from troostwatch.services.dto import EventPublisher
from . import sync as sync_module


async def sync_auction(
    *,
    db_path: str,
    auction_code: str,
    auction_url: str,
    max_pages: Optional[int] = None,
    dry_run: bool = False,
    event_publisher: EventPublisher | None = None,
) -> dict[str, object]:
    result = await asyncio.to_thread(
        sync_module.sync_auction_to_db,
        db_path=db_path,
        auction_code=auction_code,
        auction_url=auction_url,
        max_pages=max_pages,
        dry_run=dry_run,
    )

    payload = {"type": "sync_finished", "auction_code": auction_code, "result": asdict(result)}
    if event_publisher:
        await event_publisher(payload)
    return payload
