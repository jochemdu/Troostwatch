"""Auction domain model with business logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Auction:
    """Domain model representing an auction.

    This model encapsulates the business logic related to auctions,
    such as determining if an auction is active and managing pagination.
    """

    auction_code: str
    title: str | None = None
    url: str | None = None
    pagination_pages: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def has_url(self) -> bool:
        """Check if the auction has a URL configured."""
        return bool(self.url)

    @property
    def page_count(self) -> int:
        """Return the number of pagination pages discovered."""
        return len(self.pagination_pages) + 1  # +1 for the main page

    def get_all_page_urls(self) -> list[str]:
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

        def parse_datetime(value: object) -> datetime | None:
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
