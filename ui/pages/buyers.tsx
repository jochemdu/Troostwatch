import { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import { BuyerPayload, createBuyer, deleteBuyer, fetchBuyers, updateBuyer } from '../lib/api';

const emptyBuyer: BuyerPayload = { name: '', email: '', phone: '', notes: '' };

export default function BuyersPage() {
  const [buyers, setBuyers] = useState<BuyerPayload[]>([]);
  const [form, setForm] = useState<BuyerPayload>(emptyBuyer);
  const [editing, setEditing] = useState<string | null>(null);
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
    setFeedback('');
    try {
      if (editing) {
        const updated = await updateBuyer(editing, form);
        setBuyers((current) => current.map((buyer) => (buyer.id === editing ? updated : buyer)));
        setEditing(null);
      } else {
        const created = await createBuyer(form);
        setBuyers((current) => [created, ...current]);
      }
      setForm(emptyBuyer);
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Buyer opslaan mislukt';
      setFeedback(detail);
    }
  };

  const handleDelete = async (id?: string) => {
    if (!id) return;
    await deleteBuyer(id);
    setBuyers((current) => current.filter((buyer) => buyer.id !== id));
  };

  const startEdit = (buyer: BuyerPayload) => {
    setForm({ ...buyer });
    setEditing(buyer.id ?? null);
  };

  return (
    <Layout title="Buyers" subtitle="Beheer buyer-mutaties">
      <div className="panel" style={{ marginBottom: 18 }}>
        <div className="form-row">
          <div>
            <label>Naam</label>
            <input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
          </div>
          <div>
            <label>Email</label>
            <input value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
          </div>
        </div>
        <div className="form-row">
          <div>
            <label>Telefoon</label>
            <input value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} />
          </div>
          <div>
            <label>Notities</label>
            <input value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
          </div>
        </div>
        <div className="controls">
          <button className="button primary" onClick={handleSubmit}>
            {editing ? 'Bewaar wijziging' : 'Maak buyer'}
          </button>
          {editing && (
            <button className="button" onClick={() => { setEditing(null); setForm(emptyBuyer); }}>
              Annuleer
            </button>
          )}
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
              <th>Naam</th>
              <th>Email</th>
              <th>Telefoon</th>
              <th>Notities</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {buyers.map((buyer) => (
              <tr key={buyer.id ?? buyer.name}>
                <td>{buyer.name}</td>
                <td>{buyer.email ?? '—'}</td>
                <td>{buyer.phone ?? '—'}</td>
                <td>{buyer.notes ?? '—'}</td>
                <td>
                  <div className="table-actions">
                    <button className="button" onClick={() => startEdit(buyer)}>
                      Bewerk
                    </button>
                    <button className="button danger" onClick={() => handleDelete(buyer.id)}>
                      Verwijder
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Layout>
  );
}
