import { useState } from 'react';
import Layout from '../components/Layout';
import { triggerSync } from '../lib/api';
import type { SyncSummaryResponse } from '../lib/generated';

export default function SyncPage() {
  const [auctionCode, setAuctionCode] = useState<string>('');
  const [auctionUrl, setAuctionUrl] = useState<string>('');
  const [maxPages, setMaxPages] = useState<string>('');
  const [dryRun, setDryRun] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<SyncSummaryResponse | null>(null);
  const [error, setError] = useState<string>('');

  // Try to extract auction code from URL
  const handleUrlChange = (url: string) => {
    setAuctionUrl(url);
    // Extract auction code from Troostwijk URL pattern
    // e.g., https://www.troostwijkauctions.com/nl/c/ABC123 or /a/ABC123
    const match = url.match(/\/[ac]\/([A-Za-z0-9-]+)/);
    if (match && !auctionCode) {
      setAuctionCode(match[1]);
    }
  };

  const handleSync = async () => {
    if (!auctionCode || !auctionUrl) {
      setError('Vul zowel veilingcode als URL in.');
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    try {
      const response = await triggerSync({
        auction_code: auctionCode,
        auction_url: auctionUrl,
        max_pages: maxPages ? parseInt(maxPages, 10) : undefined,
        dry_run: dryRun,
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sync mislukt');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout title="Veiling Importeren" subtitle="Synchroniseer een veiling naar de database">
      <div className="panel">
        <h2 style={{ marginTop: 0 }}>Veiling Gegevens</h2>
        
        <div className="form-row">
          <div style={{ flex: 2 }}>
            <label>Veiling URL</label>
            <input
              type="url"
              value={auctionUrl}
              onChange={(e) => handleUrlChange(e.target.value)}
              placeholder="https://www.troostwijkauctions.com/nl/c/ABC123"
              style={{ width: '100%' }}
            />
            <small className="muted">Plak de volledige URL van de veilingpagina</small>
          </div>
        </div>

        <div className="form-row">
          <div>
            <label>Veilingcode</label>
            <input
              type="text"
              value={auctionCode}
              onChange={(e) => setAuctionCode(e.target.value)}
              placeholder="ABC123"
            />
            <small className="muted">Wordt automatisch uit URL gehaald</small>
          </div>
          <div>
            <label>Max pagina's (optioneel)</label>
            <input
              type="number"
              value={maxPages}
              onChange={(e) => setMaxPages(e.target.value)}
              placeholder="Alle"
              min="1"
            />
            <small className="muted">Laat leeg voor alle pagina's</small>
          </div>
        </div>

        <div className="form-row">
          <div>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <input
                type="checkbox"
                checked={dryRun}
                onChange={(e) => setDryRun(e.target.checked)}
              />
              Dry run (alleen lezen, niet opslaan)
            </label>
          </div>
        </div>

        <div className="form-row" style={{ marginTop: '16px' }}>
          <button 
            className="button primary" 
            onClick={handleSync} 
            disabled={loading || !auctionCode || !auctionUrl}
          >
            {loading ? 'Bezig met importeren...' : 'Importeer Veiling'}
          </button>
        </div>

        {error && (
          <div style={{ marginTop: '16px', padding: '12px', background: '#fee', borderRadius: '4px', color: '#c00' }}>
            {error}
          </div>
        )}
      </div>

      {result && (
        <div className="panel" style={{ marginTop: '18px' }}>
          <h2 style={{ marginTop: 0 }}>Resultaat</h2>
          
          <div style={{ 
            padding: '12px', 
            background: result.status === 'success' ? '#efe' : '#fee', 
            borderRadius: '4px',
            marginBottom: '16px'
          }}>
            <strong>Status:</strong> {result.status === 'success' ? '✅ Geslaagd' : '❌ ' + result.status}
          </div>

          {result.result && (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <tbody>
                <tr>
                  <td style={{ padding: '8px', borderBottom: '1px solid #eee' }}>Pagina's gescand</td>
                  <td style={{ padding: '8px', borderBottom: '1px solid #eee', textAlign: 'right' }}>
                    <strong>{result.result.pages_scanned}</strong>
                  </td>
                </tr>
                <tr>
                  <td style={{ padding: '8px', borderBottom: '1px solid #eee' }}>Lots gevonden</td>
                  <td style={{ padding: '8px', borderBottom: '1px solid #eee', textAlign: 'right' }}>
                    <strong>{result.result.lots_scanned}</strong>
                  </td>
                </tr>
                <tr>
                  <td style={{ padding: '8px', borderBottom: '1px solid #eee' }}>Lots bijgewerkt</td>
                  <td style={{ padding: '8px', borderBottom: '1px solid #eee', textAlign: 'right' }}>
                    <strong>{result.result.lots_updated}</strong>
                  </td>
                </tr>
                {result.result.error_count > 0 && (
                  <tr>
                    <td style={{ padding: '8px', borderBottom: '1px solid #eee', color: '#c00' }}>Fouten</td>
                    <td style={{ padding: '8px', borderBottom: '1px solid #eee', textAlign: 'right', color: '#c00' }}>
                      <strong>{result.result.error_count}</strong>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}

          {result.error && (
            <div style={{ marginTop: '12px', padding: '12px', background: '#fee', borderRadius: '4px', color: '#c00' }}>
              {result.error}
            </div>
          )}
        </div>
      )}
    </Layout>
  );
}
