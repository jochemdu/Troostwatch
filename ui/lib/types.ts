/**
 * Shared TypeScript types for Troostwatch UI.
 * 
 * These types correspond to the API response schemas and domain models.
 * Keep in sync with the Python models in troostwatch/domain/models/ and
 * the API DTOs in troostwatch/services/.
 */

// =============================================================================
// Lot Types
// =============================================================================

/**
 * Possible states for a lot.
 * Corresponds to LotState enum in Python.
 */
export type LotState = 'scheduled' | 'running' | 'closed' | 'unknown';

/**
 * Lot view as returned by the API.
 * Corresponds to LotView in troostwatch/services/lots.py
 */
export interface LotView {
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
// Buyer Types
// =============================================================================

/**
 * Buyer as returned by the API.
 */
export interface Buyer {
  label: string;
  name?: string;
  notes?: string;
  created_at?: string;
}

/**
 * Request payload for creating/updating a buyer.
 */
export interface BuyerCreateRequest {
  label: string;
  name?: string;
  notes?: string;
}

// =============================================================================
// Sync Types
// =============================================================================

/**
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
 * Summary of a sync run.
 */
export interface SyncRunSummary {
  status: 'success' | 'failed' | 'error';
  auction_code?: string;
  result?: SyncRunResult;
  error?: string;
}

/**
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
// Event Types (WebSocket)
// =============================================================================

/**
 * Lot update event from WebSocket.
 */
export interface LotEvent {
  type: 'lot_update' | 'lot_created' | 'lot_closed';
  lot_code: string;
  auction_code: string;
  data: Partial<LotView>;
  timestamp: string;
}

/**
 * Sync event from WebSocket.
 */
export interface SyncEvent {
  type: 'sync_started' | 'sync_completed' | 'sync_failed';
  auction_code: string;
  result?: SyncRunResult;
  timestamp: string;
}

