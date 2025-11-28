/**
 * ReviewQueue component for reviewing and approving extracted product codes.
 *
 * Displays a paginated list of codes pending approval, with image previews
 * and approve/reject actions.
 */
import { useState, useEffect, useCallback } from 'react';
import type {
  PendingCodeResponse,
  PendingCodesListResponse,
  ReviewStatsResponse,
} from '../lib/generated';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ReviewQueueProps {
  onStatsUpdate?: (stats: ReviewStatsResponse) => void;
}

export default function ReviewQueue({ onStatsUpdate }: ReviewQueueProps) {
  const [codes, setCodes] = useState<PendingCodeResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCodes, setSelectedCodes] = useState<Set<number>>(new Set());
  const [processingIds, setProcessingIds] = useState<Set<number>>(new Set());
  const [stats, setStats] = useState<ReviewStatsResponse | null>(null);
  const [codeTypeFilter, setCodeTypeFilter] = useState<string>('');

  const fetchCodes = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
      });
      if (codeTypeFilter) {
        params.append('code_type', codeTypeFilter);
      }
      const response = await fetch(`${API_URL}/review/codes/pending?${params}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data: PendingCodesListResponse = await response.json();
      setCodes(data.codes);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch codes');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, codeTypeFilter]);

  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/review/stats`);
      if (response.ok) {
        const data: ReviewStatsResponse = await response.json();
        setStats(data);
        onStatsUpdate?.(data);
      }
    } catch (_err) {
      // Stats are non-critical, ignore errors
    }
  }, [onStatsUpdate]);

  useEffect(() => {
    fetchCodes();
  }, [fetchCodes]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const approveCode = async (codeId: number) => {
    setProcessingIds((prev) => new Set(prev).add(codeId));
    try {
      const response = await fetch(`${API_URL}/review/codes/${codeId}/approve`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to approve code');
      }
      // Remove from list
      setCodes((prev) => prev.filter((c) => c.id !== codeId));
      setTotal((prev) => prev - 1);
      fetchStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to approve');
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev);
        next.delete(codeId);
        return next;
      });
    }
  };

  const rejectCode = async (codeId: number) => {
    setProcessingIds((prev) => new Set(prev).add(codeId));
    try {
      const response = await fetch(`${API_URL}/review/codes/${codeId}/reject`, {
        method: 'POST',
      });
      if (!response.ok) {
        throw new Error('Failed to reject code');
      }
      // Remove from list
      setCodes((prev) => prev.filter((c) => c.id !== codeId));
      setTotal((prev) => prev - 1);
      fetchStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reject');
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev);
        next.delete(codeId);
        return next;
      });
    }
  };

  const bulkApprove = async () => {
    if (selectedCodes.size === 0) return;
    const codeIds = Array.from(selectedCodes);
    setProcessingIds((prev) => new Set([...prev, ...codeIds]));
    try {
      const response = await fetch(`${API_URL}/review/codes/bulk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code_ids: codeIds, approved: true }),
      });
      if (!response.ok) {
        throw new Error('Bulk approve failed');
      }
      setCodes((prev) => prev.filter((c) => !selectedCodes.has(c.id)));
      setTotal((prev) => prev - codeIds.length);
      setSelectedCodes(new Set());
      fetchStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bulk approve failed');
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev);
        codeIds.forEach((id) => next.delete(id));
        return next;
      });
    }
  };

  const bulkReject = async () => {
    if (selectedCodes.size === 0) return;
    const codeIds = Array.from(selectedCodes);
    setProcessingIds((prev) => new Set([...prev, ...codeIds]));
    try {
      const response = await fetch(`${API_URL}/review/codes/bulk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code_ids: codeIds, approved: false }),
      });
      if (!response.ok) {
        throw new Error('Bulk reject failed');
      }
      setCodes((prev) => prev.filter((c) => !selectedCodes.has(c.id)));
      setTotal((prev) => prev - codeIds.length);
      setSelectedCodes(new Set());
      fetchStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bulk reject failed');
    } finally {
      setProcessingIds((prev) => {
        const next = new Set(prev);
        codeIds.forEach((id) => next.delete(id));
        return next;
      });
    }
  };

  const toggleCodeSelection = (codeId: number) => {
    setSelectedCodes((prev) => {
      const next = new Set(prev);
      if (next.has(codeId)) {
        next.delete(codeId);
      } else {
        next.add(codeId);
      }
      return next;
    });
  };

  const selectAll = () => {
    if (selectedCodes.size === codes.length) {
      setSelectedCodes(new Set());
    } else {
      setSelectedCodes(new Set(codes.map((c) => c.id)));
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  const getCodeTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      ean: 'EAN',
      serial_number: 'Serial',
      model_number: 'Model',
      product_code: 'Product',
    };
    return labels[type] || type;
  };

  const getConfidenceColor = (confidence: string) => {
    const colors: Record<string, string> = {
      high: '#22c55e',
      medium: '#f59e0b',
      low: '#ef4444',
    };
    return colors[confidence] || '#6b7280';
  };

  if (loading && codes.length === 0) {
    return <div className="panel">Loading codes...</div>;
  }

  return (
    <div className="review-queue">
      {/* Stats bar */}
      {stats && (
        <div className="stats-bar panel" style={{ marginBottom: 16 }}>
          <div className="stats-grid">
            <div className="stat-item">
              <span className="stat-label">Pending</span>
              <span className="stat-value" style={{ color: '#f59e0b' }}>
                {stats.pending}
              </span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Auto-approved</span>
              <span className="stat-value" style={{ color: '#22c55e' }}>
                {stats.approved_auto}
              </span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Manual</span>
              <span className="stat-value" style={{ color: '#3b82f6' }}>
                {stats.approved_manual}
              </span>
            </div>
            <div className="stat-item">
              <span className="stat-label">Total</span>
              <span className="stat-value">{stats.total}</span>
            </div>
          </div>
        </div>
      )}

      {/* Toolbar */}
      <div className="toolbar panel" style={{ marginBottom: 16 }}>
        <div className="toolbar-left">
          <select
            value={codeTypeFilter}
            onChange={(e) => {
              setCodeTypeFilter(e.target.value);
              setPage(1);
            }}
            className="filter-select"
          >
            <option value="">All types</option>
            <option value="ean">EAN</option>
            <option value="serial_number">Serial Number</option>
            <option value="model_number">Model Number</option>
            <option value="product_code">Product Code</option>
          </select>
        </div>
        <div className="toolbar-right">
          {selectedCodes.size > 0 && (
            <>
              <span style={{ marginRight: 8 }}>
                {selectedCodes.size} selected
              </span>
              <button
                onClick={bulkApprove}
                className="btn btn-success"
                disabled={processingIds.size > 0}
              >
                ✓ Approve All
              </button>
              <button
                onClick={bulkReject}
                className="btn btn-danger"
                disabled={processingIds.size > 0}
                style={{ marginLeft: 8 }}
              >
                ✕ Reject All
              </button>
            </>
          )}
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="error-message panel" style={{ marginBottom: 16 }}>
          {error}
          <button onClick={() => setError(null)} style={{ marginLeft: 8 }}>
            ✕
          </button>
        </div>
      )}

      {/* Empty state */}
      {codes.length === 0 && !loading && (
        <div className="panel empty-state">
          <p>🎉 No codes pending review!</p>
          <p style={{ opacity: 0.7 }}>
            All extracted codes have been processed.
          </p>
        </div>
      )}

      {/* Code list */}
      {codes.length > 0 && (
        <div className="panel">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 40 }}>
                  <input
                    type="checkbox"
                    checked={selectedCodes.size === codes.length}
                    onChange={selectAll}
                    title="Select all"
                  />
                </th>
                <th>Image</th>
                <th>Lot</th>
                <th>Type</th>
                <th>Value</th>
                <th>Confidence</th>
                <th>Context</th>
                <th style={{ width: 140 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {codes.map((code) => (
                <tr
                  key={code.id}
                  className={selectedCodes.has(code.id) ? 'selected' : ''}
                >
                  <td>
                    <input
                      type="checkbox"
                      checked={selectedCodes.has(code.id)}
                      onChange={() => toggleCodeSelection(code.id)}
                    />
                  </td>
                  <td>
                    {code.image_url && (
                      <img
                        src={code.image_url}
                        alt="Lot image"
                        className="thumbnail"
                        onClick={() =>
                          window.open(code.image_url || '', '_blank')
                        }
                        style={{ cursor: 'pointer' }}
                      />
                    )}
                  </td>
                  <td>
                    <a
                      href={`/lots/${code.lot_code}`}
                      className="lot-link"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {code.lot_code}
                    </a>
                  </td>
                  <td>
                    <span className="code-type-badge">
                      {getCodeTypeLabel(code.code_type)}
                    </span>
                  </td>
                  <td className="code-value">{code.value}</td>
                  <td>
                    <span
                      className="confidence-badge"
                      style={{
                        backgroundColor: getConfidenceColor(code.confidence),
                      }}
                    >
                      {code.confidence}
                    </span>
                  </td>
                  <td className="context-cell">
                    {code.context && (
                      <span title={code.context}>
                        {code.context.slice(0, 50)}
                        {code.context.length > 50 ? '...' : ''}
                      </span>
                    )}
                  </td>
                  <td>
                    <button
                      onClick={() => approveCode(code.id)}
                      className="btn btn-sm btn-success"
                      disabled={processingIds.has(code.id)}
                      title="Approve"
                    >
                      ✓
                    </button>
                    <button
                      onClick={() => rejectCode(code.id)}
                      className="btn btn-sm btn-danger"
                      disabled={processingIds.has(code.id)}
                      style={{ marginLeft: 4 }}
                      title="Reject"
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="pagination" style={{ marginTop: 16 }}>
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn"
          >
            ← Previous
          </button>
          <span style={{ margin: '0 16px' }}>
            Page {page} of {totalPages} ({total} codes)
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="btn"
          >
            Next →
          </button>
        </div>
      )}

      <style jsx>{`
        .stats-grid {
          display: flex;
          gap: 24px;
        }
        .stat-item {
          display: flex;
          flex-direction: column;
          align-items: center;
        }
        .stat-label {
          font-size: 12px;
          opacity: 0.7;
        }
        .stat-value {
          font-size: 24px;
          font-weight: bold;
        }
        .toolbar {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .filter-select {
          padding: 6px 12px;
          border: 1px solid #333;
          border-radius: 4px;
          background: #1a1a1a;
          color: inherit;
        }
        .error-message {
          background: #7f1d1d;
          color: #fecaca;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .empty-state {
          text-align: center;
          padding: 48px;
        }
        .thumbnail {
          width: 60px;
          height: 60px;
          object-fit: cover;
          border-radius: 4px;
        }
        .lot-link {
          color: #60a5fa;
        }
        .lot-link:hover {
          text-decoration: underline;
        }
        .code-type-badge {
          background: #374151;
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 12px;
        }
        .code-value {
          font-family: monospace;
          font-size: 14px;
        }
        .confidence-badge {
          color: white;
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 11px;
          text-transform: uppercase;
        }
        .context-cell {
          max-width: 200px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          font-size: 12px;
          opacity: 0.7;
        }
        .btn-sm {
          padding: 4px 8px;
          font-size: 12px;
        }
        .btn-success {
          background: #16a34a;
        }
        .btn-success:hover {
          background: #15803d;
        }
        .btn-danger {
          background: #dc2626;
        }
        .btn-danger:hover {
          background: #b91c1c;
        }
        tr.selected {
          background: rgba(59, 130, 246, 0.1);
        }
        .pagination {
          display: flex;
          justify-content: center;
          align-items: center;
        }
      `}</style>
    </div>
  );
}
