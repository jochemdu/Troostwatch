import { useEffect, useMemo, useState } from 'react';
import Layout from '../components/Layout';
import type { LotView } from '../lib/api';
import { fetchLots, getLiveSyncStatus, startLiveSync, pauseLiveSync, stopLiveSync } from '../lib/api';
import type { LotEvent } from '../lib/ws';
import { createLotSocket } from '../lib/ws';

/**
 * Extended lot with live WebSocket updates.
 */
type LiveLot = LotView & {
  ws_current_bid?: number;
  ws_ends_at?: string;
};

const formatCountdown = (target?: string) => {
  if (!target) return '—';
  const delta = new Date(target).getTime() - Date.now();
  if (Number.isNaN(delta)) return '—';
  if (delta <= 0) return 'Afgelopen';
  
  const totalSeconds = Math.floor(delta / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  
  const pad = (n: number) => n.toString().padStart(2, '0');
  
  if (days > 0) {
    return `${days}d ${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
  }
  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
};

export default function LivePage() {
  const [connection, setConnection] = useState<'connecting' | 'open' | 'closed' | 'error'>('connecting');
  const [events, setEvents] = useState<LotEvent[]>([]);
  const [lots, setLots] = useState<Record<string, LiveLot>>({});
  const [refreshing, setRefreshing] = useState(false);
  const [syncStatus, setSyncStatus] = useState<string>('unknown');
  const [, setTick] = useState(0); // Force re-render for countdown updates

  // Update countdown every second
  useEffect(() => {
    const interval = setInterval(() => {
      setTick(t => t + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    fetchLots()
      .then((list) =>
        setLots(
          list.reduce<Record<string, LiveLot>>((memo, lot) => {
            memo[lot.lot_code] = lot;
            return memo;
          }, {})
        )
      )
      .catch(() => setConnection('error'));

    getLiveSyncStatus()
      .then((status) => setSyncStatus(status.state ?? 'unknown'))
      .catch(() => setSyncStatus('error'));
  }, []);

  useEffect(() => {
    const socket = createLotSocket(
      (event) => {
        setEvents((current) => [event, ...current].slice(0, 50));
        setLots((current) => ({
          ...current,
          [event.lot_code]: {
            ...current[event.lot_code],
            lot_code: event.lot_code,
            auction_code: event.auction_code,
            ...event.data,
          }
        }));
      },
      setConnection
    );

    return () => socket.close();
  }, []);

  const liveLots = useMemo(() => Object.values(lots), [lots]);

  const reloadLots = async () => {
    setRefreshing(true);
    try {
      const fresh = await fetchLots();
      setLots(
        fresh.reduce<Record<string, LiveLot>>((memo, lot) => {
          memo[lot.lot_code] = { ...lots[lot.lot_code], ...lot };
          return memo;
        }, {})
      );
    } finally {
      setRefreshing(false);
    }
  };

  const handleSyncControl = async (action: 'start' | 'pause' | 'stop') => {
    try {
      if (action === 'start') {
        await startLiveSync({ auction_url: '', auction_code: 'DEMO', dry_run: false });
        setSyncStatus('running');
      } else if (action === 'pause') {
        await pauseLiveSync();
        setSyncStatus('paused');
      } else {
        await stopLiveSync();
        setSyncStatus('stopped');
      }
    } catch (error) {
      setSyncStatus('error');
    }
  };

  return (
    <Layout title="Live volgen" subtitle="WebSocket events en timers">
      <div className="panel" style={{ marginBottom: 18 }}>
        <div className="status-row" style={{ justifyContent: 'space-between' }}>
          <div className="status-row" style={{ gap: 8 }}>
            <span className={`badge ${connection === 'error' ? 'error' : ''}`}>WS: {connection}</span>
            <span className={`badge ${syncStatus === 'error' ? 'error' : ''}`}>Sync: {syncStatus}</span>
            <button className="button" onClick={reloadLots} disabled={refreshing}>
              Herlaad lijst
            </button>
          </div>
          <div className="controls" style={{ gap: 4 }}>
            <button className="button primary" onClick={() => handleSyncControl('start')}>Start</button>
            <button className="button" onClick={() => handleSyncControl('pause')}>Pauze</button>
            <button className="button danger" onClick={() => handleSyncControl('stop')}>Stop</button>
          </div>
        </div>
      </div>

      <div className="live-grid" style={{ marginBottom: 18 }}>
        {liveLots.map((lot) => (
          <div key={lot.lot_code} className="live-card">
            <div className="status-row" style={{ justifyContent: 'space-between' }}>
              <div>
                <strong>{lot.title ?? lot.lot_code}</strong>
                <p className="muted" style={{ margin: '4px 0' }}>
                  Lot {lot.lot_code} • {lot.auction_code}
                </p>
              </div>
              <span className={`badge ${lot.state === 'closed' ? 'error' : ''}`}>{lot.state ?? '—'}</span>
            </div>
            <div className="status-row" style={{ justifyContent: 'space-between', marginTop: 6 }}>
              <div>
                <span>€{lot.current_bid_eur?.toLocaleString('nl-NL') ?? '—'}</span>
                <span className="muted" style={{ marginLeft: 8 }}>
                  ({lot.bid_count ?? 0} biedingen)
                </span>
              </div>
              <span className="badge warning">{formatCountdown(lot.closing_time_current ?? undefined)}</span>
            </div>
          </div>
        ))}
        {liveLots.length === 0 && <p className="muted">Nog geen lots geladen.</p>}
      </div>

      <div className="panel">
        <h3>Live event feed ({events.length})</h3>
        <div className="debug-log">
          {events.map((event, index) => (
            <div key={`${event.lot_code}-${index}`} style={{ marginBottom: 6 }}>
              <strong>{event.lot_code}</strong> ({event.auction_code}) – {event.type}
              <span className="muted" style={{ marginLeft: 6 }}>{event.timestamp}</span>
            </div>
          ))}
          {events.length === 0 && <div className="muted">Nog geen events ontvangen.</div>}
        </div>
      </div>
    </Layout>
  );
}
