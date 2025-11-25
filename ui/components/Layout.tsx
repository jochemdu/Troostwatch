import Head from 'next/head';
import { ReactNode } from 'react';
import Header from './Header';

interface Props {
  children: ReactNode;
  title?: string;
  subtitle?: string;
}

export default function Layout({ children, title, subtitle }: Props) {
  return (
    <div className="layout">
      <Head>
        <title>{title ? `${title} • Troostwatch` : 'Troostwatch Console'}</title>
      </Head>
      <Header />
      <main className="main">
        {title && (
          <header style={{ marginBottom: 16 }}>
            <div className="status-row">
              <h1 style={{ margin: 0 }}>{title}</h1>
              {subtitle && <span className="badge">{subtitle}</span>}
            </div>
          </header>
        )}
        {children}
      </main>
    </div>
  );
}
