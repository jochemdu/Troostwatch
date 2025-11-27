"""Auction domain model with business logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Auction:
    """Domain model representing an auction.

    This model encapsulates the business logic related to auctions,
    such as determining if an auction is active and managing pagination.
    """

    auction_code: str
    title: Optional[str] = None
    url: Optional[str] = None
    pagination_pages: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def has_url(self) -> bool:
        """Check if the auction has a URL configured."""
        return bool(self.url)

    @property
    def page_count(self) -> int:
        """Return the number of pagination pages discovered."""
        return len(self.pagination_pages) + 1  # +1 for the main page

    def get_all_page_urls(self) -> List[str]:
        """Return all page URLs including the main URL.

        Returns:
            List of URLs starting with the main URL, followed by pagination pages.
        """
        if not self.url:
            return []
        return [self.url] + list(self.pagination_pages)

    @classmethod
    def from_dict(cls, data: dict) -> "Auction":
        """Create an Auction from a dictionary (e.g., from database row)."""
        pagination = data.get("pagination_pages")
        if isinstance(pagination, str):
            import json
            try:
                pagination = json.loads(pagination)
            except (json.JSONDecodeError, TypeError):
                pagination = []

        def parse_datetime(value) -> Optional[datetime]:
            if value is None:
                return None
            if isinstance(value, datetime):
                return value
            if isinstance(value, str):
                try:
                    return datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    return None
            return None

        return cls(
            auction_code=data.get("auction_code", ""),
            title=data.get("title"),
            url=data.get("url"),
            pagination_pages=pagination or [],
            created_at=parse_datetime(data.get("created_at")),
            updated_at=parse_datetime(data.get("updated_at")),
        )


__all__ = ["Auction"]
