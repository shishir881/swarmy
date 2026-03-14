import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { GoogleLogin, type CredentialResponse } from '@react-oauth/google';
import { Zap, AlertCircle, Loader2 } from 'lucide-react';

const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLogin, setIsLogin] = useState(true);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const { login, register, loginWithGoogle } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (isLogin) {
        await login(email, password);
        navigate('/dashboard');
      } else {
        await register(email, password, 'participant');
        navigate('/dashboard');
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    if (credentialResponse.credential) {
      try {
        setError('');
        setLoading(true);
        await loginWithGoogle(credentialResponse.credential, 'participant');
        navigate('/dashboard');
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Google Login failed');
      } finally {
        setLoading(false);
      }
    }
  };

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '10px 14px', fontSize: 13, color: 'var(--text)',
    background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 8,
    outline: 'none', fontFamily: 'inherit',
  };

  return (
    <div style={{ position: "relative", minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <div style={{ width: '100%', maxWidth: 380, position: 'relative', zIndex: 10 }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, marginBottom: 32 }}>
          <div style={{ width: 28, height: 28, borderRadius: 8, background: 'var(--lime10)', border: '1px solid var(--lime35)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Zap size={14} color="var(--green)" />
          </div>
          <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.01em' }}>SwarmOS</span>
        </div>

        {/* Card */}
        <div className="depth-panel" style={{ padding: 28 }}>
          <h2 style={{ fontSize: 16, fontWeight: 500, color: 'var(--text)', margin: '0 0 4px' }}>
            {isLogin ? 'Welcome back' : 'Create account'}
          </h2>
          <p style={{ fontSize: 12, color: 'var(--text3)', margin: '0 0 20px' }}>
            {isLogin ? 'Sign in to continue' : 'Get started with SwarmOS'}
          </p>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div>
              <label className="font-mono" style={{ fontSize: 10, textTransform: 'uppercase', color: 'var(--text3)', letterSpacing: '0.06em', display: 'block', marginBottom: 6 }}>Email</label>
              <input type="email" required value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" style={inputStyle} />
            </div>

            <div>
              <label className="font-mono" style={{ fontSize: 10, textTransform: 'uppercase', color: 'var(--text3)', letterSpacing: '0.06em', display: 'block', marginBottom: 6 }}>Password</label>
              <input type="password" required value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" style={inputStyle} />
            </div>



            {error && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 12px', borderRadius: 6, background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', fontSize: 12, color: 'var(--red)' }}>
                <AlertCircle size={13} />
                {error}
              </div>
            )}

            <button type="submit" disabled={loading}
              style={{ width: '100%', padding: '10px 0', borderRadius: 8, border: 'none', background: 'var(--green)', color: '#0a0a0b', fontSize: 13, fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, opacity: loading ? 0.6 : 1, marginTop: 4 }}>
              {loading && <Loader2 size={14} className="animate-spin" />}
              {loading ? 'Authenticating…' : (isLogin ? 'Sign in' : 'Create account')}
            </button>

            <button type="button" onClick={() => { setIsLogin(!isLogin); setError(''); }}
              style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, color: 'var(--text3)', padding: 0, textAlign: 'center' }}>
              {isLogin ? "Don't have an account? " : 'Already have an account? '}
              <span style={{ color: 'var(--text)' }}>{isLogin ? 'Sign up' : 'Sign in'}</span>
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '2px 0' }}>
              <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
              <span className="font-mono" style={{ fontSize: 10, color: 'var(--text3)' }}>OR</span>
              <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
            </div>

            <div style={{ display: 'flex', justifyContent: 'center' }}>
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={() => setError('Google Login Failed')}
                useOneTap theme="filled_black" shape="pill"
                text={isLogin ? 'signin_with' : 'signup_with'}
              />
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Login;