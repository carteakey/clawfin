import { useEffect, useMemo, useState } from 'react';
import { api } from '../../api/client';
import { formatCurrency, formatDate } from '../../utils/format';
import { LineChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis, BarChart, Bar, Cell } from 'recharts';

const PERIODS = [
  { p: '1M', l: '1M' },
  { p: '3M', l: '3M' },
  { p: '1Y', l: '1Y' },
  { p: 'ALL', l: 'All' },
];

const CASH_ACCOUNT_TYPES = new Set(['chequing', 'savings']);
const ROOM_FIELDS = [
  { key: 'tfsa_room', label: 'TFSA' },
  { key: 'rrsp_room', label: 'RRSP' },
  { key: 'fhsa_room', label: 'FHSA' },
];

function addDays(dateStr, days) {
  const d = new Date(`${dateStr}T00:00:00`);
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

function roundMoney(value) {
  return Math.round((Number(value) || 0) * 100) / 100;
}

function parseScenarioNumber(value) {
  if (value === '' || value === null || value === undefined) return 0;
  return Number(value) || 0;
}

export default function Planning() {
  const [period, setPeriod] = useState('1Y');
  const [netWorth, setNetWorth] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [accounts, setAccounts] = useState([]);
  const [room, setRoom] = useState({});
  const [loading, setLoading] = useState(true);
  const [scenario, setScenario] = useState({
    monthlySavings: 500,
    annualReturn: 5,
    oneOffExpense: 0,
  });

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.getNetWorth(period).catch((e) => ({ error: e.message })),
      api.getCashflowForecast(6).catch((e) => ({ error: e.message })),
      api.getAccounts().catch((e) => ({ error: e.message, accounts: [] })),
      api.getContributionRoom().catch((e) => ({ error: e.message })),
    ]).then(([nw, fc, accts, contributionRoom]) => {
      setNetWorth(nw);
      setForecast(fc);
      setAccounts(accts?.accounts || []);
      setRoom(contributionRoom || {});
      setLoading(false);
    });
  }, [period]);

  const planning = useMemo(() => {
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
    const firstThreeMonths = months.slice(0, 3);
    const threeMonthNet = roundMoney(firstThreeMonths.reduce((sum, m) => sum + (m.net || 0), 0));
    const avgMonthlyOut = months.length
      ? months.reduce((sum, m) => sum + (m.projected_out || 0), 0) / months.length
      : 0;
    const avgNetOutflow = months.length
      ? months.reduce((sum, m) => sum + Math.max(0, (m.projected_out || 0) - (m.projected_in || 0)), 0) / months.length
      : 0;

    const cashAccounts = accounts.filter((a) => CASH_ACCOUNT_TYPES.has(a.account_type) && a.on_budget !== false);
    const cashBalance = roundMoney(cashAccounts.reduce((sum, a) => sum + (a.balance || 0), 0));
    const runwayMonths = avgNetOutflow > 0 ? cashBalance / avgNetOutflow : null;

    const obligations = (forecast?.recurring || [])
      .filter((r) => r.avg_amount < 0)
      .map((r) => {
        const monthlyEquivalent = Math.abs(r.avg_amount) * (30 / Math.max(1, r.cadence_days || 30));
        return {
          ...r,
          monthlyEquivalent: roundMoney(monthlyEquivalent),
          annualCost: roundMoney(monthlyEquivalent * 12),
          nextCharge: r.last_seen ? addDays(r.last_seen, r.cadence_days || 30) : null,
        };
      })
      .sort((a, b) => b.monthlyEquivalent - a.monthlyEquivalent);

    const recurringMonthly = roundMoney(obligations.reduce((sum, r) => sum + r.monthlyEquivalent, 0));
    const recurringAnnual = roundMoney(recurringMonthly * 12);

    const staleAccounts = accounts.filter((a) => a.stale_reason || a.last_sync_error || a.simplefin_account_present === false);
    const negativeMonths = months.filter((m) => m.net < 0);
    const alerts = [];
    if (runwayMonths !== null && runwayMonths < 3) {
      alerts.push({
        label: 'Cash runway is tight',
        detail: `${runwayMonths.toFixed(1)} months at the current projected burn.`,
      });
    }
    if (negativeMonths.length > 0) {
      alerts.push({
        label: `${negativeMonths.length} negative forecast month${negativeMonths.length === 1 ? '' : 's'}`,
        detail: negativeMonths.map((m) => m.label || m.month).join(', '),
      });
    }
    if (staleAccounts.length > 0) {
      alerts.push({
        label: `${staleAccounts.length} account${staleAccounts.length === 1 ? '' : 's'} need sync attention`,
        detail: staleAccounts.slice(0, 3).map((a) => a.name).join(', '),
      });
    }
    if (!forecast?.error && obligations.length === 0) {
      alerts.push({
        label: 'No recurring obligations detected',
        detail: 'Forecast confidence will improve after more recurring history is imported.',
      });
    }

    const monthlySavings = parseScenarioNumber(scenario.monthlySavings);
    const annualReturn = parseScenarioNumber(scenario.annualReturn);
    const oneOffExpense = parseScenarioNumber(scenario.oneOffExpense);
    const scenarioBase = last + (monthlySavings * 12) - oneOffExpense;
    const projected12MonthNetWorth = roundMoney(scenarioBase + (last * (annualReturn / 100)));

    return {
      series,
      first,
      last,
      delta,
      deltaPct,
      months,
      threeMonthNet,
      avgMonthlyOut: roundMoney(avgMonthlyOut),
      avgNetOutflow: roundMoney(avgNetOutflow),
      cashBalance,
      runwayMonths,
      obligations,
      recurringMonthly,
      recurringAnnual,
      staleAccounts,
      alerts,
      projected12MonthNetWorth,
      scenarioDelta: roundMoney(projected12MonthNetWorth - last),
    };
  }, [accounts, forecast, netWorth, scenario]);

  if (loading && !netWorth) return <div className="loading label">Loading...</div>;

  const runwayLabel = planning.runwayMonths === null
    ? 'Positive cash flow'
    : `${planning.runwayMonths.toFixed(1)} mo`;

  return (
    <>
      <div className="hero-stat">
        <div className="l">Planning · {period}</div>
        <div className="v">{formatCurrency(planning.last)}</div>
        <div className="d">
          {planning.delta >= 0 ? '+' : '-'}
          <span className={planning.delta >= 0 ? 'pos' : 'neg'}>{formatCurrency(Math.abs(planning.delta))}</span>
          {' '}({planning.deltaPct.toFixed(1)}%) from {planning.series[0] ? formatDate(planning.series[0].date) : '-'}
        </div>
      </div>

      <div className="flex gap-2 mb-4">
        {PERIODS.map(({ p, l }) => (
          <button key={p} type="button" className={`btn ${p === period ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setPeriod(p)}>
            {l}
          </button>
        ))}
      </div>

      {(netWorth?.error || forecast?.error || room?.error) && (
        <div className="block mb-5" style={{ borderColor: 'var(--neg)' }}>
          <div className="label neg">Planning Data Error</div>
          <div className="num" style={{ fontSize: 12, marginTop: 6 }}>
            {[netWorth?.error, forecast?.error, room?.error].filter(Boolean).join(' | ')}
          </div>
        </div>
      )}

      <div className="kpi-row">
        <div className="kpi">
          <div className="l">Cash Runway</div>
          <div className={`v ${planning.runwayMonths !== null && planning.runwayMonths < 3 ? 'neg' : ''}`}>{runwayLabel}</div>
          <div className="d">{formatCurrency(planning.cashBalance)} cash</div>
        </div>
        <div className="kpi">
          <div className="l">Monthly Burn</div>
          <div className="v">{formatCurrency(planning.avgNetOutflow)}</div>
          <div className="d">{formatCurrency(planning.avgMonthlyOut)} projected out</div>
        </div>
        <div className="kpi">
          <div className="l">3M Net</div>
          <div className={`v ${planning.threeMonthNet >= 0 ? 'pos' : 'neg'}`}>
            {planning.threeMonthNet >= 0 ? '+' : '-'}{formatCurrency(Math.abs(planning.threeMonthNet))}
          </div>
          <div className="d">forecast cash surplus</div>
        </div>
        <div className="kpi">
          <div className="l">Recurring / Mo</div>
          <div className="v">{formatCurrency(planning.recurringMonthly)}</div>
          <div className="d">{formatCurrency(planning.recurringAnnual)} annualized</div>
        </div>
      </div>

      <div className="section">
        <div className="section-head">
          <h2>Scenario</h2>
          <span className="label num">12 month projection</span>
        </div>
        <div className="grid-2 mb-4">
          <div>
            <div className="block-title">Assumptions</div>
            <label className="label mb-2" htmlFor="monthly-savings">Monthly Savings</label>
            <input
              id="monthly-savings"
              type="number"
              value={scenario.monthlySavings}
              onChange={(e) => setScenario({ ...scenario, monthlySavings: e.target.value })}
              style={{ marginBottom: 'var(--sp-3)' }}
            />
            <label className="label mb-2" htmlFor="annual-return">Expected Return %</label>
            <input
              id="annual-return"
              type="number"
              value={scenario.annualReturn}
              onChange={(e) => setScenario({ ...scenario, annualReturn: e.target.value })}
              style={{ marginBottom: 'var(--sp-3)' }}
            />
            <label className="label mb-2" htmlFor="one-off-expense">One-Off Expense</label>
            <input
              id="one-off-expense"
              type="number"
              value={scenario.oneOffExpense}
              onChange={(e) => setScenario({ ...scenario, oneOffExpense: e.target.value })}
            />
          </div>
          <div>
            <div className="block-title">Result</div>
            <div className="label mb-2">Projected Net Worth</div>
            <div className="num" style={{ fontSize: 34, fontWeight: 700 }}>{formatCurrency(planning.projected12MonthNetWorth)}</div>
            <div className="num mt-2">
              <span className={planning.scenarioDelta >= 0 ? 'pos' : 'neg'}>
                {planning.scenarioDelta >= 0 ? '+' : '-'}{formatCurrency(Math.abs(planning.scenarioDelta))}
              </span>
              {' '}vs today
            </div>
          </div>
        </div>
      </div>

      {planning.alerts.length > 0 && (
        <div className="section">
          <div className="section-head">
            <h2>Actionable Gaps</h2>
            <span className="label num">{planning.alerts.length} item{planning.alerts.length === 1 ? '' : 's'}</span>
          </div>
          <div className="table-wrap">
            <table className="dense">
              <thead>
                <tr>
                  <th>Gap</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {planning.alerts.map((alert) => (
                  <tr key={alert.label}>
                    <td style={{ fontWeight: 700 }}>{alert.label}</td>
                    <td className="muted">{alert.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {planning.months.length > 0 && (
        <div className="section">
          <div className="section-head">
            <h2>Cash Flow Forecast</h2>
            <span className="label num">based on {forecast?.detected_count ?? 0} recurring txns</span>
          </div>

          <div className="kpi-row" style={{ gridTemplateColumns: `repeat(${Math.min(planning.months.length, 6)}, 1fr)` }}>
            {planning.months.map((m) => (
              <div key={m.month} className="kpi">
                <div className="l">{m.label || m.month}</div>
                <div className="v">
                  <span className={m.net >= 0 ? 'pos' : 'neg'}>
                    {m.net >= 0 ? '+' : '-'}{formatCurrency(Math.abs(m.net))}
                  </span>
                </div>
                <div className="d">
                  +{formatCurrency(m.projected_in)} / -{formatCurrency(m.projected_out)}
                </div>
              </div>
            ))}
          </div>

          <div style={{ border: '1px solid var(--ink)', borderTop: 'none', padding: 'var(--sp-4)' }}>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={planning.months} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
                <XAxis dataKey="label" tick={{ fontSize: 10 }} axisLine={{ stroke: 'var(--ink)' }} tickLine={false} />
                <YAxis tick={{ fontSize: 10 }} axisLine={{ stroke: 'var(--ink)' }} tickLine={false} width={80} tickFormatter={(v) => formatCurrency(v)} />
                <Tooltip formatter={(v) => formatCurrency(v)} />
                <Bar dataKey="net" animationDuration={200}>
                  {planning.months.map((m, i) => (
                    <Cell key={i} fill={m.net >= 0 ? 'var(--pos)' : 'var(--neg)'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      <div className="section">
        <div className="section-head">
          <h2>Contribution Room</h2>
          <span className="label num">Canada</span>
        </div>
        <div className="kpi-row" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
          {ROOM_FIELDS.map(({ key, label }) => (
            <div key={key} className="kpi">
              <div className="l">{label}</div>
              <div className="v">{room[key] === null || room[key] === undefined ? '-' : formatCurrency(room[key])}</div>
              <div className="d">available room</div>
            </div>
          ))}
        </div>
      </div>

      {planning.obligations.length > 0 && (
        <div className="section">
          <div className="section-head">
            <h2>Recurring Obligations</h2>
            <span className="label num">{planning.obligations.length} detected</span>
          </div>
          <div className="table-wrap">
            <table className="dense">
              <thead>
                <tr>
                  <th>Merchant</th>
                  <th className="r" style={{ width: 130 }}>Monthly Eq.</th>
                  <th className="r" style={{ width: 130 }}>Annual</th>
                  <th className="r" style={{ width: 100 }}>Cadence</th>
                  <th style={{ width: 120 }}>Next Charge</th>
                  <th className="r" style={{ width: 100 }}>Observed</th>
                </tr>
              </thead>
              <tbody>
                {planning.obligations.slice(0, 30).map((r, i) => (
                  <tr key={`${r.merchant}-${i}`}>
                    <td>{r.merchant}</td>
                    <td className="num r neg">-{formatCurrency(r.monthlyEquivalent)}</td>
                    <td className="num r muted">{formatCurrency(r.annualCost)}</td>
                    <td className="num r muted">{r.cadence_days}d</td>
                    <td className="num muted">{r.nextCharge ? formatDate(r.nextCharge) : '-'}</td>
                    <td className="num r muted">{r.count}x</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {planning.series.length > 0 && (
        <div className="section">
          <div className="section-head">
            <h2>Net Worth Over Time</h2>
            <span className="label num">{planning.series.length} points</span>
          </div>
          <div style={{ border: '1px solid var(--ink)', padding: 'var(--sp-4)' }}>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={planning.series} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
                <XAxis dataKey="label" tick={{ fontSize: 10 }} axisLine={{ stroke: 'var(--ink)' }} tickLine={false} />
                <YAxis tick={{ fontSize: 10 }} axisLine={{ stroke: 'var(--ink)' }} tickLine={false} width={80} tickFormatter={(v) => formatCurrency(v)} />
                <Tooltip
                  cursor={{ stroke: 'var(--ink)', strokeDasharray: '2 2' }}
                  formatter={(v) => [formatCurrency(v), 'Net Worth']}
                />
                <Line type="monotone" dataKey="amount" stroke="var(--ink)" strokeWidth={2} dot={false} animationDuration={200} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </>
  );
}
