import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ArrowRight, LogOut, Home, Users, Zap } from 'lucide-react';

const Dashboard: React.FC = () => {
  const { logout, user } = useAuth();
  const navigate = useNavigate();

  return (
    <div style={{
      position: "relative",
      minHeight: '100vh',
      background: 'var(--bg)',
      color: 'var(--text)',
      display: 'flex',
      flexDirection: 'column',
      fontFamily: "'IBM Plex Mono', monospace"
    }}>
      {/* Header */}
      <header style={{
        padding: "20px 40px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        borderBottom: "1px solid var(--border)"
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 28, height: 28, borderRadius: 8, background: 'var(--lime10)', border: '1px solid var(--lime35)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          </div>
          <span style={{ fontSize: 18, fontWeight: 700, letterSpacing: '-0.01em' }}><span style={{ color: 'var(--green)' }}>mela</span><span style={{ color: 'var(--text)' }}>.ai</span></span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <button onClick={() => navigate('/')} style={{
            background: 'none', border: '1px solid var(--border)', padding: '6px 12px',
            borderRadius: 6, color: 'var(--text3)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: 12
          }}>
            <Home size={14} /> Home
          </button>
          <span style={{ fontSize: 13, color: 'var(--text3)' }}>{user?.email}</span>
          <button onClick={() => { logout(); navigate('/login'); }} style={{
            background: 'none', border: '1px solid var(--border)', padding: '6px 12px',
            borderRadius: 6, color: 'var(--text3)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6, fontSize: 12
          }}>
            <LogOut size={14} /> Logout
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '40px 24px' }}>
        <h1 style={{ fontSize: 32, fontWeight: 600, marginBottom: 12, color: 'var(--text)' }}>Welcome to <span style={{ color: 'var(--green)' }}>mela</span><span style={{ color: 'var(--text)' }}>.ai</span></h1>
        <p style={{ fontSize: 14, color: 'var(--text3)', marginBottom: 48, maxWidth: 400, textAlign: 'center' }}>
          Select how you want to interact with the platform. You can host your own event or join an existing one.
        </p>

        <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', justifyContent: 'center', maxWidth: 900 }}>
          {/* Card 1: Host Event */}
          <div onClick={() => navigate('/organizer?create=true')} className="depth-panel" style={{
            width: 260, padding: 32, display: 'flex', flexDirection: 'column', gap: 16, cursor: 'pointer',
            transition: 'all 0.2s', border: '1px solid var(--border)'
          }}
            onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--green)'}
            onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
          >
            <div style={{ width: 48, height: 48, borderRadius: 12, background: 'rgba(184, 255, 87, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 8 }}>
              <Zap size={24} color="var(--green)" />
            </div>
            <h2 style={{ fontSize: 18, fontWeight: 600, margin: 0 }}>Host Event</h2>
            <p style={{ fontSize: 13, color: 'var(--text3)', margin: 0, lineHeight: 1.5, flex: 1 }}>
              Create a new event, configure your AI agent swarm, and manage logistics as a Lead Organizer.
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--green)', fontSize: 12, fontWeight: 600, marginTop: 16 }}>
              Get Started <ArrowRight size={14} />
            </div>
          </div>

          {/* Card 2: Join as Organizer */}
          <div onClick={() => navigate('/join?type=organizer')} className="depth-panel" style={{
            width: 260, padding: 32, display: 'flex', flexDirection: 'column', gap: 16, cursor: 'pointer',
            transition: 'all 0.2s', border: '1px solid var(--border)'
          }}
            onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--green)'}
            onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
          >
            <div style={{ width: 64, height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 8 }}>
              {/* Two figures side-hugging / collaborating */}
              <svg width="56" height="56" viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                {/* Left person */}
                <circle cx="22" cy="16" r="6" fill="var(--amber)" opacity="0.85"/>
                <path d="M14 32c0-4.4 3.6-8 8-8s8 3.6 8 8v10a2 2 0 01-2 2H16a2 2 0 01-2-2V32z" fill="var(--amber)" opacity="0.55"/>
                {/* Right person */}
                <circle cx="42" cy="16" r="6" fill="var(--green)" opacity="0.85"/>
                <path d="M34 32c0-4.4 3.6-8 8-8s8 3.6 8 8v10a2 2 0 01-2 2H36a2 2 0 01-2-2V32z" fill="var(--green)" opacity="0.55"/>
                {/* Hug / link arm */}
                <path d="M28 30c2 4 6 4 8 0" stroke="var(--text3)" strokeWidth="2" strokeLinecap="round" opacity="0.5"/>
                {/* Heart above */}
                <path d="M32 8c-1-2-4-2-4 0s3 4 4 5c1-1 4-3 4-5s-3-2-4 0z" fill="#ff6b8a" opacity="0.7"/>
              </svg>
            </div>
            <h2 style={{ fontSize: 18, fontWeight: 600, margin: 0 }}>Co-Organize</h2>
            <p style={{ fontSize: 13, color: 'var(--text3)', margin: 0, lineHeight: 1.5, flex: 1 }}>
              Join an existing event's organizing team to monitor the agent swarm and override assignments.
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--amber)', fontSize: 12, fontWeight: 600, marginTop: 16 }}>
              Enter Code <ArrowRight size={14} />
            </div>
          </div>

          {/* Card 3: Join as Participant */}
          <div onClick={() => navigate('/join?type=participant')} className="depth-panel" style={{
            width: 260, padding: 32, display: 'flex', flexDirection: 'column', gap: 16, cursor: 'pointer',
            transition: 'all 0.2s', border: '1px solid var(--border)'
          }}
            onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--green)'}
            onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
          >
            <div style={{ width: 48, height: 48, borderRadius: 12, background: 'rgba(90, 122, 138, 0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 8 }}>
              <Users size={24} color="var(--text3)" />
            </div>
            <h2 style={{ fontSize: 18, fontWeight: 600, margin: 0 }}>Join Event</h2>
            <p style={{ fontSize: 13, color: 'var(--text3)', margin: 0, lineHeight: 1.5, flex: 1 }}>
              Enter as an attendee to view the schedule, get real-time info, and connect with the support AI.
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text3)', fontSize: 12, fontWeight: 600, marginTop: 16 }}>
              Enter Code <ArrowRight size={14} />
            </div>
          </div>

          {/* Card 4: Manage Events */}
          <div onClick={() => navigate('/organizer')} className="depth-panel" style={{
            width: 260, padding: 32, display: 'flex', flexDirection: 'column', gap: 16, cursor: 'pointer',
            transition: 'all 0.2s', border: '1px solid var(--border)'
          }}
            onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--green)'}
            onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
          >
            <div style={{ width: 48, height: 48, borderRadius: 12, background: 'rgba(0, 232, 122, 0.05)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 8 }}>
              <Zap size={24} color="var(--text3)" />
            </div>
            <h2 style={{ fontSize: 18, fontWeight: 600, margin: 0 }}>My Events</h2>
            <p style={{ fontSize: 13, color: 'var(--text3)', margin: 0, lineHeight: 1.5, flex: 1 }}>
              Manage your existing events, view logs, and orchestrate your active AI agents.
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text3)', fontSize: 12, fontWeight: 600, marginTop: 16 }}>
              Open Organizer <ArrowRight size={14} />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
