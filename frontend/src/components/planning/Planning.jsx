import { useEffect, useState } from 'react';
import { api } from '../../api/client';
import { formatCurrency, formatDate } from '../../utils/format';
import { LineChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis, BarChart, Bar, Cell } from 'recharts';

const PERIODS = [
  { p: '1M', l: '1M' },
  { p: '3M', l: '3M' },
  { p: '1Y', l: '1Y' },
  { p: 'ALL', l: 'All' },
];

export default function Planning() {
  const [period, setPeriod] = useState('1Y');
  const [netWorth, setNetWorth] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.getNetWorth(period).catch((e) => ({ error: e.message })),
      api.getCashflowForecast(3).catch((e) => ({ error: e.message })),
    ]).then(([nw, fc]) => {
      setNetWorth(nw);
      setForecast(fc);
      setLoading(false);
    });
  }, [period]);

  if (loading && !netWorth) return <div className="loading label">Loading…</div>;

  const series = (netWorth?.series || []).map((p) => ({
    date: p.date,
    label: formatDate(p.date),
    amount: Math.round(p.amount),
  }));

  const first = series[0]?.amount ?? 0;
  const last = series[series.length - 1]?.amount ?? 0;
  const delta = last - first;
  const deltaPct = first > 0 ? (delta / first) * 100 : 0;

  const months = forecast?.months || [];

  return (
    <>
      <div className="hero-stat">
        <div className="l">Net Worth · {period}</div>
        <div className="v">{formatCurrency(last)}</div>
        <div className="d">
          {delta >= 0 ? '+' : '−'}
          <span className={delta >= 0 ? 'pos' : 'neg'}>{formatCurrency(Math.abs(delta))}</span>
          {' '}({deltaPct.toFixed(1)}%) from {series[0] ? formatDate(series[0].date) : '—'}
        </div>
      </div>

      <div className="flex gap-2 mb-4">
        {PERIODS.map(({ p, l }) => (
          <button key={p} type="button" className={`btn ${p === period ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setPeriod(p)}>
            {l}
          </button>
        ))}
      </div>

      {netWorth?.error && (
        <div className="block mb-5" style={{ borderColor: 'var(--neg)' }}>
          <div className="label neg">Net Worth Error</div>
          <div className="num" style={{ fontSize: 12, marginTop: 6 }}>{netWorth.error}</div>
        </div>
      )}

      {series.length > 0 && (
        <div className="section">
          <div className="section-head">
            <h2>Net Worth · Over Time</h2>
            <span className="label num">{series.length} points</span>
          </div>
          <div style={{ border: '1px solid var(--ink)', padding: 'var(--sp-4)' }}>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={series} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
                <XAxis dataKey="label" tick={{ fontSize: 10 }} axisLine={{ stroke: 'var(--ink)' }} tickLine={false} />
                <YAxis tick={{ fontSize: 10 }} axisLine={{ stroke: 'var(--ink)' }} tickLine={false} width={80} tickFormatter={(v) => formatCurrency(v)} />
                <Tooltip
                  cursor={{ stroke: 'var(--ink)', strokeDasharray: '2 2' }}
                  formatter={(v) => [formatCurrency(v), 'Net Worth']}
                />
                <Line type="monotone" dataKey="amount" stroke="var(--ink)" strokeWidth={2} dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {forecast?.error && (
        <div className="block mb-5" style={{ borderColor: 'var(--neg)' }}>
          <div className="label neg">Forecast Error</div>
          <div className="num" style={{ fontSize: 12, marginTop: 6 }}>{forecast.error}</div>
        </div>
      )}

      {months.length > 0 && (
        <div className="section">
          <div className="section-head">
            <h2>Cash Flow · 3-Month Forecast</h2>
            <span className="label num">
              based on {forecast?.detected_count ?? 0} recurring txns
            </span>
          </div>

          <div className="kpi-row" style={{ gridTemplateColumns: `repeat(${months.length}, 1fr)` }}>
            {months.map((m) => (
              <div key={m.month} className="kpi">
                <div className="l">{m.label || m.month}</div>
                <div className="v">
                  <span className={m.net >= 0 ? 'pos' : 'neg'}>
                    {m.net >= 0 ? '+' : '−'}{formatCurrency(Math.abs(m.net))}
                  </span>
                </div>
                <div className="d">
                  +{formatCurrency(m.projected_in)} · −{formatCurrency(m.projected_out)}
                </div>
              </div>
            ))}
          </div>

          <div style={{ border: '1px solid var(--ink)', borderTop: 'none', padding: 'var(--sp-4)' }}>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={months} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                <XAxis dataKey="label" tick={{ fontSize: 10 }} axisLine={{ stroke: 'var(--ink)' }} tickLine={false} />
                <YAxis tick={{ fontSize: 10 }} axisLine={{ stroke: 'var(--ink)' }} tickLine={false} width={80} tickFormatter={(v) => formatCurrency(v)} />
                <Tooltip formatter={(v) => formatCurrency(v)} />
                <Bar dataKey="net">
                  {months.map((m, i) => (
                    <Cell key={i} fill={m.net >= 0 ? 'var(--pos)' : 'var(--neg)'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {forecast?.recurring && forecast.recurring.length > 0 && (
            <div className="mt-4">
              <div className="section-head">
                <h2>Detected Recurring</h2>
              </div>
              <div className="table-wrap">
                <table className="dense">
                  <thead>
                    <tr>
                      <th>Merchant</th>
                      <th className="r" style={{ width: 130 }}>Avg Amount</th>
                      <th className="r" style={{ width: 100 }}>Cadence</th>
                      <th className="r" style={{ width: 100 }}>Observed</th>
                      <th style={{ width: 100 }}>Last Seen</th>
                    </tr>
                  </thead>
                  <tbody>
                    {forecast.recurring.slice(0, 20).map((r, i) => (
                      <tr key={i}>
                        <td>{r.merchant}</td>
                        <td className={`num r ${r.avg_amount >= 0 ? 'pos' : 'neg'}`}>
                          {r.avg_amount >= 0 ? '+' : '−'}{formatCurrency(Math.abs(r.avg_amount))}
                        </td>
                        <td className="num r muted">{r.cadence_days}d</td>
                        <td className="num r muted">{r.count}×</td>
                        <td className="num muted">{formatDate(r.last_seen)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}
