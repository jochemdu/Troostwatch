/**
 * API client for Troostwatch UI.
 *
 * All types are imported from the generated OpenAPI types to ensure
 * type safety across the frontend-backend boundary.
 *
 * @see ui/lib/generated/api-types.ts for the generated types
 * @see troostwatch/app/api.py for the FastAPI backend
 */
import type {
  LotView,
  BuyerResponse,
  BuyerCreateRequest,
  BuyerCreateResponse,
  LiveSyncControlResponse,
  LiveSyncStatusResponse,
  LiveSyncStartRequest,
  SyncSummaryResponse,
  SyncRequest,
  PositionBatchRequest,
  PositionBatchResponse,
} from './generated';

// Re-export types for convenience
export type { LotView, BuyerResponse, BuyerCreateRequest, BuyerCreateResponse };

// =============================================================================
// UI-specific Types (not in OpenAPI, used for local state/props)
// =============================================================================

/**
 * Query parameters for fetching lots.
 */
export interface LotQueryParams {
  auction_code?: string;
  state?: string;
  brand?: string;
  limit?: number;
}

// =============================================================================
// API Client Configuration
// =============================================================================

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'API call failed');
  }

  return response.json() as Promise<T>;
}

// =============================================================================
// Lot Endpoints (GET /lots)
// =============================================================================

/**
 * Fetch lots from the API with optional filters.
 * @see GET /lots in troostwatch/app/api.py
 */
export async function fetchLots(params?: LotQueryParams): Promise<LotView[]> {
  const url = new URL(`${API_BASE}/lots`);

  if (params?.auction_code) {
    url.searchParams.append('auction_code', params.auction_code);
  }
  if (params?.state) {
    url.searchParams.append('state', params.state);
  }
  if (params?.brand) {
    url.searchParams.append('brand', params.brand);
  }
  if (params?.limit) {
    url.searchParams.append('limit', params.limit.toString());
  }

  const response = await fetch(url.toString());
  return handleResponse<LotView[]>(response);
}

// =============================================================================
// Buyer Endpoints (GET/POST/DELETE /buyers)
// =============================================================================

/**
 * Fetch all buyers.
 * @see GET /buyers in troostwatch/app/api.py
 */
export async function fetchBuyers(): Promise<BuyerResponse[]> {
  const response = await fetch(`${API_BASE}/buyers`);
  return handleResponse<BuyerResponse[]>(response);
}

/**
 * Create a new buyer.
 * @see POST /buyers in troostwatch/app/api.py
 */
export async function createBuyer(buyer: BuyerCreateRequest): Promise<BuyerCreateResponse> {
  const response = await fetch(`${API_BASE}/buyers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buyer)
  });

  return handleResponse<BuyerCreateResponse>(response);
}

/**
 * Delete a buyer by label.
 * @see DELETE /buyers/{label} in troostwatch/app/api.py
 */
export async function deleteBuyer(label: string): Promise<void> {
  const response = await fetch(`${API_BASE}/buyers/${label}`, {
    method: 'DELETE'
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Delete failed');
  }
}

// =============================================================================
// Sync Endpoints (/sync, /live-sync/*)
// =============================================================================

/**
 * Trigger a sync for an auction.
 * @see POST /sync in troostwatch/app/api.py
 */
export async function triggerSync(request: SyncRequest): Promise<SyncSummaryResponse> {
  const response = await fetch(`${API_BASE}/sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });

  return handleResponse<SyncSummaryResponse>(response);
}

/**
 * Start live sync for an auction.
 * @see POST /live-sync/start in troostwatch/app/api.py
 */
export async function startLiveSync(request: LiveSyncStartRequest): Promise<LiveSyncControlResponse> {
  const response = await fetch(`${API_BASE}/live-sync/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });

  return handleResponse<LiveSyncControlResponse>(response);
}

/**
 * Pause live sync.
 * @see POST /live-sync/pause in troostwatch/app/api.py
 */
export async function pauseLiveSync(): Promise<LiveSyncControlResponse> {
  const response = await fetch(`${API_BASE}/live-sync/pause`, {
    method: 'POST'
  });

  return handleResponse<LiveSyncControlResponse>(response);
}

/**
 * Stop live sync.
 * @see POST /live-sync/stop in troostwatch/app/api.py
 */
export async function stopLiveSync(): Promise<LiveSyncControlResponse> {
  const response = await fetch(`${API_BASE}/live-sync/stop`, {
    method: 'POST'
  });

  return handleResponse<LiveSyncControlResponse>(response);
}

/**
 * Get live sync status.
 * @see GET /live-sync/status in troostwatch/app/api.py
 */
export async function getLiveSyncStatus(): Promise<LiveSyncStatusResponse> {
  const response = await fetch(`${API_BASE}/live-sync/status`);
  return handleResponse<LiveSyncStatusResponse>(response);
}

// =============================================================================
// Position Endpoints (POST /positions/batch)
// =============================================================================

/**
 * Batch update positions.
 * @see POST /positions/batch in troostwatch/app/api.py
 */
export async function updatePositionsBatch(request: PositionBatchRequest): Promise<PositionBatchResponse> {
  const response = await fetch(`${API_BASE}/positions/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request)
  });

  return handleResponse<PositionBatchResponse>(response);
}

// =============================================================================
// Debug/Sample Helpers
// =============================================================================

/**
 * Load sample data for debugging (lots + buyers).
 */
export async function loadDebugSample(): Promise<{ lots: LotView[]; buyers: BuyerResponse[] }> {
  const [lots, buyers] = await Promise.all([fetchLots(), fetchBuyers()]);
  return { lots, buyers };
}
