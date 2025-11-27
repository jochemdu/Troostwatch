import { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import LotTable from '../components/LotTable';
import type { LotView } from '../lib/api';
import { fetchLots } from '../lib/api';

// Available filter options (hardcoded for now, could be fetched from API)
const STATE_OPTIONS = ['scheduled', 'running', 'closed'] as const;

export default function LotsPage() {
  const [stateFilter, setStateFilter] = useState<string | undefined>(undefined);
  const [auctionFilter, setAuctionFilter] = useState<string>('');
  const [brandFilter, setBrandFilter] = useState<string>('');
  const [lots, setLots] = useState<LotView[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedLots, setSelectedLots] = useState<Set<string>>(new Set());
  const [feedback, setFeedback] = useState<string>('');

  // Extract unique brands from lots for filter dropdown
  const availableBrands = Array.from(new Set(lots.map((lot) => lot.brand).filter((b): b is string => !!b))).sort();

  useEffect(() => {
    const run = async () => {
      setLoading(true);
      try {
        const data = await fetchLots({
          state: stateFilter,
          auction_code: auctionFilter || undefined,
          brand: brandFilter || undefined,
        });
        setLots(data);
      } catch (error) {
        const detail = error instanceof Error ? error.message : 'Lots laden mislukt';
        setFeedback(detail);
      } finally {
        setLoading(false);
      }
    };

    run();
  }, [stateFilter, auctionFilter, brandFilter]);

  const toggleLot = (lotCode: string) => {
    setSelectedLots((current) => {
      const next = new Set(current);
      if (next.has(lotCode)) {
        next.delete(lotCode);
      } else {
        next.add(lotCode);
      }
      return next;
    });
  };

  const refreshLots = async () => {
    setLoading(true);
    try {
      const data = await fetchLots({
        state: stateFilter,
        auction_code: auctionFilter || undefined,
        brand: brandFilter || undefined,
      });
      setLots(data);
      setFeedback(`${data.length} lots geladen.`);
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Lots laden mislukt';
      setFeedback(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout title="Lots" subtitle="Filter en bekijk lots">
      <div className="panel" style={{ marginBottom: 18 }}>
        <h2 style={{ marginTop: 0 }}>Filters</h2>
        <div className="form-row">
          <div>
            <label>Status</label>
            <div className="controls">
              <button
                className={`button ${stateFilter === undefined ? 'primary' : ''}`}
                onClick={() => setStateFilter(undefined)}
              >
                Alle
              </button>
              {STATE_OPTIONS.map((state) => (
                <button
                  key={state}
                  className={`button ${stateFilter === state ? 'primary' : ''}`}
                  onClick={() => setStateFilter(state)}
                >
                  {state}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label>Veiling code</label>
            <input
              value={auctionFilter}
              onChange={(event) => setAuctionFilter(event.target.value)}
              placeholder="bijv. ABC123"
            />
          </div>
          <div>
            <label>Merk</label>
            <input
              value={brandFilter}
              onChange={(event) => setBrandFilter(event.target.value)}
              placeholder="bijv. Caterpillar"
              list="brand-options"
            />
            <datalist id="brand-options">
              {availableBrands.map((brand) => (
                <option key={brand} value={brand} />
              ))}
            </datalist>
          </div>
          <div>
            <label>&nbsp;</label>
            <button className="button" onClick={refreshLots} disabled={loading}>
              Ververs
            </button>
          </div>
        </div>
        {feedback && <p className="muted" style={{ marginTop: 12 }}>{feedback}</p>}
      </div>

      {loading ? (
        <div className="panel">Laden…</div>
      ) : (
        <LotTable lots={lots} selectedLots={selectedLots} onToggleLot={toggleLot} />
      )}
    </Layout>
  );
}
