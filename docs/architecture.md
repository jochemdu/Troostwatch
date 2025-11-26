# Troostwatch Architecture

## Overview

Troostwatch follows a layered architecture pattern to maintain separation of concerns and enable testability.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Interfaces Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │   CLI (cli/) │  │  API (app/)  │  │  WebSocket (app/ws/) │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘   │
└─────────┼─────────────────┼─────────────────────┼───────────────┘
          │                 │                     │
          ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Services Layer                            │
│  ┌────────────┐  ┌──────────────┐  ┌────────────┐  ┌─────────┐  │
│  │ SyncService│  │ BuyerService │  │ LotService │  │ Bidding │  │
│  └────────────┘  └──────────────┘  └────────────┘  └─────────┘  │
└─────────────────────────────────────────────────────────────────┘
          │                 │                     │
          ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Domain Layer                              │
│  ┌─────────┐  ┌──────────┐  ┌───────────┐  ┌─────────────────┐  │
│  │   Lot   │  │  Auction │  │  Buyer    │  │ Analytics/DTOs  │  │
│  └─────────┘  └──────────┘  └───────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
          │                 │                     │
          ▼                 ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Infrastructure Layer                         │
│  ┌────────────────┐  ┌─────────────┐  ┌─────────────────────┐   │
│  │  Repositories  │  │ HTTP Client │  │  Parsers/Scrapers   │   │
│  └────────────────┘  └─────────────┘  └─────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
troostwatch/
├── app/                    # Application layer (FastAPI, config)
│   ├── api.py             # API routes
│   ├── config.py          # Application configuration
│   └── dependencies.py    # Dependency injection
│
├── domain/                 # Domain layer (business logic)
│   ├── models/            # Domain models (Lot, Auction)
│   │   ├── lot.py        # Lot model with business logic
│   │   └── auction.py    # Auction model
│   └── analytics/         # Analytics and summaries
│
├── infrastructure/         # External adapters
│   ├── db/               # Database access
│   │   ├── repositories/ # Repository pattern
│   │   └── schema.py     # Database schema
│   ├── http/             # HTTP client for Troostwijk
│   └── web/parsers/      # HTML parsing
│
├── interfaces/            # User interfaces
│   └── cli/              # Command-line interface
│       ├── context.py    # CLI context (bridges to services)
│       └── *.py          # Individual commands
│
└── services/              # Business logic services
    ├── sync/             # Sync service
    ├── buyers.py         # Buyer management
    ├── lots.py           # Lot viewing/management
    └── bidding.py        # Bidding logic
```

## Layer Rules

### 1. Interfaces Layer (CLI, API)
- **Can import**: Services, Domain models
- **Cannot import**: Infrastructure directly (except designated adapters)
- **Responsibility**: Handle user input/output, format responses

### 2. Services Layer
- **Can import**: Domain models, Infrastructure (via dependency injection)
- **Cannot import**: Interfaces
- **Responsibility**: Business logic orchestration, use case implementation

### 3. Domain Layer
- **Can import**: Nothing from other layers (pure Python only)
- **Cannot import**: Infrastructure, Services, Interfaces
- **Responsibility**: Business rules, domain invariants

### 4. Infrastructure Layer
- **Can import**: Domain models (for mapping)
- **Cannot import**: Services, Interfaces
- **Responsibility**: External system integration (DB, HTTP, parsers)

## Import Rules

The import checker (`scripts/check_imports.py`) enforces these rules:

| Source Directory | Forbidden Imports | Exceptions |
|-----------------|-------------------|------------|
| `interfaces/cli/*` | `infrastructure.db`, `infrastructure.http` | `context.py`, `auth.py`, `debug.py` |
| `app/*` | `infrastructure.db.repositories` | `api.py`, `dependencies.py` |
| `domain/*` | `infrastructure.*` | None |

## Domain Models

### Lot (`domain/models/lot.py`)
Business logic for auction lots:
- `is_active` - Check if lot is running or scheduled
- `effective_price` - Current bid or opening bid
- `can_bid(amount)` - Validate bid amount

### Auction (`domain/models/auction.py`)
Business logic for auctions:
- `get_all_page_urls()` - All pagination URLs
- `page_count` - Number of pages

## Services

### SyncService
Handles synchronization of auction data from Troostwijk:
- `run_sync()` - Sync a single auction
- `run_multi_sync()` - Sync multiple auctions
- `choose_auction()` - Select auction for sync

### LotViewService
Read-only lot access for APIs and CLIs:
- `list_lots()` - List lots with filters
- `list_domain_lots()` - Get lots as domain models
- `get_active_lots()` - Get only active lots

### BuyerService
Buyer management:
- `add_buyer()` - Register new buyer
- `list_buyers()` - List all buyers
- `delete_buyer()` - Remove buyer

## Adding New Features

1. **Domain logic** → Add to `domain/models/`
2. **Business operations** → Add to `services/`
3. **CLI commands** → Add to `interfaces/cli/`, use services
4. **API endpoints** → Add to `app/api.py`, use services
5. **External integrations** → Add to `infrastructure/`

Always run `python scripts/check_imports.py` before committing to verify architectural boundaries.

