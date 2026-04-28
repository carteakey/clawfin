import { useEffect, useMemo, useState } from 'react';
import { Download, Edit2, Plus, Save, Trash2, X } from 'lucide-react';
import { useStore } from '../../store/ledger';
import { api } from '../../api/client';
import { formatCurrency, formatDate } from '../../utils/format';

const PERIODS = [
  { d: 30,   l: '30D' },
  { d: 90,   l: '90D' },
  { d: 365,  l: '1Y' },
  { d: 3650, l: 'All' },
];

const PAGE_SIZE = 100;
const emptyForm = {
  date: new Date().toISOString().slice(0, 10),
  merchant: '',
  amount: '',
  account_id: '',
  category: 'Other',
  currency: 'CAD',
  memo: '',
};

export default function Transactions() {
  const { transactions, transactionsTotal, transactionsLoading, fetchTransactions, selectedAccountId, setSelectedAccountId, setView } = useStore();
  const [days, setDays] = useState(30);
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('');
  const [accountId, setAccountId] = useState(selectedAccountId || '');
  const [includeOffBudget, setIncludeOffBudget] = useState(false);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [amountMin, setAmountMin] = useState('');
  const [amountMax, setAmountMax] = useState('');
  const [page, setPage] = useState(0);
  const [sort, setSort] = useState({ by: 'date', dir: 'desc' });
  const [selected, setSelected] = useState(new Set());
  const [categories, setCategories] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [showManual, setShowManual] = useState(false);
  const [manualForm, setManualForm] = useState(emptyForm);
  const [editing, setEditing] = useState(null);
  const [status, setStatus] = useState(null);
  const [mutating, setMutating] = useState(false);

  const manualAccounts = accounts.filter((a) => a.source === 'manual');

  const params = useMemo(() => ({
    days,
    start_date: startDate || undefined,
    end_date: endDate || undefined,
    amount_min: amountMin || undefined,
    amount_max: amountMax || undefined,
    category: category || undefined,
    account_id: accountId || undefined,
    search: search || undefined,
    include_off_budget: includeOffBudget,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
    sort_by: sort.by,
    sort_dir: sort.dir,
  }), [days, startDate, endDate, amountMin, amountMax, category, accountId, search, includeOffBudget, page, sort]);

  const refresh = () => fetchTransactions(params);

  useEffect(() => {
    api.getCategories().then((d) => setCategories(d.categories || [])).catch(() => {});
    api.getAccounts().then((d) => setAccounts(d.accounts || [])).catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    setSelected(new Set());
  }, [params]);

  const pageCount = Math.max(1, Math.ceil(transactionsTotal / PAGE_SIZE));

  const showStatus = (type, text) => setStatus({ type, text });

  const validateForm = (form) => {
    if (!form.date) return 'Date is required.';
    if (!form.merchant?.trim()) return 'Merchant is required.';
    if (!form.account_id) return 'Choose a manual account.';
    if (Number.isNaN(parseFloat(form.amount))) return 'Amount must be a number.';
    if (!form.currency?.trim()) return 'Currency is required.';
    return null;
  };

  const handleCategoryChange = async (tx, newCategory) => {
    useStore.setState((s) => ({
      transactions: s.transactions.map((t) => (t.id === tx.id ? { ...t, category: newCategory } : t)),
    }));
    try {
      await api.updateTransaction(tx.id, { category: newCategory, save_rule: true });
      showStatus('success', `Saved category for ${tx.merchant}.`);
    } catch (e) {
      showStatus('error', `Update failed: ${e.message}`);
    }
  };

  const createManual = async () => {
    const error = validateForm(manualForm);
    if (error) {
      showStatus('error', error);
      return;
    }
    setMutating(true);
    setStatus(null);
    try {
      await api.createTransaction({
        ...manualForm,
        amount: parseFloat(manualForm.amount),
        account_id: parseInt(manualForm.account_id, 10),
      });
      setManualForm(emptyForm);
      setShowManual(false);
      await refresh();
      showStatus('success', 'Manual transaction created.');
    } catch (e) {
      showStatus('error', e.message);
    }
    setMutating(false);
  };

  const saveEdit = async () => {
    const error = validateForm(editing);
    if (error) {
      showStatus('error', error);
      return;
    }
    setMutating(true);
    setStatus(null);
    try {
      await api.updateTransaction(editing.id, {
        date: editing.date,
        merchant: editing.merchant,
        amount: parseFloat(editing.amount),
        account_id: parseInt(editing.account_id, 10),
        category: editing.category,
        currency: editing.currency,
        memo: editing.memo || null,
      });
      setEditing(null);
      await refresh();
      showStatus('success', 'Manual transaction saved.');
    } catch (e) {
      showStatus('error', e.message);
    }
    setMutating(false);
  };

  const deleteManual = async (tx) => {
    if (!window.confirm(`Delete manual transaction "${tx.merchant}"? This cannot be undone.`)) return;
    setMutating(true);
    setStatus(null);
    try {
      await api.deleteTransaction(tx.id);
      await refresh();
      showStatus('success', 'Manual transaction deleted.');
    } catch (e) {
      showStatus('error', e.message);
    }
    setMutating(false);
  };

  const bulkCategory = async (newCategory) => {
    setMutating(true);
    setStatus(null);
    try {
      await api.bulkTransactions({ ids: [...selected], category: newCategory });
      setSelected(new Set());
      await refresh();
      showStatus('success', `${selected.size} transactions updated.`);
    } catch (e) {
      showStatus('error', e.message);
    }
    setMutating(false);
  };

  const bulkDelete = async () => {
    if (!window.confirm(`Delete ${selected.size} selected manual transactions? This cannot be undone.`)) return;
    setMutating(true);
    setStatus(null);
    try {
      await api.bulkTransactions({ ids: [...selected], delete: true });
      setSelected(new Set());
      await refresh();
      showStatus('success', 'Selected manual transactions deleted.');
    } catch (e) {
      showStatus('error', e.message);
    }
    setMutating(false);
  };

  const downloadCsv = async () => {
    const token = localStorage.getItem('clawfin_token');
    const res = await fetch(api.exportTransactionsUrl(params), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      showStatus('error', `Export failed: HTTP ${res.status}`);
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'clawfin-ledger.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const toggleSelected = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSort = (by) => {
    setSort((current) => {
      const next = current.by === by && current.dir === 'desc'
        ? { by, dir: 'asc' }
        : { by, dir: 'desc' };
      setPage(0);
      return next;
    });
  };

  const sortCls = (by) => (sort.by === by ? `sortable sorted ${sort.dir}` : 'sortable');

  const clearFilters = () => {
    setDays(30);
    setSearch('');
    setCategory('');
    setAccountId('');
    setSelectedAccountId('');
    setIncludeOffBudget(false);
    setStartDate('');
    setEndDate('');
    setAmountMin('');
    setAmountMax('');
    setPage(0);
    setSort({ by: 'date', dir: 'desc' });
    setSelected(new Set());
  };

  const allVisibleSelected = transactions.length > 0 && transactions.every((t) => selected.has(t.id));
  const accountCounts = useMemo(() => {
    const map = new Map();
    (transactions || []).forEach((t) => {
      if (!t.account_id) return;
      map.set(t.account_id, (map.get(t.account_id) || 0) + 1);
    });
    return map;
  }, [transactions]);

  return (
    <>
      <div className="section-head">
        <h2>Ledger</h2>
        <span className="label num">{transactionsTotal} rows</span>
      </div>

      {accounts.length > 0 && (
        <div className="chips">
          <button type="button" className={`chip ${!accountId ? 'active' : ''}`} onClick={() => { setAccountId(''); setSelectedAccountId(''); setPage(0); }}>
            All <span className="count">{transactionsTotal}</span>
          </button>
          {accounts.map((a) => (
            <button
              key={a.id}
              type="button"
              className={`chip ${String(accountId) === String(a.id) ? 'active' : ''}`}
              onClick={() => {
                const newId = String(accountId) === String(a.id) ? '' : String(a.id);
                setAccountId(newId);
                setSelectedAccountId(newId);
                setPage(0);
              }}
              title={`${a.institution} · ${a.currency} · balance ${a.balance}`}
            >
              {a.name}
              {accountCounts.has(a.id) && <span className="count">{accountCounts.get(a.id)}</span>}
            </button>
          ))}
        </div>
      )}

      <div className="ledger-toolbar">
        {PERIODS.map(({ d, l }) => (
          <button key={d} type="button" className={`btn ${d === days ? 'btn-primary' : 'btn-ghost'}`} onClick={() => { setDays(d); setPage(0); }}>
            {l}
          </button>
        ))}
        <select value={category} onChange={(e) => { setCategory(e.target.value); setPage(0); }} aria-label="Category filter">
          <option value="">ALL CATEGORIES</option>
          {categories.map((c) => <option key={c.id} value={c.name}>{c.icon ? `${c.icon} ` : ''}{c.name}</option>)}
        </select>
        <input type="date" value={startDate} onChange={(e) => { setStartDate(e.target.value); setPage(0); }} aria-label="Start date" />
        <input type="date" value={endDate} onChange={(e) => { setEndDate(e.target.value); setPage(0); }} aria-label="End date" />
        <input type="number" placeholder="MIN $" value={amountMin} onChange={(e) => { setAmountMin(e.target.value); setPage(0); }} />
        <input type="number" placeholder="MAX $" value={amountMax} onChange={(e) => { setAmountMax(e.target.value); setPage(0); }} />
        <input type="search" placeholder="SEARCH MERCHANTS..." value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && refresh()} />
        <button type="button" className={`toggle ${includeOffBudget ? 'on' : ''}`} onClick={() => { setIncludeOffBudget(!includeOffBudget); setPage(0); }}>
          <div className="toggle-knob" />
          <span className="toggle-label">Off-Budget</span>
        </button>
        <button type="button" className="btn btn-ghost" onClick={clearFilters}>
          <X size={14} /> Clear
        </button>
        <button type="button" className="btn btn-ghost" onClick={downloadCsv} title="Export filtered CSV" aria-label="Export filtered CSV">
          <Download size={14} /> CSV
        </button>
        <button type="button" className="btn btn-primary" onClick={() => setShowManual(!showManual)} title="Add manual transaction" aria-label="Add manual transaction" disabled={manualAccounts.length === 0}>
          <Plus size={14} /> Manual
        </button>
      </div>

      {manualAccounts.length === 0 && (
        <div className="block mb-4" style={{ maxWidth: 720 }}>
          <div className="label mb-2">Manual Account Required</div>
          <div className="muted" style={{ fontSize: 12 }}>Create a manual account in Accounts before adding manual transactions.</div>
          <button type="button" className="btn btn-primary mt-4" onClick={() => setView('accounts')}>
            <Plus size={14} /> Add Account
          </button>
        </div>
      )}

      {status && (
        <div className={`status-box ${status.type === 'error' ? 'neg' : 'pos'}`}>
          {status.text}
        </div>
      )}

      {showManual && (
        <TransactionForm
          title="Manual Transaction"
          form={manualForm}
          setForm={setManualForm}
          accounts={manualAccounts}
          categories={categories}
          onCancel={() => setShowManual(false)}
          onSave={createManual}
          disabled={mutating}
        />
      )}

      {selected.size > 0 && (
        <div className="bulk-bar">
          <span className="label">{selected.size} selected</span>
          <select defaultValue="" onChange={(e) => e.target.value && bulkCategory(e.target.value)} aria-label="Bulk category">
            <option value="">SET CATEGORY</option>
            {categories.map((c) => <option key={c.id} value={c.name}>{c.name}</option>)}
          </select>
          <button type="button" className="btn btn-ghost" onClick={bulkDelete} disabled={mutating}><Trash2 size={14} /> Delete Manual</button>
          <button type="button" className="btn btn-ghost" onClick={() => setSelected(new Set())}><X size={14} /> Clear</button>
        </div>
      )}

      <div className="table-wrap">
        <table className="dense ledger-table">
          <thead>
            <tr>
              <th style={{ width: 36 }}>
                <input
                  type="checkbox"
                  checked={allVisibleSelected}
                  onChange={(e) => setSelected(e.target.checked ? new Set(transactions.map((t) => t.id)) : new Set())}
                  aria-label="Select visible transactions"
                />
              </th>
              <th className={sortCls('date')} style={{ width: 90 }} onClick={() => toggleSort('date')}>Date</th>
              <th className={sortCls('merchant')} onClick={() => toggleSort('merchant')}>Merchant</th>
              <th className={sortCls('account_name')} style={{ width: 140 }} onClick={() => toggleSort('account_name')}>Account</th>
              <th className={sortCls('category')} style={{ width: 180 }} onClick={() => toggleSort('category')}>Category</th>
              <th className={`r ${sortCls('amount')}`} style={{ width: 140 }} onClick={() => toggleSort('amount')}>Amount</th>
              <th style={{ width: 70 }}>Ccy</th>
              <th style={{ width: 120 }}></th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((tx) => {
              const cat = categories.find((c) => c.name === tx.category);
              const isManual = tx.source === 'manual';
              return (
                <tr key={tx.id}>
                  <td><input type="checkbox" checked={selected.has(tx.id)} onChange={() => toggleSelected(tx.id)} aria-label={`Select ${tx.merchant}`} /></td>
                  <td className="num muted">{formatDate(tx.date)}</td>
                  <td>
                    <div>
                      <div className="merchant-cell">
                        <span>{tx.normalized_merchant || tx.merchant}</span>
                        {tx.pending && <span className="label pending-label">PENDING</span>}
                      </div>
                      {tx.memo && <div className="ledger-memo">{tx.memo}</div>}
                    </div>
                  </td>
                  <td className="muted truncate" title={tx.account_name}>{tx.account_name}</td>
                  <td>
                    <select value={tx.category || 'Other'} onChange={(e) => handleCategoryChange(tx, e.target.value)} className="cat-select">
                      {categories.map((c) => <option key={c.id} value={c.name}>{c.icon ? `${c.icon} ` : ''}{c.name}</option>)}
                      {!cat && tx.category && <option value={tx.category}>{tx.category}</option>}
                    </select>
                  </td>
                  <td className={`num r ${tx.amount >= 0 ? 'pos' : 'neg'}`}>
                    {tx.amount >= 0 ? '+' : '-'}{formatCurrency(Math.abs(tx.amount), tx.currency)}
                  </td>
                  <td className="num muted">{tx.currency}</td>
                  <td>
                    <div className="row-actions">
                      {isManual && (
                        <>
                          <button type="button" className="icon-btn" onClick={() => setEditing({ ...tx })} title="Edit transaction" aria-label="Edit transaction">
                            <Edit2 size={14} />
                          </button>
                          <button type="button" className="icon-btn" onClick={() => deleteManual(tx)} title="Delete transaction" aria-label="Delete transaction" disabled={mutating}>
                            <Trash2 size={14} />
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {transactionsLoading && <div className="loading label" style={{ padding: 'var(--sp-4)' }}>Loading...</div>}
        {!transactionsLoading && transactions.length === 0 && <div className="label" style={{ padding: 'var(--sp-5)' }}>No transactions match.</div>}
      </div>

      <div className="pager">
        <button type="button" className="btn btn-ghost" disabled={page === 0} onClick={() => setPage((p) => Math.max(0, p - 1))}>Prev</button>
        <span className="num muted">Page {page + 1} / {pageCount}</span>
        <button type="button" className="btn btn-ghost" disabled={page + 1 >= pageCount} onClick={() => setPage((p) => p + 1)}>Next</button>
      </div>

      {editing && (
        <TransactionForm
          title="Edit Manual Transaction"
          form={editing}
          setForm={setEditing}
          accounts={manualAccounts}
          categories={categories}
          onCancel={() => setEditing(null)}
          onSave={saveEdit}
          disabled={mutating}
        />
      )}

    </>
  );
}

function TransactionForm({ title, form, setForm, accounts, categories, onCancel, onSave, disabled = false }) {
  return (
    <div className="block mb-4 ledger-form">
      <div className="block-title">{title}</div>
      <input type="date" value={form.date || ''} onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))} />
      <input placeholder="MERCHANT" value={form.merchant || ''} onChange={(e) => setForm((f) => ({ ...f, merchant: e.target.value }))} />
      <input type="number" step="0.01" placeholder="AMOUNT" value={form.amount ?? ''} onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))} />
      <select value={form.account_id || ''} onChange={(e) => setForm((f) => ({ ...f, account_id: e.target.value }))}>
        <option value="">MANUAL ACCOUNT</option>
        {accounts.map((a) => <option key={a.id} value={a.id}>{a.institution} · {a.name}</option>)}
      </select>
      <select value={form.category || 'Other'} onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}>
        {categories.map((c) => <option key={c.id} value={c.name}>{c.name}</option>)}
      </select>
      <input placeholder="CCY" value={form.currency || 'CAD'} maxLength={3} onChange={(e) => setForm((f) => ({ ...f, currency: e.target.value.toUpperCase() }))} />
      <input placeholder="MEMO" value={form.memo || ''} onChange={(e) => setForm((f) => ({ ...f, memo: e.target.value }))} />
      <div className="form-actions">
        <button type="button" className="btn btn-primary" onClick={onSave} disabled={disabled}><Save size={14} /> Save</button>
        <button type="button" className="btn btn-ghost" onClick={onCancel} disabled={disabled}><X size={14} /> Cancel</button>
      </div>
    </div>
  );
}
