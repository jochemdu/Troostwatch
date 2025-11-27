import { useState } from 'react';
import Link from 'next/link';
import type { LotView } from '../lib/api';
import { deleteLot } from '../lib/api';
import LotEditModal from './LotEditModal';

export type SortField = 'lot_code' | 'closing_time_current' | 'current_bid_eur' | 'bid_count' | 'state';
export type SortDirection = 'asc' | 'desc';

interface SortableHeaderProps {
  field: SortField;
  sortField?: SortField;
  sortDirection?: SortDirection;
  onSort?: (field: SortField) => void;
  children: React.ReactNode;
}

function SortableHeader({ field, sortField, sortDirection, onSort, children }: SortableHeaderProps) {
  const getSortIndicator = () => {
    if (sortField !== field) return ' ↕';
    return sortDirection === 'asc' ? ' ↑' : ' ↓';
  };

  return (
    <th 
      className="sortable-header" 
      onClick={() => onSort?.(field)}
      title={`Sorteer op ${children}`}
    >
      {children}
      <span className="sort-indicator">{getSortIndicator()}</span>
    </th>
  );
}

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
  const [deletingLot, setDeletingLot] = useState<{ lotCode: string; auctionCode: string; title?: string } | null>(null);

  const handleEditClick = (lot: LotView) => {
    setEditingLot({ lotCode: lot.lot_code, auctionCode: lot.auction_code });
  };

  const handleDeleteClick = (lot: LotView) => {
    setDeletingLot({ lotCode: lot.lot_code, auctionCode: lot.auction_code, title: lot.title ?? lot.lot_code });
  };

  const handleConfirmDelete = async () => {
    if (!deletingLot) return;
    try {
      await deleteLot(deletingLot.lotCode, deletingLot.auctionCode);
      setDeletingLot(null);
      onLotUpdated?.();
    } catch (error) {
      alert(error instanceof Error ? error.message : 'Verwijderen mislukt');
    }
  };

  const handleCloseModal = () => {
    setEditingLot(null);
  };

  const handleSaved = () => {
    setEditingLot(null);
    onLotUpdated?.();
  };

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
              <SortableHeader field="lot_code" sortField={sortField} sortDirection={sortDirection} onSort={onSort}>Lot</SortableHeader>
              <th>Veiling</th>
              <SortableHeader field="state" sortField={sortField} sortDirection={sortDirection} onSort={onSort}>Status</SortableHeader>
              <SortableHeader field="current_bid_eur" sortField={sortField} sortDirection={sortDirection} onSort={onSort}>Huidig bod</SortableHeader>
              <SortableHeader field="bid_count" sortField={sortField} sortDirection={sortDirection} onSort={onSort}>Biedingen</SortableHeader>
              <SortableHeader field="closing_time_current" sortField={sortField} sortDirection={sortDirection} onSort={onSort}>Sluit</SortableHeader>
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
                  <button 
                    className="btn-delete"
                    onClick={() => handleDeleteClick(lot)}
                    aria-label={`verwijder ${lot.lot_code}`}
                    title="Verwijderen"
                  >
                    🗑️
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

        .btn-delete {
          background: none;
          border: none;
          cursor: pointer;
          padding: 4px 8px;
          font-size: 1rem;
          opacity: 0.6;
          transition: opacity 0.2s;
        }

        .btn-delete:hover {
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

      {/* Delete Confirmation Dialog */}
      {deletingLot && (
        <div className="delete-overlay">
          <div className="delete-dialog">
            <h3>Lot verwijderen?</h3>
            <p>Weet je zeker dat je <strong>{deletingLot.title}</strong> wilt verwijderen?</p>
            <p className="warning">Dit verwijdert ook alle specificaties, biedhistorie en referentieprijzen.</p>
            <div className="delete-actions">
              <button className="btn-cancel" onClick={() => setDeletingLot(null)}>Annuleren</button>
              <button className="btn-confirm-delete" onClick={handleConfirmDelete}>Verwijderen</button>
            </div>
          </div>
          <style jsx>{`
            .delete-overlay {
              position: fixed;
              inset: 0;
              background: rgba(0, 0, 0, 0.6);
              display: flex;
              align-items: center;
              justify-content: center;
              z-index: 1000;
            }
            .delete-dialog {
              background: #1a1a2e;
              border-radius: 8px;
              padding: 24px;
              max-width: 400px;
              color: #e0e0e0;
              box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            }
            .delete-dialog h3 {
              margin: 0 0 12px 0;
              color: #f56565;
            }
            .delete-dialog p {
              margin: 8px 0;
            }
            .warning {
              font-size: 0.9em;
              color: #ed8936;
            }
            .delete-actions {
              display: flex;
              gap: 12px;
              margin-top: 20px;
              justify-content: flex-end;
            }
            .btn-cancel {
              background: #333;
              border: 1px solid #555;
              color: #e0e0e0;
              padding: 8px 16px;
              border-radius: 4px;
              cursor: pointer;
            }
            .btn-cancel:hover {
              background: #444;
            }
            .btn-confirm-delete {
              background: #f56565;
              border: none;
              color: #fff;
              padding: 8px 16px;
              border-radius: 4px;
              cursor: pointer;
              font-weight: 600;
            }
            .btn-confirm-delete:hover {
              background: #e53e3e;
            }
          `}</style>
        </div>
      )}
    </>
  );
}
