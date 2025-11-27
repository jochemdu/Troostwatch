import { useState, useEffect } from 'react';
import type { LotDetailResponse, ReferencePrice, ReferencePriceCreateRequest } from '../lib/api';
import { fetchLotDetail, updateLot, addReferencePrice, deleteReferencePrice } from '../lib/api';

interface Props {
  lotCode: string;
  auctionCode: string;
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
}

const CONDITION_OPTIONS = [
  { value: 'new', label: 'Nieuw' },
  { value: 'used', label: 'Tweedehands' },
  { value: 'refurbished', label: 'Refurbished' },
] as const;

interface NewPriceForm {
  condition: 'new' | 'used' | 'refurbished';
  price: string;
  source: string;
  url: string;
  notes: string;
}

const emptyPriceForm: NewPriceForm = {
  condition: 'used',
  price: '',
  source: '',
  url: '',
  notes: '',
};

export default function LotEditModal({ lotCode, auctionCode, isOpen, onClose, onSaved }: Props) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lot, setLot] = useState<LotDetailResponse | null>(null);
  const [notes, setNotes] = useState<string>('');
  const [referencePrices, setReferencePrices] = useState<ReferencePrice[]>([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newPrice, setNewPrice] = useState<NewPriceForm>(emptyPriceForm);

  useEffect(() => {
    if (!isOpen) return;
    const loadLot = async () => {
      setLoading(true);
      setError(null);
      try {
        const detail = await fetchLotDetail(lotCode, auctionCode);
        setLot(detail);
        setNotes(detail.notes ?? '');
        setReferencePrices(detail.reference_prices ?? []);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Kon lot niet laden');
      } finally {
        setLoading(false);
      }
    };
    loadLot();
  }, [isOpen, lotCode, auctionCode]);

  const handleSaveNotes = async () => {
    setSaving(true);
    setError(null);
    try {
      await updateLot(lotCode, { notes: notes || null }, auctionCode);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kon notities niet opslaan');
    } finally {
      setSaving(false);
    }
  };

  const handleAddPrice = async () => {
    if (!newPrice.price) {
      setError('Vul een prijs in');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const data: ReferencePriceCreateRequest = {
        condition: newPrice.condition,
        price_eur: parseFloat(newPrice.price),
        source: newPrice.source || null,
        url: newPrice.url || null,
        notes: newPrice.notes || null,
      };
      const created = await addReferencePrice(lotCode, data, auctionCode);
      setReferencePrices((prev) => [created, ...prev]);
      setNewPrice(emptyPriceForm);
      setShowAddForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kon referentieprijs niet toevoegen');
    } finally {
      setSaving(false);
    }
  };

  const handleDeletePrice = async (refId: number) => {
    if (!confirm('Weet je zeker dat je deze referentieprijs wilt verwijderen?')) return;
    setSaving(true);
    setError(null);
    try {
      await deleteReferencePrice(lotCode, refId);
      setReferencePrices((prev) => prev.filter((p) => p.id !== refId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kon referentieprijs niet verwijderen');
    } finally {
      setSaving(false);
    }
  };

  const handleClose = () => {
    setShowAddForm(false);
    setNewPrice(emptyPriceForm);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Lot bewerken</h2>
          <button className="btn-close" onClick={handleClose} aria-label="Sluiten">×</button>
        </div>

        {loading ? (
          <div className="modal-body"><p className="muted">Laden...</p></div>
        ) : error && !lot ? (
          <div className="modal-body"><p className="error">{error}</p></div>
        ) : lot ? (
          <>
            <div className="modal-body">
              {error && <p className="error" style={{ marginBottom: 12 }}>{error}</p>}
              <div className="lot-info-header">
                <h3>{lot.title || lot.lot_code}</h3>
                <p className="muted">{lot.auction_code} · {lot.lot_code}{lot.brand && ` · ${lot.brand}`}</p>
                {lot.current_bid_eur && (
                  <p><strong>Huidig bod:</strong> €{lot.current_bid_eur.toLocaleString('nl-NL')}{lot.bid_count && ` (${lot.bid_count} biedingen)`}</p>
                )}
              </div>

              <fieldset className="form-fieldset">
                <legend>
                  Referentieprijzen
                  <button type="button" className="btn-add-small" onClick={() => setShowAddForm(true)} disabled={showAddForm}>+ Toevoegen</button>
                </legend>

                {showAddForm && (
                  <div className="add-price-form">
                    <div className="form-grid">
                      <div className="form-row">
                        <label>Conditie</label>
                        <select value={newPrice.condition} onChange={(e) => setNewPrice({ ...newPrice, condition: e.target.value as 'new' | 'used' | 'refurbished' })}>
                          {CONDITION_OPTIONS.map((opt) => (<option key={opt.value} value={opt.value}>{opt.label}</option>))}
                        </select>
                      </div>
                      <div className="form-row">
                        <label>Prijs (€) *</label>
                        <input type="number" step="0.01" min="0" value={newPrice.price} onChange={(e) => setNewPrice({ ...newPrice, price: e.target.value })} placeholder="0.00" required />
                      </div>
                      <div className="form-row">
                        <label>Bron</label>
                        <input type="text" value={newPrice.source} onChange={(e) => setNewPrice({ ...newPrice, source: e.target.value })} placeholder="bijv. Marktplaats" />
                      </div>
                      <div className="form-row">
                        <label>URL</label>
                        <input type="url" value={newPrice.url} onChange={(e) => setNewPrice({ ...newPrice, url: e.target.value })} placeholder="https://..." />
                      </div>
                    </div>
                    <div className="form-row">
                      <label>Notitie</label>
                      <input type="text" value={newPrice.notes} onChange={(e) => setNewPrice({ ...newPrice, notes: e.target.value })} placeholder="Optionele notitie" />
                    </div>
                    <div className="form-actions">
                      <button type="button" className="btn btn-secondary" onClick={() => { setShowAddForm(false); setNewPrice(emptyPriceForm); }}>Annuleren</button>
                      <button type="button" className="btn btn-primary" onClick={handleAddPrice} disabled={saving}>{saving ? 'Toevoegen...' : 'Toevoegen'}</button>
                    </div>
                  </div>
                )}

                {referencePrices.length > 0 ? (
                  <table className="table prices-table">
                    <thead><tr><th>Conditie</th><th>Prijs</th><th>Bron</th><th></th></tr></thead>
                    <tbody>
                      {referencePrices.map((price) => (
                        <tr key={price.id}>
                          <td><span className={`badge condition-${price.condition}`}>{CONDITION_OPTIONS.find((o) => o.value === price.condition)?.label ?? price.condition}</span></td>
                          <td className="price-cell">€{price.price_eur.toLocaleString('nl-NL', { minimumFractionDigits: 2 })}</td>
                          <td>{price.url ? (<a href={price.url} target="_blank" rel="noopener noreferrer" title={price.url}>{price.source || 'Link'}</a>) : (price.source || '—')}{price.notes && <span className="price-notes" title={price.notes}>📝</span>}</td>
                          <td><button className="btn-delete" onClick={() => handleDeletePrice(price.id)} disabled={saving} title="Verwijderen">🗑️</button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : !showAddForm && (<p className="muted">Geen referentieprijzen. Klik op &quot;+ Toevoegen&quot; om er een toe te voegen.</p>)}
              </fieldset>

              <fieldset className="form-fieldset">
                <legend>Notities</legend>
                <div className="form-row">
                  <textarea id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} placeholder="Persoonlijke notities over dit lot..." />
                </div>
                <div className="form-actions">
                  <button type="button" className="btn btn-primary" onClick={handleSaveNotes} disabled={saving}>{saving ? 'Opslaan...' : 'Notities opslaan'}</button>
                </div>
              </fieldset>

              {lot.specs && lot.specs.length > 0 && (
                <fieldset className="form-fieldset">
                  <legend>Specificaties</legend>
                  <table className="table specs-table">
                    <tbody>{lot.specs.map((spec) => (<tr key={spec.id}><td className="spec-key">{spec.key}</td><td className="spec-value">{spec.value ?? '—'}</td></tr>))}</tbody>
                  </table>
                </fieldset>
              )}
            </div>
            <div className="modal-footer"><button className="btn btn-secondary" onClick={handleClose}>Sluiten</button></div>
          </>
        ) : null}
      </div>

      <style jsx>{`
        .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
        .modal { background: var(--card-bg, #1a1a2e); border-radius: 8px; min-width: 520px; max-width: 700px; max-height: 90vh; overflow-y: auto; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3); }
        .modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid var(--border-color, #333); }
        .modal-header h2 { margin: 0; font-size: 1.25rem; }
        .btn-close { background: none; border: none; font-size: 1.5rem; color: var(--text-muted, #888); cursor: pointer; padding: 0; line-height: 1; }
        .btn-close:hover { color: var(--text-color, #fff); }
        .modal-body { padding: 20px; }
        .lot-info-header { margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid var(--border-color, #333); }
        .lot-info-header h3 { margin: 0 0 4px 0; }
        .form-fieldset { border: 1px solid var(--border-color, #333); border-radius: 6px; padding: 16px; margin-bottom: 16px; }
        .form-fieldset legend { padding: 0 8px; font-weight: 600; color: var(--text-muted, #888); display: flex; align-items: center; gap: 12px; }
        .btn-add-small { font-size: 0.75rem; padding: 2px 8px; background: var(--primary-color, #6366f1); color: #fff; border: none; border-radius: 4px; cursor: pointer; }
        .btn-add-small:hover:not(:disabled) { background: #5558e3; }
        .btn-add-small:disabled { opacity: 0.5; cursor: not-allowed; }
        .add-price-form { background: var(--input-bg, #0f0f1a); border-radius: 6px; padding: 12px; margin-bottom: 12px; }
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .form-row { margin-bottom: 12px; }
        .form-row:last-child { margin-bottom: 0; }
        .form-row label { display: block; margin-bottom: 4px; font-size: 0.8rem; color: var(--text-muted, #888); }
        .form-row input, .form-row textarea, .form-row select { width: 100%; padding: 8px 12px; border: 1px solid var(--border-color, #333); border-radius: 4px; background: var(--input-bg, #0f0f1a); color: var(--text-color, #fff); font-size: 0.9rem; }
        .form-row input:focus, .form-row textarea:focus, .form-row select:focus { outline: none; border-color: var(--primary-color, #6366f1); }
        .form-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
        .prices-table { width: 100%; font-size: 0.875rem; }
        .prices-table th { text-align: left; padding: 6px 8px; font-weight: 500; color: var(--text-muted, #888); border-bottom: 1px solid var(--border-color, #333); }
        .prices-table td { padding: 8px; border-bottom: 1px solid var(--border-color, #222); }
        .price-cell { font-weight: 600; font-family: monospace; }
        .price-notes { margin-left: 6px; cursor: help; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 500; }
        .condition-new { background: #22c55e; color: #fff; }
        .condition-used { background: #f59e0b; color: #000; }
        .condition-refurbished { background: #3b82f6; color: #fff; }
        .btn-delete { background: none; border: none; cursor: pointer; padding: 4px; opacity: 0.6; }
        .btn-delete:hover:not(:disabled) { opacity: 1; }
        .btn-delete:disabled { opacity: 0.3; cursor: not-allowed; }
        .specs-table { width: 100%; font-size: 0.875rem; }
        .specs-table td { padding: 6px 8px; }
        .spec-key { font-weight: 500; width: 40%; color: var(--text-muted, #888); }
        .modal-footer { display: flex; justify-content: flex-end; gap: 12px; padding: 16px 20px; border-top: 1px solid var(--border-color, #333); }
        .btn { padding: 8px 16px; border-radius: 4px; font-size: 0.9rem; cursor: pointer; border: none; }
        .btn-secondary { background: var(--border-color, #333); color: var(--text-color, #fff); }
        .btn-secondary:hover:not(:disabled) { background: #444; }
        .btn-primary { background: var(--primary-color, #6366f1); color: #fff; }
        .btn-primary:hover:not(:disabled) { background: #5558e3; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .muted { color: var(--text-muted, #888); }
        .error { color: var(--error-color, #ef4444); }
        a { color: var(--primary-color, #6366f1); text-decoration: none; }
        a:hover { text-decoration: underline; }
      `}</style>
    </div>
  );
}
