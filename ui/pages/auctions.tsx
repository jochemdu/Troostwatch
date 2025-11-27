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
        <div className="page-header">
          <h1>Veilingen</h1>
          <div className="header-actions">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={includeInactive}
                onChange={(e) => setIncludeInactive(e.target.checked)}
              />
              Inclusief inactieve
            </label>
            <button onClick={loadAuctions} disabled={loading} className="btn btn-secondary">
              🔄 Vernieuwen
            </button>
          </div>
        </div>

        {error && <div className="error-banner">{error}</div>}

        {/* Sync Controls */}
        {selectedAuctions.size > 0 && (
          <div className="selection-bar">
            <span>{selectedAuctions.size} veiling(en) geselecteerd</span>
            <button onClick={syncSelected} disabled={syncing} className="btn btn-primary">
              {syncing ? 'Synchroniseren...' : 'Sync Geselecteerde'}
            </button>
          </div>
        )}

        {/* Edit Modal */}
        {editingAuction && (
          <div className="modal-overlay" onClick={cancelEditing}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h2>Veiling bewerken</h2>
                <button className="btn-close" onClick={cancelEditing}>×</button>
              </div>
              <div className="modal-body">
                <div className="form-row">
                  <label>Code</label>
                  <input type="text" value={editingAuction.auction_code} disabled />
                </div>
                <div className="form-row">
                  <label>Titel</label>
                  <input 
                    type="text" 
                    value={editForm.title || ''} 
                    onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                  />
                </div>
                <div className="form-row">
                  <label>URL</label>
                  <input 
                    type="url" 
                    value={editForm.url || ''} 
                    onChange={(e) => setEditForm({ ...editForm, url: e.target.value })}
                  />
                </div>
                <div className="form-row">
                  <label>Start datum</label>
                  <input 
                    type="datetime-local" 
                    value={editForm.starts_at?.slice(0, 16) || ''} 
                    onChange={(e) => setEditForm({ ...editForm, starts_at: e.target.value })}
                  />
                </div>
                <div className="form-row">
                  <label>Eind datum</label>
                  <input 
                    type="datetime-local" 
                    value={editForm.ends_at_planned?.slice(0, 16) || ''} 
                    onChange={(e) => setEditForm({ ...editForm, ends_at_planned: e.target.value })}
                  />
                </div>
              </div>
              <div className="modal-footer">
                <button className="btn btn-secondary" onClick={cancelEditing}>Annuleren</button>
                <button className="btn btn-primary" onClick={handleSaveEdit} disabled={saving}>
                  {saving ? 'Opslaan...' : 'Opslaan'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Delete Confirmation Modal */}
        {deletingAuction && (
          <div className="modal-overlay" onClick={cancelDeleting}>
            <div className="modal modal-danger" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h2>Veiling verwijderen</h2>
                <button className="btn-close" onClick={cancelDeleting}>×</button>
              </div>
              <div className="modal-body">
                <p>Weet je zeker dat je veiling <strong>{deletingAuction.auction_code}</strong> wilt verwijderen?</p>
                {deletingAuction.title && <p className="muted">{deletingAuction.title}</p>}
                
                {deletingAuction.lot_count > 0 && (
                  <div className="delete-lots-option">
                    <label className="checkbox-label danger">
                      <input
                        type="checkbox"
                        checked={deleteWithLots}
                        onChange={(e) => setDeleteWithLots(e.target.checked)}
                      />
                      Ook alle {deletingAuction.lot_count} lots verwijderen
                    </label>
                    {deleteWithLots && (
                      <p className="warning-text">
                        ⚠️ Let op: Dit verwijdert ook alle biedgeschiedenis, referentieprijzen en specificaties van deze lots!
                      </p>
                    )}
                  </div>
                )}
              </div>
              <div className="modal-footer">
                <button className="btn btn-secondary" onClick={cancelDeleting}>Annuleren</button>
                <button className="btn btn-danger" onClick={handleDelete} disabled={deleting}>
                  {deleting ? 'Verwijderen...' : 'Verwijderen'}
                </button>
              </div>
            </div>
          </div>
        )}

        {loading ? (
          <p className="loading">Laden...</p>
        ) : auctions.length === 0 ? (
          <p className="empty-state">Geen veilingen gevonden.</p>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th className="col-checkbox">
                    <input
                      type="checkbox"
                      checked={selectedAuctions.size === auctions.length && auctions.length > 0}
                      onChange={selectAll}
                    />
                  </th>
                  <th>Code</th>
                  <th>Titel</th>
                  <th className="col-center">Actief</th>
                  <th className="col-center">Totaal</th>
                  <th>Einde</th>
                  <th>Sync</th>
                  <th className="col-actions">Acties</th>
                </tr>
              </thead>
              <tbody>
                {auctions.map((auction) => (
                  <tr
                    key={auction.auction_code}
                    className={selectedAuctions.has(auction.auction_code) ? 'selected' : ''}
                  >
                    <td>
                      <input
                        type="checkbox"
                        checked={selectedAuctions.has(auction.auction_code)}
                        onChange={() => toggleSelection(auction.auction_code)}
                      />
                    </td>
                    <td className="mono">{auction.auction_code}</td>
                    <td className="truncate" title={auction.title || undefined}>
                      {auction.url ? (
                        <a href={auction.url} target="_blank" rel="noopener noreferrer">
                          {auction.title || auction.auction_code}
                        </a>
                      ) : (
                        auction.title || '—'
                      )}
                    </td>
                    <td className="col-center">
                      <span className={auction.active_lots > 0 ? 'text-success' : 'text-muted'}>
                        {auction.active_lots}
                      </span>
                    </td>
                    <td className="col-center text-muted">{auction.lot_count}</td>
                    <td className="text-muted">{formatDate(auction.ends_at_planned)}</td>
                    <td>{getStatusBadge(syncResults.get(auction.auction_code))}</td>
                    <td className="col-actions">
                      <button 
                        className="btn-icon" 
                        onClick={() => startEditing(auction)}
                        title="Bewerken"
                      >
                        ✏️
                      </button>
                      <button 
                        className="btn-icon btn-delete" 
                        onClick={() => startDeleting(auction)}
                        title="Verwijderen"
                      >
                        🗑️
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <style jsx>{`
        .page-container { padding: 24px; }
        .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
        .page-header h1 { margin: 0; font-size: 1.75rem; color: #fff; }
        .header-actions { display: flex; align-items: center; gap: 16px; }
        .checkbox-label { display: flex; align-items: center; gap: 8px; cursor: pointer; color: #a0a0c0; font-size: 0.9rem; }
        .checkbox-label.danger { color: #ef4444; }
        .error-banner { background: #4a1a1a; border: 1px solid #dc2626; color: #fca5a5; padding: 12px 16px; border-radius: 6px; margin-bottom: 16px; }
        .selection-bar { background: #1e3a5f; border: 1px solid #3b82f6; border-radius: 8px; padding: 12px 16px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; color: #93c5fd; }
        .loading, .empty-state { color: #888; padding: 40px; text-align: center; }
        
        .table-container { background: #1a1a2e; border-radius: 8px; border: 1px solid #333; overflow: hidden; }
        table { width: 100%; border-collapse: collapse; }
        th { padding: 12px 16px; text-align: left; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; color: #888; background: #151525; border-bottom: 1px solid #333; }
        td { padding: 12px 16px; border-bottom: 1px solid #252540; color: #e0e0e0; font-size: 0.9rem; }
        tr:hover { background: #1e1e3a; }
        tr.selected { background: #1e2a40; }
        tr:last-child td { border-bottom: none; }
        
        .col-checkbox { width: 40px; }
        .col-center { text-align: center; }
        .col-actions { width: 100px; text-align: right; }
        .mono { font-family: monospace; font-size: 0.85rem; }
        .truncate { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .text-success { color: #4ade80; font-weight: 600; }
        .text-muted { color: #888; }
        
        a { color: #60a5fa; text-decoration: none; }
        a:hover { text-decoration: underline; }
        
        .btn { padding: 8px 16px; border-radius: 6px; font-size: 0.9rem; cursor: pointer; border: none; transition: all 0.15s; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .btn-primary { background: #6366f1; color: #fff; }
        .btn-primary:hover:not(:disabled) { background: #4f46e5; }
        .btn-secondary { background: #333; color: #e0e0e0; border: 1px solid #444; }
        .btn-secondary:hover:not(:disabled) { background: #444; }
        .btn-danger { background: #dc2626; color: #fff; }
        .btn-danger:hover:not(:disabled) { background: #b91c1c; }
        
        .btn-icon { background: none; border: 1px solid #444; border-radius: 6px; padding: 6px 10px; cursor: pointer; font-size: 0.9rem; transition: all 0.15s; }
        .btn-icon:hover { background: #333; border-color: #555; }
        .btn-icon.btn-delete:hover { background: #4a1a1a; border-color: #a33; }
        
        .status-badge { padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; }
        .status-badge.pending { background: #333; color: #888; }
        .status-badge.running { background: #1e3a5f; color: #60a5fa; animation: pulse 1.5s infinite; }
        .status-badge.success { background: #14532d; color: #4ade80; }
        .status-badge.failed { background: #4a1a1a; color: #f87171; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
        
        .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.7); display: flex; align-items: center; justify-content: center; z-index: 1000; }
        .modal { background: #1a1a2e; border: 1px solid #333; border-radius: 12px; width: 90%; max-width: 500px; max-height: 90vh; overflow: auto; }
        .modal.modal-danger { border-color: #dc2626; }
        .modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #333; }
        .modal-header h2 { margin: 0; font-size: 1.25rem; color: #fff; }
        .btn-close { background: none; border: none; font-size: 1.5rem; color: #888; cursor: pointer; padding: 0; line-height: 1; }
        .btn-close:hover { color: #fff; }
        .modal-body { padding: 20px; }
        .modal-body p { margin: 0 0 12px 0; color: #e0e0e0; }
        .modal-body .muted { color: #888; font-size: 0.9rem; }
        .modal-footer { display: flex; justify-content: flex-end; gap: 12px; padding: 16px 20px; border-top: 1px solid #333; }
        
        .form-row { margin-bottom: 16px; }
        .form-row label { display: block; margin-bottom: 6px; color: #a0a0c0; font-size: 0.85rem; }
        .form-row input { width: 100%; padding: 10px 14px; border: 1px solid #444; border-radius: 6px; background: #0f0f1a; color: #e0e0e0; font-size: 0.9rem; }
        .form-row input:disabled { opacity: 0.5; cursor: not-allowed; }
        .form-row input:focus { outline: none; border-color: #6366f1; }
        
        .delete-lots-option { margin-top: 16px; padding: 12px; background: #252540; border-radius: 6px; }
        .warning-text { color: #fbbf24; font-size: 0.85rem; margin-top: 8px; }
      `}</style>
    </Layout>
  );
}
