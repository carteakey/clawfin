import { create } from 'zustand';
import { api } from '../api/client';

export const useStore = create((set, get) => ({
  // Auth
  isAuthenticated: !!localStorage.getItem('clawfin_token'),
  authRequired: null,
  setAuthenticated: (v) => set({ isAuthenticated: v }),

  // Navigation
  currentView: 'dashboard',
  setView: (view) => set({ currentView: view }),

  // Dashboard
  dashboard: null,
  dashboardLoading: false,
  fetchDashboard: async (days = 30) => {
    set({ dashboardLoading: true });
    const data = await api.getDashboard(days);
    set({ dashboard: data, dashboardLoading: false });
  },

  // Transactions
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
  fetchHoldings: async () => {
    set({ holdingsLoading: true });
    const data = await api.getHoldings();
    set({ holdings: data, holdingsLoading: false });
  },

  // Chat
  chatOpen: false,
  chatMessages: [],
  chatLoading: false,
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

  // Import
  importResult: null,
  importing: false,
}));
