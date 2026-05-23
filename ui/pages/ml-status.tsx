import React, { useEffect, useState } from 'react';
import ExampleLotEventConsumer from '../components/ExampleLotEventConsumer';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';

export default function MLStatusPage() {
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_URL}/ml/training-status`)
      .then((res) => {
        if (!res.ok) throw new Error(`Server error: ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setStatus(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  return (
    <>
      <div style={{ maxWidth: 600, margin: '40px auto', padding: 24, background: '#fafafa', borderRadius: 8 }}>
        <h1>ML Training Status</h1>
        {loading && <p>Loading...</p>}
        {error && <p style={{ color: 'red' }}>Error: {error}</p>}
        {status && (
          <>
            <h2>Last Training Run</h2>
            <pre style={{ background: '#eee', padding: 12, borderRadius: 4 }}>{JSON.stringify(status.last_run, null, 2)}</pre>
            <h2>Model Info</h2>
            <pre style={{ background: '#eee', padding: 12, borderRadius: 4 }}>{JSON.stringify(status.model_info, null, 2)}</pre>
            <h2>Stats</h2>
            <pre style={{ background: '#eee', padding: 12, borderRadius: 4 }}>{JSON.stringify(status.stats, null, 2)}</pre>
            <p>{status.detail}</p>
          </>
        )}
      </div>
      <ExampleLotEventConsumer />
    </>
  );
}
