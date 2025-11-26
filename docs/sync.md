# Sync System Documentation

## Overview

The sync system fetches auction data from Troostwijk and persists it to the local database. It supports both single-auction and multi-auction synchronization.

## Data Flow

```
Troostwijk Website
        │
        ▼
┌───────────────────┐
│   HTTP Fetcher    │  ← Rate limiting, retries, concurrency
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   HTML Parsers    │  ← Extract lot cards, details
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   SyncService     │  ← Orchestrate sync, compute hashes
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│   Repositories    │  ← Persist to SQLite
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│  API/CLI Output   │  ← Present results
└───────────────────┘
```

## Components

### SyncService (`services/sync_service.py`)

The main service for sync operations:

```python
from troostwatch.services.sync_service import SyncService

service = SyncService(db_path="/path/to/db.sqlite")

# Choose an auction
selection = service.choose_auction(
    auction_code="A1-12345",
    auction_url="https://troostwijk.com/a/..."
)

# Run sync
summary = await service.run_sync(
    auction_code="A1-12345",
    auction_url="https://troostwijk.com/a/...",
    max_pages=None,  # All pages
    dry_run=False,
    verbose=True,
)
```

### HttpFetcher (`services/sync/fetcher.py`)

Handles HTTP requests with:
- Rate limiting (per-host throttling)
- Exponential backoff on failures
- Concurrent fetching (asyncio or threadpool)

### Parsers (`infrastructure/web/parsers/`)

Extract data from HTML:
- `lot_card.py` - Parse lot cards from auction pages
- `lot_detail.py` - Parse individual lot detail pages
- `auction_page.py` - Parse pagination and lot listings

## CLI Commands

### Single Auction Sync

```bash
python -m troostwatch.interfaces.cli sync \
    --db /path/to/db.sqlite \
    --auction-code A1-12345 \
    --auction-url "https://troostwijk.com/a/..."
```

Options:
- `--max-pages N` - Limit pages to fetch
- `--dry-run` - Don't persist changes
- `--verbose` - Show detailed progress
- `--delay-seconds N` - Delay between requests

### Multi-Auction Sync

```bash
python -m troostwatch.interfaces.cli sync-multi \
    --db /path/to/db.sqlite \
    --include-inactive
```

Options:
- `--include-inactive` - Include auctions without active lots
- `--max-pages N` - Limit pages per auction

## API Endpoints

### POST /sync

Trigger a single auction sync:

```json
{
    "auction_code": "A1-12345",
    "auction_url": "https://...",
    "max_pages": null,
    "dry_run": false
}
```

### POST /live-sync/start

Start continuous background sync:

```json
{
    "interval_seconds": 300,
    "auction_codes": ["A1-12345", "A1-12346"]
}
```

### GET /live-sync/status

Get current sync status:

```json
{
    "status": "running",
    "last_sync": "2024-01-15T10:30:00Z",
    "next_sync": "2024-01-15T10:35:00Z"
}
```

## Sync Process

1. **Fetch first page** - Get main auction page
2. **Discover pagination** - Extract all page URLs
3. **Fetch all pages** - With rate limiting
4. **Parse lot cards** - Extract basic lot info
5. **Fetch lot details** - For new/changed lots
6. **Compute hashes** - Detect changes
7. **Upsert to database** - Only changed records
8. **Record sync run** - Log results

## Hash-Based Change Detection

Each lot has two hashes:
- **Listing hash** - Basic info from lot card
- **Detail hash** - Full info from detail page

Lots are only updated when hashes change, reducing database writes.

## Error Handling

The sync system handles:
- Network timeouts (with retry)
- Rate limiting (429 responses)
- Parse errors (graceful degradation)
- Partial failures (continue with other lots)

Errors are logged to:
1. Sync run record in database
2. Log file (if `--log-path` specified)
3. Console (if `--verbose`)

## Configuration

Default settings in `app/config.py`:

```python
SYNC_DEFAULTS = {
    "delay_seconds": 0.5,
    "max_concurrent_requests": 5,
    "retry_attempts": 3,
    "backoff_base_seconds": 0.5,
}
```

