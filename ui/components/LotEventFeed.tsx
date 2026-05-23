import React, { useEffect, useState } from 'react';
import { createLotSocket } from '../lib/ws';
import type { LotEvent } from '../lib/types';

export default function LotEventFeed() {
  const [events, setEvents] = useState<LotEvent[]>([]);
  const [status, setStatus] = useState<string>('connecting');

  useEffect(() => {
    const ws = createLotSocket(
      (event) => {
        setEvents((prev) => [event, ...prev].slice(0, 50)); // keep last 50 events
      },
      (state) => setStatus(state)
    );
    return () => ws.close();
  }, []);

  return (
    <div style={{ maxWidth: 600, margin: '40px auto', padding: 24, background: '#f5f5f5', borderRadius: 8 }}>
      <h2>Live Lot Events</h2>
      <div>Status: <span style={{ color: status === 'open' ? 'green' : status === 'error' ? 'red' : '#666' }}>{status}</span></div>
      <ul style={{ marginTop: 16, padding: 0, listStyle: 'none' }}>
        {events.length === 0 && <li>No events yet.</li>}
        {events.map((event, idx) => (
          <li key={idx} style={{ marginBottom: 12, background: '#fff', padding: 12, borderRadius: 4, boxShadow: '0 1px 3px #eee' }}>
            <pre style={{ margin: 0, fontSize: 13 }}>{JSON.stringify(event, null, 2)}</pre>
          </li>
        ))}
      </ul>
    </div>
  );
}
