import { useEffect } from 'react';
import { useStore } from '../../store/ledger';
import { formatCurrency, cn } from '../../utils/format';

export default function Holdings() {
  const { holdings, holdingsLoading, fetchHoldings } = useStore();

  useEffect(() => { fetchHoldings(); }, []);

  if (holdingsLoading && !holdings) return <div className="loading">Loading holdings...</div>;
  if (!holdings || !holdings.holdings?.length) return <EmptyState />;

  const { total_book_value, total_market_value, total_gain_loss, holdings: items } = holdings;

  // Group by account type
  const groups = {};
  items.forEach((h) => {
    const key = h.account_type || 'Other';
    if (!groups[key]) groups[key] = [];
    groups[key].push(h);
  });

  return (
    <div className="fade-in">
      {/* Summary strip */}
      <div className="kpi-strip" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
        <div className="kpi-card">
          <div className="kpi-label">Book Value</div>
          <div className="kpi-value">{formatCurrency(total_book_value)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Market Value</div>
          <div className="kpi-value">{formatCurrency(total_market_value)}</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">Unrealized Gain/Loss</div>
          <div className={cn('kpi-value', total_gain_loss >= 0 ? '' : '')} style={{ color: total_gain_loss >= 0 ? 'var(--positive)' : 'var(--negative)' }}>
            {total_gain_loss >= 0 ? '+' : ''}{formatCurrency(total_gain_loss)}
          </div>
        </div>
      </div>

      {/* Holdings table */}
      <div className="card">
        <div className="table-container">
          <table className="dense">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Name</th>
                <th className="amount">Qty</th>
                <th className="amount">Book Value</th>
                <th className="amount">Mkt Value</th>
                <th className="amount">Gain/Loss</th>
                <th className="amount">%</th>
                <th>Currency</th>
              </tr>
            </thead>
            <tbody>
              {items.map((h, i) => (
                <tr key={i}>
                  <td className="mono" style={{ color: 'var(--teal)', fontWeight: 500 }}>{h.ticker || '—'}</td>
                  <td style={{ maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis' }}>{h.asset_name}</td>
                  <td className="amount mono">{h.quantity.toFixed(4)}</td>
                  <td className="amount mono">{formatCurrency(h.book_value, h.currency)}</td>
                  <td className="amount mono">{formatCurrency(h.market_value, h.currency)}</td>
                  <td className={cn('amount mono', h.gain_loss >= 0 ? 'positive' : 'negative')}>
                    {h.gain_loss >= 0 ? '+' : ''}{formatCurrency(h.gain_loss, h.currency)}
                  </td>
                  <td className={cn('amount mono', h.gain_pct >= 0 ? 'positive' : 'negative')}>
                    {h.gain_pct >= 0 ? '+' : ''}{h.gain_pct.toFixed(1)}%
                  </td>
                  <td className="mono" style={{ color: 'var(--text-dim)' }}>{h.currency}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  const { setView } = useStore();
  return (
    <div style={{ textAlign: 'center', padding: '80px 0' }}>
      <h2 style={{ fontSize: '20px', marginBottom: '8px' }}>No holdings data</h2>
      <p style={{ color: 'var(--text-dim)', marginBottom: '24px' }}>Import a Wealthsimple holdings CSV</p>
      <button className="btn btn-primary" onClick={() => setView('import')}>Import Data</button>
    </div>
  );
}
