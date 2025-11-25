import { useEffect, useMemo, useState } from 'react';
import Layout from '../components/Layout';
import LotTable from '../components/LotTable';
import { LotFilter, LotSummary, updateLotBatch, fetchFilters, fetchLots } from '../lib/api';

export default function LotsPage() {
  const [filters, setFilters] = useState<LotFilter[]>([]);
  const [activeFilters, setActiveFilters] = useState<Record<string, string | undefined>>({});
  const [lots, setLots] = useState<LotSummary[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedLots, setSelectedLots] = useState<Set<string>>(new Set());
  const [batchStatus, setBatchStatus] = useState<string>('ready');
  const [feedback, setFeedback] = useState<string>('');

  useEffect(() => {
    fetchFilters()
      .then(setFilters)
      .catch((error) => setFeedback(error instanceof Error ? error.message : 'Filters laden mislukt'));
  }, []);

  useEffect(() => {
    const run = async () => {
      setLoading(true);
      try {
        const data = await fetchLots(activeFilters);
        setLots(data);
      } catch (error) {
        const detail = error instanceof Error ? error.message : 'Lots laden mislukt';
        setFeedback(detail);
      } finally {
        setLoading(false);
      }
    };

    run();
  }, [activeFilters]);

  const toggleFilter = (name: string, value: string) => {
    setActiveFilters((current) => ({
      ...current,
      [name]: current[name] === value ? undefined : value
    }));
  };

  const toggleLot = (id: string) => {
    setSelectedLots((current) => {
      const next = new Set(current);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const runBatchUpdate = async () => {
    if (selectedLots.size === 0) {
      setFeedback('Selecteer eerst minimaal één lot.');
      return;
    }

    setFeedback('');
    try {
      const response = await updateLotBatch({
        lot_ids: Array.from(selectedLots),
        updates: { status: batchStatus }
      });
      setFeedback(`${response.updated} lots bijgewerkt naar status "${batchStatus}".`);
      const refreshed = await fetchLots(activeFilters);
      setLots(refreshed);
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Batch update mislukt';
      setFeedback(detail);
    }
  };

  const appliedFilters = useMemo(() =>
    filters.map((filter) => ({
      ...filter,
      selected: activeFilters[filter.name]
    })),
  [filters, activeFilters]);

  return (
    <Layout title="Lots" subtitle="Filter, selecteer en update batches">
      <div className="panel" style={{ marginBottom: 18 }}>
        <h2 style={{ marginTop: 0 }}>Filters</h2>
        <div className="controls">
          {appliedFilters.flatMap((filter) =>
            filter.values.map((value) => (
              <button
                key={`${filter.name}-${value}`}
                className={`button ${activeFilters[filter.name] === value ? 'primary' : ''}`}
                onClick={() => toggleFilter(filter.name, value)}
              >
                {filter.name}: {value}
              </button>
            ))
          )}
        </div>
        {feedback && <p className="muted" style={{ marginTop: 12 }}>{feedback}</p>}
      </div>

      <div className="panel" style={{ marginBottom: 18 }}>
        <div className="form-row">
          <div>
            <label>Nieuwe status voor batch</label>
            <input value={batchStatus} onChange={(event) => setBatchStatus(event.target.value)} />
          </div>
          <div>
            <label>&nbsp;</label>
            <button className="button primary" onClick={runBatchUpdate} disabled={loading}>
              Batch update
            </button>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="panel">Laden…</div>
      ) : (
        <LotTable lots={lots} selectedLots={selectedLots} onToggleLot={toggleLot} />
      )}
    </Layout>
  );
}
