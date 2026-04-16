import { formatCurrency } from '../../utils/format';

/*
 * Brutalist cash-flow waterfall. Horizontal bars anchored at a shared scale.
 * Income in pos, each expense category in neg, net at bottom.
 */
export default function Waterfall({ income, breakdown }) {
  if (!income && (!breakdown || breakdown.length === 0)) return null;

  const expenses = (breakdown || []).slice(0, 10);
  const totalExpenses = expenses.reduce((s, c) => s + c.amount, 0);
  const net = income - totalExpenses;
  const max = Math.max(income, totalExpenses) || 1;

  const pct = (v) => `${(Math.abs(v) / max) * 100}%`;

  return (
    <div style={{ border: '1px solid var(--ink)' }}>
      <Row
        label="Income"
        amount={income}
        pct={pct(income)}
        side="pos"
      />
      {expenses.map((c) => (
        <Row
          key={c.category}
          label={c.category}
          amount={-c.amount}
          pct={pct(c.amount)}
          side="neg"
          muted
        />
      ))}
      <Row
        label="Net"
        amount={net}
        pct={pct(net)}
        side={net >= 0 ? 'pos' : 'neg'}
        emphasis
      />
    </div>
  );
}

function Row({ label, amount, pct, side, muted, emphasis }) {
  const color = side === 'pos' ? 'var(--pos)' : 'var(--neg)';
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '160px 1fr 140px',
        alignItems: 'center',
        gap: 'var(--sp-3)',
        padding: '6px var(--sp-3)',
        borderBottom: '1px solid var(--rule)',
        fontSize: 12,
        background: emphasis ? 'var(--accent-tint)' : 'transparent',
      }}
    >
      <span
        style={{
          fontFamily: emphasis ? 'var(--font-mono)' : 'var(--font-sans)',
          fontWeight: emphasis ? 700 : 400,
          letterSpacing: emphasis ? '0.08em' : 0,
          textTransform: emphasis ? 'uppercase' : 'none',
          color: muted ? 'var(--ink-2)' : 'var(--ink)',
          fontSize: emphasis ? 11 : 12,
        }}
      >
        {label}
      </span>
      <div
        style={{
          position: 'relative',
          height: emphasis ? 18 : 12,
          background: 'var(--paper-2)',
          borderLeft: '1px solid var(--rule-2)',
          borderRight: '1px solid var(--rule-2)',
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: 0,
            bottom: 0,
            width: pct,
            background: color,
            [side === 'pos' ? 'left' : 'right']: 0,
          }}
        />
      </div>
      <span
        className="num"
        style={{
          textAlign: 'right',
          color,
          fontWeight: emphasis ? 700 : 400,
          fontSize: emphasis ? 13 : 12,
        }}
      >
        {amount >= 0 ? '+' : '−'}
        {formatCurrency(Math.abs(amount))}
      </span>
    </div>
  );
}
