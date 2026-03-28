import { useStore } from '../../store/ledger';
import { RefreshCw } from 'lucide-react';

export default function Header() {
  const { currentView } = useStore();

  const titles = {
    dashboard: 'Dashboard',
    holdings: 'Holdings',
    transactions: 'Transactions',
    import: 'Import Data',
    settings: 'Settings',
  };

  return (
    <header className="app-header">
      <h1 style={{ fontSize: '15px', fontWeight: 500 }}>{titles[currentView] || 'ClawFin'}</h1>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <kbd>⌘K</kbd>
      </div>
    </header>
  );
}
