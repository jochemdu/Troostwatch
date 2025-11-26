/**
 * Shared TypeScript types for Troostwatch UI.
 *
 * ## Type Generation Workflow
 *
 * API response types are generated from the FastAPI OpenAPI schema:
 *
 * 1. Start the API server: `uvicorn troostwatch.app.api:app`
 * 2. Generate types: `npm run generate:api-types`
 * 3. Types are written to `lib/generated/api-types.ts`
 *
 * The types below are kept in sync with:
 * - Python models in `troostwatch/domain/models/`
 * - API DTOs in `troostwatch/app/api.py`
 * - Service DTOs in `troostwatch/services/`
 *
 * ## Preferred Imports
 *
 * For API request/response types, import from generated types:
 *   import type { LotView, BuyerResponse } from '@/lib/generated';
 *
 * For UI-only types (component props, etc.), use this file.
 */

// =============================================================================
// Re-export Generated Types (preferred for API contracts)
// =============================================================================

import type { LotView as GeneratedLotView } from './generated';

export type {
  LotView,
  BuyerResponse,
  BuyerCreateRequest,
  BuyerCreateResponse,
  SyncRequest,
  SyncSummaryResponse,
  SyncRunResultResponse,
  LiveSyncStatusResponse,
  LiveSyncControlResponse,
  LiveSyncStartRequest,
  PositionUpdate,
  PositionBatchRequest,
  PositionBatchResponse,
} from './generated';

// =============================================================================
// Lot Types (deprecated - use generated LotView instead)
// =============================================================================

/**
 * Possible states for a lot.
 * Corresponds to LotState enum in Python.
 */
export type LotState = 'scheduled' | 'running' | 'closed' | 'unknown';

/**
 * @deprecated Use LotView from generated types.
 * Lot view as returned by the API.
 * Corresponds to LotView in troostwatch/services/lots.py
 */
export interface LotViewLegacy {
  auction_code: string;
  lot_code: string;
  title?: string;
  state?: LotState;
  current_bid_eur?: number;
  bid_count?: number;
  current_bidder_label?: string;
  closing_time_current?: string;  // ISO datetime
  closing_time_original?: string; // ISO datetime
  is_active: boolean;
  effective_price?: number;
}

/**
 * Lot card data from listing page.
 */
export interface LotCardData {
  auction_code: string;
  lot_code: string;
  title: string;
  url: string;
  state?: LotState;
  opens_at?: string;
  closing_time_current?: string;
  location_city?: string;
  location_country?: string;
  bid_count?: number;
  price_eur?: number;
  is_price_opening_bid?: boolean;
}

/**
 * Full lot detail data.
 */
export interface LotDetailData {
  lot_code: string;
  title: string;
  url: string;
  state?: LotState;
  opens_at?: string;
  closing_time_current?: string;
  closing_time_original?: string;
  bid_count?: number;
  opening_bid_eur?: number;
  current_bid_eur?: number;
  current_bidder_label?: string;
  vat_on_bid_pct?: number;
  auction_fee_pct?: number;
  location_city?: string;
  location_country?: string;
}

// =============================================================================
// Buyer Types (deprecated - use generated BuyerResponse/BuyerCreateRequest)
// =============================================================================

/**
 * @deprecated Use BuyerResponse from generated types.
 * Buyer as returned by the API.
 */
export interface Buyer {
  label: string;
  name?: string;
  notes?: string;
  created_at?: string;
}

/**
 * @deprecated Use BuyerCreateRequest from generated types.
 * Request payload for creating/updating a buyer.
 */
export interface BuyerCreateRequestLegacy {
  label: string;
  name?: string;
  notes?: string;
}

// =============================================================================
// Sync Types (deprecated - use generated SyncSummaryResponse etc.)
// =============================================================================

/**
 * @deprecated Use SyncRunResultResponse from generated types.
 * Result of a sync operation.
 */
export interface SyncRunResult {
  run_id?: number;
  status: 'success' | 'failed' | 'running';
  pages_scanned: number;
  lots_scanned: number;
  lots_updated: number;
  error_count: number;
  errors: string[];
}

/**
 * @deprecated Use SyncSummaryResponse from generated types.
 * Summary of a sync run.
 */
export interface SyncRunSummary {
  status: 'success' | 'failed' | 'error';
  auction_code?: string;
  result?: SyncRunResult;
  error?: string;
}

/**
 * @deprecated Use LiveSyncStatusResponse from generated types.
 * Live sync status.
 */
export interface LiveSyncStatus {
  state: 'idle' | 'running' | 'paused' | 'stopping';
  last_sync?: string;
  next_sync?: string;
  current_auction?: string;
}

// =============================================================================
// Position Types
// =============================================================================

/**
 * @deprecated Prefer PositionUpdate from generated types for API contracts.
 * A tracked position (buyer interest in a lot).
 */
export interface Position {
  buyer_label: string;
  auction_code: string;
  lot_code: string;
  max_budget_total_eur?: number;
  track_active: boolean;
  notes?: string;
}

// =============================================================================
// Event Types (WebSocket - UI-only, not in OpenAPI)
// =============================================================================

/**
 * Lot update event from WebSocket.
 */
export interface LotEvent {
  type: 'lot_update' | 'lot_created' | 'lot_closed';
  lot_code: string;
  auction_code: string;
  data: Partial<GeneratedLotView>;
  timestamp: string;
}

/**
 * Sync event from WebSocket.
 * Note: Uses deprecated SyncRunResult; update when WebSocket types are generated.
 */
export interface SyncEvent {
  type: 'sync_started' | 'sync_completed' | 'sync_failed';
  auction_code: string;
  result?: SyncRunResult;
  timestamp: string;
}

