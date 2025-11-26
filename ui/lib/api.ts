import type {
  LotView,
  BuyerResponse,
  BuyerCreateRequest,
  BuyerCreateResponse,
  LiveSyncControlResponse,
} from './generated';

/**
 * Filter option for lot queries.
 * UI-specific type for filter dropdowns.
 */
export interface LotFilter {
  name: string;
  values: string[];
}

/**
 * @deprecated Use LotView from generated types instead.
 * Kept for backward compatibility during migration.
 */
export interface LotSummary {
  id: string;
  title?: string;
  status?: string;
  buyer?: string;
  reserve?: number;
  updated_at?: string;
}

/**
 * Request payload for batch lot updates.
 */
export interface LotUpdateBody {
  lot_ids: string[];
  updates: Record<string, unknown>;
}

/**
 * @deprecated Use BuyerResponse/BuyerCreateRequest from generated types.
 * Kept for backward compatibility during migration.
 */
export interface BuyerPayload {
  id?: string;
  name: string;
  email?: string;
  phone?: string;
  notes?: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'API call failed');
  }

  return response.json() as Promise<T>;
}

export async function fetchFilters(): Promise<LotFilter[]> {
  const response = await fetch(`${API_BASE}/filters`);
  return handleResponse(response);
}

export async function fetchLots(filters?: Record<string, string | undefined>): Promise<LotSummary[]> {
  const url = new URL(`${API_BASE}/lots`);

  Object.entries(filters ?? {}).forEach(([key, value]) => {
    if (value) {
      url.searchParams.append(key, value);
    }
  });

  const response = await fetch(url.toString());
  return handleResponse(response);
}

export async function updateLotBatch(body: LotUpdateBody): Promise<{ updated: number }> {
  const response = await fetch(`${API_BASE}/lots/batch-update`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });

  return handleResponse(response);
}

export async function fetchBuyers(): Promise<BuyerPayload[]> {
  const response = await fetch(`${API_BASE}/buyers`);
  return handleResponse(response);
}

export async function createBuyer(buyer: BuyerPayload): Promise<BuyerPayload> {
  const response = await fetch(`${API_BASE}/buyers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buyer)
  });

  return handleResponse(response);
}

export async function updateBuyer(id: string, buyer: BuyerPayload): Promise<BuyerPayload> {
  const response = await fetch(`${API_BASE}/buyers/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buyer)
  });

  return handleResponse(response);
}

export async function deleteBuyer(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/buyers/${id}`, {
    method: 'DELETE'
  });

  await handleResponse(response);
}

export async function triggerControl(action: 'start' | 'pause' | 'stop'): Promise<{ state: string; detail?: string }> {
  const response = await fetch(`${API_BASE}/control/${action}`, {
    method: 'POST'
  });

  return handleResponse(response);
}

export async function loadDebugSample(): Promise<{ filters: LotFilter[]; lots: LotSummary[]; buyers: BuyerPayload[] }> {
  const [filters, lots, buyers] = await Promise.all([fetchFilters(), fetchLots(), fetchBuyers()]);
  return { filters, lots, buyers };
}
