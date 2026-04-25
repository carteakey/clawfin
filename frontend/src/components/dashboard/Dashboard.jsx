import { useEffect, useState } from 'react';
import { useStore } from '../../store/ledger';
import { api } from '../../api/client';
import { formatCurrency, formatDelta, formatMoney } from '../../utils/format';
import { BarChart, Bar, ResponsiveContainer, Tooltip, XAxis } from 'recharts';
import Waterfall from './Waterfall';

const PERIODS = [
  { d: 7,   l: '7D' },
  { d: 30,  l: '30D' },
  { d: 90,  l: '90D' },
  { d: 365, l: '1Y' },
];

export default function Dashboard() {
  const { dashboard, dashboardLoading, fetchDashboard } = useStore();
  const hideBalances = useStore((s) => s.hideBalances);
  const [days, setDays] = useState(30);
  const [categoryColors, setCategoryColors] = useState({});

  useEffect(() => { fetchDashboard(days); }, [days]);

  useEffect(() => {
    api.getCategories().then((d) => {
      const map = {};
      for (const c of d.categories || []) {
        if (c.color) map[c.name] = c.color;
      }
      setCategoryColors(map);
    }).catch(() => {});
  }, []);

  if (dashboardLoading && !dashboard) return <div className="loading label">Loading…</div>;
  if (!dashboard) return <EmptyState />;

  const { kpis, spending_breakdown, top_merchants, daily_spending, transfer_count } = dashboard;

  const dailyData = Object.entries(daily_spending || {}).map(([date, amount]) => ({
    date: new Date(date + 'T00:00:00').toLocaleDateString('en-CA', { month: 'short', day: 'numeric' }),
    amount: Math.round(amount),
  }));

  return (
    <>
      {/* Hero net worth */}
      <div className="hero-stat">
        <div className="l">Account Balance</div>
        <div className="v">{formatMoney(kpis.account_balance ?? kpis.net_worth, 'CAD', hideBalances)}</div>
        <div className="d">
          Income {formatMoney(kpis.income, 'CAD', hideBalances)} · Expenses {formatMoney(kpis.expenses, 'CAD', hideBalances)} · Savings {kpis.savings_rate}%
          {kpis.holdings_market_value ? ` · Holdings separate ${formatMoney(kpis.holdings_market_value, 'CAD', hideBalances)}` : ''}
        </div>
      </div>

      {/* Period selector */}
      <div className="flex gap-2 mb-4">
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
      </div>

      {/* KPI row */}
      <div className="kpi-row">
        <Kpi label="Income" value={formatMoney(kpis.income, 'CAD', hideBalances)} delta={kpis.income_delta_pct} goodWhenUp />
        <Kpi label="Expenses" value={formatMoney(kpis.expenses, 'CAD', hideBalances)} delta={kpis.expenses_delta_pct} goodWhenUp={false} />
        <Kpi label="Savings Rate" value={`${kpis.savings_rate}%`} />
        <Kpi label="Txns" value={dashboard.transaction_count} />
      </div>
      {transfer_count > 0 && (
        <div style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--ink-3)', letterSpacing: '0.08em', marginTop: 'calc(-1 * var(--sp-4))', marginBottom: 'var(--sp-4)', textTransform: 'uppercase' }}>
          ↔ {transfer_count} transfer{transfer_count !== 1 ? 's' : ''} excluded from income &amp; expenses
        </div>
      )}

      {/* Cash flow waterfall */}
      <div className="section">
        <div className="section-head">
          <h2>Cash Flow</h2>
          <span className="label num">{days}d window</span>
        </div>
        <Waterfall income={kpis.income} breakdown={spending_breakdown} categoryColors={categoryColors} />
      </div>

      {/* Spending + Merchants */}
      <div className="grid-2 mb-5">
        <div>
          <div className="block-title">Spending by Category</div>
          {(spending_breakdown || []).slice(0, 8).map((cat) => (
            <div
              key={cat.category}
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 90px 48px 1fr',
                alignItems: 'center',
                gap: 'var(--sp-3)',
                padding: 'var(--sp-2) 0',
                borderBottom: '1px solid var(--rule)',
                fontSize: 12,
              }}
            >
              <span>{cat.category}</span>
              <span className="num text-right">{formatMoney(cat.amount, 'CAD', hideBalances)}</span>
              <span className="num text-right muted">{cat.pct_of_total}%</span>
              <div className="bar">
                <div
                  className="bar-fill"
                  style={{
                    width: `${cat.pct_of_total}%`,
                    background: categoryColors[cat.category] || 'var(--ink)',
                    opacity: categoryColors[cat.category] ? 0.85 : 1,
                  }}
                />
              </div>
            </div>
          ))}
        </div>

        <div>
          <div className="block-title">Top Merchants</div>
          <table className="dense" style={{ border: 'none' }}>
            <thead>
              <tr>
                <th>Merchant</th>
                <th className="r">Spent</th>
                <th className="r">N</th>
              </tr>
            </thead>
            <tbody>
              {(top_merchants || []).slice(0, 10).map((m, i) => (
                <tr key={i}>
                  <td>{m.merchant}</td>
                  <td className="num r">{formatMoney(m.amount, 'CAD', hideBalances)}</td>
                  <td className="num r muted">{m.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Daily spending */}
      {dailyData.length > 0 && (
        <div className="section">
          <div className="section-head">
            <h2>Daily Spending</h2>
            <span className="label num">{dailyData.length} days</span>
          </div>
          <div style={{ border: '1px solid var(--ink)', padding: 'var(--sp-4)' }}>
            <ResponsiveContainer width="100%" height={140}>
              <BarChart data={dailyData}>
                <XAxis dataKey="date" tick={{ fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip
                  cursor={{ fill: 'var(--hover)' }}
                  formatter={(v) => [formatMoney(v, 'CAD', hideBalances), 'Spent']}
                />
                <Bar dataKey="amount" fill="var(--ink)" animationDuration={200} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </>
  );
}

function Kpi({ label, value, delta, goodWhenUp }) {
  const hasDelta = delta !== undefined && delta !== null;
  const bad = hasDelta && (goodWhenUp === false ? delta > 0 : delta < 0);
  const good = hasDelta && (goodWhenUp === false ? delta < 0 : delta > 0);
  return (
    <div className="kpi">
      <div className="l">{label}</div>
      <div className="v">{value}</div>
      {hasDelta && (
        <div className={`d ${good ? 'pos' : bad ? 'neg' : ''}`}>{formatDelta(delta)}</div>
      )}
    </div>
  );
}

function EmptyState() {
  const { setView } = useStore();
  return (
    <div style={{ padding: 'var(--sp-8) 0', textAlign: 'center' }}>
      <div className="label mb-3">No Data</div>
      <h2 style={{ fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 700, marginBottom: 'var(--sp-4)', letterSpacing: '-0.01em' }}>
        Import transactions to begin.
      </h2>
      <button type="button" className="btn btn-primary" onClick={() => setView('import')}>Import Data →</button>
    </div>
  );
}
