import { useEffect, useCallback } from 'react';
import { useStore } from './store/ledger';
import { api } from './api/client';
import Sidebar from './components/layout/Sidebar';
import Header from './components/layout/Header';
import Dashboard from './components/dashboard/Dashboard';
import Holdings from './components/holdings/Holdings';
import Transactions from './components/transactions/Transactions';
import ImportView from './components/import/ImportView';
import Settings from './components/settings/Settings';
import ChatPanel from './components/chat/ChatPanel';
import Login from './components/auth/Login';

export default function App() {
  const { isAuthenticated, authRequired, currentView, chatOpen, toggleChat } = useStore();

  // Check if auth is required
  useEffect(() => {
    api.checkAuth().then((data) => {
      useStore.setState({ authRequired: data.auth_required });
    });
  }, []);

  // ⌘K to toggle chat
  useEffect(() => {
    function onKey(e) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        toggleChat();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [toggleChat]);

  // Show login if auth required and not authenticated
  if (authRequired === null) return null; // loading
  if (authRequired && !isAuthenticated) return <Login />;

  const views = {
    dashboard: <Dashboard />,
    holdings: <Holdings />,
    transactions: <Transactions />,
    import: <ImportView />,
    settings: <Settings />,
  };

  return (
    <div className="app-shell">
      <Sidebar />
      <Header />
      <main className="app-main">
        {views[currentView] || <Dashboard />}
      </main>
      <ChatPanel />
      {!chatOpen && (
        <button className="chat-toggle" onClick={toggleChat} title="Chat (⌘K)">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="m3 21 1.9-5.7a8.5 8.5 0 1 1 3.8 3.8z" />
          </svg>
        </button>
      )}
    </div>
  );
}
