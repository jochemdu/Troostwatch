import React, { useContext } from 'react';
import { LotEventContext } from '../pages/_app';

export default function ExampleLotEventConsumer() {
  const { events } = useContext(LotEventContext);

  return (
    <div style={{ maxWidth: 600, margin: '40px auto', padding: 24, background: '#e3f2fd', borderRadius: 8 }}>
      <h2>Global Lot Events (via Context)</h2>
      <ul style={{ marginTop: 16, padding: 0, listStyle: 'none' }}>
        {events.length === 0 && <li>No events yet.</li>}
        {events.slice(0, 10).map((event, idx) => (
          <li key={idx} style={{ marginBottom: 12, background: '#fff', padding: 12, borderRadius: 4, boxShadow: '0 1px 3px #eee' }}>
            <pre style={{ margin: 0, fontSize: 13 }}>{JSON.stringify(event, null, 2)}</pre>
          </li>
        ))}
      </ul>
    </div>
  );
}
