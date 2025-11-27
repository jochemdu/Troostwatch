import { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import type { BuyerResponse, BuyerCreateRequest } from '../lib/api';
import { createBuyer, deleteBuyer, fetchBuyers } from '../lib/api';

const emptyForm: BuyerCreateRequest = { label: '', name: '', notes: '' };

export default function BuyersPage() {
  const [buyers, setBuyers] = useState<BuyerResponse[]>([]);
  const [form, setForm] = useState<BuyerCreateRequest>(emptyForm);
  const [feedback, setFeedback] = useState<string>('');

  const loadBuyers = async () => {
    try {
      const data = await fetchBuyers();
      setBuyers(data);
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Buyers laden mislukt';
      setFeedback(detail);
    }
  };

  useEffect(() => {
    loadBuyers();
  }, []);

  const handleSubmit = async () => {
    if (!form.label.trim()) {
      setFeedback('Label is verplicht.');
      return;
    }
    setFeedback('');
    try {
      await createBuyer(form);
      setFeedback(`Buyer "${form.label}" aangemaakt.`);
      setForm(emptyForm);
      await loadBuyers();
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Buyer opslaan mislukt';
      setFeedback(detail);
    }
  };

  const handleDelete = async (label: string) => {
    try {
      await deleteBuyer(label);
      setBuyers((current) => current.filter((buyer) => buyer.label !== label));
      setFeedback(`Buyer "${label}" verwijderd.`);
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Verwijderen mislukt';
      setFeedback(detail);
    }
  };

  return (
    <Layout title="Buyers" subtitle="Beheer buyers">
      <div className="panel" style={{ marginBottom: 18 }}>
        <div className="form-row">
          <div>
            <label>Label (uniek ID)</label>
            <input
              value={form.label}
              onChange={(event) => setForm({ ...form, label: event.target.value })}
              placeholder="bijv. buyer-alpha"
            />
          </div>
          <div>
            <label>Naam</label>
            <input
              value={form.name ?? ''}
              onChange={(event) => setForm({ ...form, name: event.target.value || undefined })}
              placeholder="Alpha Industries"
            />
          </div>
        </div>
        <div className="form-row">
          <div style={{ flex: 2 }}>
            <label>Notities</label>
            <input
              value={form.notes ?? ''}
              onChange={(event) => setForm({ ...form, notes: event.target.value || undefined })}
              placeholder="Optionele notities..."
            />
          </div>
        </div>
        <div className="controls">
          <button className="button primary" onClick={handleSubmit}>
            Maak buyer
          </button>
        </div>
        {feedback && <p className="muted" style={{ marginTop: 12 }}>{feedback}</p>}
      </div>

      <div className="panel">
        <div className="status-row" style={{ justifyContent: 'space-between', marginBottom: 10 }}>
          <h2 style={{ margin: 0 }}>Buyers</h2>
          <span className="badge">{buyers.length} records</span>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th>Label</th>
              <th>Naam</th>
              <th>Notities</th>
              <th>Aangemaakt</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {buyers.map((buyer) => (
              <tr key={buyer.label}>
                <td><code>{buyer.label}</code></td>
                <td>{buyer.name ?? '—'}</td>
                <td>{buyer.notes ?? '—'}</td>
                <td className="muted">
                  {/* Note: created_at not in current API schema */}
                  —
                </td>
                <td>
                  <div className="table-actions">
                    <button className="button danger" onClick={() => handleDelete(buyer.label)}>
                      Verwijder
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {buyers.length === 0 && (
              <tr>
                <td colSpan={5} className="muted">Geen buyers gevonden.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
