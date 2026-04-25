import { useStore } from '../../store/ledger';

const PRIMARY_NAV = [
  { id: 'dashboard',    label: 'Dashboard' },
  { id: 'accounts',     label: 'Accounts' },
  { id: 'transactions', label: 'Transactions' },
  { id: 'recurring',    label: 'Recurring' },
  { id: 'planning',     label: 'Planning' },
];

const UTILITY_NAV = [
  { id: 'holdings',     label: 'Holdings' },
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
        {PRIMARY_NAV.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            className={`nav-item ${currentView === id ? 'active' : ''}`}
            onClick={() => setView(id)}
          >
            {label}
          </button>
        ))}

        <div className="nav-divider" />

        <div className="nav-label">Tools</div>
        {UTILITY_NAV.map(({ id, label }) => (
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
