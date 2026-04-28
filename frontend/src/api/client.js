/**
 * ClawFin API client — talks to the FastAPI backend.
 */
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

let authToken = localStorage.getItem('clawfin_token');

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    localStorage.removeItem('clawfin_token');
    authToken = null;
    window.location.reload();
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const errorMsg = data.detail || data.error || `HTTP Error ${res.status}`;
    // Optionally handle generic 422 validation details from FastAPI
    if (Array.isArray(data.detail)) {
      throw new Error(`Validation Error: ${data.detail[0]?.msg}`);
    }
    throw new Error(errorMsg);
  }

  return data;
}

export const api = {
  // Auth
  checkAuth: () => request('/auth/check'),
  login: (password) => request('/auth/login', { method: 'POST', body: JSON.stringify({ password }) }),

  // Dashboard
  getDashboard: (params = 30) => {
    const query = typeof params === 'object'
      ? new URLSearchParams(Object.fromEntries(
        Object.entries(params).filter(([_, v]) => v !== undefined && v !== null && v !== '')
      )).toString()
      : new URLSearchParams({ days: params }).toString();
    return request(`/dashboard?${query}`);
  },
  getNetWorth: (period = '1Y') => request(`/dashboard/net-worth?period=${period}`),
  getCashflowForecast: (months = 3) => request(`/dashboard/cashflow-forecast?months=${months}`),

  // Transactions
  getTransactions: (params = {}) => {
    const cleanParams = Object.fromEntries(
      Object.entries(params).filter(([_, v]) => v !== undefined && v !== null && v !== '')
    );
    const qs = new URLSearchParams(cleanParams).toString();
    return request(`/transactions?${qs}`);
  },
  updateTransaction: (id, data) => request(`/transactions/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  createTransaction: (data) => request('/transactions', { method: 'POST', body: JSON.stringify(data) }),
  deleteTransaction: (id) => request(`/transactions/${id}`, { method: 'DELETE' }),
  bulkTransactions: (data) => request('/transactions/bulk', { method: 'POST', body: JSON.stringify(data) }),
  exportTransactionsUrl: (params = {}) => {
    const cleanParams = Object.fromEntries(
      Object.entries(params).filter(([_, v]) => v !== undefined && v !== null && v !== '')
    );
    const qs = new URLSearchParams(cleanParams).toString();
    return `${API_BASE}/transactions/export.csv${qs ? `?${qs}` : ''}`;
  },
  getAccounts: () => request('/transactions/accounts'),
  createAccount: (data) => request('/transactions/accounts', { method: 'POST', body: JSON.stringify(data) }),
  updateAccount: (id, data) => request(`/transactions/accounts/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteAccount: (id) => request(`/transactions/accounts/${id}`, { method: 'DELETE' }),
  reinferAccountTypes: () => request('/transactions/accounts/reinfer-types', { method: 'POST' }),
  redetectTransfers: (days = null) => {
    const qs = days ? `?days=${days}` : '';
    return request(`/transactions/redetect-transfers${qs}`, { method: 'POST' });
  },
  getRecurring: () => request('/transactions/recurring'),
  exportDatabase: () => request('/settings/export'),

  // Holdings
  getHoldings: (asOf) => request(asOf ? `/holdings?as_of=${asOf}` : '/holdings'),
  getHoldingsDates: () => request('/holdings/dates'),

  // Import
  uploadCSV: async (file, accountId = null, bankHint = null) => {
    const form = new FormData();
    form.append('file', file);
    if (accountId) form.append('account_id', accountId);
    if (bankHint) form.append('bank_hint', bankHint);
    const headers = {};
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
    const res = await fetch(`${API_BASE}/import/csv`, { method: 'POST', headers, body: form });
    return res.json();
  },
  uploadWealthsimple: async (file) => {
    const form = new FormData();
    form.append('file', file);
    const headers = {};
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
    const res = await fetch(`${API_BASE}/import/wealthsimple`, { method: 'POST', headers, body: form });
    return res.json();
  },
  simpleFinStatus: () => request('/import/simplefin/status'),
  simpleFinSetup: (token) => request('/import/simplefin/setup', { method: 'POST', body: JSON.stringify({ setup_token: token }) }),
  simpleFinSync: () => request('/import/simplefin/sync', { method: 'POST' }),

  // Chat
  chat: (message, history = []) => request('/chat', { method: 'POST', body: JSON.stringify({ message, history }) }),
  chatBriefing: (data) => request('/chat/briefing', { method: 'POST', body: JSON.stringify(data) }),
  chatStream: async function* (message, history = []) {
    const headers = { 'Content-Type': 'application/json' };
    if (authToken) headers['Authorization'] = `Bearer ${authToken}`;
    const res = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST', headers,
      body: JSON.stringify({ message, history }),
    });
    
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP error! status: ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop();
      for (const line of lines) {
        if (line.startsWith('data: ') && line !== 'data: [DONE]') {
          yield line.slice(6);
        }
      }
    }
  },

  // Settings
  getCategories: () => request('/settings/categories'),
  createCategory: (data) => request('/settings/categories', { method: 'POST', body: JSON.stringify(data) }),
  deleteCategory: (id) => request(`/settings/categories/${id}`, { method: 'DELETE' }),
  resetCategories: () => request('/settings/categories/reset', { method: 'POST' }),
  getAIConfig: () => request('/settings/ai'),
  getAIHealth: () => request('/settings/ai/health'),
  getContributionRoom: () => request('/settings/contribution-room'),
  updateContributionRoom: (data) => request('/settings/contribution-room', { method: 'PUT', body: JSON.stringify(data) }),

  // Categorization rules
  getRules: () => request('/settings/rules'),
  createRule: (data) => request('/settings/rules', { method: 'POST', body: JSON.stringify(data) }),
  updateRule: (id, data) => request(`/settings/rules/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteRule: (id) => request(`/settings/rules/${id}`, { method: 'DELETE' }),
  recategorize: (background = false) => request(`/transactions/recategorize${background ? '?background=true' : ''}`, { method: 'POST' }),
  getRecategorizeJob: (id) => request(`/transactions/recategorize/${id}`),

  // AI categorization toggle
  getAIFlags: () => request('/settings/ai/flags'),
  setAIFlags: (data) => request('/settings/ai/flags', { method: 'PUT', body: JSON.stringify(data) }),

  setToken: (token) => { authToken = token; localStorage.setItem('clawfin_token', token); },
};
