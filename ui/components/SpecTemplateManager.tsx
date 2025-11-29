import React, { useState, useEffect } from "react";
import { fetchSpecTemplates } from '../lib/api';

async function addSpecTemplate(template: any) {
  const response = await fetch('/spec-templates', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(template),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function updateSpecTemplate(id: number, updates: any) {
  const response = await fetch(`/spec-templates/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function deleteSpecTemplate(id: number) {
  const response = await fetch(`/spec-templates/${id}`, { method: 'DELETE' });
  if (!response.ok) throw new Error(await response.text());
}

export default function SpecTemplateManager() {
  const [templates, setTemplates] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [newTemplate, setNewTemplate] = useState({ title: '', value: '', category: '' });
  const [editId, setEditId] = useState<number | null>(null);
  const [editTemplate, setEditTemplate] = useState<any>({});
  const [toast, setToast] = useState<string | null>(null);

  const refresh = () => {
    setLoading(true);
    fetchSpecTemplates()
      .then(setTemplates)
      .catch(err => setError(err.message || 'Ophalen mislukt'))
      .finally(() => setLoading(false));
  };

  useEffect(refresh, []);

  // Logging/feedback bij templatewijzigingen
  useEffect(() => {
    if (!loading && !error && templates.length > 0) {
      setToast('Templates succesvol bijgewerkt!');
      setTimeout(() => setToast(null), 2500);
    }
  }, [templates, loading, error]);

  // Automatische refresh van suggesties na template-update
  useEffect(() => {
    if (!loading && !error && templates.length > 0) {
      // Trigger een custom event zodat andere componenten (zoals SpecSuggestionEditor) kunnen luisteren
      window.dispatchEvent(new CustomEvent('specTemplatesUpdated'));
    }
  }, [templates, loading, error]);

  const handleAdd = async () => {
    try {
      await addSpecTemplate(newTemplate);
      setNewTemplate({ title: '', value: '', category: '' });
      refresh();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleEdit = async () => {
    if (!editId) return;
    try {
      await updateSpecTemplate(editId, editTemplate);
      setEditId(null);
      setEditTemplate({});
      refresh();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Weet je zeker dat je deze template wilt verwijderen?')) return;
    try {
      await deleteSpecTemplate(id);
      refresh();
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div style={{ maxWidth: 600, margin: '2rem auto', padding: 24, border: '1px solid #eee', borderRadius: 8 }}>
      <h2>Spec Template Manager</h2>
      {loading && <div>Bezig met laden...</div>}
      {error && <div style={{ color: 'red' }}>{error}</div>}
      {toast && (
        <div style={{ position: 'fixed', top: 24, right: 24, background: '#388e3c', color: '#fff', padding: '12px 24px', borderRadius: 8, zIndex: 1000 }}>
          {toast}
        </div>
      )}
      <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: 16 }}>
        <thead>
          <tr style={{ background: '#f8f8f8' }}>
            <th style={{ textAlign: 'left', padding: 8 }}>ID</th>
            <th style={{ textAlign: 'left', padding: 8 }}>Titel</th>
            <th style={{ textAlign: 'left', padding: 8 }}>Parent</th>
            <th style={{ textAlign: 'left', padding: 8 }}>Type</th>
            <th style={{ textAlign: 'left', padding: 8 }}>Categorie</th>
            <th style={{ textAlign: 'left', padding: 8 }}>Acties</th>
          </tr>
        </thead>
        <tbody>
          {templates.map(t => (
            <tr key={t.id} style={{ borderBottom: '1px solid #eee' }}>
              <td style={{ padding: 8 }}>{t.id}</td>
              <td style={{ padding: 8 }}>
                {editId === t.id ? (
                  <input value={editTemplate.title ?? ''} onChange={e => setEditTemplate(et => ({ ...et, title: e.target.value }))} />
                ) : t.title}
              </td>
              <td style={{ padding: 8 }}>{t.parent_id ?? '-'}</td>
              <td style={{ padding: 8 }}>
                {editId === t.id ? (
                  <input value={editTemplate.value ?? ''} onChange={e => setEditTemplate(et => ({ ...et, value: e.target.value }))} />
                ) : t.value ?? '-'}
              </td>
              <td style={{ padding: 8 }}>
                {editId === t.id ? (
                  <input value={editTemplate.category ?? ''} onChange={e => setEditTemplate(et => ({ ...et, category: e.target.value }))} />
                ) : t.category ?? '-'}</td>
              <td style={{ padding: 8 }}>
                {editId === t.id ? (
                  <button onClick={handleEdit}>Opslaan</button>
                  ) : (
                  <>
                    <button onClick={() => { setEditId(t.id); setEditTemplate(t); }}>Bewerken</button>
                    <button onClick={() => handleDelete(t.id)} style={{ marginLeft: 8, color: '#d32f2f' }}>Verwijderen</button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: 24 }}>
        <h4>Nieuwe template toevoegen</h4>
        <input
          placeholder="Titel"
          value={newTemplate.title}
          onChange={e => setNewTemplate(nt => ({ ...nt, title: e.target.value }))}
          style={{ marginRight: 8 }}
        />
        <input
          placeholder="Type"
          value={newTemplate.value}
          onChange={e => setNewTemplate(nt => ({ ...nt, value: e.target.value }))}
          style={{ marginRight: 8 }}
        />
        <input
          placeholder="Categorie"
          value={newTemplate.category}
          onChange={e => setNewTemplate(nt => ({ ...nt, category: e.target.value }))}
          style={{ marginRight: 8 }}
        />
        <button onClick={handleAdd}>Toevoegen</button>
      </div>
    </div>
  );
}
