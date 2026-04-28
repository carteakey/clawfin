import { create } from 'zustand';
import { api } from '../api/client';

export const useStore = create((set, get) => ({
  // Auth
  isAuthenticated: !!localStorage.getItem('clawfin_token'),
  authRequired: null,
  setAuthenticated: (v) => set({ isAuthenticated: v }),

  // Theme
  theme: document.documentElement.dataset.theme || 'dark',
  setTheme: (t) => {
    document.documentElement.dataset.theme = t;
    localStorage.setItem('clawfin_theme', t);
    set({ theme: t });
  },
  hideBalances: localStorage.getItem('clawfin_hide_balances') === 'true',
  toggleHideBalances: () => set((s) => {
    const next = !s.hideBalances;
    localStorage.setItem('clawfin_hide_balances', String(next));
    return { hideBalances: next };
  }),

  // Navigation
  currentView: 'dashboard',
  setView: (view) => set({ currentView: view }),

  // Dashboard
  dashboard: null,
  dashboardLoading: false,
  fetchDashboard: async (params = 30) => {
    set({ dashboardLoading: true });
    const data = await api.getDashboard(params);
    set({ dashboard: data, dashboardLoading: false });
  },

  // Transactions
  selectedAccountId: '',
  setSelectedAccountId: (id) => set({ selectedAccountId: id }),
  transactions: [],
  transactionsTotal: 0,
  transactionsLoading: false,
  fetchTransactions: async (params = {}) => {
    set({ transactionsLoading: true });
    const data = await api.getTransactions(params);
    set({ transactions: data.transactions || [], transactionsTotal: data.total || 0, transactionsLoading: false });
  },

  // Holdings
  holdings: null,
  holdingsLoading: false,
  fetchHoldings: async (asOf) => {
    set({ holdingsLoading: true });
    const data = await api.getHoldings(asOf);
    set({ holdings: data, holdingsLoading: false });
  },

  // Command palette
  paletteOpen: false,
  openPalette: () => set({ paletteOpen: true }),
  closePalette: () => set({ paletteOpen: false }),
  togglePalette: () => set((s) => ({ paletteOpen: !s.paletteOpen })),

  // Chat
  chatOpen: false,
  chatMessages: [],
  chatLoading: false,
  clearChat: () => set({ chatMessages: [] }),
  toggleChat: () => set((s) => ({ chatOpen: !s.chatOpen })),
  sendMessage: async (message) => {
    const messages = [...get().chatMessages, { role: 'user', content: message }];
    set({ chatMessages: messages, chatLoading: true });

    try {
      let fullResponse = '';
      for await (const chunk of api.chatStream(message, get().chatMessages.slice(0, -1))) {
        fullResponse += chunk;
        set({ chatMessages: [...messages, { role: 'assistant', content: fullResponse }] });
      }
      if (!fullResponse) {
        const resp = await api.chat(message, get().chatMessages.slice(0, -1));
        fullResponse = resp.response || resp.error || 'No response';
        set({ chatMessages: [...messages, { role: 'assistant', content: fullResponse }] });
      }
    } catch (e) {
      set({ chatMessages: [...messages, { role: 'assistant', content: `Error: ${e.message}` }] });
    }
    set({ chatLoading: false });
  },
  sendBriefing: async ({ period }) => {
    const label = `${period === 'weekly' ? 'Weekly' : 'Daily'} transaction briefing`;
    const messages = [...get().chatMessages, { role: 'user', content: label }];
    set({ chatMessages: messages, chatLoading: true });

    try {
      const resp = await api.chatBriefing({
        period,
        include_transactions: false,
      });
      const content = resp.summary || resp.error || 'No briefing generated';
      set({ chatMessages: [...messages, { role: 'assistant', content }] });
    } catch (e) {
      set({ chatMessages: [...messages, { role: 'assistant', content: `Error: ${e.message}` }] });
    }
    set({ chatLoading: false });
  },

  // Import
  importResult: null,
  importing: false,
}));
