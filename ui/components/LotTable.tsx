import { useState } from 'react';
import Link from 'next/link';
import type { LotView } from '../lib/api';
import LotEditModal from './LotEditModal';

export type SortField = 'lot_code' | 'closing_time_current' | 'current_bid_eur' | 'bid_count' | 'state';
export type SortDirection = 'asc' | 'desc';

interface Props {
  lots: LotView[];
  selectedLots: Set<string>;
  onToggleLot: (lotCode: string) => void;
  onLotUpdated?: () => void;
  sortField?: SortField;
  sortDirection?: SortDirection;
  onSort?: (field: SortField) => void;
}

export default function LotTable({ lots, selectedLots, onToggleLot, onLotUpdated, sortField, sortDirection, onSort }: Props) {
  const [editingLot, setEditingLot] = useState<{ lotCode: string; auctionCode: string } | null>(null);

  const handleEditClick = (lot: LotView) => {
    setEditingLot({ lotCode: lot.lot_code, auctionCode: lot.auction_code });
  };

  const handleCloseModal = () => {
    setEditingLot(null);
  };

  const handleSaved = () => {
    setEditingLot(null);
    onLotUpdated?.();
  };

  const getSortIndicator = (field: SortField) => {
    if (sortField !== field) return ' ↕';
    return sortDirection === 'asc' ? ' ↑' : ' ↓';
  };

  const SortableHeader = ({ field, children }: { field: SortField; children: React.ReactNode }) => (
    <th 
      className="sortable-header" 
      onClick={() => onSort?.(field)}
      title={`Sorteer op ${children}`}
    >
      {children}
      <span className="sort-indicator">{getSortIndicator(field)}</span>
    </th>
  );

  return (
    <>
      <div className="panel">
        <div className="status-row" style={{ justifyContent: 'space-between', marginBottom: 8 }}>
          <h2 style={{ margin: 0 }}>Lots</h2>
          <span className="badge">{lots.length} records</span>
        </div>
        <table className="table">
          <thead>
            <tr>
              <th></th>
              <SortableHeader field="lot_code">Lot</SortableHeader>
              <th>Veiling</th>
              <SortableHeader field="state">Status</SortableHeader>
              <SortableHeader field="current_bid_eur">Huidig bod</SortableHeader>
              <SortableHeader field="bid_count">Biedingen</SortableHeader>
              <SortableHeader field="closing_time_current">Sluit</SortableHeader>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {lots.map((lot) => (
              <tr key={`${lot.auction_code}-${lot.lot_code}`}>
                <td>
                  <input
                    aria-label={`select-${lot.lot_code}`}
                    type="checkbox"
                    checked={selectedLots.has(lot.lot_code)}
                    onChange={() => onToggleLot(lot.lot_code)}
                  />
                </td>
                <td>
                  <Link href={`/lots/${encodeURIComponent(lot.lot_code)}?auction=${encodeURIComponent(lot.auction_code)}`} className="lot-link">
                    {lot.title ?? lot.lot_code}
                  </Link>
                </td>
                <td>{lot.auction_code}</td>
                <td>
                  <span className={`badge ${lot.state === 'closed' ? 'error' : ''}`}>{lot.state ?? 'onbekend'}</span>
                </td>
                <td>{lot.current_bid_eur ? `€${lot.current_bid_eur.toLocaleString('nl-NL')}` : '—'}</td>
                <td>{lot.bid_count ?? 0}</td>
                <td className="muted">{lot.closing_time_current ? new Date(lot.closing_time_current).toLocaleString('nl-NL') : '—'}</td>
                <td>
                  <button 
                    className="btn-edit"
                    onClick={() => handleEditClick(lot)}
                    aria-label={`bewerk ${lot.lot_code}`}
                    title="Bewerken"
                  >
                    ✏️
                  </button>
                </td>
              </tr>
            ))}
            {lots.length === 0 && (
              <tr>
                <td colSpan={8} className="muted">
                  Geen resultaten
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {editingLot && (
        <LotEditModal
          lotCode={editingLot.lotCode}
          auctionCode={editingLot.auctionCode}
          isOpen={true}
          onClose={handleCloseModal}
          onSaved={handleSaved}
        />
      )}

      <style jsx>{`
        .btn-edit {
          background: none;
          border: none;
          cursor: pointer;
          padding: 4px 8px;
          font-size: 1rem;
          opacity: 0.6;
          transition: opacity 0.2s;
        }

        .btn-edit:hover {
          opacity: 1;
        }

        .sortable-header {
          cursor: pointer;
          user-select: none;
          white-space: nowrap;
        }

        .sortable-header:hover {
          background-color: rgba(255, 255, 255, 0.05);
        }

        .sort-indicator {
          opacity: 0.5;
          font-size: 0.8em;
          margin-left: 4px;
        }

        .sortable-header:hover .sort-indicator {
          opacity: 0.8;
        }
      `}</style>
      <style jsx global>{`
        .lot-link {
          color: #6366f1;
          text-decoration: none;
        }
        .lot-link:hover {
          text-decoration: underline;
          color: #818cf8;
        }
      `}</style>
    </>
  );
}
