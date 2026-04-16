import { useEffect, useMemo, useState } from 'react';
import { useStore } from '../../store/ledger';
import { api } from '../../api/client';
import { formatCurrency, formatDate } from '../../utils/format';

const PERIODS = [
  { d: 30,   l: '30D' },
  { d: 90,   l: '90D' },
  { d: 365,  l: '1Y' },
  { d: 3650, l: 'All' },
];

export default function Transactions() {
  const { transactions, transactionsTotal, transactionsLoading, fetchTransactions } = useStore();
  const [days, setDays] = useState(30);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [accountId, setAccountId] = useState('');
  const [categories, setCategories] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [sort, setSort] = useState({ key: 'date', dir: 'desc' });

  useEffect(() => {
    api.getCategories().then((d) => setCategories(d.categories || [])).catch(() => {});
    api.getAccounts().then((d) => setAccounts(d.accounts || [])).catch(() => {});
  }, []);

  useEffect(() => {
    fetchTransactions({
      days,
      category: category || undefined,
      account_id: accountId || undefined,
      search: search || undefined,
      limit: 500,
    });
  }, [days, category, accountId]);

  const doSearch = () => {
    fetchTransactions({
      days,
      category: category || undefined,
      account_id: accountId || undefined,
      search: search || undefined,
      limit: 500,
    });
  };

  const handleCategoryChange = async (tx, newCategory) => {
    useStore.setState((s) => ({
      transactions: s.transactions.map((t) => (t.id === tx.id ? { ...t, category: newCategory } : t)),
    }));
    try {
      await api.updateTransaction(tx.id, { category: newCategory, save_rule: true });
    } catch (e) {
      console.error('update failed', e);
    }
  };

  const toggleSort = (key) => {
    setSort((s) => {
      if (s.key !== key) return { key, dir: key === 'amount' ? 'desc' : 'desc' };
      return { key, dir: s.dir === 'desc' ? 'asc' : 'desc' };
    });
  };

  const sorted = useMemo(() => {
    const list = [...(transactions || [])];
    const { key, dir } = sort;
    const mult = dir === 'asc' ? 1 : -1;
    list.sort((a, b) => {
      let av = a[key], bv = b[key];
      if (key === 'amount') { av = a.amount; bv = b.amount; }
      if (key === 'merchant') { av = (a.merchant || '').toLowerCase(); bv = (b.merchant || '').toLowerCase(); }
      if (key === 'account_name') { av = (a.account_name || ''); bv = (b.account_name || ''); }
      if (av < bv) return -1 * mult;
      if (av > bv) return  1 * mult;
      return 0;
    });
    return list;
  }, [transactions, sort]);

  const accountCounts = useMemo(() => {
    const map = new Map();
    (transactions || []).forEach((t) => {
      if (!t.account_id) return;
      map.set(t.account_id, (map.get(t.account_id) || 0) + 1);
    });
    return map;
  }, [transactions]);

  const sortCls = (key) => `sortable${sort.key === key ? ` sorted ${sort.dir}` : ''}`;

  return (
    <>
      <div className="section-head">
        <h2>Ledger</h2>
        <span className="label num">
          {transactionsTotal} txns · showing {transactions?.length ?? 0}
        </span>
      </div>

      {accounts.length > 0 && (
        <div className="chips">
          <button
            type="button"
            className={`chip ${!accountId ? 'active' : ''}`}
            onClick={() => setAccountId('')}
          >
            All <span className="count">{transactionsTotal}</span>
          </button>
          {accounts.map((a) => (
            <button
              key={a.id}
              type="button"
              className={`chip ${String(accountId) === String(a.id) ? 'active' : ''}`}
              onClick={() => setAccountId(String(accountId) === String(a.id) ? '' : String(a.id))}
              title={`${a.institution} · ${a.currency} · balance ${a.balance}`}
            >
              {a.name}
              {accountCounts.has(a.id) && <span className="count">{accountCounts.get(a.id)}</span>}
            </button>
          ))}
        </div>
      )}

      <div className="flex gap-2 items-center mb-4" style={{ flexWrap: 'wrap' }}>
        {PERIODS.map(({ d, l }) => (
          <button
            key={d}
            type="button"
            className={`btn ${d === days ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setDays(d)}
          >
            {l}
          </button>
        ))}
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          style={{ width: 180 }}
          aria-label="Category filter"
        >
          <option value="">ALL CATEGORIES</option>
          {categories.map((c) => (
            <option key={c.id} value={c.name}>
              {c.icon ? `${c.icon} ` : ''}{c.name}
            </option>
          ))}
        </select>
        <div style={{ flex: 1 }} />
        <input
          type="search"
          placeholder="SEARCH MERCHANTS…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && doSearch()}
          style={{ width: 260 }}
        />
      </div>

      <div className="table-wrap">
        <table className="dense">
          <thead>
            <tr>
              <th className={sortCls('date')} style={{ width: 90 }} onClick={() => toggleSort('date')}>Date</th>
              <th className={sortCls('merchant')} onClick={() => toggleSort('merchant')}>Merchant</th>
              <th className={sortCls('account_name')} style={{ width: 140 }} onClick={() => toggleSort('account_name')}>Account</th>
              <th style={{ width: 180 }}>Category</th>
              <th className={`r ${sortCls('amount')}`} style={{ width: 140 }} onClick={() => toggleSort('amount')}>Amount</th>
              <th style={{ width: 50 }}>Ccy</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((tx) => {
              const cat = categories.find((c) => c.name === tx.category);
              return (
                <tr key={tx.id}>
                  <td className="num muted">
                    {tx.pending && <span className="pending-dot" title="Pending">●</span>}
                    {formatDate(tx.date)}
                  </td>
                  <td title={tx.memo || tx.description || ''}>
                    {tx.merchant}
                    {tx.memo && (
                      <span className="muted" style={{ marginLeft: 8, fontSize: 10, fontFamily: 'var(--font-mono)' }}>
                        · {tx.memo.slice(0, 60)}{tx.memo.length > 60 ? '…' : ''}
                      </span>
                    )}
                  </td>
                  <td className="num muted" style={{ fontSize: 11 }}>
                    {tx.account_name ? tx.account_name : '—'}
                  </td>
                  <td>
                    <select
                      value={tx.category || 'Other'}
                      onChange={(e) => handleCategoryChange(tx, e.target.value)}
                      className="cat-select"
                    >
                      {categories.map((c) => (
                        <option key={c.id} value={c.name}>
                          {c.icon ? `${c.icon} ` : ''}{c.name}
                        </option>
                      ))}
                      {!cat && tx.category && (
                        <option value={tx.category}>{tx.category}</option>
                      )}
                    </select>
                  </td>
                  <td className={`num r ${tx.amount >= 0 ? 'pos' : 'neg'}`}>
                    {tx.amount >= 0 ? '+' : '−'}{formatCurrency(Math.abs(tx.amount), tx.currency)}
                  </td>
                  <td className="num muted">{tx.currency}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {transactionsLoading && <div className="loading label" style={{ padding: 'var(--sp-4)' }}>Loading…</div>}
        {!transactionsLoading && (sorted.length === 0) && (
          <div className="label" style={{ padding: 'var(--sp-5)' }}>No transactions match.</div>
        )}
      </div>

      <div className="label mt-4 muted" style={{ fontSize: 10 }}>
        Tip · change a category inline to save a rule for next time. Or Settings → Rules → Recategorize All to replay rules across every txn.
      </div>
    </>
  );
}
