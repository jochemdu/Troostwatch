import React, { useState, useEffect } from 'react';
import type { LotDetailResponse, ReferencePrice, ReferencePriceCreateRequest, LotSpec, LotSpecCreateRequest, SpecTemplate } from '../lib/api';
import { fetchLotDetail, updateLot, addReferencePrice, deleteReferencePrice, addLotSpec, deleteLotSpec, fetchSpecTemplates, createSpecTemplate, applyTemplateToLot } from '../lib/api';
import { buildSpecTree, buildTemplateTree, getDepthColor, type SpecNode, type TemplateNode } from '../lib/specs';

interface BaseProps {
  onClose: () => void;
  onSave?: () => void;
  onSaved?: () => void;
}

interface PropsWithCodes extends BaseProps {
  lotCode: string;
  auctionCode: string;
  isOpen: boolean;
  lot?: never;
  templates?: never;
}

interface PropsWithLot extends BaseProps {
  lot: LotDetailResponse;
  templates: SpecTemplate[];
  lotCode?: never;
  auctionCode?: never;
  isOpen?: never;
}

type Props = PropsWithCodes | PropsWithLot;

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

interface NewSpecForm {
  key: string;
  value: string;
  parentId: number | null;
  ean: string;
  price: string;
  releaseDate: string;
  category: string;
  saveAsTemplate: boolean;
}

const emptySpecForm: NewSpecForm = {
  key: '',
  value: '',
  parentId: null,
  ean: '',
  price: '',
  releaseDate: '',
  category: '',
  saveAsTemplate: false,
};

export default function LotEditModal(props: Props) {
  // Determine if we have a lot directly or need to fetch
  const providedLot = 'lot' in props ? props.lot : null;
  const lotCode = providedLot ? providedLot.lot_code : props.lotCode!;
  const auctionCode = providedLot ? providedLot.auction_code : props.auctionCode!;
  const isOpen = 'isOpen' in props ? props.isOpen : true;
  const onSaved = props.onSave || props.onSaved || (() => {});
  const onClose = props.onClose;
  const providedTemplates = 'templates' in props ? props.templates : null;

  const [loading, setLoading] = useState(!providedLot);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lot, setLot] = useState<LotDetailResponse | null>(providedLot ?? null);
  const [notes, setNotes] = useState<string>(providedLot?.notes ?? '');
  const [ean, setEan] = useState<string>(providedLot?.ean ?? '');
  const [referencePrices, setReferencePrices] = useState<ReferencePrice[]>(providedLot?.reference_prices ?? []);
  const [showAddForm, setShowAddForm] = useState(false);
  const [newPrice, setNewPrice] = useState<NewPriceForm>(emptyPriceForm);
  const [specs, setSpecs] = useState<LotSpec[]>(providedLot?.specs ?? []);
  const [showAddSpecForm, setShowAddSpecForm] = useState(false);
  const [newSpec, setNewSpec] = useState<NewSpecForm>(emptySpecForm);
  const [addingSubspecTo, setAddingSubspecTo] = useState<number | null>(null);
  const [specTemplates, setSpecTemplates] = useState<SpecTemplate[]>(providedTemplates ?? []);
  const [showTemplateSelector, setShowTemplateSelector] = useState(false);
  const [templateParentId, setTemplateParentId] = useState<number | null>(null);

  useEffect(() => {
    if (!isOpen || providedLot) return;
    const loadLot = async () => {
      setLoading(true);
      setError(null);
      try {
        const [detail, templates] = await Promise.all([
          fetchLotDetail(lotCode, auctionCode),
          fetchSpecTemplates(),
        ]);
        setLot(detail);
        setNotes(detail.notes ?? '');
        setEan(detail.ean ?? '');
        setReferencePrices(detail.reference_prices ?? []);
        setSpecs(detail.specs ?? []);
        setSpecTemplates(templates);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Kon lot niet laden');
      } finally {
        setLoading(false);
      }
    };
    loadLot();
  }, [isOpen, lotCode, auctionCode, providedLot]);

  const handleSaveLotInfo = async () => {
    setSaving(true);
    setError(null);
    try {
      await updateLot(lotCode, { notes: notes || null, ean: ean || null }, auctionCode);
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

  const handleAddSpec = async (parentId: number | null = null) => {
    const specForm = newSpec;
    if (!specForm.key.trim()) {
      setError('Vul een specificatie naam in');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const data: LotSpecCreateRequest = {
        key: specForm.key.trim(),
        value: specForm.value.trim(),
        parent_id: parentId,
        ean: specForm.ean.trim() || undefined,
        price_eur: specForm.price ? parseFloat(specForm.price) : undefined,
        release_date: specForm.releaseDate.trim() || undefined,
        category: specForm.category.trim() || undefined,
      };
      const created = await addLotSpec(lotCode, data, auctionCode);
      setSpecs((prev) => [...prev, created]);
      
      // Save as template if checkbox is checked
      if (specForm.saveAsTemplate) {
        const template = await createSpecTemplate({
          title: specForm.key.trim(),
          value: specForm.value.trim() || null,
          ean: specForm.ean.trim() || null,
          price_eur: specForm.price ? parseFloat(specForm.price) : null,
          parent_id: null,
          release_date: specForm.releaseDate.trim() || null,
          category: specForm.category.trim() || null,
        });
        setSpecTemplates(prev => [...prev, template]);
      }
      
      setNewSpec(emptySpecForm);
      setShowAddSpecForm(false);
      setAddingSubspecTo(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kon specificatie niet toevoegen');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteSpec = async (specId: number) => {
    // Check if this spec has children
    const hasChildren = specs.some(s => s.parent_id === specId);
    const confirmMsg = hasChildren 
      ? 'Deze specificatie heeft subspecificaties. Weet je zeker dat je alles wilt verwijderen?'
      : 'Weet je zeker dat je deze specificatie wilt verwijderen?';
    if (!confirm(confirmMsg)) return;
    
    setSaving(true);
    setError(null);
    try {
      await deleteLotSpec(lotCode, specId);
      // Remove this spec and all its children
      setSpecs((prev) => prev.filter((s) => s.id !== specId && s.parent_id !== specId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kon specificatie niet verwijderen');
    } finally {
      setSaving(false);
    }
  };

  const handleClose = () => {
    setShowAddForm(false);
    setNewPrice(emptyPriceForm);
    setShowAddSpecForm(false);
    setNewSpec(emptySpecForm);
    setAddingSubspecTo(null);
    onClose();
  };

  // Get root-level specs for the parent dropdown
  const rootSpecs = specs.filter(s => s.parent_id === null);
  const specTree = buildSpecTree(specs);
  const templateTree = buildTemplateTree(specTemplates);

  // Render a template node with indentation
  const renderTemplateNode = (template: TemplateNode, depth: number): React.ReactNode => (
    <div key={template.id} className="template-node">
      <button 
        className={`template-btn depth-${depth}`}
        onClick={async () => {
          try {
            const created = await applyTemplateToLot(lotCode, template.id, templateParentId, auctionCode);
            setSpecs(prev => [...prev, created]);
            setShowTemplateSelector(false);
            setTemplateParentId(null);
          } catch (err) {
            setError(err instanceof Error ? err.message : 'Kon template niet toepassen');
          }
        }}
      >
        <span className="template-title">{template.title}</span>
        {template.value && <span className="template-value">{template.value}</span>}
        {template.ean && <span className="template-ean">📦 {template.ean}</span>}
        {template.price_eur != null && <span className="template-price">€{template.price_eur.toLocaleString('nl-NL', { minimumFractionDigits: 2 })}</span>}
        {template.children.length > 0 && <span className="template-children-count">+{template.children.length} sub</span>}
      </button>
      {template.children.length > 0 && (
        <div className="template-children">
          {template.children.map(child => renderTemplateNode(child, depth + 1))}
        </div>
      )}
    </div>
  );

  const renderSpecRow = (spec: SpecNode, depth: number = 0) => (
    <div key={spec.id}>
      <div className={`spec-row depth-${depth}`}>
        <span className="spec-key">{spec.key}</span>
        <span className="spec-value">{spec.value ?? '—'}</span>
        {spec.ean && <span className="spec-ean" title="EAN">📦 {spec.ean}</span>}
        {spec.price_eur != null && <span className="spec-price">€{spec.price_eur.toLocaleString('nl-NL', { minimumFractionDigits: 2 })}</span>}
        {spec.release_date && <span className="spec-release-date" title="Release datum">📅 {spec.release_date}</span>}
        {spec.category && <span className="spec-category" title="Categorie">🏷️ {spec.category}</span>}
        {spec.template_id && <span className="spec-template" title="Gebaseerd op template">📋</span>}
        <div className="spec-actions">
          <button 
            className="btn-add-sub" 
            onClick={() => {
              setAddingSubspecTo(spec.id);
              setNewSpec({ ...emptySpecForm, parentId: spec.id });
            }}
            disabled={saving || addingSubspecTo !== null}
            title="Subspecificatie toevoegen"
          >
            +
          </button>
          <button 
            className="btn-delete" 
            onClick={() => handleDeleteSpec(spec.id)} 
            disabled={saving} 
            title="Verwijderen"
          >
            🗑️
          </button>
        </div>
      </div>
      
      {addingSubspecTo === spec.id && (
        <div className="add-subspec-form">
          <div className="form-grid">
            <div className="form-row">
              <label>Naam *</label>
              <input 
                type="text" 
                value={newSpec.key} 
                onChange={(e) => setNewSpec({ ...newSpec, key: e.target.value })} 
                placeholder="bijv. Videokaart" 
                required 
              />
            </div>
            <div className="form-row">
              <label>Waarde</label>
              <input 
                type="text" 
                value={newSpec.value} 
                onChange={(e) => setNewSpec({ ...newSpec, value: e.target.value })} 
                placeholder="bijv. RTX 4090" 
              />
            </div>
            <div className="form-row">
              <label>EAN</label>
              <input 
                type="text" 
                value={newSpec.ean} 
                onChange={(e) => setNewSpec({ ...newSpec, ean: e.target.value })} 
                placeholder="bijv. 5012345678900" 
              />
            </div>
            <div className="form-row">
              <label>Prijs (€)</label>
              <input 
                type="number" 
                step="0.01"
                min="0"
                value={newSpec.price} 
                onChange={(e) => setNewSpec({ ...newSpec, price: e.target.value })} 
                placeholder="0.00" 
              />
            </div>
            <div className="form-row">
              <label>Release datum</label>
              <input 
                type="date"
                value={newSpec.releaseDate} 
                onChange={(e) => setNewSpec({ ...newSpec, releaseDate: e.target.value })} 
              />
            </div>
            <div className="form-row">
              <label>Categorie</label>
              <input 
                type="text"
                value={newSpec.category} 
                onChange={(e) => setNewSpec({ ...newSpec, category: e.target.value })} 
                placeholder="bijv. Elektronica" 
              />
            </div>
          </div>
          <div className="form-actions">
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => { setAddingSubspecTo(null); setNewSpec(emptySpecForm); }}>Annuleren</button>
            <button type="button" className="btn btn-primary btn-sm" onClick={() => handleAddSpec(spec.id)} disabled={saving}>{saving ? '...' : 'Toevoegen'}</button>
          </div>
        </div>
      )}
      
      {spec.children.length > 0 && (
        <div className="spec-children">
          {spec.children.map(child => renderSpecRow(child, depth + 1))}
        </div>
      )}
    </div>
  );

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
                <legend>Lot informatie</legend>
                <div className="form-grid">
                  <div className="form-row">
                    <label>EAN / Barcode</label>
                    <input type="text" value={ean} onChange={(e) => setEan(e.target.value)} placeholder="bijv. 5012345678900" />
                  </div>
                </div>
                <div className="form-row">
                  <label>Notities</label>
                  <textarea id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} placeholder="Persoonlijke notities over dit lot..." />
                </div>
                <div className="form-actions">
                  <button type="button" className="btn btn-primary" onClick={handleSaveLotInfo} disabled={saving}>{saving ? 'Opslaan...' : 'Opslaan'}</button>
                </div>
              </fieldset>

              <fieldset className="form-fieldset">
                <legend>
                  Specificaties
                  <button type="button" className="btn-add-small" onClick={() => setShowTemplateSelector(true)} disabled={showAddSpecForm || addingSubspecTo !== null} style={{ marginLeft: 8 }}>📋 Template</button>
                  <button type="button" className="btn-add-small" onClick={() => setShowAddSpecForm(true)} disabled={showAddSpecForm || addingSubspecTo !== null}>+ Nieuw</button>
                </legend>

                {showTemplateSelector && specTemplates.length > 0 && (
                  <div className="template-selector">
                    <p className="muted" style={{ marginBottom: 8 }}>Kies een template om toe te passen:</p>
                    
                    {/* Parent selector for where to add the template */}
                    {rootSpecs.length > 0 && (
                      <div className="form-row" style={{ marginBottom: 12 }}>
                        <label>Toevoegen onder:</label>
                        <select 
                          value={templateParentId ?? ''} 
                          onChange={(e) => setTemplateParentId(e.target.value ? parseInt(e.target.value) : null)}
                        >
                          <option value="">— Hoofdspecificatie —</option>
                          {rootSpecs.map((s) => (
                            <option key={s.id} value={s.id}>{s.key}</option>
                          ))}
                        </select>
                      </div>
                    )}

                    <div className="template-tree">
                      {buildTemplateTree(specTemplates).map(template => renderTemplateNode(template, 0))}
                    </div>
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => { setShowTemplateSelector(false); setTemplateParentId(null); }} style={{ marginTop: 8 }}>Annuleren</button>
                  </div>
                )}

                {showTemplateSelector && specTemplates.length === 0 && (
                  <p className="muted">Geen templates beschikbaar. Maak eerst een specificatie en sla deze op als template.</p>
                )}

                {showAddSpecForm && (
                  <div className="add-price-form">
                    <div className="form-grid">
                      <div className="form-row">
                        <label>Naam *</label>
                        <input type="text" value={newSpec.key} onChange={(e) => setNewSpec({ ...newSpec, key: e.target.value })} placeholder="bijv. Computer" required />
                      </div>
                      <div className="form-row">
                        <label>Waarde</label>
                        <input type="text" value={newSpec.value} onChange={(e) => setNewSpec({ ...newSpec, value: e.target.value })} placeholder="bijv. Dell Optiplex" />
                      </div>
                      <div className="form-row">
                        <label>EAN / Barcode</label>
                        <input type="text" value={newSpec.ean} onChange={(e) => setNewSpec({ ...newSpec, ean: e.target.value })} placeholder="bijv. 5012345678900" />
                      </div>
                      <div className="form-row">
                        <label>Prijs (€)</label>
                        <input type="number" step="0.01" min="0" value={newSpec.price} onChange={(e) => setNewSpec({ ...newSpec, price: e.target.value })} placeholder="0.00" />
                      </div>
                      <div className="form-row">
                        <label>Release datum</label>
                        <input type="date" value={newSpec.releaseDate} onChange={(e) => setNewSpec({ ...newSpec, releaseDate: e.target.value })} />
                        <small className="muted">Wanneer kwam dit product op de markt?</small>
                      </div>
                      <div className="form-row">
                        <label>Categorie</label>
                        <input type="text" value={newSpec.category} onChange={(e) => setNewSpec({ ...newSpec, category: e.target.value })} placeholder="bijv. Elektronica, Computer" />
                      </div>
                    </div>
                    {rootSpecs.length > 0 && (
                      <div className="form-row">
                        <label>Onder (optioneel)</label>
                        <select value={newSpec.parentId ?? ''} onChange={(e) => setNewSpec({ ...newSpec, parentId: e.target.value ? parseInt(e.target.value) : null })}>
                          <option value="">— Hoofdspecificatie —</option>
                          {rootSpecs.map((s) => (
                            <option key={s.id} value={s.id}>{s.key}</option>
                          ))}
                        </select>
                      </div>
                    )}
                    <div className="form-row">
                      <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                        <input 
                          type="checkbox" 
                          checked={newSpec.saveAsTemplate} 
                          onChange={(e) => setNewSpec({ ...newSpec, saveAsTemplate: e.target.checked })} 
                        />
                        Opslaan als herbruikbaar template
                      </label>
                      <small className="muted">Template kan later bij andere lots worden toegepast</small>
                    </div>
                    <div className="form-actions">
                      <button type="button" className="btn btn-secondary" onClick={() => { setShowAddSpecForm(false); setNewSpec(emptySpecForm); }}>Annuleren</button>
                      <button type="button" className="btn btn-primary" onClick={() => handleAddSpec(newSpec.parentId)} disabled={saving}>{saving ? 'Toevoegen...' : 'Toevoegen'}</button>
                    </div>
                  </div>
                )}

                {specTree.length > 0 ? (
                  <div className="specs-tree">
                    {specTree.map(spec => renderSpecRow(spec))}
                  </div>
                ) : !showAddSpecForm && (<p className="muted">Geen specificaties. Klik op &quot;+ Toevoegen&quot; om er een toe te voegen.</p>)}
              </fieldset>
            </div>
            <div className="modal-footer"><button className="btn btn-secondary" onClick={handleClose}>Sluiten</button></div>
          </>
        ) : null}
      </div>

      <style jsx>{`
        .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0, 0, 0, 0.6); display: flex; align-items: center; justify-content: center; z-index: 1000; }
        .modal { background: #1a1a2e; border-radius: 8px; min-width: 520px; max-width: 700px; max-height: 90vh; overflow-y: auto; box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3); color: #e0e0e0; }
        .modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; border-bottom: 1px solid #333; }
        .modal-header h2 { margin: 0; font-size: 1.25rem; color: #fff; }
        .btn-close { background: none; border: none; font-size: 1.5rem; color: #888; cursor: pointer; padding: 0; line-height: 1; }
        .btn-close:hover { color: #fff; }
        .modal-body { padding: 20px; }
        .lot-info-header { margin-bottom: 20px; padding-bottom: 16px; border-bottom: 1px solid #333; }
        .lot-info-header h3 { margin: 0 0 4px 0; color: #fff; }
        .form-fieldset { border: 1px solid #333; border-radius: 6px; padding: 16px; margin-bottom: 16px; background: transparent; }
        .form-fieldset legend { padding: 0 8px; font-weight: 600; color: #888; display: flex; align-items: center; gap: 12px; }
        .btn-add-small { font-size: 0.75rem; padding: 2px 8px; background: #6366f1; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
        .btn-add-small:hover:not(:disabled) { background: #5558e3; }
        .btn-add-small:disabled { opacity: 0.5; cursor: not-allowed; }
        .add-price-form, .add-subspec-form { background: #252540; border: 1px solid #444; border-radius: 6px; padding: 12px; margin-bottom: 12px; }
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .form-row { margin-bottom: 12px; }
        .form-row:last-child { margin-bottom: 0; }
        .form-row label { display: block; margin-bottom: 4px; font-size: 0.8rem; color: #888; }
        .form-row input, .form-row textarea, .form-row select { 
          width: 100%; 
          padding: 8px 12px; 
          border: 1px solid #444; 
          border-radius: 4px; 
          background: #1a1a2e; 
          color: #e0e0e0; 
          font-size: 0.9rem; 
        }
        .form-row input::placeholder, .form-row textarea::placeholder { color: #666; }
        .form-row input:focus, .form-row textarea:focus, .form-row select:focus { outline: none; border-color: #6366f1; }
        .form-row select option { background: #1a1a2e; color: #e0e0e0; }
        .form-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
        .prices-table { width: 100%; font-size: 0.875rem; border-collapse: collapse; }
        .prices-table th { text-align: left; padding: 6px 8px; font-weight: 500; color: #888; border-bottom: 1px solid #333; }
        .prices-table td { padding: 8px; border-bottom: 1px solid #2a2a40; }
        .price-cell { font-weight: 600; font-family: monospace; color: #4ade80; }
        .price-notes { margin-left: 6px; cursor: help; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 500; }
        .condition-new { background: #22c55e; color: #fff; }
        .condition-used { background: #f59e0b; color: #000; }
        .condition-refurbished { background: #3b82f6; color: #fff; }
        .btn-delete { background: none; border: none; cursor: pointer; padding: 4px; opacity: 0.6; font-size: 0.9rem; }
        .btn-delete:hover:not(:disabled) { opacity: 1; }
        .btn-delete:disabled { opacity: 0.3; cursor: not-allowed; }
        .specs-tree { }
        .spec-row { display: flex; align-items: center; padding: 8px; border-bottom: 1px solid #2a2a40; gap: 12px; }
        .spec-row.depth-0 { background: #252540; border-radius: 4px; margin-bottom: 4px; padding-left: 12px; }
        .spec-row.depth-1 { background: #1e1e35; font-size: 0.9em; padding-left: 36px; border-left: 2px solid #4a4a70; margin-left: 12px; }
        .spec-row.depth-2 { background: #1a1a30; font-size: 0.85em; padding-left: 60px; border-left: 2px solid #3a3a60; margin-left: 12px; }
        .spec-key { font-weight: 500; color: #a0a0c0; min-width: 120px; }
        .spec-value { flex: 1; color: #e0e0e0; }
        .spec-ean { font-size: 0.75rem; color: #888; background: #333; padding: 2px 6px; border-radius: 3px; }
        .spec-price { font-size: 0.8rem; color: #4ade80; font-weight: 600; font-family: monospace; }
        .spec-template { font-size: 0.75rem; opacity: 0.6; }
        .spec-actions { display: flex; gap: 4px; margin-left: auto; }
        .spec-children { }
        .btn-add-sub { background: #333; border: 1px solid #555; border-radius: 4px; color: #888; cursor: pointer; padding: 2px 8px; font-size: 0.8rem; }
        .btn-add-sub:hover:not(:disabled) { background: #444; color: #fff; border-color: #666; }
        .btn-add-sub:disabled { opacity: 0.3; cursor: not-allowed; }
        .template-selector { background: #252540; border: 1px solid #444; border-radius: 6px; padding: 12px; margin-bottom: 12px; }
        .template-tree { display: flex; flex-direction: column; gap: 4px; }
        .template-node { }
        .template-btn { 
          width: 100%;
          background: #1a1a2e; 
          border: 1px solid #444; 
          border-radius: 4px; 
          padding: 10px 12px; 
          color: #e0e0e0; 
          cursor: pointer; 
          display: flex; 
          align-items: center;
          gap: 12px; 
          text-align: left;
        }
        .template-btn:hover { background: #2a2a4e; border-color: #6366f1; }
        .template-btn.depth-1 { margin-left: 24px; background: #151528; }
        .template-btn.depth-2 { margin-left: 48px; background: #121225; }
        .template-btn.depth-3 { margin-left: 72px; background: #0f0f20; }
        .template-title { font-weight: 500; }
        .template-value { color: #a0a0c0; }
        .template-ean { font-size: 0.75rem; color: #888; }
        .template-price { font-size: 0.8rem; color: #4ade80; font-weight: 600; }
        .template-children-count { font-size: 0.7rem; color: #6366f1; background: #2a2a5e; padding: 2px 6px; border-radius: 3px; margin-left: auto; }
        .template-children { margin-top: 4px; }
        .modal-footer { display: flex; justify-content: flex-end; gap: 12px; padding: 16px 20px; border-top: 1px solid #333; }
        .btn { padding: 8px 16px; border-radius: 4px; font-size: 0.9rem; cursor: pointer; border: none; }
        .btn-sm { padding: 4px 12px; font-size: 0.8rem; }
        .btn-secondary { background: #333; color: #e0e0e0; }
        .btn-secondary:hover:not(:disabled) { background: #444; }
        .btn-primary { background: #6366f1; color: #fff; }
        .btn-primary:hover:not(:disabled) { background: #5558e3; }
        .btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .muted { color: #888; }
        .error { color: #ef4444; }
        a { color: #6366f1; text-decoration: none; }
        a:hover { text-decoration: underline; }
      `}</style>
    </div>
  );
}
