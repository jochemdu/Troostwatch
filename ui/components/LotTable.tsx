import { LotSummary } from '../lib/api';

interface Props {
  lots: LotSummary[];
  selectedLots: Set<string>;
  onToggleLot: (id: string) => void;
}

export default function LotTable({ lots, selectedLots, onToggleLot }: Props) {
  return (
    <div className="panel">
      <div className="status-row" style={{ justifyContent: 'space-between', marginBottom: 8 }}>
        <h2 style={{ margin: 0 }}>Lots</h2>
        <span className="badge">{lots.length} records</span>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th></th>
            <th>Lot</th>
            <th>Status</th>
            <th>Buyer</th>
            <th>Reserve</th>
            <th>Laatst bijgewerkt</th>
          </tr>
        </thead>
        <tbody>
          {lots.map((lot) => (
            <tr key={lot.id}>
              <td>
                <input
                  aria-label={`select-${lot.id}`}
                  type="checkbox"
                  checked={selectedLots.has(lot.id)}
                  onChange={() => onToggleLot(lot.id)}
                />
              </td>
              <td>{lot.title ?? lot.id}</td>
              <td>
                <span className={`badge ${lot.status === 'error' ? 'error' : ''}`}>{lot.status ?? 'onbekend'}</span>
              </td>
              <td>{lot.buyer ?? '—'}</td>
              <td>{lot.reserve ? `€${lot.reserve.toLocaleString('nl-NL')}` : '—'}</td>
              <td className="muted">{lot.updated_at ? new Date(lot.updated_at).toLocaleString() : '—'}</td>
            </tr>
          ))}
          {lots.length === 0 && (
            <tr>
              <td colSpan={6} className="muted">
                Geen resultaten
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
