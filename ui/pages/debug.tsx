import { useState } from 'react';
import Layout from '../components/Layout';
import { BuyerPayload, LotSummary, loadDebugSample, triggerControl, updateLotBatch } from '../lib/api';

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

  const runBatchExample = async () => {
    setLoading(true);
    try {
      const parsed = (payload ? JSON.parse(payload) : {}) as Partial<LotSummary & BuyerPayload>;
      const result = await updateLotBatch({
        lot_ids: parsed.id ? [String(parsed.id)] : ['demo-lot'],
        updates: { status: parsed.status ?? 'debug' }
      });
      setOutput(`Batch response: ${JSON.stringify(result)}`);
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Kon batch niet uitvoeren';
      setOutput(detail);
    } finally {
      setLoading(false);
    }
  };

  const sendControl = async (action: 'start' | 'pause' | 'stop') => {
    setLoading(true);
    try {
      const result = await triggerControl(action);
      setOutput(`Control: ${JSON.stringify(result)}`);
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
          <button className="button primary" onClick={runBatchExample} disabled={loading}>
            Test batch update
          </button>
          <button className="button" onClick={runSampleLoad} disabled={loading}>
            Haal filters/lots/buyers op
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
