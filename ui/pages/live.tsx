import { useEffect, useMemo, useState } from 'react';
import Layout from '../components/Layout';
import { LotSummary, fetchLots } from '../lib/api';
import { LotEvent, createLotSocket } from '../lib/ws';

type LiveLot = LotSummary & {
  current_bid?: number;
  started_at?: string;
  ends_at?: string;
};

const formatCountdown = (target?: string) => {
  if (!target) return '—';
  const delta = new Date(target).getTime() - Date.now();
  if (Number.isNaN(delta)) return '—';
  if (delta <= 0) return '00:00';
  const seconds = Math.floor(delta / 1000);
  const minutes = Math.floor(seconds / 60)
    .toString()
    .padStart(2, '0');
  const remainder = (seconds % 60).toString().padStart(2, '0');
  return `${minutes}:${remainder}`;
};

export default function LivePage() {
  const [connection, setConnection] = useState<'connecting' | 'open' | 'closed' | 'error'>('connecting');
  const [events, setEvents] = useState<LotEvent[]>([]);
  const [lots, setLots] = useState<Record<string, LiveLot>>({});
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchLots()
      .then((list) =>
        setLots(
          list.reduce<Record<string, LiveLot>>((memo, lot) => {
            memo[lot.id] = lot;
            return memo;
          }, {})
        )
      )
      .catch(() => setConnection('error'));
  }, []);

  useEffect(() => {
    const socket = createLotSocket(
      (event) => {
        setEvents((current) => [event, ...current].slice(0, 50));
        setLots((current) => ({
          ...current,
          [event.id]: {
            ...current[event.id],
            id: event.id,
            status: event.status,
            buyer: event.buyer ?? current[event.id]?.buyer,
            current_bid: event.current_bid ?? current[event.id]?.current_bid,
            started_at: event.started_at ?? current[event.id]?.started_at,
            ends_at: event.ends_at ?? current[event.id]?.ends_at
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
          memo[lot.id] = { ...lots[lot.id], ...lot };
          return memo;
        }, {})
      );
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <Layout title="Live volgen" subtitle="WebSocket events en timers">
      <div className="panel" style={{ marginBottom: 18 }}>
        <div className="status-row" style={{ justifyContent: 'space-between' }}>
          <div className="status-row" style={{ gap: 8 }}>
            <span className={`badge ${connection === 'error' ? 'error' : ''}`}>WS: {connection}</span>
            <button className="button" onClick={reloadLots} disabled={refreshing}>
              Herlaad lijst
            </button>
          </div>
          <span className="muted">{events.length} live events</span>
        </div>
      </div>

      <div className="live-grid" style={{ marginBottom: 18 }}>
        {liveLots.map((lot) => (
          <div key={lot.id} className="live-card">
            <div className="status-row" style={{ justifyContent: 'space-between' }}>
              <div>
                <strong>{lot.title ?? lot.id}</strong>
                <p className="muted" style={{ margin: '4px 0' }}>
                  Buyer: {lot.buyer ?? '—'}
                </p>
              </div>
              <span className={`badge ${lot.status === 'error' ? 'error' : ''}`}>{lot.status ?? '—'}</span>
            </div>
            <div className="status-row" style={{ justifyContent: 'space-between', marginTop: 6 }}>
              <span className="muted">Bod: €{lot.current_bid?.toLocaleString('nl-NL') ?? '—'}</span>
              <span className="badge warning">Timer: {formatCountdown(lot.ends_at)}</span>
            </div>
          </div>
        ))}
        {liveLots.length === 0 && <p className="muted">Nog geen lots geladen.</p>}
      </div>

      <div className="panel">
        <h3>Live event feed</h3>
        <div className="debug-log">
          {events.map((event, index) => (
            <div key={`${event.id}-${index}`} style={{ marginBottom: 6 }}>
              <strong>{event.id}</strong> – {event.status}
              {event.message && <span style={{ marginLeft: 6 }}>({event.message})</span>}
            </div>
          ))}
          {events.length === 0 && <div className="muted">Nog geen events ontvangen.</div>}
        </div>
      </div>
    </Layout>
  );
}
