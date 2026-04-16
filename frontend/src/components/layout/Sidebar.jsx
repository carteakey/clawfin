import { useStore } from '../../store/ledger';

const NAV_ITEMS = [
  { id: 'dashboard',    label: 'Dashboard' },
  { id: 'accounts',     label: 'Accounts' },
  { id: 'holdings',     label: 'Holdings' },
  { id: 'transactions', label: 'Transactions' },
  { id: 'recurring',    label: 'Recurring' },
  { id: 'planning',     label: 'Planning' },
  { id: 'import',       label: 'Import' },
  { id: 'settings',     label: 'Settings' },
];

export default function Sidebar() {
  const { currentView, setView } = useStore();

  return (
    <aside className="app-sidebar">
      <div className="logo">
        <div className="logo-text">ClawFin</div>
      </div>

      <nav>
        <div className="nav-label">Nav</div>
        {NAV_ITEMS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            className={`nav-item ${currentView === id ? 'active' : ''}`}
            onClick={() => setView(id)}
          >
            {label}
          </button>
        ))}
      </nav>

      <div style={{ flex: 1 }} />

      <div style={{ padding: '0 16px', fontFamily: 'var(--font-mono)', fontSize: '9px', color: 'var(--ink-3)', letterSpacing: '0.12em', textTransform: 'uppercase' }}>
        <div>v0.1.0</div>
        <div style={{ marginTop: '4px' }}>⌘K · Palette</div>
        <div style={{ marginTop: '2px' }}>⇧⌘K · Chat</div>
      </div>
    </aside>
  );
}
