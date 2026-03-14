import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";

const API = "/api/v1";

interface ChatMsg {
  role: "user" | "bot";
  text: string;
  source?: string;
}

interface ScheduleItem {
  time?: string;
  title?: string;
  session?: string;
  location?: string;
  room?: string;
  [key: string]: unknown;
}

export default function ParticipantPortal() {
  const { eventId } = useParams<{ eventId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as { eventName?: string; email?: string } | null;

  const [eventName, setEventName] = useState(state?.eventName || "Event");
  const [schedule, setSchedule] = useState<ScheduleItem[]>([]);
  const [loadingTimeline, setLoadingTimeline] = useState(true);

  // Chat
  const [messages, setMessages] = useState<ChatMsg[]>([
    { role: "bot", text: "Hi! Ask me anything about the event — schedule, budget, rules, anything.", source: "system" },
  ]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Report
  const [reportText, setReportText] = useState("");
  const [reportLoading, setReportLoading] = useState(false);
  const [reportSuccess, setReportSuccess] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);

  // Fetch timeline
  useEffect(() => {
    if (!eventId) return;
    (async () => {
      try {
        const res = await fetch(`${API}/events/${eventId}/timeline`);
        if (res.ok) {
          const data = await res.json();
          setEventName(prev => data.event_name || prev);
          const sched = data.master_schedule;
          if (sched) {
            if (Array.isArray(sched)) {
              setSchedule(sched);
            } else if (typeof sched === "object") {
              const items: ScheduleItem[] = [];
              for (const val of Object.values(sched)) {
                if (Array.isArray(val)) items.push(...(val as ScheduleItem[]));
                else if (typeof val === "object" && val) items.push(val as ScheduleItem);
              }
              setSchedule(items.length > 0 ? items : [{ title: "Schedule data loaded — see organizer for details" }]);
            }
          }
        }
      } catch { /* silent */ }
      setLoadingTimeline(false);
    })();
  }, [eventId]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Send chat
  const sendChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || chatLoading) return;
    const q = chatInput.trim();
    setChatInput("");
    setMessages(prev => [...prev, { role: "user", text: q }]);
    setChatLoading(true);
    try {
      const res = await fetch(`${API}/events/${eventId}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      const data = await res.json();
      setMessages(prev => [...prev, {
        role: "bot",
        text: data.answer || "Sorry, I couldn't process that.",
        source: data.source,
      }]);
    } catch {
      setMessages(prev => [...prev, { role: "bot", text: "Connection error. Please try again." }]);
    }
    setChatLoading(false);
  };

  // Submit report
  const submitReport = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reportText.trim() || reportLoading) return;
    setReportLoading(true);
    setReportSuccess(false);
    try {
      const res = await fetch(`${API}/events/${eventId}/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ problem_description: reportText }),
      });
      if (res.ok) {
        setReportSuccess(true);
        setReportText("");
        setTimeout(() => { setReportSuccess(false); setShowReportModal(false); }, 2500);
      }
    } catch { /* silent */ }
    setReportLoading(false);
  };

  // ── Color accents ──
  const timelineColor = "var(--green)";
  const chatColor = "var(--green)";

  return (
    <div style={{
      height: "100vh",
      display: "flex",
      flexDirection: "column",
      background: "var(--bg)",
      color: "var(--text)",
      fontFamily: "inherit",
      overflow: "hidden",
    }}>
      <style>{`
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
      `}</style>

      {/* ── Header ── */}
      <header style={{
        borderBottom: "1px solid var(--border)",
        padding: "14px 28px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        background: "rgba(4,12,31,0.95)",
        backdropFilter: "blur(12px)",
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button
            onClick={() => navigate("/join")}
            style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text2)", padding: "4px 10px", borderRadius: 6, cursor: "pointer", fontSize: 12 }}
          >
            ← Leave
          </button>
          <div>
            <h1 style={{ fontSize: 15, fontWeight: 600, margin: 0, color: "var(--text)" }}>{eventName}</h1>
            <span className="font-mono" style={{ fontSize: 10, color: "var(--text3)" }}>Event #{eventId}</span>
          </div>
        </div>
        {state?.email && (
          <span className="font-mono" style={{
            fontSize: 10, color: "var(--text3)", background: "var(--surface)",
            padding: "4px 10px", borderRadius: 6, border: "1px solid var(--border)",
          }}>
            {state.email}
          </span>
        )}
      </header>

      {/* ── Main content: Timeline (left) + Chatbot (right) ── */}
      <div style={{ flex: 1, display: "flex", gap: 16, padding: "16px 20px", overflow: "hidden" }}>

        {/* ═══ LEFT: Event Timeline ═══ */}
        <div className="depth-panel" style={{
          flex: 1.6,
          display: "flex",
          flexDirection: "column",
        }}>
          {/* Timeline header */}
          <div style={{
            padding: "14px 20px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "var(--surface)",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div className="font-mono" style={{
                background: "var(--bg)", border: "1px solid var(--border)",
                padding: "4px 8px", borderRadius: 4, fontSize: 10, fontWeight: 600, color: "var(--text3)"
              }}>SCH</div>
              <div>
                <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text)", margin: 0 }}>Event Timeline</p>
                <p className="font-mono" style={{ fontSize: 10, color: "var(--text3)", margin: 0 }}>{schedule.length} sessions</p>
              </div>
            </div>
            <span className="font-mono" style={{
              fontSize: 10, color: timelineColor, background: "var(--lime10)",
              padding: "3px 10px", borderRadius: 20, border: "1px solid var(--lime35)",
              fontWeight: 500, letterSpacing: "0.05em",
            }}>LIVE</span>
          </div>

          {/* Timeline items */}
          <div style={{ flex: 1, overflowY: "auto", padding: "14px 16px", display: "flex", flexDirection: "column", gap: 8 }}>
            {loadingTimeline ? (
              <p style={{ color: "var(--text3)", textAlign: "center", padding: 40, animation: "pulse 1.5s infinite" }}>Loading schedule…</p>
            ) : schedule.length === 0 ? (
              <div className="font-mono" style={{
                textAlign: "center", padding: "60px 24px", color: "var(--text3)",
              }}>
                <p style={{ fontSize: 12, marginBottom: 12 }}>[ NO SCHEDULE DATA ]</p>
                <p style={{ fontSize: 11, marginTop: 4 }}>Awaiting organizer publication.</p>
              </div>
            ) : (
              schedule.map((item, i) => (
                <div key={i} style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  borderLeft: `2px solid ${timelineColor}`,
                  padding: "12px 16px",
                  display: "flex",
                  gap: 14,
                  alignItems: "flex-start",
                }}>
                  {item.time && (
                    <span className="font-mono" style={{
                      fontSize: 11, color: timelineColor,
                      minWidth: 72, flexShrink: 0, paddingTop: 2,
                    }}>
                      {item.time}
                    </span>
                  )}
                  <div>
                    <p style={{ fontSize: 13, color: "var(--text)", margin: 0 }}>
                      {item.title || item.session || JSON.stringify(item)}
                    </p>
                    {(item.location || item.room) && (
                      <p className="font-mono" style={{ fontSize: 10, color: "var(--text3)", margin: "3px 0 0" }}>
                        Loc: {item.location || item.room}
                      </p>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* ── Report Problem Button (bottom of timeline panel) ── */}
          <div style={{
            padding: "12px 16px",
            borderTop: "1px solid var(--border)",
            background: "var(--surface)",
          }}>
            <button
              onClick={() => setShowReportModal(true)}
              style={{
                background: "rgba(239,68,68,0.18)",
                border: "1.5px solid rgba(239,68,68,0.55)",
                color: "var(--red)",
                padding: "8px 20px",
                borderRadius: 8,
                fontSize: 11,
                textTransform: "uppercase",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                width: "100%",
                gap: 8,
                transition: "all 0.15s",
                fontFamily: "inherit",
                fontWeight: 700,
                letterSpacing: "0.04em",
              }}
            >
              ⚠️ EMERGENCY
            </button>
          </div>
        </div>

        {/* ═══ RIGHT: Queries Chatbot ═══ */}
        <div className="depth-panel" style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
        }}>
          {/* Chat header */}
          <div style={{
            padding: "14px 20px",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            background: "var(--surface)",
            gap: 10,
          }}>
            <div className="font-mono" style={{
              background: "var(--bg)", border: "1px solid var(--border)",
              padding: "4px 8px", borderRadius: 4, fontSize: 10, fontWeight: 600, color: "var(--text3)"
            }}>BOT</div>
            <div>
              <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text)", margin: 0 }}>Queries Chatbot</p>
              <p className="font-mono" style={{ fontSize: 10, color: "var(--text3)", margin: 0 }}>Automated assistance</p>
            </div>
            <span className="font-mono" style={{
              marginLeft: "auto",
              display: "flex", alignItems: "center", gap: 5,
              fontSize: 10, color: chatColor,
              background: "var(--lime10)",
              padding: "3px 10px", borderRadius: 20,
              border: "1px solid var(--lime35)",
            }}>
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: chatColor }} />
              Online
            </span>
          </div>

          {/* Messages */}
          <div style={{
            flex: 1, overflowY: "auto", padding: "14px 16px",
            display: "flex", flexDirection: "column", gap: 10,
            background: "var(--bg)",
          }}>
            {messages.map((msg, i) => (
              <div key={i} style={{
                display: "flex",
                justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
              }}>
                <div style={{
                  maxWidth: "85%",
                  padding: "9px 13px",
                  fontSize: 12,
                  lineHeight: 1.6,
                  ...(msg.role === "user"
                    ? {
                      background: "var(--surface)",
                      color: "var(--text)",
                      border: "1px solid var(--border2)",
                    }
                    : {
                      background: "var(--card)",
                      color: "var(--text)",
                      border: "1px solid var(--border)",
                    }),
                }}>
                  <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{msg.text}</p>
                  {msg.source && msg.source !== "system" && (
                    <p className="font-mono" style={{
                      margin: "4px 0 0", fontSize: 9, color: "var(--text3)",
                    }}>
                      src: {msg.source}
                    </p>
                  )}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div style={{ display: "flex" }}>
                <div className="font-mono" style={{
                  background: "var(--card)", border: "1px solid var(--border)",
                  padding: "7px 11px",
                  color: "var(--text3)", fontSize: 10, animation: "pulse 1.5s infinite",
                }}>
                  [processing...]
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={sendChat} style={{
            padding: "10px 14px",
            borderTop: "1px solid var(--border)",
            background: "var(--surface)",
            display: "flex",
            gap: 8,
          }}>
            <input
              value={chatInput}
              onChange={e => setChatInput(e.target.value)}
              placeholder="Ask about schedule, budget, rules…"
              style={{
                flex: 1, background: "var(--bg)", border: "1px solid var(--border)",
                color: "var(--text)", padding: "9px 12px", borderRadius: 0,
                fontSize: 12, fontFamily: "inherit", outline: "none",
              }}
            />
            <button
              type="submit"
              disabled={chatLoading}
              style={{
                background: chatColor, color: "#0a0a0b", border: "none",
                padding: "9px 16px", borderRadius: 0, fontSize: 11,
                fontWeight: 600, cursor: chatLoading ? "not-allowed" : "pointer",
                opacity: chatLoading ? 0.6 : 1, textTransform: "uppercase", fontFamily: "inherit",
              }}
            >
              SEND_MSG
            </button>
          </form>
        </div>
      </div>

      {/* ── Report Problem Modal ── */}
      {showReportModal && (
        <div style={{
          position: "fixed", inset: 0,
          background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)",
          display: "flex", alignItems: "center", justifyContent: "center",
          zIndex: 100,
        }}
          onClick={(e) => { if (e.target === e.currentTarget) setShowReportModal(false); }}
        >
          <div className="depth-panel" style={{
            padding: "28px", width: 480,
            animation: "fadeIn 0.2s ease-out",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
              <div className="font-mono" style={{
                background: "var(--red10)", border: "1px solid var(--red30)",
                padding: "4px 8px", borderRadius: 4, fontSize: 10, fontWeight: 600, color: "var(--red)"
              }}>ALERT</div>
              <div>
                <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text)", margin: 0 }}>Report Emergency</p>
                <p style={{ fontSize: 11, color: "var(--text3)", margin: 0 }}>Agents will prioritize this urgently</p>
              </div>
              <button
                onClick={() => setShowReportModal(false)}
                style={{ marginLeft: "auto", background: "none", border: "none", color: "var(--text3)", fontSize: 18, cursor: "pointer" }}
              >✕</button>
            </div>

            {reportSuccess ? (
              <div style={{
                textAlign: "center", padding: "30px 20px",
                color: "var(--green)",
              }}>
                <p className="font-mono" style={{ fontSize: 24, fontWeight: 600, marginBottom: 8 }}>[ OK ]</p>
                <p style={{ fontSize: 13, fontWeight: 500 }}>Report successfully ingested.</p>
                <p className="font-mono" style={{ fontSize: 10, color: "var(--text3)", marginTop: 4 }}>Agents are processing.</p>
              </div>
            ) : (
              <form onSubmit={submitReport} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <textarea
                  value={reportText}
                  onChange={e => setReportText(e.target.value)}
                  placeholder="Describe the problem... e.g. Projector in Room A is not working"
                  required
                  rows={4}
                  style={{
                    width: "100%", background: "var(--bg)", border: "1px solid var(--border)",
                    color: "var(--text)", padding: "12px 14px", borderRadius: 8,
                    fontSize: 12, lineHeight: 1.6, fontFamily: "inherit", outline: "none"
                  }}
                />
                <button
                  type="submit"
                  disabled={reportLoading}
                  style={{
                    background: "var(--red)", color: "#0a0a0b", border: "none",
                    padding: "10px", borderRadius: 8, fontSize: 12,
                    fontWeight: 600, cursor: reportLoading ? "not-allowed" : "pointer",
                    opacity: reportLoading ? 0.7 : 1, alignSelf: "flex-start",
                    paddingLeft: 24, paddingRight: 24, fontFamily: "inherit",
                  }}
                >
                  {reportLoading ? "SUBMITTING..." : "SUBMIT REPORT"}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
