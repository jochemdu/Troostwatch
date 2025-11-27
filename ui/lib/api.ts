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
// Lot Detail Types (pending OpenAPI regeneration)
// =============================================================================

/**
 * Specification for a lot item.
 */
export interface LotSpec {
  id: number;
  parent_id: number | null;
  template_id: number | null;
  key: string;
  value: string | null;
  ean: string | null;
  price_eur: number | null;
  release_date: string | null;
  category: string | null;
}

/**
 * A reference price for a lot from an external source.
 */
export interface ReferencePrice {
  id: number;
  condition: 'new' | 'used' | 'refurbished';
  price_eur: number;
  source?: string | null;
  url?: string | null;
  notes?: string | null;
  created_at?: string | null;
}

/**
 * Reusable spec template that can be applied to multiple lots.
 */
export interface SpecTemplate {
  id: number;
  parent_id: number | null;
  title: string;
  value: string | null;
  ean: string | null;
  price_eur: number | null;
  release_date: string | null;
  category: string | null;
  created_at?: string | null;
}

/**
 * Detailed lot information including specs and reference prices.
 */
export interface LotDetailResponse {
  auction_code: string;
  lot_code: string;
  title?: string | null;
  url?: string | null;
  state?: string | null;
  current_bid_eur?: number | null;
  bid_count?: number | null;
  opening_bid_eur?: number | null;
  closing_time_current?: string | null;
  closing_time_original?: string | null;
  brand?: string | null;
  ean?: string | null;
  location_city?: string | null;
  location_country?: string | null;
  notes?: string | null;
  specs: LotSpec[];
  reference_prices: ReferencePrice[];
}

/**
 * Request to update lot notes and EAN.
 */
export interface LotUpdateRequest {
  notes?: string | null;
  ean?: string | null;
}

/**
 * Request to add a reference price.
 */
export interface ReferencePriceCreateRequest {
  condition: 'new' | 'used' | 'refurbished';
  price_eur: number;
  source?: string | null;
  url?: string | null;
  notes?: string | null;
}

/**
 * Request to update a reference price.
 */
export interface ReferencePriceUpdateRequest {
  condition?: 'new' | 'used' | 'refurbished';
  price_eur?: number;
  source?: string | null;
  url?: string | null;
  notes?: string | null;
}

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
// Lot Endpoints (GET /lots, GET/PATCH /lots/{lot_code})
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

/**
 * Fetch detailed lot information including specs and reference prices.
 * @see GET /lots/{lot_code} in troostwatch/app/api.py
 */
export async function fetchLotDetail(lotCode: string, auctionCode?: string): Promise<LotDetailResponse> {
  const url = new URL(`${API_BASE}/lots/${encodeURIComponent(lotCode)}`);
  if (auctionCode) {
    url.searchParams.append('auction_code', auctionCode);
  }
  const response = await fetch(url.toString());
  return handleResponse<LotDetailResponse>(response);
}

/**
 * Update lot notes.
 * @see PATCH /lots/{lot_code} in troostwatch/app/api.py
 */
export async function updateLot(lotCode: string, updates: LotUpdateRequest, auctionCode?: string): Promise<LotDetailResponse> {
  const url = new URL(`${API_BASE}/lots/${encodeURIComponent(lotCode)}`);
  if (auctionCode) {
    url.searchParams.append('auction_code', auctionCode);
  }
  const response = await fetch(url.toString(), {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  return handleResponse<LotDetailResponse>(response);
}

/**
 * Delete a lot and all related data.
 * @see DELETE /lots/{lot_code} in troostwatch/app/api.py
 */
export async function deleteLot(lotCode: string, auctionCode: string): Promise<void> {
  const url = new URL(`${API_BASE}/lots/${encodeURIComponent(lotCode)}`);
  url.searchParams.append('auction_code', auctionCode);
  const response = await fetch(url.toString(), { method: 'DELETE' });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to delete lot: ${response.status}`);
  }
}

// =============================================================================
// Bid Endpoints
// =============================================================================

export interface Bid {
  id: number;
  buyer_label: string;
  lot_code: string;
  auction_code: string;
  lot_title: string | null;
  amount_eur: number;
  placed_at: string;
  note: string | null;
}

interface BidCreateRequest {
  buyer_label: string;
  auction_code: string;
  lot_code: string;
  amount_eur: number;
  note?: string;
}

export async function fetchBids(buyer?: string, lotCode?: string): Promise<Bid[]> {
  const url = new URL(`${API_BASE}/bids`);
  if (buyer) url.searchParams.append('buyer', buyer);
  if (lotCode) url.searchParams.append('lot_code', lotCode);
  const response = await fetch(url.toString());
  return handleResponse<Bid[]>(response);
}

export async function createBid(payload: BidCreateRequest): Promise<Bid> {
  const response = await fetch(`${API_BASE}/bids`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return handleResponse<Bid>(response);
}

/**
 * Add a reference price for a lot.
 * @see POST /lots/{lot_code}/reference-prices in troostwatch/app/api.py
 */
export async function addReferencePrice(
  lotCode: string,
  data: ReferencePriceCreateRequest,
  auctionCode?: string
): Promise<ReferencePrice> {
  const url = new URL(`${API_BASE}/lots/${encodeURIComponent(lotCode)}/reference-prices`);
  if (auctionCode) {
    url.searchParams.append('auction_code', auctionCode);
  }
  const response = await fetch(url.toString(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<ReferencePrice>(response);
}

/**
 * Update a reference price.
 * @see PATCH /lots/{lot_code}/reference-prices/{ref_id} in troostwatch/app/api.py
 */
export async function updateReferencePrice(
  lotCode: string,
  refId: number,
  data: ReferencePriceUpdateRequest
): Promise<ReferencePrice> {
  const url = new URL(`${API_BASE}/lots/${encodeURIComponent(lotCode)}/reference-prices/${refId}`);
  const response = await fetch(url.toString(), {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<ReferencePrice>(response);
}

/**
 * Delete a reference price.
 * @see DELETE /lots/{lot_code}/reference-prices/{ref_id} in troostwatch/app/api.py
 */
export async function deleteReferencePrice(lotCode: string, refId: number): Promise<void> {
  const url = new URL(`${API_BASE}/lots/${encodeURIComponent(lotCode)}/reference-prices/${refId}`);
  const response = await fetch(url.toString(), { method: 'DELETE' });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Delete failed');
  }
}

// =============================================================================
// Bid History Endpoints
// =============================================================================

/**
 * A single bid in the lot's bid history.
 */
export interface BidHistoryEntry {
  id: number;
  bidder_label: string;
  amount_eur: number;
  timestamp: string | null;
  created_at: string | null;
}

/**
 * Fetch bid history for a lot.
 * @see GET /lots/{lot_code}/bid-history in troostwatch/app/api.py
 */
export async function fetchBidHistory(lotCode: string, auctionCode?: string): Promise<BidHistoryEntry[]> {
  const url = new URL(`${API_BASE}/lots/${encodeURIComponent(lotCode)}/bid-history`);
  if (auctionCode) {
    url.searchParams.append('auction_code', auctionCode);
  }
  const response = await fetch(url.toString());
  return handleResponse<BidHistoryEntry[]>(response);
}

// =============================================================================
// Search Endpoints
// =============================================================================

/**
 * A search result with lot details and match info.
 */
export interface SearchResult {
  auction_code: string;
  lot_code: string;
  title: string | null;
  state: string | null;
  current_bid_eur: number | null;
  brand: string | null;
  match_field: 'title' | 'brand' | 'lot_code' | 'ean';
}

/**
 * Search lots by title, brand, lot code, or EAN.
 * @see GET /search in troostwatch/app/api.py
 */
export async function searchLots(
  query: string,
  options?: { state?: string; limit?: number }
): Promise<SearchResult[]> {
  const url = new URL(`${API_BASE}/search`);
  url.searchParams.append('q', query);
  if (options?.state) {
    url.searchParams.append('state', options.state);
  }
  if (options?.limit) {
    url.searchParams.append('limit', options.limit.toString());
  }
  const response = await fetch(url.toString());
  return handleResponse<SearchResult[]>(response);
}

// =============================================================================
// Dashboard Stats Endpoints
// =============================================================================

/**
 * Dashboard statistics overview.
 */
export interface DashboardStats {
  total_auctions: number;
  active_auctions: number;
  total_lots: number;
  running_lots: number;
  scheduled_lots: number;
  closed_lots: number;
  total_bids: number;
  total_positions: number;
  total_buyers: number;
}

/**
 * Fetch dashboard statistics.
 * @see GET /stats in troostwatch/app/api.py
 */
export async function fetchDashboardStats(): Promise<DashboardStats> {
  const response = await fetch(`${API_BASE}/stats`);
  return handleResponse<DashboardStats>(response);
}

// =============================================================================
// Lot Spec Endpoints (POST/DELETE /lots/{lot_code}/specs)
// =============================================================================

/**
 * Request to add a specification.
 */
export interface LotSpecCreateRequest {
  key: string;
  value?: string;
  parent_id?: number | null;
  ean?: string | null;
  price_eur?: number | null;
  template_id?: number | null;
  release_date?: string | null;
  category?: string | null;
}

/**
 * Request to create a spec template.
 */
export interface SpecTemplateCreateRequest {
  title: string;
  value?: string | null;
  ean?: string | null;
  price_eur?: number | null;
  parent_id?: number | null;
  release_date?: string | null;
  category?: string | null;
}

/**
 * Add a specification for a lot.
 * @see POST /lots/{lot_code}/specs in troostwatch/app/api.py
 */
export async function addLotSpec(
  lotCode: string,
  data: LotSpecCreateRequest,
  auctionCode?: string
): Promise<LotSpec> {
  const url = new URL(`${API_BASE}/lots/${encodeURIComponent(lotCode)}/specs`);
  if (auctionCode) {
    url.searchParams.append('auction_code', auctionCode);
  }
  const response = await fetch(url.toString(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<LotSpec>(response);
}

/**
 * Delete a specification for a lot.
 * @see DELETE /lots/{lot_code}/specs/{spec_id} in troostwatch/app/api.py
 */
export async function deleteLotSpec(lotCode: string, specId: number): Promise<void> {
  const url = new URL(`${API_BASE}/lots/${encodeURIComponent(lotCode)}/specs/${specId}`);
  const response = await fetch(url.toString(), { method: 'DELETE' });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Delete failed');
  }
}

// =============================================================================
// Spec Templates Endpoints (reusable specifications)
// =============================================================================

/**
 * Fetch all spec templates.
 * @see GET /spec-templates in troostwatch/app/api.py
 */
export async function fetchSpecTemplates(parentId?: number): Promise<SpecTemplate[]> {
  const url = new URL(`${API_BASE}/spec-templates`);
  if (parentId !== undefined) {
    url.searchParams.append('parent_id', parentId.toString());
  }
  const response = await fetch(url.toString());
  return handleResponse<SpecTemplate[]>(response);
}

/**
 * Create a new spec template.
 * @see POST /spec-templates in troostwatch/app/api.py
 */
export async function createSpecTemplate(data: SpecTemplateCreateRequest): Promise<SpecTemplate> {
  const response = await fetch(`${API_BASE}/spec-templates`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<SpecTemplate>(response);
}

/**
 * Delete a spec template.
 * @see DELETE /spec-templates/{template_id} in troostwatch/app/api.py
 */
export async function deleteSpecTemplate(templateId: number): Promise<void> {
  const response = await fetch(`${API_BASE}/spec-templates/${templateId}`, { method: 'DELETE' });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Delete failed');
  }
}

/**
 * Request to update a spec template.
 */
export interface SpecTemplateUpdateRequest {
  title?: string;
  value?: string | null;
  ean?: string | null;
  price_eur?: number | null;
  release_date?: string | null;
  category?: string | null;
}

/**
 * Update a spec template.
 * @see PATCH /spec-templates/{template_id} in troostwatch/app/api.py
 */
export async function updateSpecTemplate(
  templateId: number,
  data: SpecTemplateUpdateRequest
): Promise<SpecTemplate> {
  const response = await fetch(`${API_BASE}/spec-templates/${templateId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return handleResponse<SpecTemplate>(response);
}

/**
 * Apply a spec template to a lot.
 * @see POST /lots/{lot_code}/apply-template in troostwatch/app/api.py
 */
export async function applyTemplateToLot(
  lotCode: string,
  templateId: number,
  parentId?: number | null,
  auctionCode?: string
): Promise<LotSpec> {
  const url = new URL(`${API_BASE}/lots/${encodeURIComponent(lotCode)}/apply-template`);
  if (auctionCode) {
    url.searchParams.append('auction_code', auctionCode);
  }
  const response = await fetch(url.toString(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ template_id: templateId, parent_id: parentId }),
  });
  return handleResponse<LotSpec>(response);
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

// =============================================================================
// Position Endpoints
// =============================================================================

export interface Position {
  id: number;
  buyer_label: string;
  lot_code: string;
  auction_code: string | null;
  max_budget_total_eur: number | null;
  preferred_bid_eur: number | null;
  track_active: boolean;
  lot_title: string | null;
  current_bid_eur: number | null;
  closing_time: string | null;
}

export async function fetchPositions(buyer?: string): Promise<Position[]> {
  const url = new URL(`${API_BASE}/positions`);
  if (buyer) url.searchParams.append('buyer', buyer);
  const response = await fetch(url.toString());
  return handleResponse<Position[]>(response);
}

export async function deletePosition(buyerLabel: string, lotCode: string, auctionCode?: string): Promise<void> {
  const url = new URL(`${API_BASE}/positions/${encodeURIComponent(buyerLabel)}/${encodeURIComponent(lotCode)}`);
  if (auctionCode) url.searchParams.append('auction_code', auctionCode);
  const response = await fetch(url.toString(), { method: 'DELETE' });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Failed to delete position');
  }
}

export async function createPosition(data: {
  buyer_label: string;
  lot_code: string;
  auction_code?: string;
  max_budget_total_eur?: number;
}): Promise<void> {
  const response = await fetch(`${API_BASE}/positions/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ updates: [data] }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'Failed to create position');
  }
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

// =============================================================================
// Auction Endpoints
// =============================================================================

/**
 * Auction summary from list endpoint.
 */
export interface Auction {
  auction_code: string;
  title: string | null;
  url: string | null;
  starts_at: string | null;
  ends_at_planned: string | null;
  active_lots: number;
  lot_count: number;
}

/**
 * Detailed auction information.
 */
export interface AuctionDetail {
  auction_code: string;
  title: string | null;
  url: string | null;
  starts_at: string | null;
  ends_at_planned: string | null;
  lot_count: number;
}

/**
 * Request to update an auction.
 */
export interface AuctionUpdateRequest {
  title?: string | null;
  url?: string | null;
  starts_at?: string | null;
  ends_at_planned?: string | null;
}

/**
 * Response after deleting an auction.
 */
export interface AuctionDeleteResponse {
  status: string;
  auction_deleted: number;
  lots_deleted: number;
}

/**
 * Fetch all auctions.
 * @see GET /auctions in troostwatch/app/api.py
 */
export async function fetchAuctions(includeInactive: boolean = false): Promise<Auction[]> {
  const url = new URL(`${API_BASE}/auctions`);
  if (includeInactive) {
    url.searchParams.append('include_inactive', 'true');
  }
  const response = await fetch(url.toString());
  return handleResponse<Auction[]>(response);
}

/**
 * Fetch a single auction by code.
 * @see GET /auctions/{auction_code} in troostwatch/app/api.py
 */
export async function fetchAuction(auctionCode: string): Promise<AuctionDetail> {
  const response = await fetch(`${API_BASE}/auctions/${encodeURIComponent(auctionCode)}`);
  return handleResponse<AuctionDetail>(response);
}

/**
 * Update an auction.
 * @see PATCH /auctions/{auction_code} in troostwatch/app/api.py
 */
export async function updateAuction(auctionCode: string, updates: AuctionUpdateRequest): Promise<AuctionDetail> {
  const response = await fetch(`${API_BASE}/auctions/${encodeURIComponent(auctionCode)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  return handleResponse<AuctionDetail>(response);
}

/**
 * Delete an auction.
 * @see DELETE /auctions/{auction_code} in troostwatch/app/api.py
 */
export async function deleteAuction(auctionCode: string, deleteLots: boolean = false): Promise<AuctionDeleteResponse> {
  const url = new URL(`${API_BASE}/auctions/${encodeURIComponent(auctionCode)}`);
  if (deleteLots) {
    url.searchParams.append('delete_lots', 'true');
  }
  const response = await fetch(url.toString(), { method: 'DELETE' });
  return handleResponse<AuctionDeleteResponse>(response);
}

// =============================================================================
// Reports Endpoints
// =============================================================================

export interface BuyerSummaryReport {
  buyer_label: string;
  tracked_count: number;
  open_count: number;
  closed_count: number;
  open_exposure_min_eur: number;
  open_exposure_max_eur: number;
  open_tracked_lots: Array<{
    lot_code: string;
    title: string;
    state: string;
    current_bid_eur: number | null;
    max_budget_total_eur: number | null;
    track_active: boolean;
  }>;
  won_lots: Array<{
    lot_code: string;
    title: string;
    state: string;
    current_bid_eur: number | null;
    max_budget_total_eur: number | null;
    track_active: boolean;
  }>;
}

export async function fetchBuyerSummary(buyerLabel: string): Promise<BuyerSummaryReport> {
  const response = await fetch(`${API_BASE}/reports/buyer/${encodeURIComponent(buyerLabel)}`);
  return handleResponse<BuyerSummaryReport>(response);
}
