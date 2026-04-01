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
  getDashboard: (days = 30) => request(`/dashboard?days=${days}`),

  // Transactions
  getTransactions: (params = {}) => {
    const cleanParams = Object.fromEntries(
      Object.entries(params).filter(([_, v]) => v !== undefined && v !== null && v !== '')
    );
    const qs = new URLSearchParams(cleanParams).toString();
    return request(`/transactions?${qs}`);
  },
  updateTransaction: (id, data) => request(`/transactions/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),

  // Holdings
  getHoldings: () => request('/holdings'),

  // Import
  uploadCSV: async (file, bankHint = null) => {
    const form = new FormData();
    form.append('file', file);
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
  simpleFinSetup: (token) => request('/import/simplefin/setup', { method: 'POST', body: JSON.stringify({ setup_token: token }) }),
  simpleFinSync: () => request('/import/simplefin/sync', { method: 'POST' }),

  // Chat
  chat: (message, history = []) => request('/chat', { method: 'POST', body: JSON.stringify({ message, history }) }),
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
  getContributionRoom: () => request('/settings/contribution-room'),
  updateContributionRoom: (data) => request('/settings/contribution-room', { method: 'PUT', body: JSON.stringify(data) }),

  setToken: (token) => { authToken = token; localStorage.setItem('clawfin_token', token); },
};
