import { useEffect, useState } from 'react';
import { useStore } from '../../store/ledger';
import { formatCurrency, formatDelta, cn } from '../../utils/format';
import { BarChart, Bar, ResponsiveContainer, Tooltip, XAxis } from 'recharts';

export default function Dashboard() {
  const { dashboard, dashboardLoading, fetchDashboard } = useStore();
  const [days, setDays] = useState(30);

  useEffect(() => { fetchDashboard(days); }, [days]);

  if (dashboardLoading && !dashboard) return <div className="loading">Loading dashboard...</div>;
  if (!dashboard) return <EmptyState />;

  const { kpis, spending_breakdown, top_merchants, daily_spending } = dashboard;

  const dailyData = Object.entries(daily_spending || {}).map(([date, amount]) => ({
    date: new Date(date + 'T00:00:00').toLocaleDateString('en-CA', { month: 'short', day: 'numeric' }),
    amount: Math.round(amount),
  }));

  return (
    <div className="fade-in">
      {/* Period selector */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        {[7, 30, 90, 365].map((d) => (
          <button key={d} className={cn('btn', d === days ? 'btn-primary' : 'btn-ghost')} onClick={() => setDays(d)}>
            {d === 365 ? '1Y' : `${d}d`}
          </button>
        ))}
      </div>

      {/* KPI Strip */}
      <div className="kpi-strip">
        <KpiCard label="Income" value={formatCurrency(kpis.income)} delta={kpis.income_delta_pct} positive />
        <KpiCard label="Expenses" value={formatCurrency(kpis.expenses)} delta={kpis.expenses_delta_pct} />
        <KpiCard label="Savings Rate" value={`${kpis.savings_rate}%`} />
        <KpiCard label="Net Worth" value={formatCurrency(kpis.net_worth)} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
        {/* Spending by Category */}
        <div className="card">
          <div className="card-title">Spending by Category</div>
          <div className="spending-grid">
            {(spending_breakdown || []).slice(0, 8).map((cat) => (
              <div className="spending-row" key={cat.category}>
                <span className="category">{cat.category}</span>
                <span className="amount">{formatCurrency(cat.amount)}</span>
                <span className="pct">{cat.pct_of_total}%</span>
                <span className={cn('delta', cat.delta_pct > 0 ? 'positive' : 'negative')}>
                  {formatDelta(cat.delta_pct)}
                </span>
                <div className="spending-bar">
                  <div className="spending-bar-fill" style={{ width: `${cat.pct_of_total}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Top Merchants */}
        <div className="card">
          <div className="card-title">Top Merchants</div>
          <table className="dense">
            <thead>
              <tr>
                <th>Merchant</th>
                <th className="amount">Spent</th>
                <th className="amount">Txns</th>
              </tr>
            </thead>
            <tbody>
              {(top_merchants || []).slice(0, 10).map((m, i) => (
                <tr key={i}>
                  <td>{m.merchant}</td>
                  <td className="amount mono">{formatCurrency(m.amount)}</td>
                  <td className="amount mono">{m.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Daily Spending Chart */}
      {dailyData.length > 0 && (
        <div className="card" style={{ marginTop: '16px' }}>
          <div className="card-title">Daily Spending</div>
          <ResponsiveContainer width="100%" height={120}>
            <BarChart data={dailyData}>
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#5A5A55' }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ background: '#161616', border: '1px solid #2A2A28', borderRadius: 6, fontSize: 12 }}
                labelStyle={{ color: '#888780' }}
                formatter={(v) => [formatCurrency(v), 'Spent']}
              />
              <Bar dataKey="amount" fill="#1D9E75" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

function KpiCard({ label, value, delta, positive }) {
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {delta !== undefined && (
        <div className={cn('kpi-delta', delta >= 0 ? (positive ? 'positive' : 'negative') : (positive ? 'negative' : 'positive'))}>
          {formatDelta(delta)}
        </div>
      )}
    </div>
  );
}

function EmptyState() {
  const { setView } = useStore();
  return (
    <div style={{ textAlign: 'center', padding: '80px 0' }}>
      <div style={{ fontSize: '48px', marginBottom: '16px' }}>🐾</div>
      <h2 style={{ fontSize: '20px', marginBottom: '8px' }}>No data yet</h2>
      <p style={{ color: 'var(--text-dim)', marginBottom: '24px' }}>Import transactions to see your dashboard</p>
      <button className="btn btn-primary" onClick={() => setView('import')}>Import Data</button>
    </div>
  );
}
