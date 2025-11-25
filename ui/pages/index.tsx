import Link from 'next/link';
import Layout from '../components/Layout';

export default function Home() {
  return (
    <Layout title="Welkom" subtitle="Kies een module">
      <div className="panel">
        <p className="muted">Gebruik het menu om naar de gewenste module te gaan.</p>
        <div className="controls">
          <Link className="button" href="/lots">
            Lots overzicht
          </Link>
          <Link className="button" href="/live">
            Live volgen
          </Link>
          <Link className="button" href="/buyers">
            Buyers
          </Link>
          <Link className="button" href="/debug">
            Debug
          </Link>
        </div>
      </div>
    </Layout>
  );
}
