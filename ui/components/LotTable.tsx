import type { LotView } from '../lib/api';

interface Props {
  lots: LotView[];
  selectedLots: Set<string>;
  onToggleLot: (lotCode: string) => void;
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
            <th>Veiling</th>
            <th>Status</th>
            <th>Huidig bod</th>
            <th>Biedingen</th>
            <th>Sluit</th>
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
              <td>{lot.title ?? lot.lot_code}</td>
              <td>{lot.auction_code}</td>
              <td>
                <span className={`badge ${lot.state === 'closed' ? 'error' : ''}`}>{lot.state ?? 'onbekend'}</span>
              </td>
              <td>{lot.current_bid_eur ? `€${lot.current_bid_eur.toLocaleString('nl-NL')}` : '—'}</td>
              <td>{lot.bid_count ?? 0}</td>
              <td className="muted">{lot.closing_time_current ? new Date(lot.closing_time_current).toLocaleString('nl-NL') : '—'}</td>
            </tr>
          ))}
          {lots.length === 0 && (
            <tr>
              <td colSpan={7} className="muted">
                Geen resultaten
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
