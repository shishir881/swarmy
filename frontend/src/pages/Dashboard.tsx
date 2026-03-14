import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Zap, Settings, Users, ArrowRight, LogOut } from 'lucide-react';

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
            <Zap size={14} color="var(--green)" />
          </div>
          <span style={{ fontSize: 18, fontWeight: 700, letterSpacing: '-0.01em' }}>SwarmOS</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
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
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '80px 24px' }}>
        <h1 style={{ fontSize: 32, fontWeight: 600, marginBottom: 12, color: 'var(--text)' }}>Welcome to SwarmOS</h1>
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
            <div style={{ width: 48, height: 48, borderRadius: 12, background: 'rgba(255, 170, 0, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 8 }}>
              <Settings size={24} color="var(--amber)" />
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
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
