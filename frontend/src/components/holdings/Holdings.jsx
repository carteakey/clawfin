import { useEffect, useState } from 'react';
import { useStore } from '../../store/ledger';
import { api } from '../../api/client';
import { formatCurrency, formatDateFull } from '../../utils/format';

export default function Holdings() {
  const { holdings, holdingsLoading, fetchHoldings } = useStore();
  const [dates, setDates] = useState([]);
  const [asOf, setAsOf] = useState('');

  // Load snapshot dates once
  useEffect(() => {
    api.getHoldingsDates()
      .then((d) => {
        const list = d?.dates || [];
        setDates(list);
        // Default to latest
        if (list.length > 0 && !asOf) setAsOf(list[0].date);
      })
      .catch(() => {});
  }, []);

  // Fetch holdings for the chosen (or latest) snapshot
  useEffect(() => {
    fetchHoldings(asOf || undefined);
  }, [asOf]);

  if (holdingsLoading && !holdings) return <div className="loading label">Loading…</div>;
  if (!holdings || !holdings.holdings?.length) return <EmptyState />;

  const { total_book_value, total_market_value, total_gain_loss, holdings: items, as_of: serverAsOf } = holdings;
  const gainPct = total_book_value > 0 ? (total_gain_loss / total_book_value) * 100 : 0;
  const activeAsOf = asOf || serverAsOf || '';

  // Prev/next step through snapshots
  const idx = dates.findIndex((d) => d.date === activeAsOf);
  const prev = idx >= 0 && idx < dates.length - 1 ? dates[idx + 1] : null; // older
  const next = idx > 0 ? dates[idx - 1] : null; // newer

  return (
    <>
      <div className="hero-stat">
        <div className="l">Market Value</div>
        <div className="v">{formatCurrency(total_market_value)}</div>
        <div className="d">
          Book {formatCurrency(total_book_value)} · P/L{' '}
          <span className={total_gain_loss >= 0 ? 'pos' : 'neg'}>
            {total_gain_loss >= 0 ? '+' : '−'}{formatCurrency(Math.abs(total_gain_loss))} ({gainPct.toFixed(1)}%)
          </span>
        </div>
      </div>

      {dates.length > 0 && (
        <div className="flex items-center gap-2 mb-4" style={{ flexWrap: 'wrap' }}>
          <span className="label">Snapshot</span>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => prev && setAsOf(prev.date)}
            disabled={!prev}
            title="Older snapshot"
          >
            ←
          </button>
          <select
            value={activeAsOf}
            onChange={(e) => setAsOf(e.target.value)}
            style={{ width: 220 }}
          >
            {dates.map((d) => (
              <option key={d.date} value={d.date}>
                {formatDateFull(d.date)} · {d.count} lines
              </option>
            ))}
          </select>
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => next && setAsOf(next.date)}
            disabled={!next}
            title="Newer snapshot"
          >
            →
          </button>
          {dates.length > 1 && (
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => setAsOf(dates[0].date)}
              disabled={activeAsOf === dates[0].date}
              title="Jump to latest"
            >
              Latest
            </button>
          )}
          <span className="muted num" style={{ fontSize: 10, marginLeft: 'auto' }}>
            {dates.length} {dates.length === 1 ? 'snapshot' : 'snapshots'} available
          </span>
        </div>
      )}

      <div className="section-head">
        <h2>Positions</h2>
        <span className="label num">{items.length} lines</span>
      </div>

      <div className="table-wrap">
        <table className="dense">
          <thead>
            <tr>
              <th style={{ width: 90 }}>Ticker</th>
              <th>Name</th>
              <th className="r" style={{ width: 100 }}>Qty</th>
              <th className="r" style={{ width: 130 }}>Book</th>
              <th className="r" style={{ width: 130 }}>Market</th>
              <th className="r" style={{ width: 130 }}>P/L</th>
              <th className="r" style={{ width: 80 }}>%</th>
              <th style={{ width: 50 }}>Ccy</th>
            </tr>
          </thead>
          <tbody>
            {items.map((h, i) => (
              <tr key={i}>
                <td className="num"><strong>{h.ticker || '—'}</strong></td>
                <td style={{ maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis' }} className="muted">{h.asset_name}</td>
                <td className="num r">{h.quantity.toFixed(4)}</td>
                <td className="num r">{formatCurrency(h.book_value, h.currency)}</td>
                <td className="num r">{formatCurrency(h.market_value, h.currency)}</td>
                <td className={`num r ${h.gain_loss >= 0 ? 'pos' : 'neg'}`}>
                  {h.gain_loss >= 0 ? '+' : '−'}{formatCurrency(Math.abs(h.gain_loss), h.currency)}
                </td>
                <td className={`num r ${h.gain_pct >= 0 ? 'pos' : 'neg'}`}>
                  {h.gain_pct >= 0 ? '+' : ''}{h.gain_pct.toFixed(1)}%
                </td>
                <td className="num muted">{h.currency}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function EmptyState() {
  const { setView } = useStore();
  return (
    <div style={{ padding: 'var(--sp-8) 0', textAlign: 'center' }}>
      <div className="label mb-3">No Holdings</div>
      <h2 style={{ fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 700, marginBottom: 'var(--sp-4)', letterSpacing: '-0.01em' }}>
        Import a Wealthsimple CSV to begin.
      </h2>
      <button type="button" className="btn btn-primary" onClick={() => setView('import')}>Import Data →</button>
    </div>
  );
}
