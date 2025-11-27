import { useEffect, useState, useMemo } from 'react';
import Layout from '../components/Layout';
import LotTable, { SortField, SortDirection } from '../components/LotTable';
import type { LotView, SearchResult } from '../lib/api';
import { fetchLots, searchLots } from '../lib/api';

// Available filter options (hardcoded for now, could be fetched from API)
const STATE_OPTIONS = ['scheduled', 'running', 'closed'] as const;

export default function LotsPage() {
  const [stateFilter, setStateFilter] = useState<string | undefined>(undefined);
  const [auctionFilter, setAuctionFilter] = useState<string>('');
  const [brandFilter, setBrandFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [lots, setLots] = useState<LotView[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [selectedLots, setSelectedLots] = useState<Set<string>>(new Set());
  const [feedback, setFeedback] = useState<string>('');
  const [sortField, setSortField] = useState<SortField>('closing_time_current');
  const [sortDirection, setSortDirection] = useState<SortDirection>('asc');

  // Extract unique brands from lots for filter dropdown
  const availableBrands = Array.from(new Set(lots.map((lot) => lot.brand).filter((b): b is string => !!b))).sort();

  // Sort lots client-side
  const sortedLots = useMemo(() => {
    return [...lots].sort((a, b) => {
      let aVal: string | number | null = null;
      let bVal: string | number | null = null;

      switch (sortField) {
        case 'lot_code':
          aVal = a.title ?? a.lot_code;
          bVal = b.title ?? b.lot_code;
          break;
        case 'closing_time_current':
          aVal = a.closing_time_current ?? '';
          bVal = b.closing_time_current ?? '';
          break;
        case 'current_bid_eur':
          aVal = a.current_bid_eur ?? 0;
          bVal = b.current_bid_eur ?? 0;
          break;
        case 'bid_count':
          aVal = a.bid_count ?? 0;
          bVal = b.bid_count ?? 0;
          break;
        case 'state':
          aVal = a.state ?? '';
          bVal = b.state ?? '';
          break;
      }

      // Handle null/undefined
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return sortDirection === 'asc' ? 1 : -1;
      if (bVal == null) return sortDirection === 'asc' ? -1 : 1;

      // Compare
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }

      const strA = String(aVal).toLowerCase();
      const strB = String(bVal).toLowerCase();
      const cmp = strA.localeCompare(strB);
      return sortDirection === 'asc' ? cmp : -cmp;
    });
  }, [lots, sortField, sortDirection]);

  const handleSort = (field: SortField) => {
    if (field === sortField) {
      // Toggle direction
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // New field, default to ascending
      setSortField(field);
      setSortDirection('asc');
    }
  };

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

  const handleSearch = async (query: string) => {
    setSearchQuery(query);
    if (query.length < 2) {
      setSearchResults(null);
      return;
    }
    setLoading(true);
    try {
      const results = await searchLots(query, { state: stateFilter, limit: 100 });
      setSearchResults(results);
      setFeedback(`${results.length} zoekresultaten`);
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Zoeken mislukt';
      setFeedback(detail);
    } finally {
      setLoading(false);
    }
  };

  const clearSearch = () => {
    setSearchQuery('');
    setSearchResults(null);
  };

  return (
    <Layout title="Lots" subtitle="Filter en bekijk lots">
      {/* Search Bar */}
      <div className="panel" style={{ marginBottom: 18 }}>
        <div className="search-row">
          <input
            type="text"
            className="input search-input"
            placeholder="Zoeken op titel, merk, lot code of EAN..."
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
          />
          {searchQuery && (
            <button className="button" onClick={clearSearch}>✕ Wissen</button>
          )}
        </div>
      </div>

      {/* Search Results or Filters */}
      {searchResults !== null ? (
        <div className="panel" style={{ marginBottom: 18 }}>
          <h2 style={{ marginTop: 0 }}>Zoekresultaten ({searchResults.length})</h2>
          {searchResults.length === 0 ? (
            <p className="muted">Geen resultaten gevonden voor "{searchQuery}"</p>
          ) : (
            <div className="search-results">
              {searchResults.map((result) => (
                <a
                  key={`${result.auction_code}-${result.lot_code}`}
                  href={`/lots/${result.lot_code}?auction=${result.auction_code}`}
                  className="search-result-item"
                >
                  <div className="result-main">
                    <span className="result-code">{result.lot_code}</span>
                    <span className="result-title">{result.title || 'Geen titel'}</span>
                    {result.brand && <span className="result-brand">🏷️ {result.brand}</span>}
                  </div>
                  <div className="result-meta">
                    <span className={`result-state ${result.state}`}>{result.state}</span>
                    {result.current_bid_eur != null && (
                      <span className="result-price">€{result.current_bid_eur.toLocaleString('nl-NL', { minimumFractionDigits: 2 })}</span>
                    )}
                    <span className="result-match">match: {result.match_field}</span>
                  </div>
                </a>
              ))}
            </div>
          )}
          <style jsx>{`
            .search-results { display: flex; flex-direction: column; gap: 8px; }
            .search-result-item {
              display: flex;
              justify-content: space-between;
              align-items: center;
              padding: 12px 16px;
              background: #252540;
              border-radius: 6px;
              text-decoration: none;
              color: inherit;
              transition: background 0.2s;
            }
            .search-result-item:hover { background: #333355; }
            .result-main { display: flex; align-items: center; gap: 12px; flex: 1; }
            .result-code { font-family: monospace; color: #888; min-width: 100px; }
            .result-title { color: #fff; }
            .result-brand { font-size: 0.85rem; color: #a0a0c0; }
            .result-meta { display: flex; align-items: center; gap: 12px; }
            .result-state { font-size: 0.8rem; padding: 2px 8px; border-radius: 4px; background: #333; }
            .result-state.running { background: #166534; color: #4ade80; }
            .result-state.scheduled { background: #854d0e; color: #fbbf24; }
            .result-state.closed { background: #374151; color: #9ca3af; }
            .result-price { font-family: monospace; color: #4ade80; }
            .result-match { font-size: 0.75rem; color: #666; }
          `}</style>
        </div>
      ) : (
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
      )}

      {loading ? (
        <div className="panel">Laden…</div>
      ) : searchResults === null && (
        <LotTable 
          lots={sortedLots} 
          selectedLots={selectedLots} 
          onToggleLot={toggleLot} 
          onLotUpdated={refreshLots}
          sortField={sortField}
          sortDirection={sortDirection}
          onSort={handleSort}
        />
      )}

      <style jsx>{`
        .search-row {
          display: flex;
          gap: 12px;
          align-items: center;
        }
        .search-input {
          flex: 1;
          padding: 10px 14px;
          font-size: 1rem;
        }
      `}</style>
    </Layout>
  );
}
