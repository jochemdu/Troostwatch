# Feature status audit

This document summarises the current implementation status of capabilities that were previously flagged as missing.

## Authentication and bidding
- The repository now includes an authenticated HTTP client with CSRF/cookie handling and session timeouts (`troostwatch/http_client.py`).
- A bidding service and CLI command (`troostwatch/services/bidding.py`, `troostwatch/cli/bid.py`) allow submitting bids via the authenticated client and persisting bid records locally.

## Database schema and indexing
- The core schema defines auctions, lots, buyers, positions, bids and related indexes (`schema/schema.sql`).
- Runtime helpers ensure schema installation and add hash/timestamp columns for incremental sync (`troostwatch/db.py`).

## Parsing and change detection
- Lot card and detail parsers normalise amounts, timezones and bidder status while providing structured dataclasses (`troostwatch/parsers/lot_card.py`, `troostwatch/parsers/lot_detail.py`).
- Listing and detail hashes are computed during sync to detect changes and avoid redundant work (`troostwatch/sync/sync.py`).

## Sync pipeline efficiency
- The sync pipeline supports concurrent detail fetches, rate limiting, retries, incremental updates via hashes and options to skip unchanged details (`troostwatch/sync/sync.py`).
- CLI flags expose concurrency and throttling controls (see README for the latest options).

Overall, the previously identified gaps around authentication, bidding, schema completeness, parsing robustness and incremental/rate-limited sync have been addressed in the current codebase.
