import { useState, useEffect } from 'react';
import Layout from '../components/Layout';
import type { SpecTemplate, SpecTemplateCreateRequest } from '../lib/api';
import { fetchSpecTemplates, createSpecTemplate, deleteSpecTemplate } from '../lib/api';

interface TemplateNode extends SpecTemplate {
  children: TemplateNode[];
}

function buildTemplateTree(templates: SpecTemplate[]): TemplateNode[] {
  const map = new Map<number, TemplateNode>();
  const roots: TemplateNode[] = [];

  for (const template of templates) {
    map.set(template.id, { ...template, children: [] });
  }

  for (const template of templates) {
    const node = map.get(template.id)!;
    if (template.parent_id && map.has(template.parent_id)) {
      map.get(template.parent_id)!.children.push(node);
    } else {
      roots.push(node);
    }
  }

  return roots;
}

interface NewTemplateForm {
  title: string;
  value: string;
  ean: string;
  price: string;
  parentId: number | null;
}

const emptyForm: NewTemplateForm = {
  title: '',
  value: '',
  ean: '',
  price: '',
  parentId: null,
};

export default function TemplatesPage() {
  const [templates, setTemplates] = useState<SpecTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newTemplate, setNewTemplate] = useState<NewTemplateForm>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [addingChildTo, setAddingChildTo] = useState<number | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchSpecTemplates();
      setTemplates(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kon templates niet laden');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (parentId: number | null = null) => {
    if (!newTemplate.title.trim()) {
      setError('Vul een titel in');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const data: SpecTemplateCreateRequest = {
        title: newTemplate.title.trim(),
        value: newTemplate.value.trim() || null,
        ean: newTemplate.ean.trim() || null,
        price_eur: newTemplate.price ? parseFloat(newTemplate.price) : null,
        parent_id: parentId,
      };
      const created = await createSpecTemplate(data);
      setTemplates(prev => [...prev, created]);
      setNewTemplate(emptyForm);
      setShowAddForm(false);
      setAddingChildTo(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kon template niet aanmaken');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (templateId: number) => {
    const hasChildren = templates.some(t => t.parent_id === templateId);
    const msg = hasChildren 
      ? 'Dit template heeft sub-templates. Alles verwijderen?'
      : 'Weet je zeker dat je dit template wilt verwijderen?';
    if (!confirm(msg)) return;
    
    setSaving(true);
    setError(null);
    try {
      await deleteSpecTemplate(templateId);
      setTemplates(prev => prev.filter(t => t.id !== templateId && t.parent_id !== templateId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kon template niet verwijderen');
    } finally {
      setSaving(false);
    }
  };

  const templateTree = buildTemplateTree(templates);
  const rootTemplates = templates.filter(t => !t.parent_id);

  const renderTemplateRow = (template: TemplateNode, depth: number = 0) => (
    <div key={template.id} className="template-item">
      <div className={`template-row depth-${depth}`}>
        <div className="template-info">
          <span className="template-title">{template.title}</span>
          {template.value && <span className="template-value">{template.value}</span>}
          {template.ean && <span className="template-ean">📦 {template.ean}</span>}
          {template.price_eur != null && (
            <span className="template-price">€{template.price_eur.toLocaleString('nl-NL', { minimumFractionDigits: 2 })}</span>
          )}
        </div>
        <div className="template-actions">
          <button 
            className="btn-icon" 
            onClick={() => {
              setAddingChildTo(template.id);
              setNewTemplate({ ...emptyForm, parentId: template.id });
            }}
            disabled={saving || addingChildTo !== null}
            title="Sub-template toevoegen"
          >
            ➕
          </button>
          <button 
            className="btn-icon btn-delete" 
            onClick={() => handleDelete(template.id)}
            disabled={saving}
            title="Verwijderen"
          >
            🗑️
          </button>
        </div>
      </div>

      {addingChildTo === template.id && (
        <div className="add-child-form">
          <h4>Sub-template toevoegen aan &quot;{template.title}&quot;</h4>
          <div className="form-grid">
            <div className="form-row">
              <label>Titel *</label>
              <input 
                type="text" 
                value={newTemplate.title} 
                onChange={e => setNewTemplate({ ...newTemplate, title: e.target.value })}
                placeholder="bijv. Videokaart"
              />
            </div>
            <div className="form-row">
              <label>Waarde</label>
              <input 
                type="text" 
                value={newTemplate.value} 
                onChange={e => setNewTemplate({ ...newTemplate, value: e.target.value })}
                placeholder="bijv. RTX 4090"
              />
            </div>
            <div className="form-row">
              <label>EAN / Barcode</label>
              <input 
                type="text" 
                value={newTemplate.ean} 
                onChange={e => setNewTemplate({ ...newTemplate, ean: e.target.value })}
                placeholder="bijv. 5012345678900"
              />
            </div>
            <div className="form-row">
              <label>Prijs (€)</label>
              <input 
                type="number" 
                step="0.01"
                min="0"
                value={newTemplate.price} 
                onChange={e => setNewTemplate({ ...newTemplate, price: e.target.value })}
                placeholder="0.00"
              />
            </div>
          </div>
          <div className="form-actions">
            <button className="btn btn-secondary" onClick={() => { setAddingChildTo(null); setNewTemplate(emptyForm); }}>Annuleren</button>
            <button className="btn btn-primary" onClick={() => handleCreate(template.id)} disabled={saving}>
              {saving ? 'Opslaan...' : 'Toevoegen'}
            </button>
          </div>
        </div>
      )}

      {template.children.length > 0 && (
        <div className="template-children">
          {template.children.map(child => renderTemplateRow(child, depth + 1))}
        </div>
      )}
    </div>
  );

  return (
    <Layout title="Spec Templates">
      <div className="page-header">
        <h1>Spec Templates</h1>
        <p className="muted">Herbruikbare specificaties die je bij meerdere lots kunt toepassen</p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="actions-bar">
        <button 
          className="btn btn-primary" 
          onClick={() => setShowAddForm(true)}
          disabled={showAddForm || addingChildTo !== null}
        >
          + Nieuw Template
        </button>
        <button className="btn btn-secondary" onClick={loadTemplates} disabled={loading}>
          🔄 Vernieuwen
        </button>
      </div>

      {showAddForm && (
        <div className="add-form-panel">
          <h3>Nieuw Template</h3>
          <div className="form-grid">
            <div className="form-row">
              <label>Titel *</label>
              <input 
                type="text" 
                value={newTemplate.title} 
                onChange={e => setNewTemplate({ ...newTemplate, title: e.target.value })}
                placeholder="bijv. Computer"
              />
            </div>
            <div className="form-row">
              <label>Waarde</label>
              <input 
                type="text" 
                value={newTemplate.value} 
                onChange={e => setNewTemplate({ ...newTemplate, value: e.target.value })}
                placeholder="bijv. Dell Optiplex 7090"
              />
            </div>
            <div className="form-row">
              <label>EAN / Barcode</label>
              <input 
                type="text" 
                value={newTemplate.ean} 
                onChange={e => setNewTemplate({ ...newTemplate, ean: e.target.value })}
                placeholder="bijv. 5012345678900"
              />
            </div>
            <div className="form-row">
              <label>Prijs (€)</label>
              <input 
                type="number" 
                step="0.01"
                min="0"
                value={newTemplate.price} 
                onChange={e => setNewTemplate({ ...newTemplate, price: e.target.value })}
                placeholder="0.00"
              />
            </div>
          </div>
          {rootTemplates.length > 0 && (
            <div className="form-row">
              <label>Onder (optioneel)</label>
              <select 
                value={newTemplate.parentId ?? ''} 
                onChange={e => setNewTemplate({ ...newTemplate, parentId: e.target.value ? parseInt(e.target.value) : null })}
              >
                <option value="">— Hoofdtemplate —</option>
                {rootTemplates.map(t => (
                  <option key={t.id} value={t.id}>{t.title}</option>
                ))}
              </select>
            </div>
          )}
          <div className="form-actions">
            <button className="btn btn-secondary" onClick={() => { setShowAddForm(false); setNewTemplate(emptyForm); }}>Annuleren</button>
            <button className="btn btn-primary" onClick={() => handleCreate(newTemplate.parentId)} disabled={saving}>
              {saving ? 'Opslaan...' : 'Aanmaken'}
            </button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="loading">Laden...</div>
      ) : templateTree.length === 0 ? (
        <div className="empty-state">
          <p>Nog geen templates. Maak je eerste template aan om te beginnen.</p>
          <p className="muted">Templates kun je hergebruiken bij het toevoegen van specificaties aan lots.</p>
        </div>
      ) : (
        <div className="templates-list">
          {templateTree.map(template => renderTemplateRow(template))}
        </div>
      )}

      <style jsx>{`
        .page-header { margin-bottom: 24px; }
        .page-header h1 { margin: 0 0 8px 0; }
        .muted { color: #888; }
        .error-banner { background: #fee; color: #c00; padding: 12px; border-radius: 6px; margin-bottom: 16px; }
        .actions-bar { display: flex; gap: 12px; margin-bottom: 20px; }
        .btn { padding: 10px 18px; border-radius: 6px; font-size: 0.9rem; cursor: pointer; border: none; font-weight: 500; }
        .btn-primary { background: #6366f1; color: #fff; }
        .btn-primary:hover:not(:disabled) { background: #5558e3; }
        .btn-secondary { background: #333; color: #e0e0e0; }
        .btn-secondary:hover:not(:disabled) { background: #444; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .add-form-panel { background: #1a1a2e; border: 1px solid #333; border-radius: 8px; padding: 20px; margin-bottom: 24px; }
        .add-form-panel h3 { margin: 0 0 16px 0; color: #fff; }
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
        .form-row { margin-bottom: 12px; }
        .form-row label { display: block; margin-bottom: 6px; font-size: 0.85rem; color: #888; }
        .form-row input, .form-row select { 
          width: 100%; 
          padding: 10px 14px; 
          border: 1px solid #444; 
          border-radius: 6px; 
          background: #0f0f1a; 
          color: #e0e0e0; 
          font-size: 0.9rem; 
        }
        .form-row input:focus, .form-row select:focus { outline: none; border-color: #6366f1; }
        .form-row input::placeholder { color: #666; }
        .form-row select option { background: #0f0f1a; color: #e0e0e0; }
        .form-actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 16px; }
        .loading { color: #888; padding: 40px; text-align: center; }
        .empty-state { text-align: center; padding: 60px 20px; background: #1a1a2e; border-radius: 8px; }
        .empty-state p { margin: 0 0 8px 0; }
        .templates-list { }
        .template-item { margin-bottom: 4px; }
        .template-row { 
          display: flex; 
          align-items: center; 
          justify-content: space-between;
          padding: 14px 16px; 
          background: #1a1a2e; 
          border-radius: 6px; 
          border: 1px solid #333;
        }
        .template-row.depth-1 { margin-left: 32px; background: #151528; }
        .template-row.depth-2 { margin-left: 64px; background: #121225; }
        .template-row.depth-3 { margin-left: 96px; background: #0f0f20; }
        .template-info { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
        .template-title { font-weight: 600; color: #fff; font-size: 1rem; }
        .template-value { color: #a0a0c0; }
        .template-ean { font-size: 0.8rem; color: #888; background: #252540; padding: 3px 8px; border-radius: 4px; }
        .template-price { font-size: 0.9rem; color: #4ade80; font-weight: 600; font-family: monospace; }
        .template-actions { display: flex; gap: 8px; }
        .btn-icon { 
          background: none; 
          border: 1px solid #444; 
          border-radius: 6px; 
          padding: 6px 10px; 
          cursor: pointer; 
          font-size: 0.9rem;
          transition: all 0.15s;
        }
        .btn-icon:hover:not(:disabled) { background: #333; border-color: #555; }
        .btn-icon:disabled { opacity: 0.3; cursor: not-allowed; }
        .btn-icon.btn-delete:hover:not(:disabled) { background: #4a1a1a; border-color: #a33; }
        .template-children { margin-top: 4px; }
        .add-child-form { 
          margin-left: 32px; 
          background: #252540; 
          border: 1px solid #444; 
          border-radius: 6px; 
          padding: 16px; 
          margin-top: 8px; 
          margin-bottom: 8px;
        }
        .add-child-form h4 { margin: 0 0 12px 0; color: #a0a0c0; font-size: 0.9rem; }
      `}</style>
    </Layout>
  );
}
