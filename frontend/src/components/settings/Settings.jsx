import { useEffect, useState } from 'react';
import { api } from '../../api/client';

const TABS = [
  { id: 'ai',         label: 'AI' },
  { id: 'categories', label: 'Categories' },
  { id: 'rules',      label: 'Rules' },
  { id: 'room',       label: 'Contribution' },
  { id: 'data',       label: 'Data' },
];

export default function Settings() {
  const [tab, setTab] = useState('ai');

  return (
    <>
      <div className="section-head">
        <h2>Settings</h2>
      </div>

      <div className="tabs">
        {TABS.map(({ id, label }) => (
          <button key={id} type="button" className={`tab ${tab === id ? 'active' : ''}`} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </div>

      {tab === 'ai' && <AIPanel />}
      {tab === 'categories' && <CategoriesPanel />}
      {tab === 'rules' && <RulesPanel />}
      {tab === 'room' && <RoomPanel />}
      {tab === 'data' && <DataPanel />}
    </>
  );
}

function DataPanel() {
  const apiBase = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api').replace(/\/$/, '');
  const token = localStorage.getItem('clawfin_token');
  const [reinferMsg, setReinferMsg] = useState('');
  const [reinferBusy, setReinferBusy] = useState(false);

  const downloadExport = async () => {
    try {
      const res = await fetch(`${apiBase}/settings/export`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const cd = res.headers.get('content-disposition') || '';
      const match = /filename="?([^"]+)"?/.exec(cd);
      const filename = match ? match[1] : 'clawfin-export.db';
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert(`Export failed: ${e.message}`);
    }
  };

  const reinfer = async () => {
    setReinferBusy(true);
    setReinferMsg('');
    try {
      const r = await api.reinferAccountTypes();
      setReinferMsg(`Updated ${r.updated} of ${r.total} accounts.`);
    } catch (e) {
      setReinferMsg(`Error: ${e.message}`);
    }
    setReinferBusy(false);
  };

  return (
    <>
      <div className="block mb-4" style={{ maxWidth: 720 }}>
        <div className="block-title">Database Backup</div>
        <p className="muted mb-4" style={{ fontSize: 12, lineHeight: 1.6 }}>
          Download the full SQLite database file. This contains every account, transaction, holding, rule and setting.
          Store it somewhere safe — it is the single source of truth.
        </p>
        <button type="button" className="btn btn-primary" onClick={downloadExport}>
          Download Backup →
        </button>
        <p className="muted mt-4" style={{ fontSize: 10, fontFamily: 'var(--font-mono)', letterSpacing: '0.05em' }}>
          Location on disk: ~/.clawfin/clawfin.db (CLAWFIN_DB_PATH env override)
        </p>
      </div>

      <div className="block" style={{ maxWidth: 720 }}>
        <div className="block-title">Maintenance</div>
        <div className="flex items-center justify-between mb-3">
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.12em' }}>
              Re-infer Account Types
            </div>
            <div className="muted mt-2" style={{ fontSize: 11, lineHeight: 1.6 }}>
              Older SimpleFin imports came in as "chequing" regardless of type.<br />
              This re-classifies them by name (TFSA, RRSP, credit card, etc.).
            </div>
          </div>
          <button type="button" className="btn btn-primary" onClick={reinfer} disabled={reinferBusy}>
            {reinferBusy ? 'Running…' : 'Run →'}
          </button>
        </div>
        {reinferMsg && <div className="num" style={{ fontSize: 12 }}>{reinferMsg}</div>}
      </div>

      <div className="block mt-4" style={{ maxWidth: 720 }}>
        <div className="block-title">Transfers</div>
        <div className="flex items-center justify-between mb-3">
          <div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.12em' }}>
              Redetect Internal Transfers
            </div>
            <div className="muted mt-2" style={{ fontSize: 11, lineHeight: 1.6 }}>
              Scan your history for matching pairs of transactions (same amount, opposite sign, ≤2 days apart)
              across different accounts. This helps clean up income/expense reports.
            </div>
          </div>
          <button type="button" className="btn btn-primary" onClick={async () => {
            const btn = document.activeElement;
            const origText = btn.innerText;
            btn.innerText = 'Running…';
            btn.disabled = true;
            try {
              const r = await api.redetectTransfers();
              alert(`Scan complete. Found ${r.newly_marked} new transfer pairs. ${r.already_marked} were already marked.`);
            } catch (e) {
              alert(`Error: ${e.message}`);
            }
            btn.innerText = origText;
            btn.disabled = false;
          }}>
            Run →
          </button>
        </div>
      </div>
    </>
  );
}

const PROVIDERS = [
  { id: 'ollama',    label: 'Ollama',    default_base: 'http://localhost:11434' },
  { id: 'openai',    label: 'OpenAI',    default_base: 'https://api.openai.com' },
  { id: 'anthropic', label: 'Anthropic', default_base: 'https://api.anthropic.com' },
];

function AIPanel() {
  const [flags, setFlags] = useState(null);
  const [health, setHealth] = useState(null);
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadAll = async () => {
    try {
      const [fl, h] = await Promise.all([
        api.getAIFlags(),
        api.getAIHealth().catch(() => null),
      ]);
      setFlags(fl);
      setHealth(h);
    } catch {
      // ignore
    }
  };

  useEffect(() => { loadAll(); }, []);

  const test = async () => {
    setTesting(true);
    setHealth(null);
    try {
      setHealth(await api.getAIHealth());
    } catch (e) {
      setHealth({ ok: false, error: e.message });
    }
    setTesting(false);
  };

  const saveFlags = async (patch) => {
    setSaving(true);
    try {
      await api.setAIFlags(patch);
      const next = await api.getAIFlags();
      setFlags(next);
      // Re-test after switching provider
      const h = await api.getAIHealth().catch(() => null);
      setHealth(h);
    } finally {
      setSaving(false);
    }
  };

  const setProvider = (id) => {
    const p = PROVIDERS.find((x) => x.id === id);
    saveFlags({ provider: id, base_url: p?.default_base || '' });
  };
  const setBaseUrl = (v) => saveFlags({ base_url: v });
  const setModel = (m) => saveFlags({ model: m });
  const setApiKey = (v) => saveFlags({ api_key: v });
  const clearApiKey = () => saveFlags({ clear_api_key: true });
  const toggleAI = (on) => saveFlags({ ai_categorization_enabled: on });

  const availableModels = health?.ok && Array.isArray(health.models) ? health.models : [];

  return (
    <>
      <div className="block mb-4" style={{ maxWidth: 720 }}>
        <div className="block-title">Provider</div>

        <div className="flex gap-2 mb-4" role="radiogroup" aria-label="AI provider">
          {PROVIDERS.map((p) => (
            <button
              key={p.id}
              type="button"
              role="radio"
              aria-checked={flags?.provider === p.id}
              className={`btn ${flags?.provider === p.id ? 'btn-primary' : 'btn-ghost'}`}
              onClick={() => setProvider(p.id)}
              disabled={saving}
            >
              {p.label}
            </button>
          ))}
        </div>

        <Row
          label="Endpoint"
          value={
            <input
              type="text"
              value={flags?.base_url || ''}
              onChange={(e) => setFlags((f) => ({ ...f, base_url: e.target.value }))}
              onBlur={(e) => setBaseUrl(e.target.value)}
              style={{ width: 320 }}
            />
          }
        />
        <Row
          label="Model"
          value={
            <span className="flex gap-2 items-center" style={{ width: '100%' }}>
              {availableModels.length > 0 ? (
                <select
                  value={flags?.model || ''}
                  onChange={(e) => setModel(e.target.value)}
                  disabled={saving}
                  style={{ width: 280 }}
                >
                  {availableModels.map((m) => (
                    <option key={m} value={m}>{m}</option>
                  ))}
                  {flags?.model && !availableModels.includes(flags.model) && (
                    <option value={flags.model}>{flags.model}</option>
                  )}
                </select>
              ) : (
                <input
                  type="text"
                  value={flags?.model || ''}
                  onChange={(e) => setFlags((f) => ({ ...f, model: e.target.value }))}
                  onBlur={(e) => setModel(e.target.value)}
                  style={{ width: 280 }}
                  placeholder="model-id"
                />
              )}
            </span>
          }
        />
        <Row
          label="API Key"
          value={
            <span className="flex gap-2 items-center" style={{ width: '100%' }}>
              <input
                type="password"
                placeholder={flags?.has_api_key ? 'Stored — enter new key to replace' : 'API key'}
                onBlur={(e) => {
                  const next = e.target.value.trim();
                  if (next) {
                    setApiKey(next);
                    e.target.value = '';
                  }
                }}
                style={{ width: 320 }}
              />
              {flags?.has_api_key && (
                <button type="button" className="btn btn-ghost" onClick={clearApiKey} disabled={saving}>
                  Clear
                </button>
              )}
            </span>
          }
        />
        {health && (
          <Row
            label="Connection"
            value={
              <span className={health.ok ? 'pos' : 'neg'}>
                {health.ok
                  ? `● REACHABLE${health.models ? ` · ${health.models.length} models` : ''}`
                  : `○ ${(health.error || 'UNREACHABLE').toUpperCase()}`}
              </span>
            }
          />
        )}

        <div className="mt-4 flex gap-2">
          <button type="button" className="btn btn-primary" onClick={test} disabled={testing}>
            {testing ? 'Testing…' : 'Test / Refresh'}
          </button>
          {saving && <span className="label muted">Saving…</span>}
        </div>
      </div>

      <div className="block" style={{ maxWidth: 720 }}>
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="block-title" style={{ marginBottom: 6, paddingBottom: 0, borderBottom: 'none' }}>
              AI Categorization
              <span className="experimental-pill">EXPERIMENTAL</span>
            </div>
            <div className="muted" style={{ fontSize: 11, lineHeight: 1.6 }}>
              When on, the categorizer asks the LLM to classify merchants that rules miss,<br />
              and saves successful matches as new rules. Runs on import + Recategorize All.
            </div>
          </div>
          <Toggle
            checked={!!flags?.ai_categorization_enabled}
            onChange={toggleAI}
          />
        </div>
      </div>
    </>
  );
}

function Toggle({ checked, onChange }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      className={`toggle ${checked ? 'on' : ''}`}
      onClick={() => onChange(!checked)}
    >
      <span className="toggle-knob" />
      <span className="toggle-label">{checked ? 'ON' : 'OFF'}</span>
    </button>
  );
}

const EMOJI_SUGGESTIONS = ['📦', '🛒', '🍽️', '🚌', '🔁', '🏠', '⚡', '↔️', '💰', '🎬', '💊', '🛍️', '🎮', '✈️', '🧾', '📱', '🐾', '💳', '🎁', '💡', '🏦', '🔧', '👶', '📚'];

function CategoriesPanel() {
  const [categories, setCategories] = useState([]);
  const [form, setForm] = useState({ name: '', icon: '📦' });

  const load = () => api.getCategories().then((d) => setCategories(d.categories || []));
  useEffect(() => { load(); }, []);

  const addCat = async () => {
    if (!form.name.trim()) return;
    await api.createCategory({ name: form.name.trim(), icon: form.icon || null });
    setForm({ name: '', icon: '📦' });
    load();
  };

  const delCat = async (id) => { await api.deleteCategory(id); load(); };
  const reset = async () => { await api.resetCategories(); load(); };

  return (
    <div className="block" style={{ maxWidth: 720 }}>
      <div className="flex items-center justify-between mb-3">
        <div className="block-title" style={{ marginBottom: 0, paddingBottom: 0, borderBottom: 'none' }}>Categories</div>
        <button type="button" className="btn btn-ghost" onClick={reset}>Reset Defaults</button>
      </div>
      {categories.map((c) => (
        <div key={c.id} className="settings-row" style={{ gridTemplateColumns: '40px 1fr 80px auto' }}>
          <span style={{ fontSize: 16, textAlign: 'center' }}>{c.icon || '—'}</span>
          <span className="settings-label" style={{ color: 'var(--ink)', textTransform: 'none', letterSpacing: 0, fontFamily: 'var(--font-sans)', fontSize: 13 }}>{c.name}</span>
          <span className="settings-value muted" style={{ fontSize: 10 }}>
            {c.is_default ? 'DEFAULT' : 'CUSTOM'}
          </span>
          <span>
            {!c.is_default && (
              <button type="button" className="btn btn-ghost" onClick={() => delCat(c.id)}>Del</button>
            )}
          </span>
        </div>
      ))}

      <div className="mt-4" style={{ borderTop: '1px solid var(--rule)', paddingTop: 'var(--sp-4)' }}>
        <div className="label mb-3">Add Category</div>
        <div className="flex gap-2 items-center mb-3">
          <input
            value={form.icon}
            onChange={(e) => setForm((f) => ({ ...f, icon: e.target.value }))}
            style={{ width: 56, textAlign: 'center', fontSize: 16 }}
            maxLength={3}
            aria-label="Emoji icon"
          />
          <input
            placeholder="NAME"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            onKeyDown={(e) => e.key === 'Enter' && addCat()}
            style={{ flex: 1 }}
          />
          <button type="button" className="btn btn-primary" onClick={addCat}>Add</button>
        </div>
        <div className="flex gap-2" style={{ flexWrap: 'wrap' }}>
          {EMOJI_SUGGESTIONS.map((e) => (
            <button
              key={e}
              type="button"
              onClick={() => setForm((f) => ({ ...f, icon: e }))}
              style={{
                width: 32, height: 32, border: '1px solid var(--rule-2)',
                background: form.icon === e ? 'var(--accent-tint)' : 'var(--paper)',
                borderColor: form.icon === e ? 'var(--accent)' : 'var(--rule-2)',
                fontSize: 16, cursor: 'pointer',
              }}
            >
              {e}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function RulesPanel() {
  const [rules, setRules] = useState(null);
  const [categories, setCategories] = useState([]);
  const [recatRunning, setRecatRunning] = useState(false);
  const [recatResult, setRecatResult] = useState(null);

  const load = async () => {
    try {
      const [r, c] = await Promise.all([api.getRules(), api.getCategories()]);
      setRules(r.rules || []);
      setCategories(c.categories || []);
    } catch {
      setRules([]);
    }
  };

  useEffect(() => { load(); }, []);

  const updateRule = async (id, category) => {
    await api.updateRule(id, { category });
    load();
  };

  const deleteRule = async (id) => { await api.deleteRule(id); load(); };

  const recategorize = async () => {
    setRecatRunning(true);
    setRecatResult(null);
    try {
      const r = await api.recategorize();
      setRecatResult(r);
    } catch (e) {
      setRecatResult({ error: e.message });
    }
    setRecatRunning(false);
    load();
  };

  if (rules === null) return <div className="loading label">Loading…</div>;

  return (
    <>
      <div className="block mb-4" style={{ maxWidth: 640 }}>
        <div className="flex items-center justify-between">
          <div>
            <div className="block-title" style={{ marginBottom: 6, paddingBottom: 0, borderBottom: 'none' }}>Recategorize</div>
            <div className="muted" style={{ fontSize: 11 }}>Apply all rules + AI to every transaction.</div>
          </div>
          <button type="button" className="btn btn-primary" onClick={recategorize} disabled={recatRunning}>
            {recatRunning ? 'Running…' : 'Run →'}
          </button>
        </div>
        {recatResult && !recatResult.error && (
          <div className="num mt-4" style={{ fontSize: 12 }}>
            {recatResult.updated} updated · {recatResult.total} total
          </div>
        )}
        {recatResult?.error && <div className="num neg mt-4" style={{ fontSize: 12 }}>{recatResult.error}</div>}
      </div>

      <div className="section-head">
        <h2>Rules · {rules.length}</h2>
      </div>

      {rules.length === 0 ? (
        <div className="label">No rules yet — rules are learned as you categorize.</div>
      ) : (
        <div className="table-wrap">
          <table className="dense">
            <thead>
              <tr>
                <th>Pattern (Merchant)</th>
                <th style={{ width: 200 }}>Category</th>
                <th style={{ width: 80 }} className="r">Priority</th>
                <th style={{ width: 80 }} className="r">Regex</th>
                <th style={{ width: 80 }}></th>
              </tr>
            </thead>
            <tbody>
              {rules.map((r) => (
                <tr key={r.id}>
                  <td className="num">{r.pattern}</td>
                  <td>
                    <select
                      value={r.category}
                      onChange={(e) => updateRule(r.id, e.target.value)}
                      style={{ border: 'none', padding: '2px 4px' }}
                    >
                      {categories.map((c) => (
                        <option key={c.id} value={c.name}>{c.name}</option>
                      ))}
                    </select>
                  </td>
                  <td className="num r muted">{r.priority}</td>
                  <td className="num r muted">{r.is_regex ? 'Y' : '—'}</td>
                  <td>
                    <button type="button" className="btn btn-ghost" onClick={() => deleteRule(r.id)}>Del</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function RoomPanel() {
  const [room, setRoom] = useState({});
  const [saved, setSaved] = useState(false);

  useEffect(() => { api.getContributionRoom().then(setRoom); }, []);

  const save = async () => {
    await api.updateContributionRoom(room);
    setSaved(true);
    setTimeout(() => setSaved(false), 1600);
  };

  const fields = [
    { key: 'tfsa_room', label: 'TFSA' },
    { key: 'rrsp_room', label: 'RRSP' },
    { key: 'fhsa_room', label: 'FHSA' },
  ];

  return (
    <div className="block" style={{ maxWidth: 640 }}>
      <div className="block-title">Contribution Room (Canada)</div>
      {fields.map(({ key, label }) => (
        <div key={key} className="settings-row">
          <span className="settings-label">{label}</span>
          <input
            type="number"
            placeholder="0.00"
            value={room[key] ?? ''}
            onChange={(e) => setRoom({ ...room, [key]: e.target.value ? parseFloat(e.target.value) : null })}
            style={{ textAlign: 'right', width: 180 }}
          />
          <span />
        </div>
      ))}
      <button type="button" className="btn btn-primary mt-4" onClick={save}>
        {saved ? 'Saved ✓' : 'Save'}
      </button>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="settings-row">
      <span className="settings-label">{label}</span>
      <span className="settings-value">{value}</span>
      <span />
    </div>
  );
}
