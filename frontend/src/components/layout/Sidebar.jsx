import { useStore } from '../../store/ledger';
import { LayoutDashboard, Briefcase, List, Upload, Settings } from 'lucide-react';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'holdings', label: 'Holdings', icon: Briefcase },
  { id: 'transactions', label: 'Transactions', icon: List },
  { id: 'import', label: 'Import', icon: Upload },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export default function Sidebar() {
  const { currentView, setView } = useStore();

  return (
    <aside className="app-sidebar">
      <div className="logo">
        <svg className="logo-mark" viewBox="-30 -50 60 96" fill="none">
          <ellipse cx="0" cy="2" rx="38" ry="38" fill="#1D9E75" opacity="0.10" />
          <path d="M-18,-36 C-22,-18 -20,4 -16,34" stroke="#1D9E75" strokeWidth="5.5" strokeLinecap="round" />
          <path d="M-2,-40 C-4,-18 -2,4 0,36" stroke="#1D9E75" strokeWidth="5.5" strokeLinecap="round" />
          <path d="M14,-36 C18,-18 16,4 12,34" stroke="#1D9E75" strokeWidth="5.5" strokeLinecap="round" />
          <circle cx="-18" cy="-38" r="3.5" fill="#085041" />
          <circle cx="-2" cy="-42" r="3.5" fill="#085041" />
          <circle cx="14" cy="-38" r="3.5" fill="#085041" />
        </svg>
        <div className="logo-text">
          <span>Claw</span><span>Fin</span>
        </div>
      </div>

      <nav>
        <div className="nav-section">
          <div className="nav-label">Navigation</div>
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
            <div
              key={id}
              className={`nav-item ${currentView === id ? 'active' : ''}`}
              onClick={() => setView(id)}
            >
              <Icon />
              {label}
            </div>
          ))}
        </div>
      </nav>

      <div style={{ flex: 1 }} />

      <div style={{ padding: '0 16px', fontSize: '10px', color: 'var(--text-muted)' }}>
        <div style={{ fontFamily: 'var(--font-mono)' }}>v0.1.0</div>
        <div style={{ marginTop: '4px', opacity: 0.6 }}>⌘K to chat</div>
      </div>
    </aside>
  );
}
