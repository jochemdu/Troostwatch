/**
 * Re-export generated API types for convenient imports.
 *
 * Usage:
 *   import type { LotView, BuyerResponse, SyncSummaryResponse } from '@/lib/generated';
 *
 * These types are auto-generated from the FastAPI OpenAPI schema.
 * Run `npm run generate:api-types:file` to regenerate after backend changes.
 */

export type {
  components,
  operations,
  paths,
} from './api-types';

// Convenient type aliases for schema types
export type LotView = import('./api-types').components['schemas']['LotView'];
export type BuyerResponse = import('./api-types').components['schemas']['BuyerResponse'];
export type BuyerCreateRequest = import('./api-types').components['schemas']['BuyerCreateRequest'];
export type BuyerCreateResponse = import('./api-types').components['schemas']['BuyerCreateResponse'];
export type SyncRequest = import('./api-types').components['schemas']['SyncRequest'];
export type SyncSummaryResponse = import('./api-types').components['schemas']['SyncSummaryResponse'];
export type SyncRunResultResponse = import('./api-types').components['schemas']['SyncRunResultResponse'];
export type LiveSyncStatusResponse = import('./api-types').components['schemas']['LiveSyncStatusResponse'];
export type LiveSyncControlResponse = import('./api-types').components['schemas']['LiveSyncControlResponse'];
export type LiveSyncStartRequest = import('./api-types').components['schemas']['LiveSyncStartRequest'];
export type PositionUpdate = import('./api-types').components['schemas']['PositionUpdate'];
export type PositionBatchRequest = import('./api-types').components['schemas']['PositionBatchRequest'];
export type PositionBatchResponse = import('./api-types').components['schemas']['PositionBatchResponse'];
export type ValidationError = import('./api-types').components['schemas']['ValidationError'];
export type HTTPValidationError = import('./api-types').components['schemas']['HTTPValidationError'];
