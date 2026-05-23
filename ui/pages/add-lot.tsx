import { useState, useEffect, FormEvent } from 'react';
import Layout from '../components/Layout';
import ExampleLotEventConsumer from '../components/ExampleLotEventConsumer';

interface Auction {
  auction_code: string;
  title: string | null;
  url: string | null;
  active_lots: number;
  lot_count: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function AddLotPage() {
  const [auctions, setAuctions] = useState<Auction[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Form state
  const [auctionCode, setAuctionCode] = useState('');
  const [auctionTitle, setAuctionTitle] = useState('');
  const [auctionUrl, setAuctionUrl] = useState('');
  const [lotCode, setLotCode] = useState('');
  const [title, setTitle] = useState('');
  const [lotUrl, setLotUrl] = useState('');
  const [state, setState] = useState('');
  const [opensAt, setOpensAt] = useState('');
  const [closingTime, setClosingTime] = useState('');
  const [bidCount, setBidCount] = useState('');
  const [openingBid, setOpeningBid] = useState('');
  const [currentBid, setCurrentBid] = useState('');
  const [city, setCity] = useState('');
  const [country, setCountry] = useState('');

  // Fetch auctions for suggestions
  useEffect(() => {
    fetch(`${API_BASE}/auctions?include_inactive=true`)
      .then((res) => res.json())
      .then((data) => setAuctions(data))
      .catch(() => { /* ignore */ });
  }, []);

  const handleAuctionSelect = (code: string) => {
    setAuctionCode(code);
    const auction = auctions.find((a) => a.auction_code === code);
    if (auction) {
      if (auction.title) setAuctionTitle(auction.title);
      if (auction.url) setAuctionUrl(auction.url);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    const payload = {
      auction_code: auctionCode,
      lot_code: lotCode,
      title,
      url: lotUrl || undefined,
      state: state || undefined,
      opens_at: opensAt || undefined,
      closing_time: closingTime || undefined,
      bid_count: bidCount ? parseInt(bidCount, 10) : undefined,
      opening_bid_eur: openingBid ? parseFloat(openingBid) : undefined,
      current_bid_eur: currentBid ? parseFloat(currentBid) : undefined,
      location_city: city || undefined,
      location_country: country || undefined,
      auction_title: auctionTitle || undefined,
      auction_url: auctionUrl || undefined,
    };

    try {
      const res = await fetch(`${API_BASE}/lots`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to add lot');
      }

      const result = await res.json();
      setSuccess(`Lot ${result.lot_code} succesvol toegevoegd aan ${result.auction_code}`);
      
      // Reset form
      setLotCode('');
      setTitle('');
      setLotUrl('');
      setState('');
      setOpensAt('');
      setClosingTime('');
      setBidCount('');
      setOpeningBid('');
      setCurrentBid('');
      setCity('');
      setCountry('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      <div className="p-6 max-w-3xl">
        <h1 className="text-2xl font-bold mb-6">Lot Toevoegen</h1>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {success && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
            {success}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Auction Section */}
          <div className="bg-white p-4 rounded-lg shadow border">
            <h2 className="font-semibold text-gray-800 mb-4">Veiling Informatie</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Veiling Code *
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={auctionCode}
                    onChange={(e) => setAuctionCode(e.target.value)}
                    placeholder="bijv. A1-39500"
                    required
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md"
                  />
                  {auctions.length > 0 && (
                    <select
                      onChange={(e) => handleAuctionSelect(e.target.value)}
                      className="px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                      value=""
                    >
                      <option value="">Kies...</option>
                      {auctions.map((a) => (
                        <option key={a.auction_code} value={a.auction_code}>
                          {a.auction_code} {a.title && `- ${a.title.slice(0, 30)}`}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Veiling Titel
                </label>
                <input
                  type="text"
                  value={auctionTitle}
                  onChange={(e) => setAuctionTitle(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Veiling URL
                </label>
                <input
                  type="url"
                  value={auctionUrl}
                  onChange={(e) => setAuctionUrl(e.target.value)}
                  placeholder="https://www.troostwijkauctions.com/nl/..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
            </div>
          </div>

          {/* Lot Section */}
          <div className="bg-white p-4 rounded-lg shadow border">
            <h2 className="font-semibold text-gray-800 mb-4">Lot Informatie</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Lot Code *
                </label>
                <input
                  type="text"
                  value={lotCode}
                  onChange={(e) => setLotCode(e.target.value)}
                  placeholder="bijv. A1-39500-1"
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Titel *
                </label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Beschrijving van het lot"
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Lot URL
                </label>
                <input
                  type="url"
                  value={lotUrl}
                  onChange={(e) => setLotUrl(e.target.value)}
                  placeholder="https://www.troostwijkauctions.com/nl/l/..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Status
                </label>
                <select
                  value={state}
                  onChange={(e) => setState(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  <option value="">-- Kies status --</option>
                  <option value="scheduled">Scheduled</option>
                  <option value="running">Running</option>
                  <option value="closed">Closed</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Aantal Biedingen
                </label>
                <input
                  type="number"
                  min="0"
                  value={bidCount}
                  onChange={(e) => setBidCount(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
            </div>
          </div>

          {/* Timing Section */}
          <div className="bg-white p-4 rounded-lg shadow border">
            <h2 className="font-semibold text-gray-800 mb-4">Timing</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Opens At (ISO)
                </label>
                <input
                  type="datetime-local"
                  value={opensAt}
                  onChange={(e) => setOpensAt(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Sluitingstijd (ISO)
                </label>
                <input
                  type="datetime-local"
                  value={closingTime}
                  onChange={(e) => setClosingTime(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
            </div>
          </div>

          {/* Pricing Section */}
          <div className="bg-white p-4 rounded-lg shadow border">
            <h2 className="font-semibold text-gray-800 mb-4">Prijzen (EUR)</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Openingsbod
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={openingBid}
                  onChange={(e) => setOpeningBid(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Huidig Bod
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={currentBid}
                  onChange={(e) => setCurrentBid(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
            </div>
          </div>

          {/* Location Section */}
          <div className="bg-white p-4 rounded-lg shadow border">
            <h2 className="font-semibold text-gray-800 mb-4">Locatie</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Stad
                </label>
                <input
                  type="text"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Land
                </label>
                <input
                  type="text"
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
            </div>
          </div>

          {/* Submit Button */}
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Bezig...' : 'Lot Toevoegen'}
            </button>
          </div>
        </form>

        <ExampleLotEventConsumer />
      </div>
    </Layout>
  );
}
