import { useEffect, useMemo, useState } from 'react';
import { api } from '../../api/client';
import { formatCurrency, formatDate } from '../../utils/format';

export default function Recurring() {
  const [data, setData] = useState(null);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('ALL');

  const load = () => {
    setLoading(true);
    Promise.all([
      api.getRecurring().catch((e) => ({ error: e.message })),
      api.getCategories().then((d) => d.categories || []).catch(() => []),
    ]).then(([rec, cats]) => {
      setData(rec);
      setCategories(cats);
      setLoading(false);
    });
  };

  useEffect(() => { load(); }, []);

  const rows = useMemo(() => {
    const list = data?.recurring || [];
    return filter === 'ALL' ? list : list.filter((r) => r.category === filter);
  }, [data, filter]);

  const counts = useMemo(() => {
    const out = { ALL: 0 };
    for (const r of data?.recurring || []) {
      out.ALL += 1;
      out[r.category] = (out[r.category] || 0) + 1;
    }
    return out;
  }, [data]);

  const chipOrder = useMemo(() => {
    const present = new Set(Object.keys(counts).filter((k) => k !== 'ALL'));
    const ordered = categories.filter((c) => present.has(c.name)).map((c) => c.name);
    // Include any categories present but not in the main category list
    for (const k of present) if (!ordered.includes(k)) ordered.push(k);
    return ordered;
  }, [categories, counts]);

  const updateCategory = async (row, newCategory) => {
    setData((d) => ({
      ...d,
      recurring: d.recurring.map((r) =>
        r.merchant === row.merchant ? { ...r, category: newCategory } : r
      ),
    }));
    try {
      await api.createRule({ pattern: row.merchant, category: newCategory, priority: 1 });
    } catch (e) {
      console.error('save rule failed', e);
    }
  };

  if (loading && !data) return <div className="loading label">Scanning…</div>;
  if (data?.error) return (
    <div className="block" style={{ borderColor: 'var(--neg)' }}>
      <div className="label neg">Error</div>
      <div className="num" style={{ fontSize: 12, marginTop: 6 }}>{data.error}</div>
    </div>
  );

  const byCategory = data?.by_category || {};

  return (
    <>
      <div className="hero-stat">
        <div className="l">Recurring · Monthly Run-Rate</div>
        <div className="v">{formatCurrency(data?.total_monthly ?? 0)}</div>
        <div className="d">
          {formatCurrency(data?.total_annual ?? 0)} annual · {data?.count ?? 0} detected ·
          <span className="muted"> ≥3 charges, 6–35d cadence, ±15% amount</span>
        </div>
      </div>

      {Object.keys(byCategory).length > 0 && (
        <div className="kpi-row" style={{ gridTemplateColumns: `repeat(${Math.min(Object.keys(byCategory).length, 4)}, 1fr)` }}>
          {Object.entries(byCategory).slice(0, 4).map(([cat, annual]) => (
            <div key={cat} className="kpi">
              <div className="l">{cat}</div>
              <div className="v">{formatCurrency(annual)}</div>
              <div className="d muted">annual</div>
            </div>
          ))}
        </div>
      )}

      <div className="section-head">
        <h2>Detected</h2>
        <button type="button" className="btn btn-ghost" onClick={load}>Rescan</button>
      </div>

      <div className="chips">
        <button
          type="button"
          className={`chip ${filter === 'ALL' ? 'active' : ''}`}
          onClick={() => setFilter('ALL')}
        >
          All <span className="count">{counts.ALL || 0}</span>
        </button>
        {chipOrder.map((name) => {
          const cat = categories.find((c) => c.name === name);
          return (
            <button
              key={name}
              type="button"
              className={`chip ${filter === name ? 'active' : ''}`}
              onClick={() => setFilter(filter === name ? 'ALL' : name)}
            >
              {cat?.icon && <span>{cat.icon}</span>} {name}
              {counts[name] > 0 && <span className="count">{counts[name]}</span>}
            </button>
          );
        })}
      </div>

      {rows.length === 0 ? (
        <div className="label" style={{ padding: 'var(--sp-5)' }}>
          {filter === 'ALL'
            ? 'Nothing detected yet. Import a few months of transactions first.'
            : `No recurring in ${filter}.`}
        </div>
      ) : (
        <div className="table-wrap">
          <table className="dense">
            <thead>
              <tr>
                <th>Merchant</th>
                <th style={{ width: 180 }}>Category</th>
                <th className="r" style={{ width: 120 }}>Avg Charge</th>
                <th className="r" style={{ width: 80 }}>Cadence</th>
                <th className="r" style={{ width: 130 }}>Annual</th>
                <th style={{ width: 90 }}>Last</th>
                <th style={{ width: 90 }}>Next</th>
                <th className="r" style={{ width: 50 }}>N</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => (
                <tr key={s.merchant}>
                  <td>{s.display_name}</td>
                  <td>
                    <select
                      value={s.category}
                      onChange={(e) => updateCategory(s, e.target.value)}
                      className="cat-select"
                    >
                      {categories.map((c) => (
                        <option key={c.id} value={c.name}>
                          {c.icon ? `${c.icon} ` : ''}{c.name}
                        </option>
                      ))}
                      {!categories.some((c) => c.name === s.category) && (
                        <option value={s.category}>{s.category}</option>
                      )}
                    </select>
                  </td>
                  <td className="num r neg">−{formatCurrency(s.avg_amount, s.currency)}</td>
                  <td className="num r muted">{s.cadence_days}d</td>
                  <td className="num r"><strong>{formatCurrency(s.annual_cost, s.currency)}</strong></td>
                  <td className="num muted">{formatDate(s.last_charge)}</td>
                  <td className="num">{formatDate(s.next_estimated)}</td>
                  <td className="num r muted">{s.count}×</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
