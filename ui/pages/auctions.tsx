import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import type { Auction, AuctionUpdateRequest } from '../lib/api';
import { fetchAuctions as fetchAuctionsApi, updateAuction, deleteAuction } from '../lib/api';

interface SyncResult {
  auction_code: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  error?: string;
  lots_updated?: number;
  pages_scanned?: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function AuctionsPage() {
  const [auctions, setAuctions] = useState<Auction[]>([]);
  const [includeInactive, setIncludeInactive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAuctions, setSelectedAuctions] = useState<Set<string>>(new Set());
  const [syncResults, setSyncResults] = useState<Map<string, SyncResult>>(new Map());
  const [syncing, setSyncing] = useState(false);
  
  // Edit state
  const [editingAuction, setEditingAuction] = useState<Auction | null>(null);
  const [editForm, setEditForm] = useState<AuctionUpdateRequest>({});
  const [saving, setSaving] = useState(false);
  
  // Delete state
  const [deletingAuction, setDeletingAuction] = useState<Auction | null>(null);
  const [deleteWithLots, setDeleteWithLots] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const loadAuctions = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAuctionsApi(includeInactive);
      setAuctions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAuctions();
  }, [includeInactive]);

  const toggleSelection = (code: string) => {
    const newSelection = new Set(selectedAuctions);
    if (newSelection.has(code)) {
      newSelection.delete(code);
    } else {
      newSelection.add(code);
    }
    setSelectedAuctions(newSelection);
  };

  const selectAll = () => {
    if (selectedAuctions.size === auctions.length) {
      setSelectedAuctions(new Set());
    } else {
      setSelectedAuctions(new Set(auctions.map((a) => a.auction_code)));
    }
  };

  const syncSelected = async () => {
    if (selectedAuctions.size === 0) return;
    
    setSyncing(true);
    const results = new Map<string, SyncResult>();
    
    // Initialize all as pending
    selectedAuctions.forEach((code) => {
      results.set(code, { auction_code: code, status: 'pending' });
    });
    setSyncResults(new Map(results));

    // Sync each auction sequentially
    for (const code of selectedAuctions) {
      const auction = auctions.find((a) => a.auction_code === code);
      if (!auction || !auction.url) {
        results.set(code, { 
          auction_code: code, 
          status: 'failed', 
          error: 'Geen URL beschikbaar' 
        });
        setSyncResults(new Map(results));
        continue;
      }

      results.set(code, { auction_code: code, status: 'running' });
      setSyncResults(new Map(results));

      try {
        const res = await fetch(`${API_BASE}/sync`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            auction_code: code,
            auction_url: auction.url,
            dry_run: false,
          }),
        });

        const data = await res.json();
        
        if (data.status === 'success') {
          results.set(code, {
            auction_code: code,
            status: 'success',
            lots_updated: data.result?.lots_updated || 0,
            pages_scanned: data.result?.pages_scanned || 0,
          });
        } else {
          results.set(code, {
            auction_code: code,
            status: 'failed',
            error: data.error || 'Sync failed',
          });
        }
      } catch (err) {
        results.set(code, {
          auction_code: code,
          status: 'failed',
          error: err instanceof Error ? err.message : 'Unknown error',
        });
      }
      setSyncResults(new Map(results));
    }

    setSyncing(false);
    loadAuctions();
  };

  const startEditing = (auction: Auction) => {
    setEditingAuction(auction);
    setEditForm({
      title: auction.title || undefined,
      url: auction.url || undefined,
      starts_at: auction.starts_at || undefined,
      ends_at_planned: auction.ends_at_planned || undefined,
    });
  };

  const cancelEditing = () => {
    setEditingAuction(null);
    setEditForm({});
  };

  const handleSaveEdit = async () => {
    if (!editingAuction) return;
    setSaving(true);
    setError(null);
    try {
      await updateAuction(editingAuction.auction_code, editForm);
      await loadAuctions();
      setEditingAuction(null);
      setEditForm({});
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kon veiling niet bijwerken');
    } finally {
      setSaving(false);
    }
  };

  const startDeleting = (auction: Auction) => {
    setDeletingAuction(auction);
    setDeleteWithLots(false);
  };

  const cancelDeleting = () => {
    setDeletingAuction(null);
    setDeleteWithLots(false);
  };

  const handleDelete = async () => {
    if (!deletingAuction) return;
    setDeleting(true);
    setError(null);
    try {
      const result = await deleteAuction(deletingAuction.auction_code, deleteWithLots);
      await loadAuctions();
      setDeletingAuction(null);
      setDeleteWithLots(false);
      if (result.lots_deleted > 0) {
        alert(`Veiling verwijderd. ${result.lots_deleted} lots ook verwijderd.`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kon veiling niet verwijderen');
    } finally {
      setDeleting(false);
    }
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '—';
    try {
      return new Date(dateStr).toLocaleString('nl-NL', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  const getStatusBadge = (result: SyncResult | undefined) => {
    if (!result) return null;
    switch (result.status) {
      case 'pending':
        return <span className="status-badge pending">Wachtend</span>;
      case 'running':
        return <span className="status-badge running">Bezig...</span>;
      case 'success':
        return <span className="status-badge success">✓ {result.lots_updated} lots</span>;
      case 'failed':
        return <span className="status-badge failed" title={result.error}>✗ Fout</span>;
    }
  };

  return (
    <Layout title="Veilingen">
      <div className="page-container">
          <h1 className="text-2xl font-bold">Veilingen</h1>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={includeInactive}
                onChange={(e) => setIncludeInactive(e.target.checked)}
                className="rounded"
              />
              Inclusief inactieve
            </label>
            <button
              onClick={fetchAuctions}
              disabled={loading}
              className="px-3 py-1.5 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 disabled:opacity-50"
            >
              Vernieuwen
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {/* Sync Controls */}
        {selectedAuctions.size > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4 flex items-center justify-between">
            <span className="text-blue-800">
              {selectedAuctions.size} veiling(en) geselecteerd
            </span>
            <button
              onClick={syncSelected}
              disabled={syncing}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {syncing ? 'Synchroniseren...' : 'Sync Geselecteerde'}
            </button>
          </div>
        )}

        {loading ? (
          <p className="text-gray-500">Laden...</p>
        ) : auctions.length === 0 ? (
          <p className="text-gray-500">Geen veilingen gevonden.</p>
        ) : (
          <div className="bg-white rounded-lg shadow border overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left">
                    <input
                      type="checkbox"
                      checked={selectedAuctions.size === auctions.length && auctions.length > 0}
                      onChange={selectAll}
                      className="rounded"
                    />
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Code</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Titel</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Actieve Lots</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Totaal Lots</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Einde</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Sync Status</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {auctions.map((auction) => (
                  <tr
                    key={auction.auction_code}
                    className={`hover:bg-gray-50 ${selectedAuctions.has(auction.auction_code) ? 'bg-blue-50' : ''}`}
                  >
                    <td className="px-4 py-3">
                      <input
                        type="checkbox"
                        checked={selectedAuctions.has(auction.auction_code)}
                        onChange={() => toggleSelection(auction.auction_code)}
                        className="rounded"
                      />
                    </td>
                    <td className="px-4 py-3 text-sm font-mono">{auction.auction_code}</td>
                    <td className="px-4 py-3 text-sm truncate max-w-xs" title={auction.title || undefined}>
                      {auction.url ? (
                        <a
                          href={auction.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline"
                        >
                          {auction.title || auction.auction_code}
                        </a>
                      ) : (
                        auction.title || '—'
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-center">
                      <span className={`font-medium ${auction.active_lots > 0 ? 'text-green-600' : 'text-gray-400'}`}>
                        {auction.active_lots}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-center text-gray-600">
                      {auction.lot_count}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {formatDate(auction.ends_at_planned)}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {getStatusBadge(syncResults.get(auction.auction_code))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Layout>
  );
}
