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

## Architecture Enforcement

### Automated Checks

Troostwatch uses `import-linter` to verify architectural boundaries. The tool
runs in CI and produces a report, but **does not block builds** in the current
phase.

#### Running locally

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run import-linter
lint-imports

# Run legacy check script
python scripts/check_imports.py
```

#### Reading the report

The `lint-imports` output shows:

1. **Contract name** – Which architectural rule was checked
2. **KEPT/BROKEN** – Whether the contract passed or failed
3. **Forbidden imports** – If broken, shows the violating import chains

Example output (all contracts pass):
```
=============
Import Linter
=============

Contracts: 6 kept, 0 broken.
```

Example output (contract broken):
```
-----
BROKEN: Domain layer must not import infrastructure

troostwatch.domain.models.lot -> troostwatch.infrastructure.db
```

#### Contracts enforced

| Contract | Description |
|----------|-------------|
| `domain-purity` | Domain layer has no infrastructure/services/app imports |
| `services-no-interfaces` | Services don't import from interfaces or app |
| `cli-no-infrastructure` | CLI uses services, not infrastructure directly |
| `api-no-infrastructure` | API routes use services, not infrastructure directly |
| `infrastructure-isolation` | Infrastructure doesn't import from higher layers |
| `layers` | Overall layered architecture validation |

#### Policy for violations

1. **New PRs**: Reviewers should note any new violations in review comments.
2. **Existing violations**: May be merged with documented exceptions.
3. **Resolution**: Prefer refactoring before merge; if not feasible, create a
   TODO/issue for follow-up.

See `docs/review_checklist.md` for the full PR review process.

