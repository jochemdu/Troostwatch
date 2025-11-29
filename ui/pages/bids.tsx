import { useState, useEffect, useCallback } from 'react';
import Layout from '../components/Layout';
import { fetchBuyers, fetchLots, fetchBids, createBid, type Bid } from '../lib/api';
import type { BuyerResponse, LotView } from '../lib/api';
import ExampleLotEventConsumer from '../components/ExampleLotEventConsumer';

export default function BidsPage() {
  const [bids, setBids] = useState<Bid[]>([]);
  const [buyers, setBuyers] = useState<BuyerResponse[]>([]);
  const [lots, setLots] = useState<LotView[]>([]);
  const [filterBuyer, setFilterBuyer] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [formBuyer, setFormBuyer] = useState('');
  const [formLot, setFormLot] = useState('');
  const [formAmount, setFormAmount] = useState('');
  const [formNote, setFormNote] = useState('');
  const [formSaving, setFormSaving] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [bidData, buyerData, lotData] = await Promise.all([
        fetchBids(filterBuyer || undefined),
        fetchBuyers(),
        fetchLots({ limit: 500 }),
      ]);
      setBids(bidData);
      setBuyers(buyerData);
      setLots(lotData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  }, [filterBuyer]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formBuyer || !formLot || !formAmount) {
      setError('Vul alle verplichte velden in');
      return;
    }
    setFormSaving(true);
    setError('');
    try {
      const lot = lots.find(l => l.lot_code === formLot);
      if (!lot) {
        setError('Lot niet gevonden');
        return;
      }
      await createBid({
        buyer_label: formBuyer,
        auction_code: lot.auction_code,
        lot_code: formLot,
        amount_eur: parseFloat(formAmount),
        note: formNote || undefined,
      });
      setShowForm(false);
      setFormBuyer('');
      setFormLot('');
      setFormAmount('');
      setFormNote('');
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Create failed');
    } finally {
      setFormSaving(false);
    }
  };

  const formatCurrency = (value: number) => {
    return `€${value.toLocaleString('nl-NL', { minimumFractionDigits: 2 })}`;
  };

  const formatDate = (value: string) => {
    return new Date(value).toLocaleString('nl-NL');
  };

  // Calculate totals per buyer
  const buyerTotals = bids.reduce((acc, bid) => {
    acc[bid.buyer_label] = (acc[bid.buyer_label] || 0) + bid.amount_eur;
    return acc;
  }, {} as Record<string, number>);

  return (
    <Layout title="Biedingen" subtitle="Overzicht van geplaatste biedingen">
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
            <span className="badge">{bids.length} biedingen</span>
          </div>
          <button className="button primary" onClick={() => setShowForm(!showForm)}>
            {showForm ? 'Annuleren' : '+ Bod registreren'}
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
            <h3 style={{ marginTop: 0 }}>Nieuw bod registreren</h3>
            <p className="muted" style={{ marginTop: -8, marginBottom: 16 }}>
              Dit registreert het bod lokaal. Het wordt <strong>niet</strong> automatisch op Troostwijk geplaatst.
            </p>
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
                <label>Bedrag (€) *</label>
                <input 
                  type="number" 
                  value={formAmount} 
                  onChange={(e) => setFormAmount(e.target.value)}
                  min="0.01"
                  step="0.01"
                  required
                  placeholder="0.00"
                />
              </div>
              <div>
                <label>Notitie</label>
                <input 
                  type="text" 
                  value={formNote} 
                  onChange={(e) => setFormNote(e.target.value)}
                  placeholder="Optioneel"
                />
              </div>
            </div>
            <button type="submit" className="button primary" disabled={formSaving}>
              {formSaving ? 'Opslaan...' : 'Bod registreren'}
            </button>
          </form>
        )}

        {/* Summary cards */}
        {Object.keys(buyerTotals).length > 0 && (
          <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
            {Object.entries(buyerTotals).map(([label, total]) => (
              <div 
                key={label} 
                style={{ 
                  padding: '12px 16px', 
                  background: '#f0f4f8', 
                  borderRadius: 4,
                  minWidth: 150,
                }}
              >
                <div className="muted" style={{ fontSize: 12 }}>{label}</div>
                <div style={{ fontSize: 18, fontWeight: 600 }}>{formatCurrency(total)}</div>
              </div>
            ))}
          </div>
        )}

        {loading ? (
          <p className="muted">Laden...</p>
        ) : bids.length === 0 ? (
          <p className="muted">Geen biedingen gevonden.</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Datum</th>
                <th>Koper</th>
                <th>Lot</th>
                <th>Titel</th>
                <th>Bedrag</th>
                <th>Notitie</th>
              </tr>
            </thead>
            <tbody>
              {bids.map((bid) => (
                <tr key={bid.id}>
                  <td className="muted">{formatDate(bid.placed_at)}</td>
                  <td><strong>{bid.buyer_label}</strong></td>
                  <td>{bid.lot_code}</td>
                  <td className="muted">{bid.lot_title?.slice(0, 30) ?? '—'}</td>
                  <td style={{ fontWeight: 600 }}>{formatCurrency(bid.amount_eur)}</td>
                  <td className="muted">{bid.note ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <ExampleLotEventConsumer />
    </Layout>
  );
}
