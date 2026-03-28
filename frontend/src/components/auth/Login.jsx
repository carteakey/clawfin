import { useState } from 'react';
import { api } from '../../api/client';
import { useStore } from '../../store/ledger';

export default function Login() {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!password) return;
    setLoading(true);
    setError('');
    try {
      const data = await api.login(password);
      if (data.token) {
        api.setToken(data.token);
        useStore.setState({ isAuthenticated: true });
      } else {
        setError(data.detail || 'Login failed');
      }
    } catch {
      setError('Login failed');
    }
    setLoading(false);
  };

  return (
    <div className="login-page">
      <div className="login-card fade-in">
        <svg viewBox="-30 -50 60 96" fill="none" style={{ width: '48px', height: '48px', margin: '0 auto 16px' }}>
          <ellipse cx="0" cy="2" rx="38" ry="38" fill="#1D9E75" opacity="0.10" />
          <path d="M-18,-36 C-22,-18 -20,4 -16,34" stroke="#1D9E75" strokeWidth="5.5" strokeLinecap="round" />
          <path d="M-2,-40 C-4,-18 -2,4 0,36" stroke="#1D9E75" strokeWidth="5.5" strokeLinecap="round" />
          <path d="M14,-36 C18,-18 16,4 12,34" stroke="#1D9E75" strokeWidth="5.5" strokeLinecap="round" />
          <circle cx="-18" cy="-38" r="3.5" fill="#085041" />
          <circle cx="-2" cy="-42" r="3.5" fill="#085041" />
          <circle cx="14" cy="-38" r="3.5" fill="#085041" />
        </svg>
        <h1>
          <span style={{ color: 'var(--teal-dark)' }}>Claw</span>
          <span style={{ color: 'var(--text)' }}>Fin</span>
        </h1>
        <p className="tagline">Your AI Grip on Canadian Finances</p>

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
          autoFocus
        />
        {error && <div style={{ color: 'var(--negative)', fontSize: '12px', marginBottom: '12px' }}>{error}</div>}
        <button className="btn btn-primary" onClick={handleLogin} disabled={loading}>
          {loading ? 'Logging in...' : 'Enter'}
        </button>
      </div>
    </div>
  );
}
