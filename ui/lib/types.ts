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
 * ## Imports
 *
 * For API request/response types, import from generated types:
 *   import type { LotView, BuyerResponse } from '@/lib/generated';
 *
 * Or from api.ts which re-exports them:
 *   import type { LotView, BuyerResponse } from '@/lib/api';
 *
 * For WebSocket event types, use this file:
 *   import type { LotEvent, SyncEvent } from '@/lib/types';
 */

// =============================================================================
// Re-export Generated Types (for convenience)
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
// Lot State (shared enum)
// =============================================================================

/**
 * Possible states for a lot.
 * Corresponds to LotState enum in Python.
 */
export type LotState = 'scheduled' | 'running' | 'closed' | 'unknown';

// =============================================================================
// WebSocket Event Types (UI-only, not in OpenAPI)
// =============================================================================

/**
 * Lot update event from WebSocket.
 * Contains partial LotView data for incremental updates.
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
 */
export interface SyncEvent {
  type: 'sync_started' | 'sync_completed' | 'sync_failed';
  auction_code: string;
  timestamp: string;
}

