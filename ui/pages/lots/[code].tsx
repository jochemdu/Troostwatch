import { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Layout from '../../components/Layout';
import LotEditModal from '../../components/LotEditModal';
import type { LotDetailResponse, SpecTemplate } from '../../lib/api';
import { fetchLotDetail, fetchSpecTemplates } from '../../lib/api';
import { buildSpecTree, getDepthColor, type SpecNode } from '../../lib/specs';

export default function LotDetailPage() {
  const router = useRouter();
  const { code } = router.query;
  const auctionCode = typeof router.query.auction === 'string' ? router.query.auction : undefined;
  
  const [lot, setLot] = useState<LotDetailResponse | null>(null);
  const [templates, setTemplates] = useState<SpecTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);

  useEffect(() => {
    if (typeof code === 'string') {
      loadLot(code);
      loadTemplates();
    }
  }, [code, auctionCode]);

  const loadLot = async (lotCode: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchLotDetail(lotCode, auctionCode);
      setLot(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Kon lot niet laden');
    } finally {
      setLoading(false);
    }
  };

  const loadTemplates = async () => {
    try {
      const data = await fetchSpecTemplates();
      setTemplates(data);
    } catch (err) {
      console.error('Failed to load templates:', err);
    }
  };

  const handleEditSave = () => {
    setShowEditModal(false);
    if (typeof code === 'string') {
      loadLot(code);
    }
  };

  if (loading) {
    return (
      <Layout title="Laden...">
        <div className="loading">Lot laden...</div>
        <style jsx>{`
          .loading { color: #888; padding: 60px; text-align: center; font-size: 1.1rem; }
        `}</style>
      </Layout>
    );
  }

  if (error || !lot) {
    return (
      <Layout title="Fout">
        <div className="error-page">
          <h1>Lot niet gevonden</h1>
          <p>{error || 'Het opgevraagde lot bestaat niet.'}</p>
          <Link href="/lots" className="back-link">← Terug naar lots</Link>
        </div>
        <style jsx>{`
          .error-page { text-align: center; padding: 60px 20px; }
          .error-page h1 { margin: 0 0 16px 0; color: #f87171; }
          .error-page p { color: #888; margin-bottom: 24px; }
          .back-link { color: #6366f1; text-decoration: none; }
          .back-link:hover { text-decoration: underline; }
        `}</style>
      </Layout>
    );
  }

  const stateColor = lot.state === 'open' ? '#4ade80' : lot.state === 'closed' ? '#888' : '#f59e0b';

  return (
    <Layout title={`${lot.lot_code} - ${lot.title || 'Lot'}`}>
      <div className="lot-detail">
        {/* Header */}
        <div className="header">
          <div className="breadcrumb">
            <Link href="/lots">Lots</Link>
            <span className="sep">/</span>
            <Link href={`/auctions?code=${lot.auction_code}`}>{lot.auction_code}</Link>
            <span className="sep">/</span>
            <span>{lot.lot_code}</span>
          </div>
          <div className="title-row">
            <h1>{lot.title || lot.lot_code}</h1>
            <div className="actions">
              <button className="btn btn-primary" onClick={() => setShowEditModal(true)}>
                ✏️ Bewerken
              </button>
              {lot.url && (
                <a href={lot.url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary">
                  🔗 Troostwijk
                </a>
              )}
            </div>
          </div>
          <div className="meta">
            <span className="state" style={{ color: stateColor }}>{lot.state || 'onbekend'}</span>
            {lot.brand && <span className="brand">🏷️ {lot.brand}</span>}
            {lot.ean && <span className="ean">📦 {lot.ean}</span>}
            {lot.location_city && (
              <span className="location">📍 {lot.location_city}{lot.location_country ? `, ${lot.location_country}` : ''}</span>
            )}
          </div>
        </div>

        {/* Bidding Info */}
        <div className="section">
          <h2>Biedinformatie</h2>
          <div className="info-grid">
            <div className="info-card">
              <span className="label">Huidig bod</span>
              <span className="value price">
                {lot.current_bid_eur != null 
                  ? `€${lot.current_bid_eur.toLocaleString('nl-NL', { minimumFractionDigits: 2 })}`
                  : '—'}
              </span>
            </div>
            <div className="info-card">
              <span className="label">Aantal biedingen</span>
              <span className="value">{lot.bid_count ?? '—'}</span>
            </div>
            <div className="info-card">
              <span className="label">Openingsbod</span>
              <span className="value">
                {lot.opening_bid_eur != null 
                  ? `€${lot.opening_bid_eur.toLocaleString('nl-NL', { minimumFractionDigits: 2 })}`
                  : '—'}
              </span>
            </div>
            <div className="info-card">
              <span className="label">Sluitingstijd</span>
              <span className="value">
                {lot.closing_time_current 
                  ? new Date(lot.closing_time_current).toLocaleString('nl-NL')
                  : '—'}
              </span>
            </div>
          </div>
        </div>

        {/* Reference Prices */}
        {lot.reference_prices.length > 0 && (
          <div className="section">
            <h2>Referentieprijzen</h2>
            <div className="ref-prices">
              {lot.reference_prices.map(rp => (
                <div key={rp.id} className="ref-price-card">
                  <div className="condition">{rp.condition}</div>
                  <div className="price">€{rp.price_eur.toLocaleString('nl-NL', { minimumFractionDigits: 2 })}</div>
                  {rp.source && <div className="source">{rp.source}</div>}
                  {rp.url && (
                    <a href={rp.url} target="_blank" rel="noopener noreferrer" className="link">Bekijk</a>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Specifications */}
        <div className="section">
          <h2>Specificaties</h2>
          {lot.specs.length === 0 ? (
            <p className="empty">Geen specificaties. Klik op Bewerken om toe te voegen.</p>
          ) : (
            <div className="specs-list">
              {(() => {
                const specTree = buildSpecTree(lot.specs);
                
                const renderSpecNode = (node: SpecNode, depth: number = 0): JSX.Element => (
                  <div key={node.id} className="spec-item">
                    <div 
                      className="spec-row" 
                      style={{ 
                        marginLeft: depth * 24, 
                        borderLeft: depth > 0 ? `3px solid ${getDepthColor(depth)}` : undefined,
                        paddingLeft: depth > 0 ? '12px' : undefined
                      }}
                    >
                      {depth > 0 && <span className="spec-indent">└─ </span>}
                      <span className="spec-key">{node.key}</span>
                      <span className="spec-value">{node.value || '—'}</span>
                      {node.ean && <span className="spec-ean">📦 {node.ean}</span>}
                      {node.price_eur != null && (
                        <span className="spec-price">€{node.price_eur.toLocaleString('nl-NL', { minimumFractionDigits: 2 })}</span>
                      )}
                      {node.release_date && <span className="spec-release-date">📅 {node.release_date}</span>}
                      {node.category && <span className="spec-category">🏷️ {node.category}</span>}
                    </div>
                    {node.children.map(child => renderSpecNode(child, depth + 1))}
                  </div>
                );
                
                return specTree.map(node => renderSpecNode(node));
              })()}
            </div>
          )}
        </div>

        {/* Notes */}
        {lot.notes && (
          <div className="section">
            <h2>Notities</h2>
            <div className="notes">{lot.notes}</div>
          </div>
        )}
      </div>

      {/* Edit Modal */}
      {showEditModal && (
        <LotEditModal
          lot={lot}
          templates={templates}
          onClose={() => setShowEditModal(false)}
          onSave={handleEditSave}
        />
      )}

      <style jsx>{`
        .lot-detail { max-width: 1000px; margin: 0 auto; }
        
        .header { margin-bottom: 32px; }
        .breadcrumb { font-size: 0.85rem; color: #888; margin-bottom: 12px; }
        .breadcrumb a { color: #6366f1; text-decoration: none; }
        .breadcrumb a:hover { text-decoration: underline; }
        .breadcrumb .sep { margin: 0 8px; color: #555; }
        
        .title-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; flex-wrap: wrap; }
        .title-row h1 { margin: 0; font-size: 1.8rem; flex: 1; }
        .actions { display: flex; gap: 10px; }
        
        .btn { padding: 10px 18px; border-radius: 6px; font-size: 0.9rem; cursor: pointer; border: none; font-weight: 500; text-decoration: none; display: inline-block; }
        .btn-primary { background: #6366f1; color: #fff; }
        .btn-primary:hover { background: #5558e3; }
        .btn-secondary { background: #333; color: #e0e0e0; }
        .btn-secondary:hover { background: #444; }
        
        .meta { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 12px; font-size: 0.9rem; }
        .state { font-weight: 600; text-transform: uppercase; }
        .brand, .ean, .location { color: #a0a0c0; }
        
        .section { background: #1a1a2e; border: 1px solid #333; border-radius: 8px; padding: 20px; margin-bottom: 20px; }
        .section h2 { margin: 0 0 16px 0; font-size: 1.1rem; color: #fff; }
        .empty { color: #666; font-style: italic; margin: 0; }
        
        .info-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }
        .info-card { background: #252540; border-radius: 6px; padding: 16px; }
        .info-card .label { display: block; font-size: 0.8rem; color: #888; margin-bottom: 6px; }
        .info-card .value { font-size: 1.2rem; font-weight: 600; color: #fff; }
        .info-card .value.price { color: #4ade80; font-family: monospace; }
        
        .ref-prices { display: flex; gap: 12px; flex-wrap: wrap; }
        .ref-price-card { background: #252540; border-radius: 6px; padding: 14px; min-width: 150px; }
        .ref-price-card .condition { font-size: 0.75rem; color: #888; text-transform: uppercase; margin-bottom: 4px; }
        .ref-price-card .price { font-size: 1.1rem; font-weight: 600; color: #4ade80; font-family: monospace; }
        .ref-price-card .source { font-size: 0.8rem; color: #a0a0c0; margin-top: 6px; }
        .ref-price-card .link { font-size: 0.8rem; color: #6366f1; text-decoration: none; display: inline-block; margin-top: 4px; }
        .ref-price-card .link:hover { text-decoration: underline; }
        
        .specs-list { }
        .spec-item { margin-bottom: 8px; }
        .spec-row { 
          display: flex; 
          align-items: center; 
          gap: 16px; 
          padding: 10px 14px; 
          background: #252540; 
          border-radius: 6px;
          flex-wrap: wrap;
        }
        .spec-indent { color: #555; font-family: monospace; }
        .spec-key { font-weight: 500; color: #a0a0c0; min-width: 120px; }
        .spec-value { flex: 1; color: #fff; }
        .spec-ean { font-size: 0.8rem; color: #888; background: #1a1a2e; padding: 2px 8px; border-radius: 4px; }
        .spec-price { font-size: 0.9rem; color: #4ade80; font-weight: 600; font-family: monospace; }
        .spec-release-date { font-size: 0.8rem; color: #a0a0c0; background: #1a1a2e; padding: 2px 8px; border-radius: 4px; }
        .spec-category { font-size: 0.8rem; color: #60a5fa; background: #1a1a2e; padding: 2px 8px; border-radius: 4px; }
        
        .notes { background: #252540; border-radius: 6px; padding: 14px; white-space: pre-wrap; color: #e0e0e0; line-height: 1.5; }
      `}</style>
    </Layout>
  );
}
