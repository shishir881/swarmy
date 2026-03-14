/* eslint-disable react-hooks/set-state-in-effect */
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
interface LogItem {
  agent: string;
  msg: string;
  color: string;
  delay: number;
  id?: number;
}

const LOG_ITEMS: LogItem[] = [
  { agent: "Supervisor", msg: "[INFO] New event received → analyzing task parameters", color: "var(--text3)", delay: 0 },
  { agent: "Scheduler", msg: "[EXEC] Building master schedule from constraints", color: "var(--green)", delay: 700 },
  { agent: "Scheduler", msg: "[WARN] Conflict: Room A double-booked at 9:00 AM", color: "var(--yellow)", delay: 1400 },
  { agent: "Scheduler", msg: "[OK] Conflict resolved → shifted to Room B", color: "var(--green)", delay: 2100 },
  { agent: "Email", msg: "[EXEC] Triggered → personalizing 342 emails", color: "var(--purple)", delay: 2800 },
  { agent: "Email", msg: "[OK] 342 emails queued → awaiting approval", color: "var(--green)", delay: 3500 },
  { agent: "Budget", msg: "[WARN] Catering overspend detected: +41%", color: "var(--red)", delay: 4200 },
  { agent: "Budget", msg: "[INFO] Suggestion: reduce menu to save $180.00", color: "var(--text3)", delay: 4900 },
  { agent: "Content", msg: "[EXEC] Generating distribution posts", color: "var(--green)", delay: 5600 },
  { agent: "Content", msg: "[OK] 3 posts queued → pending human approval", color: "var(--green)", delay: 6300 },
  { agent: "Supervisor", msg: "[INFO] All tasks complete → swarm idle", color: "var(--text3)", delay: 7000 },
];

function LiveLog() {
  const [visible, setVisible] = useState<LogItem[]>([]);
  const [cycleCount, setCycleCount] = useState(0);

  const runCycle = () => {
    setVisible([]);
    LOG_ITEMS.forEach((item, i) => {
      setTimeout(() => {
        setVisible(v => [...v, { ...item, id: Date.now() + i }].slice(-8));
      }, item.delay);
    });
  };

  useEffect(() => {
    runCycle();
    const interval = setInterval(() => {
      setCycleCount(c => c + 1);
      runCycle();
    }, 9000);
    return () => clearInterval(interval);
  }, []);

  const now = () =>
    new Date().toLocaleTimeString("en-US", {
      hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit",
    });

  return (
    <div className="depth-panel" style={{
      padding: "24px 24px 20px",
      fontFamily: "'IBM Plex Mono', monospace",
      position: "relative",
      overflow: "hidden",
      boxShadow: "0 4px 6px rgba(0,0,0,0.1)",
    }}>



      {/* Terminal bar */}
      <div style={{
        display: "flex", alignItems: "center", gap: 8,
        marginBottom: 20, paddingBottom: 14,
        borderBottom: "1px solid var(--border)",
      }}>
        <div style={{ display: "flex", gap: 7 }}>
          {["var(--red)", "var(--yellow)", "var(--green)"].map(c => (
            <div key={c} style={{ width: 12, height: 12, borderRadius: "50%", background: c }} />
          ))}
        </div>
        <span style={{ color: "var(--text3)", fontSize: 12, marginLeft: 6 }}>
          swarm_activity.log
        </span>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 10, color: "var(--text3)" }}>
            cycle #{cycleCount + 1}
          </span>
          <span style={{
            display: "flex", alignItems: "center", gap: 6,
            background: "var(--lime10)",
            border: "1px solid var(--lime35)",
            borderRadius: 4, padding: "3px 8px",
            fontSize: 11, color: "var(--green)",
          }}>
            <span style={{
              width: 6, height: 6, borderRadius: "50%",
              background: "var(--green)", display: "inline-block",
            }} />
            SYS_ONLINE
          </span>
        </div>
      </div>

      {/* Log lines */}
      <div style={{ minHeight: 280 }}>
        {visible.map((item, i) => (
          <div
            key={`${item.id}-${i}`}
            style={{
              display: "flex", gap: 12, marginBottom: 13,
              padding: "8px 12px", borderRadius: 8,
              background: item.msg.includes("⚠️") || item.msg.includes("WARN")
                ? "var(--red10)"
                : item.msg.includes("✅") || item.msg.includes("OK")
                  ? "var(--lime10)"
                  : "transparent",
              border: item.msg.includes("⚠️") || item.msg.includes("WARN")
                ? "1px solid var(--red30)"
                : item.msg.includes("✅") || item.msg.includes("OK")
                  ? "1px solid var(--lime35)"
                  : "1px solid transparent",
              animation: "fadeSlideIn 0.4s ease forwards",
              opacity: 0,
              alignItems: "flex-start",
            }}
          >
            <span style={{ color: "var(--text3)", flexShrink: 0, fontSize: 11, paddingTop: 1 }}>
              {now()}
            </span>
            <span style={{
              color: item.color, fontWeight: 700,
              flexShrink: 0, minWidth: 96, fontSize: 11, paddingTop: 1,
            }}>
              [{item.agent.toUpperCase()}]
            </span>
            <span style={{
              color: "var(--text)",
              fontSize: 12, lineHeight: 1.5,
            }}>
              {item.msg}
            </span>
          </div>
        ))}

        {/* Blinking cursor */}
        {visible.length > 0 && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 12px" }}>
            <span style={{ color: "var(--text3)", fontSize: 11 }}>{now()}</span>
            <span style={{ color: "var(--green)", fontSize: 13, animation: "blink 1s step-end infinite" }}>█</span>
          </div>
        )}
      </div>

      {/* Bottom fade */}
      <div style={{
        position: "absolute", bottom: 0, left: 0, right: 0, height: 48,
        background: "linear-gradient(to top, var(--card), transparent)",
        pointerEvents: "none",
      }} />
    </div>
  );
}

export default function HeroPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [mounted, setMounted] = useState<boolean>(false);

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 80);
    return () => clearTimeout(t);
  }, []);

  const fadeUp = (delay: number): React.CSSProperties => ({
    opacity: mounted ? 1 : 0,
    transform: mounted ? "translateY(0)" : "translateY(28px)",
    transition: `opacity 0.7s ${delay}s ease, transform 0.7s ${delay}s ease`,
  });

  return (
    <div style={{
      minHeight: "100vh",
      background: "var(--bg)",
      color: "var(--text)",
      overflowX: "hidden",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;700&family=Syne:wght@700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateX(-8px); }
          to   { opacity: 1; transform: translateX(0); }
        }
        @keyframes pulse {
          0%,100% { opacity: 1; }
          50%      { opacity: 0.3; }
        }
        @keyframes gridDrift {
          0%   { transform: translateY(0); }
          100% { transform: translateY(44px); }
        }
        @keyframes float {
          0%,100% { transform: translateY(0px); }
          50%     { transform: translateY(-16px); }
        }
        @keyframes scanLine {
          0%   { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        @keyframes blink {
          0%,100% { opacity: 1; }
          50%      { opacity: 0; }
        }

        .btn-primary {
          background: var(--green); color: var(--bg); border: none;
          padding: 16px 36px; border-radius: 8px;
          font-size: 16px; font-weight: 700; cursor: pointer;
          font-family: inherit; letter-spacing: 0.2px;
          transition: all 0.2s;
        }
        .btn-primary:hover {
          opacity: 0.9;
          transform: translateY(-2px);
          box-shadow: 0 4px 20px var(--lime35);
        }
        .nav-link {
          color: var(--text3); text-decoration: none; font-size: 14px;
          transition: color 0.2s;
        }
        .nav-link:hover { color: var(--text); }
        .agent-pill:hover {
          transform: translateY(-2px);
          transition: transform 0.2s;
        }
      `}</style>

      {/* Background */}
      <div style={{
        position: "fixed", inset: 0, zIndex: 0, pointerEvents: "none",
        background: "var(--bg-main)"
      }} />

      <div style={{ position: "relative", zIndex: 1 }}>

        <nav style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "18px 48px",
          borderBottom: "1px solid var(--border)",
          backdropFilter: "blur(16px)",
          background: "rgba(4, 12, 31, 0.8)",
          position: "sticky", top: 0, zIndex: 100,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 24, height: 24, borderRadius: 4,
              background: "var(--green)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}></div>
            <span style={{
              fontWeight: 700,
              fontSize: 19, letterSpacing: "-0.5px", color: "var(--text)"
            }}>
              Event<span style={{ color: "var(--green)" }}>Swarm</span>
            </span>
          </div>

          <div style={{ display: "flex", gap: 36 }}>
            {["Features", "How it works", "Agents"].map(l => (
              <a key={l} href="#" className="nav-link">{l}</a>
            ))}
          </div>

          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            {!user ? (
              <>
                <button onClick={() => navigate("/login")} className="nav-link" style={{ background: 'none', border: 'none', cursor: 'pointer' }}>Login</button>
                <button onClick={() => navigate("/login")} className="btn-primary" style={{ padding: "8px 16px", fontSize: 13 }}>
                  Get Started →
                </button>
              </>
            ) : (
              <>
                {user && (
                  <button
                    onClick={() => navigate("/dashboard")}
                    style={{
                      background: "var(--lime10)",
                      color: "var(--green)",
                      border: "1px solid var(--lime35)",
                      padding: "10px 22px",
                      borderRadius: "8px",
                      fontSize: "13px",
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    Dashboard
                  </button>
                )}
                <button onClick={logout} className="nav-link" style={{ background: 'none', border: 'none', cursor: 'pointer' }}>Logout</button>
              </>
            )}
          </div>
        </nav>

        {/* HERO */}
        <section style={{
          maxWidth: 1200, margin: "0 auto",
          padding: "80px 48px 80px",
        }}>

          {/* Two column */}
          <div style={{ display: "flex", gap: 80, alignItems: "center", flexWrap: "wrap", justifyContent: "center" }}>

            {/* LEFT */}
            <div style={{ flex: "1 1 420px", display: "flex", flexDirection: "column", alignItems: "center", textAlign: "center" }}>

              <h1 style={{
                ...fadeUp(0.1),
                fontWeight: 700,
                fontSize: "clamp(44px, 6vw, 78px)",
                lineHeight: 1.04, letterSpacing: "-2.5px", marginBottom: 24,
                color: "var(--text)"
              }}>
                Event automation.<br />
                <span style={{ color: "var(--green)" }}>
                  Scalable execution.
                </span>
              </h1>

              <p style={{
                ...fadeUp(0.2),
                fontSize: 14, color: "var(--text2)", lineHeight: 1.75,
                maxWidth: 440, marginBottom: 36, margin: "0 auto",
              }}>
                One organizer. Four AI agents. Zero manual overhead.
                EventSwarm handles emails, scheduling, budgets and
                social media — completely autonomously.
              </p>

              {/* Action Area: Button + Trust Signals */}
              <div style={{
                ...fadeUp(0.3),
                display: "flex", flexDirection: "column", alignItems: "center", gap: 16, marginBottom: 32
              }}>
                <button className="btn-primary" onClick={() => navigate(user ? '/dashboard' : "/login")}>
                  Launch Your Swarm →
                </button>

                {/* Trust Signals / Micro-copy */}
                <div style={{ display: "flex", alignItems: "center", gap: 16, justifyContent: "center" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ color: "var(--green)", fontSize: 13, fontWeight: "bold" }}>✓</span>
                    <span style={{ color: "var(--text3)", fontSize: 13 }}>
                      No credit card required
                    </span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ color: "var(--green)", fontSize: 13, fontWeight: "bold" }}>✓</span>
                    <span style={{ color: "var(--text3)", fontSize: 13 }}>
                      Setup in 5 minutes
                    </span>
                  </div>
                </div>
              </div>

              {/* Powered by */}
              <div style={{
                ...fadeUp(0.5),
                display: "inline-flex", alignItems: "center", gap: 8,
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: 4, padding: "6px 12px",
              }}>
                <span style={{
                  fontSize: 10, color: "var(--text3)",
                }}>POWERED BY</span>
                <span style={{
                  fontSize: 11, fontWeight: 700, color: "var(--text)",
                }}>LANGGRAPH</span>
              </div>

            </div>

            {/* RIGHT — live log */}
            <div style={{
              ...fadeUp(0.2),
              flex: "1 1 480px",
              animation: "float 7s ease-in-out infinite",
            }}>
              <LiveLog />

              <div style={{
                marginTop: 14,
                display: "flex", alignItems: "center",
                justifyContent: "center", gap: 8,
                background: "var(--lime10)",
                border: "1px solid var(--border)",
                borderRadius: 8, padding: "10px 20px",
              }}>
                <span style={{ fontSize: 11, color: "var(--text3)" }}>
                  powered by
                </span>
                <span style={{ fontSize: 12, fontWeight: 700, color: "var(--text2)" }}>
                  LangGraph + Llama 3
                </span>
                <span style={{
                  width: 6, height: 6, borderRadius: "50%",
                  background: "var(--green)", display: "inline-block",
                  animation: "pulse 2s infinite",
                }} />
              </div>
            </div>

          </div>
        </section>

        {/* FOOTER CTA */}
        <section style={{
          maxWidth: 1200, margin: "0 auto",
          padding: "80px 48px 96px", textAlign: "center",
          borderTop: "1px solid var(--border)",
        }}>
          <h2 style={{
            fontWeight: 700,
            fontSize: "clamp(32px, 4vw, 52px)",
            letterSpacing: "-1.5px", lineHeight: 1.1, marginBottom: 18,
            color: "var(--text)"
          }}>
            Deploy autonomous<br />
            <span style={{ color: "var(--green)" }}>
              systems for your event.
            </span>
          </h2>

          <p style={{ color: "var(--text2)", marginBottom: 40, fontSize: 16, lineHeight: 1.6 }}>
            Set up your first event in under 5 minutes.<br />
            No manual overhead. Ever.
          </p>

          <button className="btn-primary" onClick={() => navigate(user ? '/dashboard' : "/login")}>Get Started →</button>

          <div style={{
            marginTop: 56, display: "flex",
            justifyContent: "center", gap: 40, flexWrap: "wrap",
          }}>
            {["Built on LangGraph", "Powered by Llama 3", "React + FastAPI", "PostgreSQL"].map(t => (
              <span key={t} style={{
                color: "var(--text3)", fontSize: 12,
              }}>{t}</span>
            ))}
          </div>
        </section>

      </div>
    </div>
  );
}