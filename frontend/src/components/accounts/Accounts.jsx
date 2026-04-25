import { useEffect, useMemo, useState } from 'react';
import { api } from '../../api/client';
import { useStore } from '../../store/ledger';
import { formatMoney } from '../../utils/format';

const TYPE_LABELS = {
  chequing: 'CHEQUING',
  savings: 'SAVINGS',
  credit_card: 'CREDIT CARD',
  tfsa: 'TFSA',
  rrsp: 'RRSP',
  fhsa: 'FHSA',
  margin: 'MARGIN',
  crypto: 'CRYPTO',
  other: 'OTHER',
};

function syncStatus(acct) {
  // CSV / manual sources don't have live sync
  if (!acct.source || acct.source === 'manual' || !acct.source.startsWith('simplefin')) {
    return { color: 'var(--ink-3)', label: 'Static — no live sync', symbol: '○' };
  }
  if (!acct.simplefin_account_present) {
    return { color: 'var(--neg)', label: 'Account missing from SimpleFIN', symbol: '●' };
  }
  if (acct.last_sync_error) {
    return { color: 'var(--neg)', label: `Sync error: ${acct.last_sync_error}`, symbol: '●' };
  }
  if (acct.stale_reason) {
    return { color: '#F59E0B', label: `Stale: ${acct.stale_reason}`, symbol: '●' };
  }
  if (acct.last_sync_at) {
    return { color: 'var(--pos)', label: 'Synced', symbol: '●' };
  }
  return { color: 'var(--ink-3)', label: 'Never synced', symbol: '○' };
}

export default function Accounts() {
  const [accounts, setAccounts] = useState(null);
  const [error, setError] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [newAcct, setNewAcct] = useState({ name: '', institution: '', account_type: 'chequing', currency: 'CAD', on_budget: true });
  const hideBalances = useStore((s) => s.hideBalances);

  const load = () => {
    api.getAccounts()
      .then((d) => setAccounts(d.accounts || []))
      .catch((e) => setError(e.message));
  };

  useEffect(() => { load(); }, []);

  const handleAddAccount = async (e) => {
    e.preventDefault();
    try {
      await api.createAccount(newAcct);
      setShowAdd(false);
      setNewAcct({ name: '', institution: '', account_type: 'chequing', currency: 'CAD', on_budget: true });
      load();
    } catch (e) {
      alert(`Error creating account: ${e.message}`);
    }
  };

  const toggleBudget = async (id, currentVal) => {
    try {
      await api.updateAccount(id, { on_budget: !currentVal });
      load();
    } catch (e) {
      alert(`Error updating account: ${e.message}`);
    }
  };

  const deleteAccount = async (id) => {
    if (!window.confirm('Delete this account and all its transactions? This cannot be undone.')) return;
    try {
      await api.deleteAccount(id);
      load();
    } catch (e) {
      alert(`Error deleting account: ${e.message}`);
    }
  };

  const { byInstitution, totals } = useMemo(() => {
    const list = accounts || [];
    const grouped = {};
    list.forEach((a) => {
      const inst = a.institution || 'Unknown';
      (grouped[inst] ||= []).push(a);
    });
    const totals = {
      total: list.reduce((s, a) => s + (a.balance || 0), 0),
      cash: list
        .filter((a) => ['chequing', 'savings'].includes(a.account_type))
        .reduce((s, a) => s + (a.balance || 0), 0),
      credit: list
        .filter((a) => a.account_type === 'credit_card')
        .reduce((s, a) => s + (a.balance || 0), 0),
      registered: list
        .filter((a) => ['tfsa', 'rrsp', 'fhsa'].includes(a.account_type))
        .reduce((s, a) => s + (a.balance || 0), 0),
    };
    return { byInstitution: grouped, totals };
  }, [accounts]);

  if (error) return (
    <div className="block" style={{ borderColor: 'var(--neg)' }}>
      <div className="label neg">Error</div>
      <div className="num" style={{ fontSize: 12, marginTop: 6 }}>{error}</div>
    </div>
  );

  if (accounts === null) return <div className="loading label">Loading…</div>;
  if (accounts.length === 0 && !showAdd) return (
    <div style={{ padding: 'var(--sp-8) 0', textAlign: 'center' }}>
      <div className="label mb-3">No Accounts</div>
      <h2 style={{ fontFamily: 'var(--font-mono)', fontSize: 24, fontWeight: 700, marginBottom: 'var(--sp-4)' }}>
        Connect a bank or import a CSV.
      </h2>
      <button type="button" className="btn btn-primary" onClick={() => setShowAdd(true)}>+ ADD MANUAL ACCOUNT</button>
    </div>
  );

  return (
    <>
      <div className="hero-stat">
        <div className="l">Total Balance</div>
        <div className="v">{formatMoney(totals.total, 'CAD', hideBalances)}</div>
        <div className="d muted">
          {accounts.length} accounts · {Object.keys(byInstitution).length} institutions
          <button
            type="button"
            className="btn btn-ghost"
            style={{ marginLeft: 'var(--sp-4)', fontSize: 10 }}
            onClick={() => setShowAdd(!showAdd)}
          >
            {showAdd ? 'CANCEL' : '+ ADD MANUAL ACCOUNT'}
          </button>
        </div>
      </div>

      {showAdd && (
        <div className="block mb-6" style={{ maxWidth: 600 }}>
          <div className="block-title">Create Manual Account</div>
          <form onSubmit={handleAddAccount} className="grid-2" style={{ border: 'none', padding: 0 }}>
            <div style={{ border: 'none', padding: '0 var(--sp-4) var(--sp-4) 0' }}>
              <div className="label mb-2">Account Name</div>
              <input
                required
                placeholder="e.g. My Savings"
                value={newAcct.name}
                onChange={(e) => setNewAcct({ ...newAcct, name: e.target.value })}
              />
            </div>
            <div style={{ border: 'none', padding: '0 0 var(--sp-4) 0' }}>
              <div className="label mb-2">Institution</div>
              <input
                required
                placeholder="e.g. TD Bank"
                value={newAcct.institution}
                onChange={(e) => setNewAcct({ ...newAcct, institution: e.target.value })}
              />
            </div>
            <div style={{ border: 'none', padding: '0 var(--sp-4) 0 0' }}>
              <div className="label mb-2">Type</div>
              <select
                value={newAcct.account_type}
                onChange={(e) => setNewAcct({ ...newAcct, account_type: e.target.value })}
              >
                {Object.entries(TYPE_LABELS).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </select>
            </div>
            <div style={{ border: 'none', padding: 0, display: 'flex', alignItems: 'flex-end', gap: 'var(--sp-4)' }}>
              <div style={{ flex: 1 }}>
                <div className="label mb-2">Currency</div>
                <input
                  required
                  value={newAcct.currency}
                  onChange={(e) => setNewAcct({ ...newAcct, currency: e.target.value.toUpperCase() })}
                />
              </div>
              <button type="submit" className="btn btn-primary" style={{ height: 34 }}>CREATE</button>
            </div>
          </form>
        </div>
      )}

      <div className="kpi-row">
        <Kpi label="Cash" value={formatMoney(totals.cash, 'CAD', hideBalances)} />
        <Kpi label="Credit" value={formatMoney(totals.credit, 'CAD', hideBalances)} />
        <Kpi label="Registered" value={formatMoney(totals.registered, 'CAD', hideBalances)} />
        <Kpi label="Accounts" value={accounts.length} />
      </div>

      {Object.entries(byInstitution).map(([inst, items]) => (
        <div className="section" key={inst}>
          <div className="section-head">
            <h2>{inst}</h2>
            <span className="label num">{items.length} accts</span>
          </div>
          <div className="table-wrap">
            <table className="dense">
              <thead>
                <tr>
                  <th style={{ width: 24 }} />
                  <th>Account</th>
                  <th style={{ width: 140 }}>Type</th>
                  <th className="r" style={{ width: 160 }}>Balance</th>
                  <th className="r" style={{ width: 160 }}>Available</th>
                  <th style={{ width: 60 }}>Ccy</th>
                  <th style={{ width: 100, textAlign: 'center' }}>Budget</th>
                  <th style={{ width: 80, textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((a) => {
                  const sync = syncStatus(a);
                  return (
                  <tr key={a.id}>
                    <td style={{ width: 24, textAlign: 'center', paddingRight: 0 }}>
                      <span
                        title={sync.label}
                        style={{
                          color: sync.color,
                          fontSize: 9,
                          lineHeight: 1,
                          cursor: 'default',
                          fontFamily: 'var(--font-mono)',
                        }}
                      >
                        {sync.symbol}
                      </span>
                    </td>
                    <td
                      style={{ cursor: 'pointer', textDecoration: 'underline', textUnderlineOffset: '3px' }}
                      onClick={() => {
                        useStore.getState().setSelectedAccountId(String(a.id));
                        useStore.getState().setView('transactions');
                      }}
                    >
                      {a.name}
                    </td>
                    <td className="muted num" style={{ fontSize: 10, letterSpacing: '0.1em' }}>
                      <select
                        value={a.account_type || 'other'}
                        onChange={(e) => {
                          api.updateAccount(a.id, { account_type: e.target.value }).then(load).catch(alert);
                        }}
                        style={{ background: 'transparent', border: 'none', color: 'inherit', fontSize: 'inherit', letterSpacing: 'inherit', padding: 0, cursor: 'pointer', textTransform: 'uppercase' }}
                      >
                        {Object.entries(TYPE_LABELS).map(([k, v]) => (
                          <option key={k} value={k}>{v}</option>
                        ))}
                      </select>
                    </td>
                    <td className={`num r ${a.balance >= 0 ? '' : 'neg'}`}>
                      {formatMoney(a.balance, a.currency, hideBalances)}
                    </td>
                    <td className="num r muted">
                      {a.available_balance !== null && a.available_balance !== undefined
                        ? formatMoney(a.available_balance, a.currency, hideBalances)
                        : '—'}
                    </td>
                    <td className="num muted">{a.currency}</td>
                    <td style={{ textAlign: 'center' }}>
                      <button
                        type="button"
                        className="btn btn-ghost"
                        style={{ fontSize: 10, padding: '2px 8px' }}
                        onClick={() => toggleBudget(a.id, a.on_budget)}
                      >
                        {a.on_budget ? 'ON' : 'OFF'}
                      </button>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        type="button"
                        className="btn btn-ghost neg"
                        style={{ fontSize: 10, padding: '2px 8px' }}
                        onClick={() => deleteAccount(a.id)}
                      >
                        Del
                      </button>
                    </td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </>
  );
}

function Kpi({ label, value }) {
  return (
    <div className="kpi">
      <div className="l">{label}</div>
      <div className="v">{value}</div>
    </div>
  );
}
