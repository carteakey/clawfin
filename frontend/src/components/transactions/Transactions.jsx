import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeftRight, Download, Edit2, Plus, Save, Search, Split, Trash2, Undo2, X } from 'lucide-react';
import { useStore } from '../../store/ledger';
import { api } from '../../api/client';
import { formatCurrency, formatDate } from '../../utils/format';

const PERIODS = [
  { key: '30', d: 30, l: '30D' },
  { key: '90', d: 90, l: '90D' },
  { key: '365', d: 365, l: '1Y' },
  { key: 'last_month', l: 'Last Month' },
  { key: 'all', d: 3650, l: 'All' },
];

const PAGE_SIZE = 100;
const SAVED_VIEWS = [
  { key: 'uncategorized', label: 'Uncategorized', patch: { category: 'Other' } },
  { key: 'manual', label: 'Manual only', patch: { source: 'manual' } },
  { key: 'off_budget', label: 'Off-budget', patch: { includeOffBudget: true } },
  { key: 'subscriptions', label: 'Subscriptions', patch: { category: 'Subscriptions' } },
  { key: 'last_30', label: 'Last 30 days', patch: { days: 30, periodKey: '30' } },
];
const emptyForm = {
  date: new Date().toISOString().slice(0, 10),
  merchant: '',
  amount: '',
  account_id: '',
  category: 'Other',
  currency: 'CAD',
  memo: '',
};

function dateInputValue(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function lastMonthRange() {
  const now = new Date();
  const first = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const last = new Date(now.getFullYear(), now.getMonth(), 0);
  return { start: dateInputValue(first), end: dateInputValue(last) };
}

function readLedgerUrlState() {
  const query = new URLSearchParams(window.location.search);
  const bool = (value) => value === '1' || value === 'true';
  return {
    days: Number(query.get('days')) || 30,
    periodKey: query.get('period') || '30',
    search: query.get('search') || '',
    category: query.get('category') || '',
    sourceFilter: query.get('source') || '',
    accountId: query.get('account_id') || '',
    includeOffBudget: bool(query.get('include_off_budget')),
    startDate: query.get('start_date') || '',
    endDate: query.get('end_date') || '',
    amountMin: query.get('amount_min') || '',
    amountMax: query.get('amount_max') || '',
    page: Number(query.get('page')) || 0,
    sort: { by: query.get('sort_by') || 'date', dir: query.get('sort_dir') || 'desc' },
  };
}

export default function Transactions() {
  const { transactions, transactionsTotal, transactionsLoading, fetchTransactions, selectedAccountId, setSelectedAccountId, setView } = useStore();
  const initialUrlState = useMemo(() => readLedgerUrlState(), []);
  const [days, setDays] = useState(initialUrlState.days);
  const [periodKey, setPeriodKey] = useState(initialUrlState.periodKey);
  const [search, setSearch] = useState(initialUrlState.search);
  const [category, setCategory] = useState(initialUrlState.category);
  const [sourceFilter, setSourceFilter] = useState(initialUrlState.sourceFilter);
  const [accountId, setAccountId] = useState(selectedAccountId || initialUrlState.accountId);
  const [includeOffBudget, setIncludeOffBudget] = useState(initialUrlState.includeOffBudget);
  const [startDate, setStartDate] = useState(initialUrlState.startDate);
  const [endDate, setEndDate] = useState(initialUrlState.endDate);
  const [amountMin, setAmountMin] = useState(initialUrlState.amountMin);
  const [amountMax, setAmountMax] = useState(initialUrlState.amountMax);
  const [page, setPage] = useState(initialUrlState.page);
  const [sort, setSort] = useState(initialUrlState.sort);
  const [selected, setSelected] = useState(new Set());
  const [categories, setCategories] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [accountSearch, setAccountSearch] = useState('');
  const [advancedOpen, setAdvancedOpen] = useState(Boolean(initialUrlState.startDate || initialUrlState.endDate || initialUrlState.amountMin || initialUrlState.amountMax || initialUrlState.includeOffBudget));
  const [density, setDensity] = useState(localStorage.getItem('autofin_ledger_density') || 'comfortable');
  const [savedView, setSavedView] = useState('');
  const [showManual, setShowManual] = useState(false);
  const [manualForm, setManualForm] = useState(emptyForm);
  const [editing, setEditing] = useState(null);
  const [splitTarget, setSplitTarget] = useState(null);
  const [undoState, setUndoState] = useState(null);
  const [status, setStatus] = useState(null);
  const [mutating, setMutating] = useState(false);
  const searchRef = useRef(null);

  const manualAccounts = accounts.filter((a) => a.source === 'manual');

  const params = useMemo(() => ({
    days,
    start_date: startDate || undefined,
    end_date: endDate || undefined,
    amount_min: amountMin || undefined,
    amount_max: amountMax || undefined,
    category: category || undefined,
    source: sourceFilter || undefined,
    account_id: accountId || undefined,
    search: search || undefined,
    include_off_budget: includeOffBudget,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
    sort_by: sort.by,
    sort_dir: sort.dir,
  }), [days, startDate, endDate, amountMin, amountMax, category, sourceFilter, accountId, search, includeOffBudget, page, sort]);

  const refresh = () => fetchTransactions(params);

  useEffect(() => {
    api.getCategories().then((d) => setCategories(d.categories || [])).catch(() => {});
    api.getAccounts().then((d) => setAccounts(d.accounts || [])).catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    setSelected(new Set());
  }, [params]);

  useEffect(() => {
    const query = new URLSearchParams();
    Object.entries({
      days, period: periodKey, search, category, account_id: accountId,
      source: sourceFilter, include_off_budget: includeOffBudget ? '1' : '', start_date: startDate,
      end_date: endDate, amount_min: amountMin, amount_max: amountMax,
      page, sort_by: sort.by, sort_dir: sort.dir,
    }).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '' && !(key === 'page' && value === 0)) query.set(key, value);
    });
    const next = `${window.location.pathname}${query.toString() ? `?${query}` : ''}`;
    window.history.replaceState(null, '', next);
  }, [days, periodKey, search, category, sourceFilter, accountId, includeOffBudget, startDate, endDate, amountMin, amountMax, page, sort]);

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) {
        event.preventDefault();
        searchRef.current?.focus();
      }
      if (event.key === 'Escape') {
        if (document.activeElement === searchRef.current) searchRef.current.blur();
        if (selected.size) setSelected(new Set());
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [selected]);

  const pageCount = Math.max(1, Math.ceil(transactionsTotal / PAGE_SIZE));

  const showStatus = (type, text) => {
    setStatus({ type, text });
    useStore.getState().pushToast({ type, text });
  };

  const validateForm = (form) => {
    if (!form.date) return 'Date is required.';
    if (!form.merchant?.trim()) return 'Merchant is required.';
    if (!form.account_id) return 'Choose a manual account.';
    if (Number.isNaN(parseFloat(form.amount))) return 'Amount must be a number.';
    if (!form.currency?.trim()) return 'Currency is required.';
    return null;
  };

  const handleCategoryChange = async (tx, newCategory) => {
    const previousCategory = tx.category;
    useStore.setState((s) => ({
      transactions: s.transactions.map((t) => (t.id === tx.id ? { ...t, category: newCategory } : t)),
    }));
    try {
      await api.updateTransaction(tx.id, { category: newCategory, save_rule: true });
      setUndoState({ id: tx.id, previousCategory, merchant: tx.merchant });
      showStatus('success', `Saved category for ${tx.merchant}.`);
    } catch (e) {
      useStore.setState((s) => ({
        transactions: s.transactions.map((t) => (t.id === tx.id ? { ...t, category: previousCategory } : t)),
      }));
      showStatus('error', `Update failed: ${e.message}`);
    }
  };

  const undoCategoryChange = async () => {
    if (!undoState) return;
    setMutating(true);
    try {
      await api.updateTransaction(undoState.id, { category: undoState.previousCategory, save_rule: false });
      await refresh();
      showStatus('success', `Restored category for ${undoState.merchant}.`);
      setUndoState(null);
    } catch (e) {
      showStatus('error', `Undo failed: ${e.message}`);
    }
    setMutating(false);
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
    const count = selected.size;
    setMutating(true);
    setStatus(null);
    try {
      await api.bulkTransactions({ ids: [...selected], category: newCategory });
      setSelected(new Set());
      await refresh();
      showStatus('success', `${count} transactions updated.`);
    } catch (e) {
      showStatus('error', e.message);
    }
    setMutating(false);
  };

  const bulkMark = async (kind) => {
    const count = selected.size;
    setMutating(true);
    setStatus(null);
    try {
      await api.bulkTransactions({ ids: [...selected], [kind === 'transfer' ? 'mark_transfer' : 'mark_other']: true });
      setSelected(new Set());
      await refresh();
      showStatus('success', `${count} transactions marked ${kind === 'transfer' ? 'Transfer' : 'Other'}.`);
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
    const token = localStorage.getItem('autofin_token');
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
    a.download = 'autofin-ledger.csv';
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

  const setPeriod = (period) => {
    setPeriodKey(period.key);
    setPage(0);
    if (period.key === 'last_month') {
      const { start, end } = lastMonthRange();
      setStartDate(start);
      setEndDate(end);
      setDays(3650);
      return;
    }
    setDays(period.d);
    setStartDate('');
    setEndDate('');
  };

  const clearFilters = () => {
    setDays(30);
    setPeriodKey('30');
    setSearch('');
    setAccountSearch('');
    setCategory('');
    setSourceFilter('');
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
    setSavedView('');
  };

  const applySavedView = (view) => {
    if (!view) {
      clearFilters();
      return;
    }
    const next = SAVED_VIEWS.find((candidate) => candidate.key === view);
    if (!next) return;
    setSavedView(view);
    setPage(0);
    if (next.patch.days) setDays(next.patch.days);
    if (next.patch.periodKey) setPeriodKey(next.patch.periodKey);
    if (next.patch.category) setCategory(next.patch.category);
    if (next.patch.source) setSourceFilter(next.patch.source);
    if (next.patch.includeOffBudget !== undefined) setIncludeOffBudget(next.patch.includeOffBudget);
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

  const visibleAccounts = useMemo(() => {
    const needle = accountSearch.trim().toLowerCase();
    return needle
      ? accounts.filter((account) => `${account.name} ${account.institution}`.toLowerCase().includes(needle))
      : accounts;
  }, [accounts, accountSearch]);

  return (
    <>
      <div className="section-head">
        <h2>Ledger</h2>
        <span className="label num">{transactionsTotal} rows</span>
      </div>

      {accounts.length > 0 && (
        <div>
          {accounts.length > 6 && (
            <div className="flex items-center gap-2 mb-2" style={{ maxWidth: 360 }}>
              <Search size={13} className="muted" />
              <input type="search" value={accountSearch} onChange={(event) => setAccountSearch(event.target.value)} placeholder="SEARCH ACCOUNTS..." aria-label="Search accounts" />
            </div>
          )}
        <div className="chips ledger-chip-scroll">
          <button type="button" className={`chip ${!accountId ? 'active' : ''}`} onClick={() => { setAccountId(''); setSelectedAccountId(''); setPage(0); }}>
            All <span className="count">{transactionsTotal}</span>
          </button>
          {visibleAccounts.map((a) => (
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
        </div>
      )}

      <div className="ledger-toolbar">
        {PERIODS.map((period) => (
          <button key={period.key} type="button" className={`btn ${period.key === periodKey ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setPeriod(period)}>
            {period.l}
          </button>
        ))}
        <select value={category} onChange={(e) => { setCategory(e.target.value); setPage(0); }} aria-label="Category filter">
          <option value="">ALL CATEGORIES</option>
          {categories.map((c) => <option key={c.id} value={c.name}>{c.icon ? `${c.icon} ` : ''}{c.name}</option>)}
        </select>
        <input ref={searchRef} type="search" placeholder="SEARCH MERCHANTS... (/)" value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && refresh()} aria-label="Search merchants" />
        <select value={savedView} onChange={(event) => applySavedView(event.target.value)} aria-label="Saved ledger view">
          <option value="">SAVED VIEWS</option>
          {SAVED_VIEWS.map((view) => <option key={view.key} value={view.key}>{view.label}</option>)}
        </select>
        <select value={density} onChange={(event) => { setDensity(event.target.value); localStorage.setItem('autofin_ledger_density', event.target.value); }} aria-label="Ledger row density">
          <option value="compact">COMPACT ROWS</option>
          <option value="comfortable">COMFORTABLE ROWS</option>
        </select>
        <details className="ledger-advanced" open={advancedOpen} onToggle={(event) => setAdvancedOpen(event.currentTarget.open)}>
          <summary>Advanced filters</summary>
          <div className="flex gap-2" style={{ flexWrap: 'wrap' }}>
            <input type="date" value={startDate} onChange={(e) => { setStartDate(e.target.value); setPeriodKey('custom'); setPage(0); }} aria-label="Start date" />
            <input type="date" value={endDate} onChange={(e) => { setEndDate(e.target.value); setPeriodKey('custom'); setPage(0); }} aria-label="End date" />
            <input type="number" placeholder="MIN $" value={amountMin} onChange={(e) => { setAmountMin(e.target.value); setPage(0); }} aria-label="Minimum amount" />
            <input type="number" placeholder="MAX $" value={amountMax} onChange={(e) => { setAmountMax(e.target.value); setPage(0); }} aria-label="Maximum amount" />
            <button type="button" className={`toggle ${includeOffBudget ? 'on' : ''}`} onClick={() => { setIncludeOffBudget(!includeOffBudget); setPage(0); }}>
              <div className="toggle-knob" />
              <span className="toggle-label">Off-Budget</span>
            </button>
          </div>
        </details>
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
          {undoState && status.type === 'success' && (
            <button type="button" className="btn btn-ghost" style={{ marginLeft: 12 }} onClick={undoCategoryChange} disabled={mutating}>
              <Undo2 size={13} /> Undo
            </button>
          )}
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

      {splitTarget && (
        <SplitForm
          transaction={splitTarget}
          categories={categories}
          onCancel={() => setSplitTarget(null)}
          onSave={async (allocations) => {
            setMutating(true);
            try {
              await api.splitTransaction(splitTarget.id, allocations);
              setSplitTarget(null);
              await refresh();
              showStatus('success', 'Transaction split into reconciled categories.');
            } catch (e) {
              showStatus('error', e.message);
            }
            setMutating(false);
          }}
          disabled={mutating}
        />
      )}

      {selected.size > 0 && (
        <div className="bulk-bar">
          <span className="selection-count">{selected.size} selected</span>
          <select defaultValue="" onChange={(e) => e.target.value && bulkCategory(e.target.value)} aria-label="Bulk category" disabled={mutating}>
            <option value="">SET CATEGORY</option>
            {categories.map((c) => <option key={c.id} value={c.name}>{c.name}</option>)}
          </select>
          <button type="button" className="btn btn-ghost" onClick={() => bulkMark('transfer')} disabled={mutating}><ArrowLeftRight size={14} /> Transfer</button>
          <button type="button" className="btn btn-ghost" onClick={() => bulkMark('other')} disabled={mutating}>Other</button>
          <button type="button" className="btn btn-ghost" onClick={bulkDelete} disabled={mutating}><Trash2 size={14} /> Delete Manual</button>
          <button type="button" className="btn btn-ghost" onClick={() => setSelected(new Set())}><X size={14} /> Clear</button>
        </div>
      )}

      <div className="table-wrap">
        <table className={`dense ledger-table density-${density}`}>
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
                    <select value={tx.category || 'Other'} onChange={(e) => handleCategoryChange(tx, e.target.value)} className="cat-select" disabled={mutating} title={`Category source: ${tx.category_reason || 'unknown'}`}>
                      {categories.map((c) => <option key={c.id} value={c.name}>{c.icon ? `${c.icon} ` : ''}{c.name}</option>)}
                      {!cat && tx.category && <option value={tx.category}>{tx.category}</option>}
                    </select>
                    <div className="diagnostic-label">{tx.category_reason || 'unknown'}</div>
                  </td>
                  <td className={`num r ${tx.amount >= 0 ? 'pos' : 'neg'}`}>
                    {tx.amount >= 0 ? '+' : '-'}{formatCurrency(Math.abs(tx.amount), tx.currency)}
                  </td>
                  <td className="num muted">{tx.currency}</td>
                  <td>
                    <div className="row-actions">
                      {isManual && (
                        <>
                          {!tx.parent_transaction_id && (
                            <button type="button" className="icon-btn" onClick={() => setSplitTarget(tx)} title="Split transaction" aria-label="Split transaction" disabled={mutating}>
                              <Split size={14} />
                            </button>
                          )}
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
  const [suggestions, setSuggestions] = useState([]);
  const lookupSuggestions = async () => {
    if (!form.merchant?.trim()) {
      setSuggestions([]);
      return;
    }
    try {
      const data = await api.getCategorySuggestions(form.merchant);
      setSuggestions(data.suggestions || []);
    } catch {
      setSuggestions([]);
    }
  };

  return (
    <div className="block mb-4 ledger-form">
      <div className="block-title">{title}</div>
      <input type="date" value={form.date || ''} onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))} />
      <input placeholder="MERCHANT" value={form.merchant || ''} onChange={(e) => setForm((f) => ({ ...f, merchant: e.target.value }))} onBlur={lookupSuggestions} />
      <input type="number" step="0.01" placeholder="AMOUNT" value={form.amount ?? ''} onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))} />
      <select value={form.account_id || ''} onChange={(e) => setForm((f) => ({ ...f, account_id: e.target.value }))}>
        <option value="">MANUAL ACCOUNT</option>
        {accounts.map((a) => <option key={a.id} value={a.id}>{a.institution} · {a.name}</option>)}
      </select>
      <select value={form.category || 'Other'} onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))}>
        {categories.map((c) => <option key={c.id} value={c.name}>{c.name}</option>)}
      </select>
      {suggestions.length > 0 && (
        <div className="diagnostic-label" style={{ gridColumn: '1 / -1' }}>
          Suggested: {suggestions.map((suggestion) => (
            <button key={suggestion.category} type="button" className="chip" style={{ marginLeft: 6 }} onMouseDown={() => setForm((f) => ({ ...f, category: suggestion.category }))}>
              {suggestion.category}
            </button>
          ))}
        </div>
      )}
      <input placeholder="CCY" value={form.currency || 'CAD'} maxLength={3} onChange={(e) => setForm((f) => ({ ...f, currency: e.target.value.toUpperCase() }))} />
      <input placeholder="MEMO" value={form.memo || ''} onChange={(e) => setForm((f) => ({ ...f, memo: e.target.value }))} />
      <div className="form-actions">
        <button type="button" className="btn btn-primary" onClick={onSave} disabled={disabled}><Save size={14} /> Save</button>
        <button type="button" className="btn btn-ghost" onClick={onCancel} disabled={disabled}><X size={14} /> Cancel</button>
      </div>
    </div>
  );
}

function SplitForm({ transaction, categories, onCancel, onSave, disabled }) {
  const [allocations, setAllocations] = useState([
    { category: transaction.category || 'Other', amount: (transaction.amount / 2).toFixed(2) },
    { category: 'Other', amount: (transaction.amount - transaction.amount / 2).toFixed(2) },
  ]);
  const total = allocations.reduce((sum, allocation) => sum + (parseFloat(allocation.amount) || 0), 0);
  const expected = Number(transaction.amount || 0);
  const valid = Math.abs(total - expected) < 0.005 && allocations.every((allocation) => allocation.category && parseFloat(allocation.amount));

  return (
    <div className="block mb-4" style={{ maxWidth: 720 }}>
      <div className="block-title">Split {transaction.merchant} · {expected.toFixed(2)} {transaction.currency}</div>
      {allocations.map((allocation, index) => (
        <div className="flex gap-2 mb-2" key={index}>
          <select value={allocation.category} onChange={(event) => setAllocations((items) => items.map((item, i) => i === index ? { ...item, category: event.target.value } : item))}>
            {categories.map((category) => <option key={category.id} value={category.name}>{category.name}</option>)}
          </select>
          <input type="number" step="0.01" value={allocation.amount} onChange={(event) => setAllocations((items) => items.map((item, i) => i === index ? { ...item, amount: event.target.value } : item))} aria-label={`Split amount ${index + 1}`} />
          {allocations.length > 2 && <button type="button" className="icon-btn" onClick={() => setAllocations((items) => items.filter((_, i) => i !== index))} aria-label="Remove split allocation"><X size={14} /></button>}
        </div>
      ))}
      <div className={`num ${valid ? 'pos' : 'neg'}`} style={{ fontSize: 11 }}>Allocated {total.toFixed(2)} / {expected.toFixed(2)}</div>
      <div className="form-actions mt-3">
        <button type="button" className="btn btn-ghost" onClick={() => setAllocations((items) => [...items, { category: 'Other', amount: '0' }])} disabled={disabled}>+ Allocation</button>
        <button type="button" className="btn btn-primary" onClick={() => onSave(allocations.map((allocation) => ({ ...allocation, amount: parseFloat(allocation.amount) })))} disabled={disabled || !valid}><Save size={14} /> Split</button>
        <button type="button" className="btn btn-ghost" onClick={onCancel} disabled={disabled}>Cancel</button>
      </div>
    </div>
  );
}
