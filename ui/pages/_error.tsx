import { NextPageContext } from 'next';
import Link from 'next/link';
import Layout from '../components/Layout';

interface ErrorProps {
  statusCode?: number;
}

function Error({ statusCode }: ErrorProps) {
  return (
    <Layout title="Fout">
      <div className="error-container">
        <h1>{statusCode || 'Fout'}</h1>
        <p>
          {statusCode === 404
            ? 'Deze pagina kon niet worden gevonden.'
            : statusCode
            ? `Er is een serverfout opgetreden (${statusCode}).`
            : 'Er is een fout opgetreden in de client.'}
        </p>
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
          font-size: 4rem;
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

Error.getInitialProps = ({ res, err }: NextPageContext) => {
  const statusCode = res ? res.statusCode : err ? err.statusCode : 404;
  return { statusCode };
};

export default Error;
