import { useState, useCallback, useEffect } from 'react';
import { api } from '../../api/client';

const TABS = [
  { id: 'csv',          label: 'Bank CSV' },
  { id: 'wealthsimple', label: 'Wealthsimple' },
  { id: 'simplefin',    label: 'SimpleFin' },
];

export default function ImportView() {
  const [result, setResult] = useState(null);
  const [importing, setImporting] = useState(false);
  const [tab, setTab] = useState('csv');
  const [dragging, setDragging] = useState(false);
  const [sfToken, setSfToken] = useState('');
  const [sfStatus, setSfStatus] = useState(null);
  const [sfAccounts, setSfAccounts] = useState(null);

  useEffect(() => {
    if (tab === 'simplefin') {
      api.simpleFinStatus().then(setSfStatus).catch(console.error);
      api.getAccounts().then(d => {
        setSfAccounts((d.accounts || []).filter(a => a.source === 'simplefin'));
      }).catch(console.error);
    }
  }, [tab, result]);

  const handleFile = useCallback(async (file) => {
    setImporting(true);
    setResult(null);
    try {
      const data = tab === 'wealthsimple'
        ? await api.uploadWealthsimple(file)
        : await api.uploadCSV(file);
      setResult(data);
    } catch (e) {
      setResult({ error: e.message });
    }
    setImporting(false);
  }, [tab]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer?.files?.[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const onFileInput = (e) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  const handleSimpleFin = async () => {
    if (!sfToken.trim()) return;
    setImporting(true);
    try {
      setResult(await api.simpleFinSetup(sfToken.trim()));
    } catch (e) { setResult({ error: e.message }); }
    setImporting(false);
  };

  const handleSync = async () => {
    setImporting(true);
    try {
      setResult(await api.simpleFinSync());
    } catch (e) { setResult({ error: e.message }); }
    setImporting(false);
  };

  return (
    <>
      <div className="section-head">
        <h2>Import</h2>
      </div>

      <div className="tabs">
        {TABS.map(({ id, label }) => (
          <button key={id} type="button" className={`tab ${tab === id ? 'active' : ''}`} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </div>

      {(tab === 'csv' || tab === 'wealthsimple') && (
        <>
          <div
            className={`drop-zone ${dragging ? 'dragging' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => document.getElementById('file-input').click()}
          >
            Drop CSV Here<br />
            <span className="muted" style={{ fontSize: 10 }}>
              {tab === 'csv' ? 'TD · RBC · Scotiabank · BMO · CIBC' : 'Holdings + Activity exports'}
            </span>
          </div>
          <input id="file-input" type="file" accept=".csv" onChange={onFileInput} style={{ display: 'none' }} />
        </>
      )}

      {tab === 'simplefin' && (
        <div className="flex flex-col gap-4">
          <div className="block" style={{ maxWidth: 560 }}>
            <div className="block-title">{sfStatus?.is_configured ? 'SimpleFin Connected' : 'Connect SimpleFin'}</div>
            {!sfStatus?.is_configured && (
              <p className="muted mb-3" style={{ fontSize: 12 }}>
                Setup token from{' '}
                <a href="https://app.simplefin.org" target="_blank" rel="noreferrer">app.simplefin.org</a>
              </p>
            )}
            <input
              placeholder={sfStatus?.is_configured ? "PASTE NEW SETUP TOKEN TO OVERRIDE" : "PASTE SETUP TOKEN"}
              value={sfToken}
              onChange={(e) => setSfToken(e.target.value)}
              style={{ marginBottom: 'var(--sp-3)' }}
            />
            <div className="flex gap-2">
              <button type="button" className={`btn ${sfStatus?.is_configured ? 'btn-ghost' : 'btn-primary'}`} onClick={handleSimpleFin} disabled={importing || !sfToken.trim()}>
                {sfStatus?.is_configured ? 'Reconnect' : 'Connect'}
              </button>
              {sfStatus?.is_configured && (
                <button type="button" className="btn btn-primary" onClick={handleSync} disabled={importing}>Sync Now</button>
              )}
            </div>
          </div>
          
          {sfAccounts && sfAccounts.length > 0 && (
            <div className="block" style={{ maxWidth: 560 }}>
              <div className="block-title">Imported Accounts</div>
              <table className="dense">
                <thead>
                  <tr>
                    <th>Institution</th>
                    <th>Account</th>
                    <th style={{ width: 150 }}>Last Sync</th>
                    <th style={{ width: 80 }} className="r">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {sfAccounts.map(a => (
                    <tr key={a.id}>
                      <td>{a.institution}</td>
                      <td>{a.name}</td>
                      <td className="muted num" style={{ fontSize: 11 }}>
                        {a.last_sync_at ? new Date(a.last_sync_at + 'Z').toLocaleString() : 'Never'}
                      </td>
                      <td className="r">
                        {a.stale_reason || a.last_sync_error ? (
                          <span className="neg" title={a.stale_reason || a.last_sync_error}>Error</span>
                        ) : (
                          <span className="pos">OK</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {importing && <div className="loading label mt-4">Importing…</div>}

      {result && (
        <div className="block mt-4" style={{ maxWidth: 560 }}>
          {result.error ? (
            <>
              <div className="label neg">Error</div>
              <div className="num" style={{ fontSize: 12, marginTop: 6 }}>{result.error}</div>
            </>
          ) : (
            <>
              <div className="label pos">Complete</div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 12, lineHeight: 1.8, marginTop: 6 }}>
                {result.bank && <>BANK · {result.bank}<br /></>}
                {result.type && <>TYPE · {result.type}<br /></>}
                {result.accounts_synced !== undefined && <>ACCOUNTS · {result.accounts_synced}<br /></>}
                {result.imported !== undefined && (
                  <>IMPORTED · {result.imported}{result.skipped ? ` · SKIPPED · ${result.skipped}` : ''}</>
                )}
              </div>
              {result.access_url && (
                <div className="mt-4">
                  <div className="label mb-2">Access URL · Save to .env as CLAWFIN_SIMPLEFIN_ACCESS_URL</div>
                  <pre style={{ fontFamily: 'var(--font-mono)', fontSize: 11, padding: 'var(--sp-3)', border: '1px solid var(--ink)', overflowX: 'auto', background: 'var(--paper-2)' }}>{result.access_url}</pre>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </>
  );
}
