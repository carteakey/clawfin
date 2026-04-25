import { useEffect, useState } from 'react';
import { useStore } from '../../store/ledger';
import { api } from '../../api/client';
import { formatMoney } from '../../utils/format';
import Sparkline from './Sparkline';

const TITLES = {
  dashboard:    'Dashboard',
  accounts:     'Accounts',
  holdings:     'Holdings',
  transactions: 'Transactions',
  recurring:    'Recurring',
  planning:     'Planning',
  import:       'Import',
  settings:     'Settings',
};

export default function Header() {
  const { currentView, theme, setTheme, dashboard, fetchDashboard, hideBalances, toggleHideBalances } = useStore();
  const [sparkPoints, setSparkPoints] = useState([]);

  useEffect(() => {
    if (!dashboard) fetchDashboard();
  }, [dashboard, fetchDashboard]);

  useEffect(() => {
    let cancelled = false;
    api.getNetWorth('3M')
      .then((d) => {
        if (cancelled) return;
        const pts = (d?.series || []).map((p) => p.amount);
        setSparkPoints(pts);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  const netWorth = dashboard?.kpis?.net_worth ?? null;
  const incomeDelta = dashboard?.kpis?.income_delta_pct ?? null;
  const sparkTrend = sparkPoints.length >= 2 ? sparkPoints[sparkPoints.length - 1] - sparkPoints[0] : 0;

  return (
    <header className="app-header">
      <h1>{TITLES[currentView] || 'ClawFin'}</h1>

      <div className="hdr-strip">
        {netWorth !== null && (
          <div className="hdr-stat">
            <span className="l">Net</span>
            <span className="num">{formatMoney(netWorth, 'CAD', hideBalances)}</span>
            {sparkPoints.length >= 2 && (
              <Sparkline
                points={sparkPoints}
                width={60}
                height={16}
                stroke={sparkTrend >= 0 ? 'var(--pos)' : 'var(--neg)'}
              />
            )}
          </div>
        )}
        {incomeDelta !== null && (
          <div className="hdr-stat">
            <span className="l">Δ Inc</span>
            <span className={`num ${incomeDelta >= 0 ? 'pos' : 'neg'}`}>
              {incomeDelta >= 0 ? '+' : ''}{incomeDelta.toFixed(1)}%
            </span>
          </div>
        )}

        <div className="theme-toggle" role="group" aria-label="Theme">
          <button type="button" className={hideBalances ? 'active' : ''} onClick={toggleHideBalances}>
            {hideBalances ? 'Show $' : 'Hide $'}
          </button>
          <button type="button" className={theme === 'dark' ? 'active' : ''} onClick={() => setTheme('dark')}>Dark</button>
          <button type="button" className={theme === 'light' ? 'active' : ''} onClick={() => setTheme('light')}>Light</button>
        </div>

        <kbd>⌘K</kbd>
      </div>
    </header>
  );
}
