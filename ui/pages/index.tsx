import { useState, useEffect } from 'react';
import Link from 'next/link';
import Layout from '../components/Layout';
import { fetchDashboardStats, type DashboardStats } from '../lib/api';
import LabelExtractor from "../components/LabelExtractor";

export default function Home() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardStats()
      .then(setStats)
      .catch(() => setStats(null))
      .finally(() => setLoading(false));
  }, []);

  return (
    <Layout title="Dashboard" subtitle="Overzicht">
      {/* Stats Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{loading ? '...' : stats?.active_auctions ?? 0}</div>
          <div className="stat-label">Actieve veilingen</div>
          <div className="stat-sub">{stats?.total_auctions ?? 0} totaal</div>
        </div>
        <div className="stat-card">
          <div className="stat-value running">{loading ? '...' : stats?.running_lots ?? 0}</div>
          <div className="stat-label">Lopende lots</div>
          <div className="stat-sub">{stats?.scheduled_lots ?? 0} gepland</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{loading ? '...' : stats?.total_positions ?? 0}</div>
          <div className="stat-label">Posities</div>
          <div className="stat-sub">{stats?.total_bids ?? 0} biedingen</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{loading ? '...' : stats?.total_buyers ?? 0}</div>
          <div className="stat-label">Buyers</div>
          <div className="stat-sub">{stats?.closed_lots ?? 0} gesloten lots</div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="panel">
        <h2>Snelle acties</h2>
        <div className="controls">
          <Link className="button primary" href="/lots?state=running">
            🔴 Lopende lots
          </Link>
          <Link className="button" href="/live">
            📡 Live volgen
          </Link>
          <Link className="button" href="/sync">
            🔄 Sync uitvoeren
          </Link>
          <Link className="button" href="/positions">
            📊 Posities
          </Link>
        </div>
      </div>

      {/* Navigation */}
      <div className="panel">
        <h2>Modules</h2>
        <div className="controls">
          <Link className="button" href="/lots">
            Lots overzicht
          </Link>
          <Link className="button" href="/auctions">
            Veilingen
          </Link>
          <Link className="button" href="/buyers">
            Buyers
          </Link>
          <Link className="button" href="/bids">
            Biedingen
          </Link>
          <Link className="button" href="/reports">
            Rapportages
          </Link>
          <Link className="button" href="/templates">
            Templates
          </Link>
        </div>
      </div>

      <div style={{ margin: "32px 0" }}>
        <Link href="/extract-label">
          <button style={{ padding: "10px 20px", fontSize: "1rem", background: "#1976d2", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}>
            Ga naar Label Extractor
          </button>
        </Link>
      </div>

      <LabelExtractor />

      <style jsx>{`
        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
          gap: 16px;
          margin-bottom: 24px;
        }
        .stat-card {
          background: #1a1a2e;
          border: 1px solid #333;
          border-radius: 8px;
          padding: 20px;
          text-align: center;
        }
        .stat-value {
          font-size: 2.5rem;
          font-weight: 700;
          color: #fff;
          font-family: monospace;
        }
        .stat-value.running {
          color: #4ade80;
        }
        .stat-label {
          font-size: 0.9rem;
          color: #a0a0c0;
          margin-top: 4px;
        }
        .stat-sub {
          font-size: 0.8rem;
          color: #666;
          margin-top: 4px;
        }
        .panel {
          background: #1a1a2e;
          border: 1px solid #333;
          border-radius: 8px;
          padding: 20px;
          margin-bottom: 16px;
        }
        .panel h2 {
          margin: 0 0 16px 0;
          font-size: 1rem;
          color: #a0a0c0;
        }
        .controls {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
        }
        .button {
          display: inline-block;
          padding: 10px 18px;
          background: #252540;
          border: 1px solid #444;
          border-radius: 6px;
          color: #fff;
          text-decoration: none;
          font-size: 0.9rem;
          transition: background 0.2s;
        }
        .button:hover {
          background: #333355;
        }
        .button.primary {
          background: #4f46e5;
          border-color: #4f46e5;
        }
        .button.primary:hover {
          background: #5b54f0;
        }
      `}</style>
    </Layout>
  );
}
