import { useState } from 'react';
import Layout from '../components/Layout';
import type { LotView, BuyerResponse } from '../lib/api';
import { loadDebugSample, startLiveSync, pauseLiveSync, stopLiveSync } from '../lib/api';

export default function DebugPage() {
  const [payload, setPayload] = useState<string>('');
  const [output, setOutput] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const runSampleLoad = async () => {
    setLoading(true);
    try {
      const response = await loadDebugSample();
      setOutput(JSON.stringify(response, null, 2));
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Debug call mislukt';
      setOutput(detail);
    } finally {
      setLoading(false);
    }
  };

  const runPayloadTest = async () => {
    setLoading(true);
    try {
      const parsed = payload ? JSON.parse(payload) : {};
      setOutput(`Parsed payload: ${JSON.stringify(parsed, null, 2)}`);
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Ongeldige JSON';
      setOutput(detail);
    } finally {
      setLoading(false);
    }
  };

  const sendControl = async (action: 'start' | 'pause' | 'stop') => {
    setLoading(true);
    try {
      let result;
      if (action === 'start') {
        result = await startLiveSync({ auction_url: '', auction_code: 'DEBUG', dry_run: false });
      } else if (action === 'pause') {
        result = await pauseLiveSync();
      } else {
        result = await stopLiveSync();
      }
      setOutput(`Control: ${JSON.stringify(result, null, 2)}`);
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Control call mislukt';
      setOutput(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout title="Debug" subtitle="API en WebSocket calls testen">
      <div className="panel" style={{ marginBottom: 18 }}>
        <h3>Payload (JSON)</h3>
        <textarea
          rows={5}
          value={payload}
          onChange={(event) => setPayload(event.target.value)}
          placeholder='{"id":"lot-1","status":"sold"}'
        />
        <div className="controls">
          <button className="button primary" onClick={runPayloadTest} disabled={loading}>
            Test JSON parse
          </button>
          <button className="button" onClick={runSampleLoad} disabled={loading}>
            Haal lots/buyers op
          </button>
        </div>
      </div>

      <div className="panel" style={{ marginBottom: 18 }}>
        <h3>Besturing</h3>
        <div className="controls">
          <button className="button primary" onClick={() => sendControl('start')} disabled={loading}>
            Start
          </button>
          <button className="button" onClick={() => sendControl('pause')} disabled={loading}>
            Pauzeer
          </button>
          <button className="button danger" onClick={() => sendControl('stop')} disabled={loading}>
            Stop
          </button>
        </div>
      </div>

      <div className="panel">
        <h3>Laatste response</h3>
        <div className="debug-log">{output || 'Nog niets uitgevoerd.'}</div>
      </div>
    </Layout>
  );
}
