import { useState, useEffect } from 'react';
import type { LotDetailResponse, LotUpdateRequest } from '../lib/api';
import { fetchLotDetail, updateLot } from '../lib/api';

interface Props {
  lotCode: string;
  auctionCode: string;
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export default function LotEditModal({ lotCode, auctionCode, isOpen, onClose, onSaved }: Props) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lot, setLot] = useState<LotDetailResponse | null>(null);

  // Form state
  const [referencePriceNew, setReferencePriceNew] = useState<string>('');
  const [referencePriceUsed, setReferencePriceUsed] = useState<string>('');
  const [referenceSource, setReferenceSource] = useState<string>('');
  const [referenceUrl, setReferenceUrl] = useState<string>('');
  const [notes, setNotes] = useState<string>('');

  useEffect(() => {
    if (!isOpen) return;

    const loadLot = async () => {
      setLoading(true);
      setError(null);
      try {
        const detail = await fetchLotDetail(lotCode, auctionCode);
        setLot(detail);
        // Populate form
        setReferencePriceNew(detail.reference_price_new_eur?.toString() ?? '');
        setReferencePriceUsed(detail.reference_price_used_eur?.toString() ?? '');
        setReferenceSource(detail.reference_source ?? '');
        setReferenceUrl(detail.reference_url ?? '');
        setNotes(detail.notes ?? '');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Kon lot niet laden');
      } finally {
        setLoading(false);
      }
    };

    loadLot();
  }, [isOpen, lotCode, auctionCode]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);

    const updates: LotUpdateRequest = {
      reference_price_new_eur: referencePriceNew ? parseFloat(referencePriceNew) : null,
      reference_price_used_eur: referencePriceUsed ? parseFloat(referencePriceUsed) : null,
      reference_source: referenceSource || null,
      reference_url: referenceUrl || null,
      notes: notes || null,
    };

    try {
      await updateLot(lotCode, updates, auctionCode);
      onSaved();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kon wijzigingen niet opslaan');
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Lot bewerken</h2>
          <button className="btn-close" onClick={onClose} aria-label="Sluiten">×</button>
        </div>

        {loading ? (
          <div className="modal-body">
            <p className="muted">Laden...</p>
          </div>
        ) : error ? (
          <div className="modal-body">
            <p className="error">{error}</p>
          </div>
        ) : lot ? (
          <>
            <div className="modal-body">
              {/* Lot info header */}
              <div className="lot-info-header">
                <h3>{lot.title || lot.lot_code}</h3>
                <p className="muted">
                  {lot.auction_code} · {lot.lot_code}
                  {lot.brand && ` · ${lot.brand}`}
                </p>
                {lot.current_bid_eur && (
                  <p>
                    <strong>Huidig bod:</strong> €{lot.current_bid_eur.toLocaleString('nl-NL')}
                    {lot.bid_count && ` (${lot.bid_count} biedingen)`}
                  </p>
                )}
              </div>

              {/* Reference prices section */}
              <fieldset className="form-fieldset">
                <legend>Referentieprijzen</legend>
                
                <div className="form-row">
                  <label htmlFor="reference-price-new">Nieuwprijs (€)</label>
                  <input
                    id="reference-price-new"
                    type="number"
                    step="0.01"
                    min="0"
                    value={referencePriceNew}
                    onChange={(e) => setReferencePriceNew(e.target.value)}
                    placeholder="Bijv. 1500.00"
                  />
                </div>

                <div className="form-row">
                  <label htmlFor="reference-price-used">Tweedehands prijs (€)</label>
                  <input
                    id="reference-price-used"
                    type="number"
                    step="0.01"
                    min="0"
                    value={referencePriceUsed}
                    onChange={(e) => setReferencePriceUsed(e.target.value)}
                    placeholder="Bijv. 800.00"
                  />
                </div>

                <div className="form-row">
                  <label htmlFor="reference-source">Bron</label>
                  <input
                    id="reference-source"
                    type="text"
                    value={referenceSource}
                    onChange={(e) => setReferenceSource(e.target.value)}
                    placeholder="Bijv. Marktplaats, Amazon, eBay"
                  />
                </div>

                <div className="form-row">
                  <label htmlFor="reference-url">URL</label>
                  <input
                    id="reference-url"
                    type="url"
                    value={referenceUrl}
                    onChange={(e) => setReferenceUrl(e.target.value)}
                    placeholder="https://..."
                  />
                </div>
              </fieldset>

              {/* Notes section */}
              <fieldset className="form-fieldset">
                <legend>Notities</legend>
                <div className="form-row">
                  <textarea
                    id="notes"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={4}
                    placeholder="Persoonlijke notities over dit lot..."
                  />
                </div>
              </fieldset>

              {/* Specs section (read-only) */}
              {lot.specs && lot.specs.length > 0 && (
                <fieldset className="form-fieldset">
                  <legend>Specificaties</legend>
                  <table className="table specs-table">
                    <tbody>
                      {lot.specs.map((spec) => (
                        <tr key={spec.id}>
                          <td className="spec-key">{spec.key}</td>
                          <td className="spec-value">{spec.value ?? '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </fieldset>
              )}
            </div>

            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={onClose} disabled={saving}>
                Annuleren
              </button>
              <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
                {saving ? 'Opslaan...' : 'Opslaan'}
              </button>
            </div>
          </>
        ) : null}
      </div>

      <style jsx>{`
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
        }

        .modal {
          background: var(--card-bg, #1a1a2e);
          border-radius: 8px;
          min-width: 480px;
          max-width: 600px;
          max-height: 90vh;
          overflow-y: auto;
          box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }

        .modal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 20px;
          border-bottom: 1px solid var(--border-color, #333);
        }

        .modal-header h2 {
          margin: 0;
          font-size: 1.25rem;
        }

        .btn-close {
          background: none;
          border: none;
          font-size: 1.5rem;
          color: var(--text-muted, #888);
          cursor: pointer;
          padding: 0;
          line-height: 1;
        }

        .btn-close:hover {
          color: var(--text-color, #fff);
        }

        .modal-body {
          padding: 20px;
        }

        .lot-info-header {
          margin-bottom: 20px;
          padding-bottom: 16px;
          border-bottom: 1px solid var(--border-color, #333);
        }

        .lot-info-header h3 {
          margin: 0 0 4px 0;
        }

        .form-fieldset {
          border: 1px solid var(--border-color, #333);
          border-radius: 6px;
          padding: 16px;
          margin-bottom: 16px;
        }

        .form-fieldset legend {
          padding: 0 8px;
          font-weight: 600;
          color: var(--text-muted, #888);
        }

        .form-row {
          margin-bottom: 12px;
        }

        .form-row:last-child {
          margin-bottom: 0;
        }

        .form-row label {
          display: block;
          margin-bottom: 4px;
          font-size: 0.875rem;
          color: var(--text-muted, #888);
        }

        .form-row input,
        .form-row textarea {
          width: 100%;
          padding: 8px 12px;
          border: 1px solid var(--border-color, #333);
          border-radius: 4px;
          background: var(--input-bg, #0f0f1a);
          color: var(--text-color, #fff);
          font-size: 0.9rem;
        }

        .form-row input:focus,
        .form-row textarea:focus {
          outline: none;
          border-color: var(--primary-color, #6366f1);
        }

        .specs-table {
          width: 100%;
          font-size: 0.875rem;
        }

        .specs-table td {
          padding: 6px 8px;
        }

        .spec-key {
          font-weight: 500;
          width: 40%;
          color: var(--text-muted, #888);
        }

        .modal-footer {
          display: flex;
          justify-content: flex-end;
          gap: 12px;
          padding: 16px 20px;
          border-top: 1px solid var(--border-color, #333);
        }

        .btn {
          padding: 8px 16px;
          border-radius: 4px;
          font-size: 0.9rem;
          cursor: pointer;
          border: none;
        }

        .btn-secondary {
          background: var(--border-color, #333);
          color: var(--text-color, #fff);
        }

        .btn-secondary:hover:not(:disabled) {
          background: #444;
        }

        .btn-primary {
          background: var(--primary-color, #6366f1);
          color: #fff;
        }

        .btn-primary:hover:not(:disabled) {
          background: #5558e3;
        }

        .btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .muted {
          color: var(--text-muted, #888);
        }

        .error {
          color: var(--error-color, #ef4444);
        }
      `}</style>
    </div>
  );
}
