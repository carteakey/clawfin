import { useEffect } from 'react';
import { useStore } from './store/ledger';
import { api } from './api/client';
import Sidebar from './components/layout/Sidebar';
import Header from './components/layout/Header';
import Dashboard from './components/dashboard/Dashboard';
import Holdings from './components/holdings/Holdings';
import Accounts from './components/accounts/Accounts';
import Transactions from './components/transactions/Transactions';
import Planning from './components/planning/Planning';
import Recurring from './components/recurring/Recurring';
import ImportView from './components/import/ImportView';
import Settings from './components/settings/Settings';
import ChatPanel from './components/chat/ChatPanel';
import CommandPalette from './components/palette/CommandPalette';
import Login from './components/auth/Login';

export default function App() {
  const {
    isAuthenticated, authRequired, currentView,
    chatOpen, toggleChat,
    togglePalette,
  } = useStore();

  useEffect(() => {
    api.checkAuth().then((data) => {
      useStore.setState({ authRequired: data.auth_required });
    });
  }, []);

  // ⌘K = palette, Shift+⌘K = chat
  useEffect(() => {
    function onKey(e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        if (e.shiftKey) {
          toggleChat();
        } else {
          togglePalette();
        }
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [toggleChat, togglePalette]);

  if (authRequired === null) return null;
  if (authRequired && !isAuthenticated) return <Login />;

  const views = {
    dashboard:    <Dashboard />,
    holdings:     <Holdings />,
    accounts:     <Accounts />,
    transactions: <Transactions />,
    recurring:    <Recurring />,
    planning:     <Planning />,
    import:       <ImportView />,
    settings:     <Settings />,
  };

  return (
    <div className="app-shell">
      <Sidebar />
      <Header />
      <main className="app-main">
        {views[currentView] || <Dashboard />}
      </main>
      <ChatPanel />
      <CommandPalette />
      {!chatOpen && (
        <button type="button" className="chat-toggle" onClick={toggleChat} title="Chat (⇧⌘K)" aria-label="Open chat">
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 700, letterSpacing: '0.05em' }}>ASK</span>
        </button>
      )}
    </div>
  );
}
