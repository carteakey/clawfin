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
        setError(data.detail || 'Login failed.');
      }
    } catch (e) {
      setError(e.message || 'Login failed.');
    }
    setLoading(false);
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>ClawFin</h1>
        <p className="tag">Your Ledger · Locally Held</p>

        {error && <div className="err">{error.toUpperCase()}</div>}

        <input
          type="password"
          placeholder="PASSWORD"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleLogin()}
          autoFocus
        />
        <button type="button" className="btn btn-primary" onClick={handleLogin} disabled={loading}>
          {loading ? 'Authenticating…' : 'Enter →'}
        </button>
      </div>
    </div>
  );
}
