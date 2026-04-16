import { useEffect, useState } from 'react';
import { useStore } from '../../store/ledger';
import { formatCurrency, formatDelta } from '../../utils/format';
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
  const [days, setDays] = useState(30);

  useEffect(() => { fetchDashboard(days); }, [days]);

  if (dashboardLoading && !dashboard) return <div className="loading label">Loading…</div>;
  if (!dashboard) return <EmptyState />;

  const { kpis, spending_breakdown, top_merchants, daily_spending } = dashboard;

  const dailyData = Object.entries(daily_spending || {}).map(([date, amount]) => ({
    date: new Date(date + 'T00:00:00').toLocaleDateString('en-CA', { month: 'short', day: 'numeric' }),
    amount: Math.round(amount),
  }));

  return (
    <>
      {/* Hero net worth */}
      <div className="hero-stat">
        <div className="l">Net Worth</div>
        <div className="v">{formatCurrency(kpis.net_worth)}</div>
        <div className="d">
          Income {formatCurrency(kpis.income)} · Expenses {formatCurrency(kpis.expenses)} · Savings {kpis.savings_rate}%
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
        <Kpi label="Income" value={formatCurrency(kpis.income)} delta={kpis.income_delta_pct} goodWhenUp />
        <Kpi label="Expenses" value={formatCurrency(kpis.expenses)} delta={kpis.expenses_delta_pct} goodWhenUp={false} />
        <Kpi label="Savings Rate" value={`${kpis.savings_rate}%`} />
        <Kpi label="Txns" value={dashboard.transaction_count} />
      </div>

      {/* Cash flow waterfall */}
      <div className="section">
        <div className="section-head">
          <h2>Cash Flow</h2>
          <span className="label num">{days}d window</span>
        </div>
        <Waterfall income={kpis.income} breakdown={spending_breakdown} />
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
              <span className="num text-right">{formatCurrency(cat.amount)}</span>
              <span className="num text-right muted">{cat.pct_of_total}%</span>
              <div className="bar">
                <div className="bar-fill" style={{ width: `${cat.pct_of_total}%` }} />
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
                  <td className="num r">{formatCurrency(m.amount)}</td>
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
                  formatter={(v) => [formatCurrency(v), 'Spent']}
                />
                <Bar dataKey="amount" fill="var(--ink)" />
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
