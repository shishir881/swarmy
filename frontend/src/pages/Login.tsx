import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { GoogleLogin, type CredentialResponse } from '@react-oauth/google';
import { AlertCircle, Loader2, Eye, EyeOff, ArrowLeft } from 'lucide-react';

const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
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

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 24,
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Ambient glow */}
      <div style={{
        position: 'absolute', top: '20%', left: '50%', transform: 'translate(-50%, -50%)',
        width: 600, height: 600, borderRadius: '50%',
        background: 'radial-gradient(circle, rgba(29,158,117,0.06) 0%, transparent 70%)',
        pointerEvents: 'none',
      }} />

      <div style={{ width: '100%', maxWidth: 400, position: 'relative', zIndex: 10 }}>
        {/* Back to home */}
        <button onClick={() => navigate('/')} style={{
          background: 'none', border: 'none', color: 'var(--text3)', fontSize: 12,
          cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 20, padding: 0,
        }}>
          <ArrowLeft size={13} /> Back to home
        </button>

        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, marginBottom: 36 }}>
          <span style={{ fontSize: 20, fontWeight: 800, color: 'var(--text)', letterSpacing: '-0.01em', fontFamily: "'Syne', sans-serif" }}>
            <span style={{ color: 'var(--green)' }}>mela</span><span style={{ color: 'var(--text)' }}>.ai</span>
          </span>
        </div>

        {/* Tab Switch */}
        <div style={{
          display: 'flex', background: 'var(--surface)', border: '1px solid var(--border)',
          borderRadius: 12, padding: 4, marginBottom: 24, gap: 4,
        }}>
          {(['Sign In', 'Sign Up'] as const).map((label, i) => {
            const active = (i === 0) === isLogin;
            return (
              <button key={label} onClick={() => { setIsLogin(i === 0); setError(''); }}
                style={{
                  flex: 1, padding: '8px 0', borderRadius: 8, border: 'none', cursor: 'pointer',
                  fontSize: 13, fontWeight: active ? 600 : 400,
                  background: active ? 'var(--bg)' : 'transparent',
                  color: active ? 'var(--text)' : 'var(--text3)',
                  transition: 'all 0.2s',
                  boxShadow: active ? '0 1px 3px rgba(0,0,0,0.3)' : 'none',
                }}
              >
                {label}
              </button>
            );
          })}
        </div>

        {/* Card */}
        <div className="depth-panel" style={{ padding: '28px 28px 24px' }}>
          <div style={{ marginBottom: 22 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text)', margin: '0 0 4px', fontFamily: "'Syne', sans-serif" }}>
              {isLogin ? 'Welcome back' : 'Create your account'}
            </h2>
            <p style={{ fontSize: 12, color: 'var(--text3)', margin: 0 }}>
              {isLogin ? 'Sign in to access your event swarm.' : 'Start orchestrating AI agents for your events.'}
            </p>
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <label className="font-mono" style={{ fontSize: 10, textTransform: 'uppercase', color: 'var(--text3)', letterSpacing: '0.06em', display: 'block', marginBottom: 7 }}>Email</label>
              <input
                type="email" required value={email} onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                style={{
                  width: '100%', padding: '10px 14px', fontSize: 13, color: 'var(--text)',
                  background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 8,
                  outline: 'none', fontFamily: 'inherit', transition: 'border-color 0.2s, box-shadow 0.2s',
                  boxSizing: 'border-box',
                }}
                onFocus={e => { e.target.style.borderColor = 'var(--green)'; e.target.style.boxShadow = '0 0 0 3px rgba(29,158,117,0.12)'; }}
                onBlur={e => { e.target.style.borderColor = 'var(--border)'; e.target.style.boxShadow = 'none'; }}
              />
            </div>

            <div>
              <label className="font-mono" style={{ fontSize: 10, textTransform: 'uppercase', color: 'var(--text3)', letterSpacing: '0.06em', display: 'block', marginBottom: 7 }}>Password</label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPassword ? 'text' : 'password'} required value={password} onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  style={{
                    width: '100%', padding: '10px 40px 10px 14px', fontSize: 13, color: 'var(--text)',
                    background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 8,
                    outline: 'none', fontFamily: 'inherit', transition: 'border-color 0.2s, box-shadow 0.2s',
                    boxSizing: 'border-box',
                  }}
                  onFocus={e => { e.target.style.borderColor = 'var(--green)'; e.target.style.boxShadow = '0 0 0 3px rgba(29,158,117,0.12)'; }}
                  onBlur={e => { e.target.style.borderColor = 'var(--border)'; e.target.style.boxShadow = 'none'; }}
                />
                <button
                  type="button" onClick={() => setShowPassword(p => !p)}
                  style={{
                    position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', color: 'var(--text3)', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', padding: 2,
                  }}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            {error && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px',
                borderRadius: 8, background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)',
                fontSize: 12, color: 'var(--red)',
              }}>
                <AlertCircle size={13} style={{ flexShrink: 0 }} />
                {error}
              </div>
            )}

            <button
              type="submit" disabled={loading}
              style={{
                width: '100%', padding: '11px 0', borderRadius: 8, border: 'none',
                background: loading ? 'var(--border2)' : 'var(--green)',
                color: loading ? 'var(--text3)' : '#0a0a0b',
                fontSize: 13, fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                transition: 'all 0.2s', marginTop: 2,
                fontFamily: "'Syne', sans-serif",
              }}
            >
              {loading && <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />}
              {loading ? 'Authenticating…' : (isLogin ? 'Sign In' : 'Create Account')}
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '4px 0 2px' }}>
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

        <p style={{ textAlign: 'center', fontSize: 12, color: 'var(--text3)', marginTop: 20 }}>
          {isLogin ? "Don't have an account? " : 'Already have an account? '}
          <button onClick={() => { setIsLogin(l => !l); setError(''); }}
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--green)', fontSize: 12, fontWeight: 600, padding: 0 }}>
            {isLogin ? 'Sign up' : 'Sign in'}
          </button>
        </p>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

export default Login;