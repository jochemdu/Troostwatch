import { useState, useEffect, useRef } from 'react';
import Layout from '../components/Layout';
import { triggerSync } from '../lib/api';
import { createLotSocket, LotEvent } from '../lib/ws';
import type { SyncSummaryResponse } from '../lib/generated';

interface LogEntry {
  timestamp: string;
  type: 'info' | 'event' | 'error' | 'success';
  message: string;
}

export default function SyncPage() {
  const [auctionCode, setAuctionCode] = useState<string>('');
  const [auctionUrl, setAuctionUrl] = useState<string>('');
  const [maxPages, setMaxPages] = useState<string>('');
  const [dryRun, setDryRun] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<SyncSummaryResponse | null>(null);
  const [error, setError] = useState<string>('');
  
  // Debug console state
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [wsStatus, setWsStatus] = useState<string>('disconnected');
  const logContainerRef = useRef<HTMLDivElement>(null);
  const socketRef = useRef<WebSocket | null>(null);

  const addLog = (type: LogEntry['type'], message: string) => {
    const timestamp = new Date().toLocaleTimeString('nl-NL', { hour12: false });
    setLogs(prev => [...prev.slice(-99), { timestamp, type, message }]);
  };

  // Connect to WebSocket on mount
  useEffect(() => {
    const socket = createLotSocket(
      (event: LotEvent) => {
        if (event.type === 'lot_update') {
          addLog('event', `Lot bijgewerkt: ${event.lot_code} - €${event.data?.current_bid_eur || 0}`);
        } else if (event.type === 'lot_created') {
          addLog('info', `Nieuw lot: ${event.lot_code}`);
        } else if (event.type === 'lot_closed') {
          addLog('success', `Lot gesloten: ${event.lot_code}`);
        } else {
          addLog('event', `Event: ${event.type}`);
        }
      },
      (status) => {
        setWsStatus(status);
        if (status === 'open') {
          addLog('info', 'WebSocket verbonden');
        } else if (status === 'closed') {
          addLog('info', 'WebSocket verbinding gesloten');
        } else if (status === 'error') {
          addLog('error', 'WebSocket fout');
        }
      }
    );
    socketRef.current = socket;

    return () => {
      socket.close();
    };
  }, []);

  // Auto-scroll logs
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  // Try to extract auction code from URL
  const handleUrlChange = (url: string) => {
    setAuctionUrl(url);
    // Extract auction code from Troostwijk URL pattern
    // The code is the last segment, e.g.:
    // /a/goederen-opgekocht-uit-faillissement-max-ict-(2-2)-A1-39500 → A1-39500
    // /nl/c/ABC123 → ABC123
    const pathMatch = url.match(/\/[ac]\/([A-Za-z0-9()_-]+)/);
    if (pathMatch) {
      const fullPath = pathMatch[1];
      // The auction code is typically at the end: look for pattern like A1-39500, ABC-123
      // Match the last segment that looks like an auction code (letters + hyphen + digits)
      const codeMatch = fullPath.match(/([A-Z]+\d*-\d+)$/i);
      const extractedCode = codeMatch ? codeMatch[1] : fullPath;
      setAuctionCode(extractedCode);
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
    addLog('info', `Start sync voor ${auctionCode}...`);

    try {
      const response = await triggerSync({
        auction_code: auctionCode,
        auction_url: auctionUrl,
        max_pages: maxPages ? parseInt(maxPages, 10) : undefined,
        dry_run: dryRun,
      });
      setResult(response);
      if (response.status === 'success' && response.result) {
        addLog('success', `Sync voltooid: ${response.result.lots_updated} lots bijgewerkt, ${response.result.pages_scanned} pagina's gescand`);
      } else if (response.error) {
        addLog('error', `Sync fout: ${response.error}`);
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Sync mislukt';
      setError(errorMsg);
      addLog('error', errorMsg);
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

      {/* Debug Console */}
      <div className="panel" style={{ marginTop: '18px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h2 style={{ margin: 0 }}>Debug Console</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ 
              display: 'inline-flex', 
              alignItems: 'center', 
              gap: '6px',
              fontSize: '12px',
              color: wsStatus === 'open' ? '#080' : wsStatus === 'error' ? '#c00' : '#666'
            }}>
              <span style={{ 
                width: '8px', 
                height: '8px', 
                borderRadius: '50%', 
                background: wsStatus === 'open' ? '#0c0' : wsStatus === 'error' ? '#c00' : '#999'
              }} />
              {wsStatus === 'open' ? 'Verbonden' : wsStatus === 'connecting' ? 'Verbinden...' : 'Niet verbonden'}
            </span>
            <button 
              className="button" 
              onClick={() => setLogs([])}
              style={{ padding: '4px 8px', fontSize: '12px' }}
            >
              Wissen
            </button>
          </div>
        </div>
        
        <div 
          ref={logContainerRef}
          style={{ 
            background: '#1a1a2e', 
            color: '#eee', 
            padding: '12px', 
            borderRadius: '4px',
            fontFamily: 'monospace',
            fontSize: '13px',
            height: '200px',
            overflowY: 'auto',
          }}
        >
          {logs.length === 0 ? (
            <div style={{ color: '#666' }}>Wachten op events...</div>
          ) : (
            logs.map((log, i) => (
              <div key={i} style={{ marginBottom: '4px' }}>
                <span style={{ color: '#666' }}>[{log.timestamp}]</span>{' '}
                <span style={{ 
                  color: log.type === 'error' ? '#f66' : 
                         log.type === 'success' ? '#6f6' : 
                         log.type === 'event' ? '#6cf' : '#aaa'
                }}>
                  {log.message}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </Layout>
  );
}
