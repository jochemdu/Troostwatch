import Link from 'next/link';
import Layout from '../components/Layout';

export default function Custom404() {
  return (
    <Layout title="Niet gevonden">
      <div className="error-container">
        <h1>404</h1>
        <p>Deze pagina kon niet worden gevonden.</p>
        <Link href="/" className="btn btn-primary">Terug naar home</Link>
      </div>

      <style jsx>{`
        .error-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 50vh;
          text-align: center;
        }
        h1 {
          font-size: 6rem;
          margin-bottom: 1rem;
          color: #6366f1;
        }
        p {
          font-size: 1.2rem;
          color: #888;
          margin-bottom: 2rem;
        }
        .btn {
          padding: 12px 24px;
          border-radius: 6px;
          text-decoration: none;
          font-weight: 500;
        }
        .btn-primary {
          background: #6366f1;
          color: #fff;
        }
        .btn-primary:hover {
          background: #5558e3;
        }
      `}</style>
    </Layout>
  );
}
