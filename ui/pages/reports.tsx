import { useState, useEffect } from 'react';
import Layout from '../components/Layout';

interface TrackedLotSummary {
  lot_code: string;
  title: string;
  state: string;
  current_bid_eur: number | null;
  max_budget_total_eur: number | null;
  track_active: boolean;
}

interface BuyerSummary {
  buyer_label: string;
  tracked_count: number;
  open_count: number;
  closed_count: number;
  open_exposure_min_eur: number;
  open_exposure_max_eur: number;
  open_tracked_lots: TrackedLotSummary[];
  won_lots: TrackedLotSummary[];
}

interface Buyer {
  id: number;
  label: string;
  name: string | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ReportsPage() {
  const [buyers, setBuyers] = useState<Buyer[]>([]);
  const [selectedBuyer, setSelectedBuyer] = useState<string>('');
  const [report, setReport] = useState<BuyerSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch buyers on mount
  useEffect(() => {
    fetch(`${API_BASE}/buyers`)
      .then((res) => res.json())
      .then((data) => {
        setBuyers(data);
        if (data.length > 0 && !selectedBuyer) {
          setSelectedBuyer(data[0].label);
        }
      })
      .catch((err) => setError(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch report when buyer changes
  useEffect(() => {
    if (!selectedBuyer) return;

    setLoading(true);
    setError(null);

    fetch(`${API_BASE}/reports/buyer/${encodeURIComponent(selectedBuyer)}`)
      .then((res) => {
        if (!res.ok) throw new Error('Failed to fetch report');
        return res.json();
      })
      .then((data) => {
        setReport(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [selectedBuyer]);

  const formatCurrency = (value: number | null | undefined) => {
    if (value == null) return '—';
    return `€${value.toLocaleString('nl-NL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <Layout>
      <div className="p-6">
        <h1 className="text-2xl font-bold mb-6">Buyer Rapport</h1>

        {/* Buyer Selection */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Selecteer Buyer
          </label>
          <select
            value={selectedBuyer}
            onChange={(e) => setSelectedBuyer(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 w-64"
          >
            <option value="">-- Kies buyer --</option>
            {buyers.map((buyer) => (
              <option key={buyer.id} value={buyer.label}>
                {buyer.label} {buyer.name && `(${buyer.name})`}
              </option>
            ))}
          </select>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {loading && <p className="text-gray-500">Laden...</p>}

        {report && !loading && (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="bg-white p-4 rounded-lg shadow border">
                <div className="text-sm text-gray-500">Gevolgde Posities</div>
                <div className="text-2xl font-bold">{report.tracked_count}</div>
              </div>
              <div className="bg-white p-4 rounded-lg shadow border">
                <div className="text-sm text-gray-500">Open Lots</div>
                <div className="text-2xl font-bold text-blue-600">{report.open_count}</div>
              </div>
              <div className="bg-white p-4 rounded-lg shadow border">
                <div className="text-sm text-gray-500">Gesloten Lots</div>
                <div className="text-2xl font-bold text-gray-600">{report.closed_count}</div>
              </div>
              <div className="bg-white p-4 rounded-lg shadow border">
                <div className="text-sm text-gray-500">Exposure (Open)</div>
                <div className="text-lg font-bold">
                  <span className="text-green-600">{formatCurrency(report.open_exposure_min_eur)}</span>
                  <span className="text-gray-400 mx-1">–</span>
                  <span className="text-red-600">{formatCurrency(report.open_exposure_max_eur)}</span>
                </div>
              </div>
            </div>

            {/* Open Tracked Lots */}
            {report.open_tracked_lots.length > 0 && (
              <div className="bg-white rounded-lg shadow border">
                <div className="px-4 py-3 border-b bg-blue-50">
                  <h2 className="font-semibold text-blue-800">Open Gevolgde Lots ({report.open_tracked_lots.length})</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Lot Code</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Titel</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                        <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Huidig Bod</th>
                        <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Max Budget</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {report.open_tracked_lots.map((lot) => (
                        <tr key={lot.lot_code} className={!lot.track_active ? 'opacity-50' : ''}>
                          <td className="px-4 py-2 text-sm font-mono">{lot.lot_code}</td>
                          <td className="px-4 py-2 text-sm truncate max-w-xs" title={lot.title}>{lot.title}</td>
                          <td className="px-4 py-2 text-sm">
                            <span className={`px-2 py-1 rounded text-xs ${
                              lot.state === 'running' ? 'bg-green-100 text-green-800' :
                              lot.state === 'scheduled' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-gray-100 text-gray-800'
                            }`}>
                              {lot.state}
                            </span>
                          </td>
                          <td className="px-4 py-2 text-sm text-right">{formatCurrency(lot.current_bid_eur)}</td>
                          <td className="px-4 py-2 text-sm text-right font-medium">
                            {lot.max_budget_total_eur != null ? formatCurrency(lot.max_budget_total_eur) : '(geen max)'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Won/Closed Lots */}
            {report.won_lots.length > 0 && (
              <div className="bg-white rounded-lg shadow border">
                <div className="px-4 py-3 border-b bg-gray-50">
                  <h2 className="font-semibold text-gray-800">Gesloten Lots ({report.won_lots.length})</h2>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Lot Code</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Titel</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                        <th className="px-4 py-2 text-right text-xs font-medium text-gray-500 uppercase">Eindprijs</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {report.won_lots.map((lot) => (
                        <tr key={lot.lot_code}>
                          <td className="px-4 py-2 text-sm font-mono">{lot.lot_code}</td>
                          <td className="px-4 py-2 text-sm truncate max-w-xs" title={lot.title}>{lot.title}</td>
                          <td className="px-4 py-2 text-sm">
                            <span className="px-2 py-1 rounded text-xs bg-gray-200 text-gray-700">
                              {lot.state}
                            </span>
                          </td>
                          <td className="px-4 py-2 text-sm text-right font-medium">{formatCurrency(lot.current_bid_eur)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {report.tracked_count === 0 && (
              <div className="text-center py-8 text-gray-500">
                Geen posities gevonden voor deze buyer.
              </div>
            )}
          </div>
        )}
      </div>
    </Layout>
  );
}
