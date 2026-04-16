import { useEffect, useMemo, useState } from 'react';
import { api } from '../../api/client';
import { formatCurrency } from '../../utils/format';

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

export default function Accounts() {
  const [accounts, setAccounts] = useState(null);
  const [error, setError] = useState(null);

  const load = () => {
    api.getAccounts()
      .then((d) => setAccounts(d.accounts || []))
      .catch((e) => setError(e.message));
  };

  useEffect(() => { load(); }, []);

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
  if (accounts.length === 0) return (
    <div style={{ padding: 'var(--sp-8) 0', textAlign: 'center' }}>
      <div className="label mb-3">No Accounts</div>
      <h2 style={{ fontFamily: 'var(--font-mono)', fontSize: 24, fontWeight: 700, marginBottom: 'var(--sp-4)' }}>
        Connect a bank or import a CSV.
      </h2>
    </div>
  );

  return (
    <>
      <div className="hero-stat">
        <div className="l">Total Balance</div>
        <div className="v">{formatCurrency(totals.total)}</div>
        <div className="d muted">
          {accounts.length} accounts · {Object.keys(byInstitution).length} institutions
        </div>
      </div>

      <div className="kpi-row">
        <Kpi label="Cash" value={formatCurrency(totals.cash)} />
        <Kpi label="Credit" value={formatCurrency(totals.credit)} />
        <Kpi label="Registered" value={formatCurrency(totals.registered)} />
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
                  <th>Account</th>
                  <th style={{ width: 140 }}>Type</th>
                  <th className="r" style={{ width: 160 }}>Balance</th>
                  <th className="r" style={{ width: 160 }}>Available</th>
                  <th style={{ width: 60 }}>Ccy</th>
                </tr>
              </thead>
              <tbody>
                {items.map((a) => (
                  <tr key={a.id}>
                    <td>{a.name}</td>
                    <td className="muted num" style={{ fontSize: 10, letterSpacing: '0.1em' }}>
                      {TYPE_LABELS[a.account_type] || (a.account_type || '').toUpperCase()}
                    </td>
                    <td className={`num r ${a.balance >= 0 ? '' : 'neg'}`}>
                      {formatCurrency(a.balance, a.currency)}
                    </td>
                    <td className="num r muted">
                      {a.available_balance !== null && a.available_balance !== undefined
                        ? formatCurrency(a.available_balance, a.currency)
                        : '—'}
                    </td>
                    <td className="num muted">{a.currency}</td>
                  </tr>
                ))}
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
