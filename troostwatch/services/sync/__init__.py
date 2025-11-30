"""Sync services for fetching and persisting auction data.

This module provides the official API for synchronizing Troostwijk auctions
with the local database. All sync functionality should be imported from this
package, not directly from submodules like .sync or .fetcher.

Public API:
  - sync_auction_to_db() – Synchronize an auction to the database (sync wrapper)
  - sync_auction() – Synchronize an auction asynchronously
  - SyncRunResult – Result data transfer object
  - PageResult – Pagination result wrapper
  - HttpFetcher – HTTP client with rate limiting
  - RateLimiter – Per-host rate limiting
  - RequestResult – HTTP request result
  - compute_detail_hash() – Hash for lot details
  - compute_listing_hash() – Hash for lot listings

Internal Helpers (private, not in __all__, for use by services/lots.py and tests):
  - _upsert_auction() – Helper for tests to set up auctions
  - _listing_detail_from_card() – Builds detail object from card data

Implementation Note:
  Internal modules (fetcher.py, sync.py, service.py) should not be imported
  directly outside of tests. They are implementation details that may change.
"""

from .fetcher import HttpFetcher, RateLimiter, RequestResult
from .service import sync_auction
from .sync import (PageResult, SyncRunResult,  # noqa: F401
                   _listing_detail_from_card, _upsert_auction,
                   compute_detail_hash, compute_listing_hash,
                   sync_auction_to_db)

__all__ = [
    # === HTTP & Fetching Infrastructure
    "HttpFetcher",
    "RateLimiter",
    "RequestResult",
    # === Sync Results & Data Transfer Objects
    "PageResult",
    "SyncRunResult",
    # === Hash Computation for Change Detection
    "compute_detail_hash",
    "compute_listing_hash",
    # === Core Sync Functions
    "sync_auction",
    "sync_auction_to_db",
]

# Private internal helpers (NOT in __all__, but available for services and tests)
# Do not use in production code
__internal_helpers__ = ["_upsert_auction", "_listing_detail_from_card"]
