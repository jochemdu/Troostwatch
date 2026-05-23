import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/router';
import Link from 'next/link';
import Layout from '../../components/Layout';
import LotEditModal from '../../components/LotEditModal';
import ImageAnalyzer from '../../components/ImageAnalyzer';
import LabelExtractor from '../../components/LabelExtractor';
import SpecSuggestionEditor from '../../components/SpecSuggestionEditor';
import type { LotDetailResponse, SpecTemplate, BidHistoryEntry } from '../../lib/api';
import { fetchLotDetail, fetchSpecTemplates, fetchBidHistory, fetchLotImages, saveExtractedLabelToLot } from '../../lib/api';
import { buildSpecTree, getDepthColor, type SpecNode } from '../../lib/specs';

export default function LotDetailPage() {
  const router = useRouter();
  const { code } = router.query;
  const auctionCode = typeof router.query.auction === 'string' ? router.query.auction : undefined;
  
  const [lot, setLot] = useState<LotDetailResponse | null>(null);
  const [templates, setTemplates] = useState<SpecTemplate[]>([]);
  const [bidHistory, setBidHistory] = useState<BidHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [images, setImages] = useState<string[]>([]);
  const [imgLoading, setImgLoading] = useState(false);
  const [labelSaveLoading, setLabelSaveLoading] = useState(false);
  const [labelSaveError, setLabelSaveError] = useState<string | null>(null);
  const [batchExtractLoading, setBatchExtractLoading] = useState(false);
  const [batchExtractResults, setBatchExtractResults] = useState<Array<{url: string; status: string; label?: any; error?: string}>>([]);

  const loadLot = useCallback(async (lotCode: string) => {
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
  }, [auctionCode]);

  const loadTemplates = useCallback(async () => {
    try {
      const data = await fetchSpecTemplates();
      setTemplates(data);
    } catch (err) {
      console.error('Failed to load templates:', err);
    }
  }, []);

  const loadBidHistory = useCallback(async (lotCode: string) => {
    try {
      const data = await fetchBidHistory(lotCode, auctionCode);
      setBidHistory(data);
    } catch (err) {
      console.error('Failed to load bid history:', err);
    }
  }, [auctionCode]);

  useEffect(() => {
    if (typeof code === 'string') {
      loadLot(code);
      loadTemplates();
      loadBidHistory(code);
    }
  }, [code, loadLot, loadTemplates, loadBidHistory]);

  const handleEditSave = () => {
    setShowEditModal(false);
    if (typeof code === 'string') {
      loadLot(code);
    }
  };

  const handleFetchImages = async () => {
    if (!lot) return;
    setImgLoading(true);
    try {
      const imgs = await fetchLotImages(lot.lot_code, lot.auction_code);
      setImages(imgs);
    } catch (err) {
      setImages([]);
    } finally {
      setImgLoading(false);
    }
  };

  const handleSaveLabel = async (label: any) => {
    if (!lot) return;
    setLabelSaveLoading(true);
    setLabelSaveError(null);
    try {
      await saveExtractedLabelToLot(lot.lot_code, label, lot.auction_code);
      await loadLot(lot.lot_code); // refresh lot details
    } catch (err: any) {
      setLabelSaveError(err.message || 'Opslaan mislukt');
    } finally {
      setLabelSaveLoading(false);
    }
  };

  const handleBatchExtractLabels = async () => {
    if (!images || images.length === 0) return;
    setBatchExtractLoading(true);
    setBatchExtractResults([]);
    const results: Array<{url: string; status: string; label?: any; error?: string}> = [];
    for (const url of images) {
      if (!lot) continue;
      try {
        // Fetch image as blob
        const imgRes = await fetch(url);
        const imgBlob = await imgRes.blob();
        const formData = new FormData();
        formData.append("file", imgBlob, "lot-image.png");
        formData.append("ocr_language", "eng+nld");
        // Send to extract-label endpoint
        const res = await fetch("/extract-label", {
          method: "POST",
          body: formData,
        });
        if (!res.ok) throw new Error(`Server error: ${res.status}`);
        const data = await res.json();
        // Save label to lot
        await saveExtractedLabelToLot(lot.lot_code, data.label, lot.auction_code);
        results.push({ url, status: "success", label: data.label });
      } catch (err: any) {
        results.push({ url, status: "error", error: err.message || "Extractie mislukt" });
      }
    }
    setBatchExtractResults(results);
    setBatchExtractLoading(false);
    if (lot) await loadLot(lot.lot_code); // refresh lot details
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
                
                const renderSpecNode = (node: SpecNode, depth: number = 0): React.ReactElement => (
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

        {/* Image Analysis */}
        <div className="section">
          <h2>🔍 Afbeelding Analyse</h2>
          <p className="section-description">
            Analyseer afbeeldingen van dit lot om productcodes, modelnummers en EAN-codes te vinden.
          </p>
          <ImageAnalyzer 
            onCodeFound={(code) => {
              console.log('Found code:', code);
              // TODO: Auto-fill EAN or add to specs
            }}
          />
        </div>

        {/* Bid History */}
        {bidHistory.length > 0 && (
          <div className="section">
            <h2>Biedgeschiedenis ({bidHistory.length})</h2>
            <div className="bid-history">
              {bidHistory.map((bid, index) => (
                <div key={bid.id} className={`bid-row ${index === 0 ? 'latest' : ''}`}>
                  <span className="bid-rank">#{bidHistory.length - index}</span>
                  <span className="bid-amount">€{bid.amount_eur.toLocaleString('nl-NL', { minimumFractionDigits: 2 })}</span>
                  <span className="bid-bidder">{bid.bidder_label}</span>
                  {bid.timestamp && (
                    <span className="bid-time">{new Date(bid.timestamp).toLocaleString('nl-NL')}</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Label Extraction */}
        <div style={{ margin: '32px 0' }}>
          <h3>Label Extractie (afbeelding uploaden)</h3>
          <LabelExtractor
            onSaveLabel={handleSaveLabel}
            saveLoading={labelSaveLoading}
            saveError={labelSaveError}
          />
          <button onClick={handleFetchImages} disabled={imgLoading} style={{ marginTop: 16 }}>
            {imgLoading ? 'Bezig met ophalen...' : 'Haal afbeeldingen op van lot'}
          </button>
          {images.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <strong>Lot afbeeldingen:</strong>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {images.map((url) => (
                  <img key={url} src={url} alt="Lot afbeelding" style={{ maxWidth: 120, maxHeight: 120, borderRadius: 4, border: '1px solid #ccc' }} />
                ))}
              </div>
              <button
                onClick={handleBatchExtractLabels}
                disabled={batchExtractLoading}
                style={{ marginTop: 16, background: '#1976d2', color: '#fff', padding: '8px 16px', border: 'none', borderRadius: 6, cursor: 'pointer' }}
              >
                {batchExtractLoading ? 'Extractie & opslaan bezig...' : 'Extracteer en sla alle labels'}
              </button>
              {batchExtractResults.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <strong>Batch extractie status:</strong>
                  <ul style={{ paddingLeft: 18 }}>
                    {batchExtractResults.map((r) => (
                      <li key={r.url} style={{ color: r.status === 'success' ? '#388e3c' : '#d32f2f' }}>
                        {r.status === 'success'
                          ? `✅ Gelukt voor afbeelding: ${r.url}`
                          : `❌ Mislukt voor afbeelding: ${r.url} (${r.error})`}
                      </li>
                    ))}
                  </ul>
                  {/* Samenvatting van alle gevonden labels */}
                  <div style={{ marginTop: 18, background: '#f8f8f8', padding: 12, borderRadius: 6 }}>
                    <strong>Samenvatting gevonden labels:</strong>
                    {batchExtractResults.filter(r => r.status === 'success' && r.label).length === 0 ? (
                      <div style={{ color: '#999', fontStyle: 'italic' }}>Geen labels gevonden.</div>
                    ) : (
                      <ul style={{ paddingLeft: 18 }}>
                        {batchExtractResults.filter(r => r.status === 'success' && r.label).map((r, idx) => (
                          <li key={r.url + '-label'}>
                            <div><span style={{ fontWeight: 'bold' }}>Afbeelding:</span> {r.url}</div>
                            {Object.entries(r.label).map(([key, value]) => (
                              <div key={key}>
                                <span style={{ fontWeight: 'bold', color: key === 'vendor' ? '#1976d2' : '#333' }}>{key}:</span> <span>{String(value)}</span>
                              </div>
                            ))}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                  {/* Suggestie voor automatische koppeling aan lot-specs */}
                  <div style={{ marginTop: 18, background: '#f8f8f8', padding: 12, borderRadius: 6 }}>
                    <strong>Suggestie voor automatische koppeling aan lot-specs:</strong>
                    {batchExtractResults.filter(r => r.status === 'success' && r.label).length === 0 ? (
                      <div style={{ color: '#999', fontStyle: 'italic' }}>Geen labels gevonden.</div>
                    ) : (
                      <SpecSuggestionEditor
                        labels={batchExtractResults.filter(r => r.status === 'success' && r.label).map(r => r.label)}
                        lotSpecs={lot?.specs || []}
                        lotCode={lot?.lot_code || ''}
                        auctionCode={lot?.auction_code || ''}
                        onApply={async () => await loadLot(lot?.lot_code || '')}
                      />
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {lot && lot.notes && (
          <div style={{ marginTop: 24, background: '#f8f8f8', padding: 12, borderRadius: 6 }}>
            <strong>Extracted label data:</strong>
            <div>{lot.notes}</div>
            {lot.ean && <div>EAN: {lot.ean}</div>}
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
        .section-description { color: #888; font-size: 0.9rem; margin: 0 0 16px 0; }
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
        
        .bid-history { display: flex; flex-direction: column; gap: 8px; }
        .bid-row { 
          display: flex; 
          align-items: center; 
          gap: 16px; 
          padding: 10px 14px; 
          background: #252540; 
          border-radius: 6px;
        }
        .bid-row.latest { background: #1e3a2f; border: 1px solid #4ade80; }
        .bid-rank { font-size: 0.8rem; color: #666; min-width: 30px; }
        .bid-amount { font-size: 1rem; font-weight: 600; color: #4ade80; font-family: monospace; min-width: 100px; }
        .bid-bidder { color: #a0a0c0; flex: 1; }
        .bid-time { font-size: 0.8rem; color: #666; }
      `}</style>
    </Layout>
  );
}
