import { beforeEach, describe, expect, it, vi } from 'vitest';

function installBrowserStubs() {
  const values = new Map();
  vi.stubGlobal('localStorage', {
    getItem: (key) => values.get(key) || null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  });
  vi.stubGlobal('window', { location: { reload: vi.fn() } });
}

describe('API client parameter generation', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.restoreAllMocks();
    installBrowserStubs();
  });

  it('omits empty ledger filters while preserving numeric zeroes', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ transactions: [] }) });
    vi.stubGlobal('fetch', fetchMock);
    const { api } = await import('./client');
    await api.getTransactions({ days: 30, search: '', amount_min: 0, category: null, offset: 0 });
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/transactions?days=30&amount_min=0&offset=0',
      expect.objectContaining({ headers: { 'Content-Type': 'application/json' } }),
    );
  });

  it('builds export and split URLs with encoded parameters', async () => {
    const { api } = await import('./client');
    expect(api.exportTransactionsUrl({ search: 'Cafe & Co', page: 0 })).toContain('search=Cafe+%26+Co&page=0');
    expect(api.splitTransaction).toBeTypeOf('function');
  });
});
