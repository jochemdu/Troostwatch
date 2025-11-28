# Database Schema

This document describes the SQLite database schema used by Troostwatch.

## Overview

Troostwatch uses SQLite for local data storage. The canonical schema is defined
in `schema/schema.sql` and managed via `SchemaMigrator` (see
[Migration Policy](migration_policy.md)).

**Current schema version:** 7

## Entity Relationship Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  auctions   │────<│    lots     │>────│   buyers    │
└─────────────┘     └─────────────┘     └─────────────┘
                          │                    │
                          │                    │
              ┌───────────┼───────────┐        │
              │           │           │        │
              ▼           ▼           ▼        ▼
        ┌──────────┐ ┌──────────┐ ┌──────────────────┐
        │ my_bids  │ │lot_items │ │ my_lot_positions │
        └──────────┘ └──────────┘ └──────────────────┘
              │           │
              │           ▼
              │     ┌──────────┐
              │     │ products │
              │     └──────────┘
              │
              ▼
        ┌─────────────┐
        │ bid_history │  (scraped bids from lot pages)
        └─────────────┘
```

## Tables

### Core Tables

#### `auctions`

Stores auction metadata synced from the source website.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment ID |
| `auction_code` | TEXT UNIQUE | Auction identifier (e.g., `ABC123`) |
| `title` | TEXT | Auction title |
| `url` | TEXT | Full auction URL |
| `pagination_pages` | TEXT | JSON list of pagination URLs |
| `starts_at` | TEXT | ISO timestamp of auction start |
| `ends_at_planned` | TEXT | ISO timestamp of planned end |

#### `lots`

Stores individual lot data within auctions.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment ID |
| `auction_id` | INTEGER FK | Reference to `auctions.id` |
| `lot_code` | TEXT | Lot identifier within auction |
| `title` | TEXT | Lot title/description |
| `url` | TEXT | Full lot URL |
| `state` | TEXT | Current state (`scheduled`, `running`, `closed`) |
| `status` | TEXT | Detailed status |
| `opens_at` | TEXT | ISO timestamp when bidding opens |
| `closing_time_current` | TEXT | Current closing time (may extend) |
| `closing_time_original` | TEXT | Original scheduled closing time |
| `bid_count` | INTEGER | Number of bids placed |
| `opening_bid_eur` | REAL | Starting bid amount |
| `current_bid_eur` | REAL | Current highest bid |
| `current_bidder_label` | TEXT | Label of current high bidder |
| `current_bid_buyer_id` | INTEGER FK | Reference to `buyers.id` (if known) |
| `buyer_fee_percent` | REAL | Buyer's premium percentage |
| `buyer_fee_vat_percent` | REAL | VAT on buyer's premium |
| `vat_percent` | REAL | VAT on hammer price |
| `awarding_state` | TEXT | Award status |
| `total_example_price_eur` | REAL | Example total cost |
| `location_city` | TEXT | Lot location city |
| `location_country` | TEXT | Lot location country |
| `seller_allocation_note` | TEXT | Seller notes |
| `brand` | TEXT | Brand/manufacturer of the lot item |
| `listing_hash` | TEXT | Hash of listing page (change detection) |
| `detail_hash` | TEXT | Hash of detail page (change detection) |
| `last_seen_at` | TEXT | Last sync timestamp for listing |
| `detail_last_seen_at` | TEXT | Last sync timestamp for details |

**Indexes:**
- `idx_lots_auction_id` on `auction_id`
- `idx_lots_current_bid_buyer_id` on `current_bid_buyer_id`

**Constraints:**
- `UNIQUE (auction_id, lot_code)`
- `FOREIGN KEY (auction_id) REFERENCES auctions(id) ON DELETE CASCADE`

#### `buyers`

Stores buyer/bidder accounts.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment ID |
| `label` | TEXT UNIQUE | Unique buyer identifier |
| `name` | TEXT | Display name |
| `notes` | TEXT | Free-text notes |

### Tracking Tables

#### `my_lot_positions`

Tracks which lots a buyer is interested in and their budget limits.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment ID |
| `buyer_id` | INTEGER FK | Reference to `buyers.id` |
| `lot_id` | INTEGER FK | Reference to `lots.id` |
| `track_active` | INTEGER | 1 = actively tracking, 0 = paused |
| `max_budget_total_eur` | REAL | Maximum total spend limit |
| `my_highest_bid_eur` | REAL | User's highest bid on this lot |

**Indexes:**
- `idx_my_lot_positions_buyer_id` on `buyer_id`
- `idx_my_lot_positions_lot_id` on `lot_id`

**Constraints:**
- `UNIQUE (buyer_id, lot_id)`
- Cascading deletes from both `buyers` and `lots`

#### `bid_history`

Stores historical bids on lots as scraped from lot detail pages.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment ID |
| `lot_id` | INTEGER FK | Reference to `lots.id` |
| `bidder_label` | TEXT | Bidder identifier/label |
| `amount_eur` | REAL | Bid amount in EUR |
| `bid_time` | TEXT | ISO timestamp of the bid |

**Indexes:**
- `idx_bid_history_lot_id` on `lot_id`

**Constraints:**
- Cascading delete from `lots`

#### `my_bids`

Records bid history for auditing and analysis.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment ID |
| `lot_id` | INTEGER FK | Reference to `lots.id` |
| `buyer_id` | INTEGER FK | Reference to `buyers.id` (nullable) |
| `amount_eur` | REAL | Bid amount |
| `placed_at` | TEXT | ISO timestamp of bid placement |
| `note` | TEXT | Optional note |

**Indexes:**
- `idx_my_bids_lot_id` on `lot_id`

### Product Tables

#### `products`

Catalog of products that may appear in lots.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment ID |
| `sku` | TEXT UNIQUE | Product SKU |
| `title` | TEXT | Product title |
| `description` | TEXT | Product description |
| `category` | TEXT | Product category |

#### `product_specs`

Key-value specifications for products.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment ID |
| `product_id` | INTEGER FK | Reference to `products.id` |
| `spec_key` | TEXT | Specification name |
| `spec_value` | TEXT | Specification value |

**Constraints:**
- `UNIQUE (product_id, spec_key)`
- Cascading delete from `products`

#### `lot_items`

Links products to lots (many-to-many with quantities).

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment ID |
| `lot_id` | INTEGER FK | Reference to `lots.id` |
| `product_id` | INTEGER FK | Reference to `products.id` |
| `quantity` | REAL | Quantity in lot (default 1) |
| `unit` | TEXT | Unit of measure |
| `extra_cost_eur` | REAL | Additional costs |
| `extra_cost_description` | TEXT | Description of extra costs |

#### `product_layers`

Hierarchical product layer data from lot details.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment ID |
| `lot_id` | INTEGER FK | Reference to `lots.id` |
| `layer` | INTEGER | Layer depth (0 = root) |
| `title` | TEXT | Layer title |
| `value` | TEXT | Layer value |

### Market Tables

#### `market_offers`

Tracks offers made on lots.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment ID |
| `lot_id` | INTEGER FK | Reference to `lots.id` |
| `buyer_id` | INTEGER FK | Reference to `buyers.id` |
| `offer_amount_eur` | REAL | Offer amount |
| `offer_state` | TEXT | Offer status |
| `created_at` | TEXT | Creation timestamp |
| `updated_at` | TEXT | Last update timestamp |

### System Tables

#### `sync_runs`

Logs each synchronization run for monitoring and debugging.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment ID |
| `auction_code` | TEXT | Auction being synced |
| `started_at` | TEXT | Sync start timestamp |
| `finished_at` | TEXT | Sync end timestamp |
| `status` | TEXT | Result (`success`, `failed`, `partial`) |
| `pages_scanned` | INTEGER | Number of pages fetched |
| `lots_scanned` | INTEGER | Total lots found |
| `lots_updated` | INTEGER | Lots with changes |
| `error_count` | INTEGER | Errors encountered |
| `max_pages` | INTEGER | Page limit (if set) |
| `dry_run` | INTEGER | 1 = dry run, 0 = real |
| `notes` | TEXT | Additional notes |

#### `schema_version`

Tracks the current schema version for migrations.

| Column | Type | Description |
|--------|------|-------------|
| `version` | INTEGER PK | Schema version number |
| `applied_at` | TEXT | When version was applied |

#### `schema_migrations`

Records individual migration scripts that have been applied.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment ID |
| `name` | TEXT UNIQUE | Migration identifier |
| `applied_at` | TEXT | When migration was applied |
| `notes` | TEXT | Optional notes |

#### `user_preferences`

Key-value store for user settings.

| Column | Type | Description |
|--------|------|-------------|
| `key` | TEXT PK | Preference key |
| `value` | TEXT | Preference value |

## Schema Management

See [Migration Policy](migration_policy.md) for details on:

- How to add columns or tables
- Version tracking with `CURRENT_SCHEMA_VERSION`
- Using `scripts/check_schema.py` to inspect state

## Related Documentation

- [API Reference](api.md) – REST endpoints
- [Sync Service](sync.md) – How data is populated
- [Architecture](architecture.md) – System design
