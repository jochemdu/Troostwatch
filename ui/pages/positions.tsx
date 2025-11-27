import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import { fetchBuyers, fetchLots } from '../lib/api';
import type { BuyerResponse, LotView } from '../lib/api';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000';

interface Position {
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

async function fetchPositions(buyer?: string): Promise<Position[]> {
  const url = new URL(`${API_BASE}/positions`);
  if (buyer) url.searchParams.append('buyer', buyer);
  const response = await fetch(url.toString());
  if (!response.ok) throw new Error('Failed to fetch positions');
  return response.json();
}

async function createPosition(data: {
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

async function deletePosition(buyerLabel: string, lotCode: string, auctionCode?: string): Promise<void> {
  const url = new URL(`${API_BASE}/positions/${buyerLabel}/${lotCode}`);
  if (auctionCode) url.searchParams.append('auction_code', auctionCode);
  const response = await fetch(url.toString(), { method: 'DELETE' });
  if (!response.ok) throw new Error('Failed to delete position');
}

export default function PositionsPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [buyers, setBuyers] = useState<BuyerResponse[]>([]);
  const [lots, setLots] = useState<LotView[]>([]);
  const [filterBuyer, setFilterBuyer] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [formBuyer, setFormBuyer] = useState('');
  const [formLot, setFormLot] = useState('');
  const [formBudget, setFormBudget] = useState('');
  const [formSaving, setFormSaving] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [posData, buyerData, lotData] = await Promise.all([
        fetchPositions(filterBuyer || undefined),
        fetchBuyers(),
        fetchLots({ limit: 500 }),
      ]);
      setPositions(posData);
      setBuyers(buyerData);
      setLots(lotData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [filterBuyer]);

  const handleDelete = async (pos: Position) => {
    if (!confirm(`Positie verwijderen voor ${pos.buyer_label} op lot ${pos.lot_code}?`)) return;
    try {
      await deletePosition(pos.buyer_label, pos.lot_code, pos.auction_code ?? undefined);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formBuyer || !formLot) {
      setError('Selecteer een koper en lot');
      return;
    }
    setFormSaving(true);
    setError('');
    try {
      const lot = lots.find(l => l.lot_code === formLot);
      await createPosition({
        buyer_label: formBuyer,
        lot_code: formLot,
        auction_code: lot?.auction_code,
        max_budget_total_eur: formBudget ? parseFloat(formBudget) : undefined,
      });
      setShowForm(false);
      setFormBuyer('');
      setFormLot('');
      setFormBudget('');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create failed');
    } finally {
      setFormSaving(false);
    }
  };

  const formatCurrency = (value: number | null) => {
    if (value === null) return '—';
    return `€${value.toLocaleString('nl-NL')}`;
  };

  const formatDate = (value: string | null) => {
    if (!value) return '—';
    return new Date(value).toLocaleString('nl-NL');
  };

  return (
    <Layout title="Posities" subtitle="Beheer getraceerde posities per koper">
      <div className="panel">
        <div className="status-row" style={{ justifyContent: 'space-between', marginBottom: 16 }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
            <label>Filter op koper:</label>
            <select 
              value={filterBuyer} 
              onChange={(e) => setFilterBuyer(e.target.value)}
              style={{ padding: '6px 12px' }}
            >
              <option value="">Alle kopers</option>
              {buyers.map(b => (
                <option key={b.label} value={b.label}>{b.label}</option>
              ))}
            </select>
          </div>
          <button className="button primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? 'Annuleren' : '+ Positie toevoegen'}
          </button>
        </div>

        {error && (
          <div style={{ padding: 12, background: '#fee', borderRadius: 4, color: '#c00', marginBottom: 16 }}>
            {error}
          </div>
        )}

        {showForm && (
          <form onSubmit={handleCreate} style={{ 
            padding: 16, 
            background: '#f8f9fa', 
            borderRadius: 4, 
            marginBottom: 16 
          }}>
            <h3 style={{ marginTop: 0 }}>Nieuwe positie</h3>
            <div className="form-row">
              <div>
                <label>Koper *</label>
                <select 
                  value={formBuyer} 
                  onChange={(e) => setFormBuyer(e.target.value)}
                  required
                >
                  <option value="">Selecteer koper...</option>
                  {buyers.map(b => (
                    <option key={b.label} value={b.label}>{b.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label>Lot *</label>
                <select 
                  value={formLot} 
                  onChange={(e) => setFormLot(e.target.value)}
                  required
                >
                  <option value="">Selecteer lot...</option>
                  {lots.map(l => (
                    <option key={l.lot_code} value={l.lot_code}>
                      {l.lot_code} - {l.title?.slice(0, 40) ?? 'Geen titel'}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label>Max budget (€)</label>
                <input 
                  type="number" 
                  value={formBudget} 
                  onChange={(e) => setFormBudget(e.target.value)}
                  min="0"
                  step="0.01"
                  placeholder="Optioneel"
                />
              </div>
            </div>
            <button type="submit" className="button primary" disabled={formSaving}>
              {formSaving ? 'Opslaan...' : 'Positie opslaan'}
            </button>
          </form>
        )}

        {loading ? (
          <p className="muted">Laden...</p>
        ) : positions.length === 0 ? (
          <p className="muted">Geen posities gevonden.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Koper</th>
                <th>Lot</th>
                <th>Titel</th>
                <th>Budget</th>
                <th>Huidig bod</th>
                <th>Sluit</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {positions.map((pos) => {
                const overBudget = pos.max_budget_total_eur && pos.current_bid_eur 
                  && pos.current_bid_eur > pos.max_budget_total_eur;
                return (
                  <tr key={`${pos.buyer_label}-${pos.lot_code}`}>
                    <td><strong>{pos.buyer_label}</strong></td>
                    <td>{pos.lot_code}</td>
                    <td className="muted">{pos.lot_title?.slice(0, 30) ?? '—'}</td>
                    <td>{formatCurrency(pos.max_budget_total_eur)}</td>
                    <td style={{ color: overBudget ? '#c00' : undefined }}>
                      {formatCurrency(pos.current_bid_eur)}
                      {overBudget && ' ⚠️'}
                    </td>
                    <td className="muted">{formatDate(pos.closing_time)}</td>
                    <td>
                      <span className={`badge ${pos.track_active ? '' : 'error'}`}>
                        {pos.track_active ? 'Actief' : 'Inactief'}
                      </span>
                    </td>
                    <td>
                      <button 
                        className="button danger" 
                        style={{ padding: '4px 8px', fontSize: 12 }}
                        onClick={() => handleDelete(pos)}
                      >
                        Verwijderen
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </Layout>
  );
}
