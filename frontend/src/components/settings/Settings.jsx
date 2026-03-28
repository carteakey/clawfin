import { useEffect, useState } from 'react';
import { api } from '../../api/client';
import { formatCurrency } from '../../utils/format';
import { RotateCcw, Plus, Trash2 } from 'lucide-react';

export default function Settings() {
  const [categories, setCategories] = useState([]);
  const [aiConfig, setAiConfig] = useState(null);
  const [room, setRoom] = useState({});
  const [newCat, setNewCat] = useState('');

  useEffect(() => {
    api.getCategories().then((d) => setCategories(d.categories || []));
    api.getAIConfig().then(setAiConfig);
    api.getContributionRoom().then(setRoom);
  }, []);

  const handleResetCategories = async () => {
    await api.resetCategories();
    const d = await api.getCategories();
    setCategories(d.categories || []);
  };

  const handleAddCategory = async () => {
    if (!newCat.trim()) return;
    await api.createCategory({ name: newCat.trim() });
    const d = await api.getCategories();
    setCategories(d.categories || []);
    setNewCat('');
  };

  const handleDeleteCategory = async (id) => {
    await api.deleteCategory(id);
    const d = await api.getCategories();
    setCategories(d.categories || []);
  };

  const handleRoomSave = async () => {
    await api.updateContributionRoom(room);
  };

  return (
    <div className="fade-in" style={{ maxWidth: '600px' }}>
      {/* AI Config */}
      <div className="settings-section">
        <h2>🤖 AI Provider</h2>
        <div className="card">
          {aiConfig && (
            <>
              <div className="settings-row">
                <span className="settings-label">Provider</span>
                <span className="settings-value">{aiConfig.provider}</span>
              </div>
              <div className="settings-row">
                <span className="settings-label">Model</span>
                <span className="settings-value">{aiConfig.model}</span>
              </div>
              <div className="settings-row">
                <span className="settings-label">Endpoint</span>
                <span className="settings-value">{aiConfig.base_url}</span>
              </div>
              <div className="settings-row">
                <span className="settings-label">Status</span>
                <span className="settings-value" style={{ color: aiConfig.is_configured ? 'var(--positive)' : 'var(--negative)' }}>
                  {aiConfig.is_configured ? '● Connected' : '○ Not configured'}
                </span>
              </div>
            </>
          )}
          <p style={{ color: 'var(--text-muted)', fontSize: '11px', marginTop: '12px' }}>
            Configure via env vars: CLAWFIN_AI_PROVIDER, CLAWFIN_AI_MODEL, CLAWFIN_AI_BASE_URL, CLAWFIN_AI_API_KEY
          </p>
        </div>
      </div>

      {/* Categories */}
      <div className="settings-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2>📂 Categories</h2>
          <button className="btn btn-ghost" onClick={handleResetCategories} style={{ fontSize: '12px' }}>
            <RotateCcw size={12} /> Reset to defaults
          </button>
        </div>
        <div className="card">
          {categories.map((cat) => (
            <div key={cat.id} className="settings-row">
              <span>
                <span style={{ marginRight: '8px' }}>{cat.icon}</span>
                <span style={{ color: cat.color }}>{cat.name}</span>
              </span>
              {!cat.is_default && (
                <button onClick={() => handleDeleteCategory(cat.id)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                  <Trash2 size={14} />
                </button>
              )}
            </div>
          ))}
          <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
            <input
              placeholder="New category..."
              value={newCat}
              onChange={(e) => setNewCat(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddCategory()}
              style={{
                flex: 1, background: 'var(--bg-input)', border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)', padding: '6px 10px', color: 'var(--text)',
                fontSize: '13px', fontFamily: 'var(--font-sans)', outline: 'none',
              }}
            />
            <button className="btn btn-ghost" onClick={handleAddCategory}><Plus size={14} /></button>
          </div>
        </div>
      </div>

      {/* Contribution Room */}
      <div className="settings-section">
        <h2>🇨🇦 Contribution Room <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontWeight: 400 }}>(optional)</span></h2>
        <div className="card">
          {[
            { key: 'tfsa_room', label: 'TFSA Room' },
            { key: 'rrsp_room', label: 'RRSP Room' },
            { key: 'fhsa_room', label: 'FHSA Room' },
          ].map(({ key, label }) => (
            <div key={key} className="settings-row">
              <span className="settings-label">{label}</span>
              <input
                type="number"
                placeholder="$0.00"
                value={room[key] ?? ''}
                onChange={(e) => setRoom({ ...room, [key]: e.target.value ? parseFloat(e.target.value) : null })}
                style={{
                  width: '120px', background: 'var(--bg-input)', border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-md)', padding: '4px 8px', color: 'var(--text)',
                  fontSize: '13px', fontFamily: 'var(--font-mono)', textAlign: 'right', outline: 'none',
                }}
              />
            </div>
          ))}
          <button className="btn btn-primary" onClick={handleRoomSave} style={{ marginTop: '12px' }}>Save</button>
        </div>
      </div>
    </div>
  );
}
