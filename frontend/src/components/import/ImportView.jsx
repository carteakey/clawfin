import { useState, useCallback } from 'react';
import { api } from '../../api/client';
import { Upload, Link } from 'lucide-react';

export default function ImportView() {
  const [result, setResult] = useState(null);
  const [importing, setImporting] = useState(false);
  const [tab, setTab] = useState('csv'); // csv | wealthsimple | simplefin
  const [dragging, setDragging] = useState(false);
  const [sfToken, setSfToken] = useState('');

  const handleFile = useCallback(async (file) => {
    setImporting(true);
    setResult(null);
    try {
      let data;
      if (tab === 'wealthsimple') {
        data = await api.uploadWealthsimple(file);
      } else {
        data = await api.uploadCSV(file);
      }
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
      const data = await api.simpleFinSetup(sfToken.trim());
      setResult(data);
    } catch (e) {
      setResult({ error: e.message });
    }
    setImporting(false);
  };

  const handleSync = async () => {
    setImporting(true);
    try {
      const data = await api.simpleFinSync();
      setResult(data);
    } catch (e) {
      setResult({ error: e.message });
    }
    setImporting(false);
  };

  return (
    <div className="fade-in">
      {/* Tab selector */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '24px' }}>
        {[
          { id: 'csv', label: 'Bank CSV', icon: '🏦' },
          { id: 'wealthsimple', label: 'Wealthsimple', icon: '📈' },
          { id: 'simplefin', label: 'SimpleFin', icon: '🔗' },
        ].map(({ id, label, icon }) => (
          <button key={id} className={`btn ${tab === id ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setTab(id)}>
            {icon} {label}
          </button>
        ))}
      </div>

      {/* CSV / Wealthsimple drop zone */}
      {(tab === 'csv' || tab === 'wealthsimple') && (
        <div
          className={`drop-zone ${dragging ? 'dragging' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => document.getElementById('file-input').click()}
        >
          <div className="drop-zone-icon"><Upload size={32} /></div>
          <div className="drop-zone-text">
            {tab === 'csv' ? 'Drop a bank CSV file here' : 'Drop a Wealthsimple export CSV'}
          </div>
          <div className="drop-zone-hint">
            {tab === 'csv'
              ? 'Auto-detects TD, RBC, Scotiabank, BMO, CIBC'
              : 'Supports holdings and activity exports'}
          </div>
          <input id="file-input" type="file" accept=".csv" onChange={onFileInput} style={{ display: 'none' }} />
        </div>
      )}

      {/* SimpleFin setup */}
      {tab === 'simplefin' && (
        <div className="card" style={{ maxWidth: '500px' }}>
          <div className="card-title">Connect SimpleFin</div>
          <p style={{ color: 'var(--text-dim)', fontSize: '13px', marginBottom: '16px' }}>
            Get your setup token from <a href="https://app.simplefin.org" target="_blank" rel="noreferrer">app.simplefin.org</a>
          </p>
          <input
            placeholder="Paste setup token..."
            value={sfToken}
            onChange={(e) => setSfToken(e.target.value)}
            style={{
              width: '100%', background: 'var(--bg-input)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius-md)', padding: '8px 12px', color: 'var(--text)',
              fontSize: '13px', fontFamily: 'var(--font-mono)', marginBottom: '12px', outline: 'none',
            }}
          />
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn btn-primary" onClick={handleSimpleFin} disabled={importing}>
              <Link size={14} /> Connect
            </button>
            <button className="btn btn-ghost" onClick={handleSync} disabled={importing}>
              Sync Now
            </button>
          </div>
        </div>
      )}

      {/* Import result */}
      {importing && <div className="loading" style={{ marginTop: '24px', textAlign: 'center' }}>Importing...</div>}
      {result && (
        <div className="card" style={{ marginTop: '24px', maxWidth: '500px' }}>
          {result.error ? (
            <div style={{ color: 'var(--negative)' }}>❌ {result.error}</div>
          ) : (
            <div>
              <div style={{ color: 'var(--positive)', marginBottom: '8px' }}>✅ Import complete</div>
              {result.bank && <div style={{ color: 'var(--text-dim)', fontSize: '12px' }}>Bank: {result.bank}</div>}
              {result.type && <div style={{ color: 'var(--text-dim)', fontSize: '12px' }}>Type: {result.type}</div>}
              {result.accounts_synced !== undefined && (
                <div style={{ color: 'var(--text-dim)', fontSize: '12px' }}>Accounts synced: {result.accounts_synced}</div>
              )}
              {result.imported !== undefined && (
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: '13px', marginTop: '4px' }}>
                  {result.imported} imported{result.skipped ? `, ${result.skipped} skipped (duplicates)` : ''}
                </div>
              )}
              {result.access_url && (
                <div style={{ marginTop: '12px' }}>
                  <div style={{ color: 'var(--text-dim)', fontSize: '12px', marginBottom: '8px' }}>
                    Success! To finish setup, add this URL to your <code>.env</code> file as <code>CLAWFIN_SIMPLEFIN_ACCESS_URL</code> and restart the backend.
                  </div>
                  <pre style={{
                    background: 'var(--bg-input)', padding: '8px', border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)', overflowX: 'auto', fontSize: '12px', color: 'var(--positive)'
                  }}>
                    {result.access_url}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
