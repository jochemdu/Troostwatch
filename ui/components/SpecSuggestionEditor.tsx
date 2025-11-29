import React, { useState, useEffect } from "react";
import { saveSpecsToLot, fetchSpecTemplates } from '../lib/api';
import { SpecTemplate } from '../lib/api';

interface SpecSuggestionEditorProps {
  labels: any[];
  lotSpecs: any[];
  lotCode: string;
  auctionCode: string;
  onApply: () => void;
}

export default function SpecSuggestionEditor({ labels, lotSpecs, lotCode, auctionCode, onApply }: SpecSuggestionEditorProps) {
  // Combine all label fields into editable spec suggestions
  const initialSpecs = labels.flatMap(label =>
    Object.entries(label).filter(([key]) => key !== 'vendor').map(([key, value]) => ({ key, value: String(value) }))
  );
  const [specs, setSpecs] = useState(initialSpecs);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [templates, setTemplates] = useState<SpecTemplate[]>([]);

  useEffect(() => {
    function handleTemplatesUpdated() {
      fetchSpecTemplates().then(setTemplates).catch(() => setTemplates([]));
    }
    window.addEventListener('specTemplatesUpdated', handleTemplatesUpdated);
    return () => window.removeEventListener('specTemplatesUpdated', handleTemplatesUpdated);
  }, []);

  const handleChange = (idx: number, newValue: string) => {
    setSpecs(specs => specs.map((spec, i) => i === idx ? { ...spec, value: newValue } : spec));
  };

  // Extra validatie: check of spec key in templates voorkomt
  function validateSpec(key: string, value: string): string | null {
    const template = templates.find(t => t.title === key);
    if (!template) return 'Onbekende spec (geen template)';
    if (key === 'ean' && value && !/^\d{8,13}$/.test(value)) return 'Ongeldige EAN';
    if (key === 'price_eur' && value && isNaN(Number(value))) return 'Geen geldig bedrag';
    if (key === 'release_date' && value && !/^\d{4}-\d{2}-\d{2}$/.test(value)) return 'Gebruik formaat YYYY-MM-DD';
    return null;
  }

  // Fallback: onbekende specs worden niet opgeslagen
  const handleApply = async () => {
    setLoading(true);
    setError(null);
    try {
      const mappedSpecs = specs
        .map(s => ({
          ...s,
          ...mapSpecMeta(s.key),
          ean: s.key === 'ean' ? s.value : undefined,
          price_eur: s.key === 'price_eur' ? Number(s.value) : undefined,
          release_date: s.key === 'release_date' ? s.value : undefined,
          category: s.key === 'category' ? s.value : undefined,
        }))
        .filter(s => templates.some(t => t.title === s.key)); // alleen bekende specs
      await saveSpecsToLot(lotCode, mappedSpecs, auctionCode);
      onApply();
    } catch (err: any) {
      setError(err.message || 'Opslaan mislukt');
    } finally {
      setLoading(false);
    }
  };

  // Spec keys die als EAN, prijs, datum, categorie, etc. gelden
  const keyTypes: Record<string, string> = {
    ean: 'EAN',
    price_eur: 'Prijs (EUR)',
    release_date: 'Release datum',
    category: 'Categorie',
    product_code: 'Productcode',
    serial_number: 'Serienummer',
    model_number: 'Modelnummer',
  };

  // Mapping naar templates en parent_id
  function mapSpecMeta(key: string): { template_id?: number, parent_id?: number } {
    // Dynamisch: zoek template op basis van key
    const template = templates.find(t => t.title === key);
    if (template) return { template_id: template.id, parent_id: template.parent_id ?? undefined };
    return {};
  }

  return (
    <div style={{ marginTop: 12 }}>
      <strong>Voorgestelde specs:</strong>
      <div>
        {specs.map((spec, idx) => {
          const typeLabel = keyTypes[spec.key] || spec.key;
          const errorMsg = validateSpec(spec.key, spec.value);
          return (
            <div key={spec.key} style={{ marginBottom: 6 }}>
              <span style={{ fontWeight: 'bold', marginRight: 8 }}>{typeLabel}:</span>
              <input
                type="text"
                value={spec.value}
                onChange={e => handleChange(idx, e.target.value)}
                style={{ padding: '2px 8px', borderRadius: 4, border: errorMsg ? '1px solid #d32f2f' : '#ccc', minWidth: 80 }}
              />
              {errorMsg && <span style={{ color: '#d32f2f', marginLeft: 8 }}>{errorMsg}</span>}
            </div>
          );
        })}
      </div>
      <div style={{ marginTop: 18 }}>
        {specs.filter(s => !templates.some(t => t.title === s.key)).length > 0 && (
          <div style={{ color: '#d32f2f', marginBottom: 8 }}>
            <strong>Uitgesloten specs:</strong>
            <ul>
              {specs.filter(s => !templates.some(t => t.title === s.key)).map(s => (
                <li key={s.key}>{s.key}: {s.value}</li>
              ))}
            </ul>
            <span style={{ fontSize: '0.95em', color: '#888' }}>Deze specs hebben geen template en worden niet opgeslagen.</span>
          </div>
        )}
      </div>
      <button
        onClick={handleApply}
        disabled={loading || specs.some(s => validateSpec(s.key, s.value))}
        style={{ marginTop: 10, background: '#388e3c', color: '#fff', padding: '6px 16px', border: 'none', borderRadius: 4, cursor: 'pointer' }}
      >
        {loading ? 'Toepassen...' : 'Apply'}
      </button>
      {error && <div style={{ color: 'red', marginTop: 8 }}>{error}</div>}
    </div>
  );
}
