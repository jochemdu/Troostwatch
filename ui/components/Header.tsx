import Link from 'next/link';
import { useRouter } from 'next/router';
import { useMemo, useState } from 'react';
import { startLiveSync, pauseLiveSync, stopLiveSync } from '../lib/api';

const NAV_LINKS = [
  { href: '/lots', label: 'Lots overzicht' },
  { href: '/auctions', label: 'Veilingen' },
  { href: '/sync', label: 'Importeren' },
  { href: '/live', label: 'Live volgen' },
  { href: '/positions', label: 'Posities' },
  { href: '/bids', label: 'Biedingen' },
  { href: '/buyers', label: 'Kopers' },
  { href: '/templates', label: 'Templates' },
  { href: '/reports', label: 'Rapportage' },
  { href: '/add-lot', label: 'Lot toevoegen' },
  { href: '/debug', label: 'Debug' }
];

const CONTROL_ACTIONS: Array<{ label: string; action: 'start' | 'pause' | 'stop'; variant?: string }> = [
  { label: 'Start', action: 'start', variant: 'primary' },
  { label: 'Pauzeer', action: 'pause' },
  { label: 'Stop', action: 'stop', variant: 'danger' }
];

export default function Header() {
  const router = useRouter();
  const [controlState, setControlState] = useState<string>('idle');
  const [message, setMessage] = useState<string>('');
  const [busyAction, setBusyAction] = useState<string | null>(null);

  const activePath = useMemo(() => (router.pathname === '/' ? '/lots' : router.pathname), [router.pathname]);

  const handleControl = async (action: 'start' | 'pause' | 'stop') => {
    setBusyAction(action);
    try {
      let response;
      if (action === 'start') {
        response = await startLiveSync({ auction_url: '', auction_code: 'DEMO', dry_run: false });
      } else if (action === 'pause') {
        response = await pauseLiveSync();
      } else {
        response = await stopLiveSync();
      }
      setControlState(response.state ?? action);
      setMessage(`Control actie "${action}" verstuurd`);
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Onbekende fout';
      setMessage(detail);
      setControlState('error');
    } finally {
      setBusyAction(null);
    }
  };

  return (
    <aside className="sidebar">
      <div className="logo">Troostwatch</div>
      <nav className="nav">
        {NAV_LINKS.map((item) => (
          <Link key={item.href} href={item.href} className={activePath === item.href ? 'active' : ''}>
            {item.label}
          </Link>
        ))}
      </nav>
      <div style={{ marginTop: 24 }}>
        <p className="muted" style={{ marginTop: 0, marginBottom: 8 }}>
          Live besturing
        </p>
        <div className="controls">
          {CONTROL_ACTIONS.map((button) => (
            <button
              key={button.action}
              className={`button ${button.variant ?? ''}`}
              onClick={() => handleControl(button.action)}
              disabled={busyAction !== null}
            >
              {busyAction === button.action ? '…' : button.label}
            </button>
          ))}
        </div>
        <div className="status-row" style={{ marginTop: 12 }}>
          <span className={`badge ${controlState === 'error' ? 'error' : ''}`}>Status: {controlState}</span>
        </div>
        {message && <p className="muted" style={{ marginTop: 8 }}>{message}</p>}
      </div>
    </aside>
  );
}
