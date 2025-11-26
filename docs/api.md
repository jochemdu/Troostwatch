# API Reference

This document describes the Troostwatch REST API exposed via FastAPI.

## Overview

The API provides endpoints for:

- **Lots** – Query auction lots with filters
- **Buyers** – Manage buyer records
- **Positions** – Track buyer positions on lots
- **Sync** – Trigger and control auction synchronization
- **WebSocket** – Real-time lot updates

Base URL: `http://localhost:8000` (default)

OpenAPI docs: `/docs` (Swagger UI) or `/redoc`

## Authentication

Currently no authentication is required. All endpoints are public.

---

## Endpoints

### Lots

#### `GET /lots`

List lots with optional filters.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `auction_code` | string | Filter by auction code |
| `state` | string | Filter by lot state (e.g., `running`, `closed`) |
| `limit` | integer | Maximum number of results (≥1) |

**Response:** `200 OK`

```json
[
  {
    "id": 123,
    "lot_code": "LOT001",
    "auction_code": "ABC123",
    "title": "Industrial Equipment",
    "state": "running",
    "current_bid_eur": 1500.00,
    "bid_count": 12,
    "closing_time_current": "2025-11-27T14:00:00Z"
  }
]
```

---

### Buyers

#### `GET /buyers`

List all registered buyers.

**Response:** `200 OK`

```json
[
  {
    "id": 1,
    "label": "buyer-alpha",
    "name": "Alpha Industries",
    "notes": "Primary buyer account"
  }
]
```

#### `POST /buyers`

Create a new buyer.

**Request Body:**

```json
{
  "label": "buyer-beta",
  "name": "Beta Corp",
  "notes": "Secondary account"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `label` | string | Yes | Unique buyer identifier |
| `name` | string | No | Display name |
| `notes` | string | No | Free-text notes |

**Response:** `201 Created`

```json
{
  "status": "created",
  "label": "buyer-beta"
}
```

**Errors:**

- `409 Conflict` – Buyer with this label already exists

#### `DELETE /buyers/{label}`

Delete a buyer by label.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `label` | string | Buyer label to delete |

**Response:** `204 No Content`

---

### Positions

#### `POST /positions/batch`

Batch upsert buyer positions on lots.

**Request Body:**

```json
{
  "updates": [
    {
      "buyer_label": "buyer-alpha",
      "lot_code": "LOT001",
      "auction_code": "ABC123",
      "max_budget_total_eur": 5000.00,
      "preferred_bid_eur": 2500.00,
      "watch": true
    }
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `buyer_label` | string | Yes | Buyer identifier |
| `lot_code` | string | Yes | Lot code |
| `auction_code` | string | No | Auction code (for disambiguation) |
| `max_budget_total_eur` | float | No | Maximum budget for this lot |
| `preferred_bid_eur` | float | No | Preferred bid amount |
| `watch` | boolean | No | Whether to track this lot |

**Response:** `200 OK`

```json
{
  "updated": 1,
  "positions": [
    {
      "buyer_label": "buyer-alpha",
      "lot_code": "LOT001",
      "auction_code": "ABC123"
    }
  ]
}
```

**Errors:**

- `404 Not Found` – Buyer or lot not found

---

### Sync

#### `POST /sync`

Trigger a single auction sync.

**Request Body:**

```json
{
  "auction_code": "ABC123",
  "auction_url": "https://www.troostwijkauctions.com/nl/c/ABC123",
  "max_pages": 5,
  "dry_run": false
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `auction_code` | string | Yes | Auction identifier |
| `auction_url` | string | Yes | Full auction URL |
| `max_pages` | integer | No | Limit pages to fetch |
| `dry_run` | boolean | No | If true, don't persist changes |

**Response:** `202 Accepted`

```json
{
  "auction_code": "ABC123",
  "status": "success",
  "lots_scanned": 150,
  "lots_updated": 12,
  "pages_scanned": 5,
  "duration_seconds": 8.3
}
```

#### `POST /live-sync/start`

Start continuous background sync.

**Request Body:**

```json
{
  "auction_code": "ABC123",
  "auction_url": "https://www.troostwijkauctions.com/nl/c/ABC123",
  "max_pages": null,
  "dry_run": false,
  "interval_seconds": 30
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `auction_code` | string | Yes | Auction identifier |
| `auction_url` | string | Yes | Full auction URL |
| `max_pages` | integer | No | Limit pages per sync |
| `dry_run` | boolean | No | If true, don't persist |
| `interval_seconds` | float | No | Seconds between syncs |

**Response:** `202 Accepted`

```json
{
  "status": "started",
  "auction_code": "ABC123"
}
```

#### `POST /live-sync/pause`

Pause the live sync (can be resumed).

**Response:** `202 Accepted`

```json
{
  "status": "paused"
}
```

#### `POST /live-sync/stop`

Stop the live sync completely.

**Response:** `202 Accepted`

```json
{
  "status": "stopped"
}
```

#### `GET /live-sync/status`

Get current live sync status.

**Response:** `200 OK`

```json
{
  "running": true,
  "paused": false,
  "auction_code": "ABC123",
  "last_sync_at": "2025-11-26T14:30:00Z",
  "syncs_completed": 42
}
```

---

### WebSocket

#### `WS /ws/lots`

Real-time lot update stream.

**Connection:** `ws://localhost:8000/ws/lots`

**Message Format (server → client):**

```json
{
  "type": "lot_updated",
  "lot_code": "LOT001",
  "auction_code": "ABC123",
  "current_bid_eur": 1600.00,
  "bid_count": 13
}
```

Events include:
- `lot_updated` – Lot data changed
- `sync_completed` – Sync run finished
- `buyer_created` / `buyer_deleted` – Buyer changes
- `positions_updated` – Position batch update

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Human-readable error message"
}
```

| Status | Meaning |
|--------|---------|
| `400` | Bad request (validation error) |
| `404` | Resource not found |
| `409` | Conflict (duplicate resource) |
| `422` | Unprocessable entity (invalid payload) |
| `500` | Internal server error |

---

## Running the API

```bash
# Development
uvicorn troostwatch.app.api:app --reload

# Production
uvicorn troostwatch.app.api:app --host 0.0.0.0 --port 8000
```

## Related Documentation

- [Architecture Overview](architecture.md) – System design
- [Database Schema](db.md) – Table definitions
- [Sync Service](sync.md) – Synchronization details
- [Observability](observability.md) – Logging and metrics

---

## TypeScript Types

The UI uses TypeScript types generated from this API's OpenAPI schema. This
ensures type safety across the frontend-backend boundary.

### Generating Types

```bash
# 1. Start the API server
uvicorn troostwatch.app.api:app --reload

# 2. Generate types from live server
cd ui && npm run generate:api-types

# Or generate from the committed schema file
cd ui && npm run generate:api-types:file
```

Generated types are in `ui/lib/generated/api-types.ts`.

### Using Generated Types

```typescript
import type { LotView, BuyerResponse, SyncSummaryResponse } from '@/lib/generated';

// Types match API responses exactly
const lot: LotView = await fetchLot(lotCode);
```

### CI Validation

The `ui-types` CI job validates that generated types match the backend:

1. Exports fresh OpenAPI schema from `troostwatch.app.api`
2. Regenerates TypeScript types
3. Fails if changes are detected (means types are out of sync)
4. Runs TypeScript compiler to catch type errors

### Adding New Response Models

When adding a new API endpoint:

1. Define a Pydantic response model in `troostwatch/app/api.py`
2. Use it as the `response_model` parameter
3. Regenerate types: `npm run generate:api-types`
4. Add re-export to `ui/lib/generated/index.ts` for convenience
5. Commit both the schema and generated types
