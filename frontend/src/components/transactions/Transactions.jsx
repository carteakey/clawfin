import { useEffect, useState } from 'react';
import { useStore } from '../../store/ledger';
import { formatCurrency, formatDate, cn } from '../../utils/format';

export default function Transactions() {
  const { transactions, transactionsTotal, transactionsLoading, fetchTransactions } = useStore();
  const [days, setDays] = useState(30);
  const [category, setCategory] = useState('');
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchTransactions({ days, category: category || undefined, search: search || undefined, limit: 200 });
  }, [days, category]);

  const doSearch = () => {
    fetchTransactions({ days, category: category || undefined, search: search || undefined, limit: 200 });
  };

  return (
    <div className="fade-in">
      {/* Filters */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', alignItems: 'center' }}>
        {[30, 90, 365].map((d) => (
          <button key={d} className={cn('btn', d === days ? 'btn-primary' : 'btn-ghost')} onClick={() => setDays(d)}>
            {d === 365 ? '1Y' : `${d}d`}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <input
          placeholder="Search merchants..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && doSearch()}
          style={{
            background: 'var(--bg-input)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)',
            padding: '6px 12px', color: 'var(--text)', fontSize: '13px', fontFamily: 'var(--font-sans)', outline: 'none', width: '240px',
          }}
        />
        <span style={{ color: 'var(--text-muted)', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
          {transactionsTotal} txns
        </span>
      </div>

      {/* Table */}
      <div className="card">
        <div className="table-container">
          <table className="dense">
            <thead>
              <tr>
                <th>Date</th>
                <th>Merchant</th>
                <th>Category</th>
                <th className="amount">Amount</th>
                <th>Currency</th>
              </tr>
            </thead>
            <tbody>
              {(transactions || []).map((tx) => (
                <tr key={tx.id}>
                  <td className="mono" style={{ color: 'var(--text-dim)' }}>{formatDate(tx.date)}</td>
                  <td>{tx.merchant}</td>
                  <td><span className="cat-badge">{tx.category}</span></td>
                  <td className={cn('amount mono', tx.amount >= 0 ? 'positive' : 'negative')}>
                    {tx.amount >= 0 ? '+' : ''}{formatCurrency(Math.abs(tx.amount), tx.currency)}
                  </td>
                  <td className="mono" style={{ color: 'var(--text-dim)' }}>{tx.currency}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {transactionsLoading && <div className="loading" style={{ padding: '16px', textAlign: 'center' }}>Loading...</div>}
      </div>
    </div>
  );
}
