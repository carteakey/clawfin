import { useState, useCallback, useEffect } from 'react';
import { api } from '../../api/client';
import { useStore } from '../../store/ledger';

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
  const [targetAccountId, setTargetAccountId] = useState('');
  const [accounts, setAccounts] = useState([]);
  const [preview, setPreview] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewing, setPreviewing] = useState(false);
  const pushToast = useStore((state) => state.pushToast);

  useEffect(() => {
    api.getAccounts().then(d => {
      const list = d.accounts || [];
      setAccounts(list);
      if (tab === 'simplefin') {
        setSfAccounts(list.filter(a => a.source === 'simplefin'));
      }
    }).catch(console.error);

    if (tab === 'simplefin') {
      api.simpleFinStatus().then(setSfStatus).catch(console.error);
    }
  }, [tab, result]);

  const handleFile = useCallback(async (file) => {
    setSelectedFile(file);
    setResult(null);
    setPreview(null);
    if (tab === 'csv') {
      setPreviewing(true);
      try {
        setPreview(await api.previewCSV(file));
      } catch (e) {
        setResult({ error: e.message });
      }
      setPreviewing(false);
      return;
    }
    setImporting(true);
    try {
      const data = await api.uploadWealthsimple(file);
      setResult(data);
      pushToast({ text: 'Wealthsimple import complete.' });
    } catch (e) {
      setResult({ error: e.message });
      pushToast({ type: 'error', text: `Import failed: ${e.message}` });
    }
    setImporting(false);
  }, [tab, targetAccountId]);

  const confirmImport = async () => {
    if (!selectedFile) return;
    setImporting(true);
    setResult(null);
    try {
      const data = await api.uploadCSV(selectedFile, targetAccountId || null);
      setResult(data);
      setPreview(null);
      pushToast({ text: `Imported ${data.imported || 0} rows.` });
    } catch (e) {
      setResult({ error: e.message });
      pushToast({ type: 'error', text: `Import failed: ${e.message}` });
    }
    setImporting(false);
  };

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
      pushToast({ text: 'SimpleFin connected; credential stored encrypted.' });
      setSfToken('');
    } catch (e) { setResult({ error: e.message }); pushToast({ type: 'error', text: `SimpleFin setup failed: ${e.message}` }); }
    setImporting(false);
  };

  const handleSync = async () => {
    setImporting(true);
    try {
      const data = await api.simpleFinSync();
      setResult(data);
      pushToast({ text: `SimpleFin sync imported ${data.imported || 0} rows.` });
    } catch (e) { setResult({ error: e.message }); pushToast({ type: 'error', text: `SimpleFin sync failed: ${e.message}` }); }
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
        <div style={{ maxWidth: 560 }}>
          {tab === 'csv' && accounts.length > 0 && (
            <div className="mb-4">
              <div className="label mb-2">Target Account (Optional)</div>
              <select
                value={targetAccountId}
                onChange={(e) => setTargetAccountId(e.target.value)}
              >
                <option value="">AUTO-DETECT OR UNASSIGNED</option>
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>{a.institution} — {a.name}</option>
                ))}
              </select>
            </div>
          )}
          <div
            className={`drop-zone ${dragging ? 'dragging' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => document.getElementById(`file-input-${tab}`).click()}
          >
            Drop CSV Here<br />
            <span className="muted" style={{ fontSize: 10 }}>
              {tab === 'csv' ? 'TD · RBC · Scotiabank · BMO · CIBC' : 'Holdings + Activity exports'}
            </span>
          </div>
          <input id={`file-input-${tab}`} type="file" accept=".csv" onChange={onFileInput} style={{ display: 'none' }} />
        </div>
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
            {sfStatus?.is_configured && (
              <p className="muted mb-3" style={{ fontSize: 12 }}>
                Stored credential source: {sfStatus.source || 'configured'}.
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

      {previewing && <div className="loading label mt-4">Checking rows without writing…</div>}

      {preview && (
        <div className="block import-preview mt-4">
          <div className="block-title">Review before import</div>
          <div className="muted mb-3" style={{ fontSize: 11 }}>
            {preview.bank || 'Detected bank'} · {preview.parsed_rows} parsed rows · database writes: {preview.writes_database ? 'yes' : 'no'}
          </div>
          {preview.warnings?.map((warning) => <div key={warning} className="status-box" style={{ marginBottom: 8 }}>{warning}</div>)}
          <div className="table-wrap mb-3">
            <table className="dense">
              <thead><tr><th>Date</th><th>Merchant</th><th>Category</th><th className="r">Amount</th><th>Memo</th></tr></thead>
              <tbody>{preview.preview?.map((row, index) => <tr key={`${row.date}-${index}`}><td className="num">{row.date}</td><td>{row.merchant}</td><td>{row.category}</td><td className="num r">{row.amount}</td><td className="muted">{row.memo || '—'}</td></tr>)}</tbody>
            </table>
          </div>
          <div className="form-actions">
            <button type="button" className="btn btn-primary" onClick={confirmImport} disabled={importing || previewing}>Import rows</button>
            <button type="button" className="btn btn-ghost" onClick={() => { setPreview(null); setSelectedFile(null); }}>Cancel</button>
          </div>
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
                  <>IMPORTED · {result.imported}{result.skipped ? ` · SKIPPED · ${result.skipped}` : ''}<br /></>
                )}
                {result.duplicates_skipped !== undefined && <>DUPLICATES · {result.duplicates_skipped}<br /></>}
                {result.transfer_marked_count !== undefined && <>TRANSFERS MARKED · {result.transfer_marked_count}<br /></>}
                {result.stale_accounts?.length > 0 && <>STALE SIMPLEFIN ACCOUNTS · {result.stale_accounts.length}</>}
              </div>
              {result.status === 'connected' && <div className="muted mt-4" style={{ fontSize: 12 }}>SimpleFin access URL stored encrypted.</div>}
            </>
          )}
        </div>
      )}
    </>
  );
}
