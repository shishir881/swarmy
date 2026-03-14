import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";

const API = "/api/v1";

export default function JoinEvent() {
  const navigate = useNavigate();
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const isOrganizer = queryParams.get("type") === "organizer";

  const [code, setCode] = useState("");
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleJoin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const endpoint = isOrganizer ? `${API}/events/join/organizer` : `${API}/events/join`;
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code, email, name: name || undefined }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || `Join failed (${res.status})`);
      }
      const data = await res.json();
      if (isOrganizer) {
        navigate(`/organizer`);
      } else {
        navigate(`/event/${data.event_id}`, { state: { eventName: data.event_name, email } });
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "var(--bg)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: "inherit",
    }}>
      <style>{`
        /* Using global font from index.css */
      `}</style>

      <div style={{
        width: "100%",
        maxWidth: 420,
        padding: "0 24px",
      }}>
        {/* Back button */}
        <button
          onClick={() => navigate("/dashboard")}
          style={{
            background: "none",
            border: "none",
            color: "var(--text3)",
            fontSize: 14,
            cursor: "pointer",
            marginBottom: 32,
            padding: 0,
            fontFamily: "inherit",
          }}
        >
          ← Back to Dashboard
        </button>

        {/* Card */}
        <div className="depth-panel" style={{
          padding: "40px 32px",
        }}>
          <div style={{ textAlign: "center", marginBottom: 32 }}>
            <div style={{
              width: 48,
              height: 48,
              borderRadius: 12,
              background: isOrganizer ? "rgba(255, 170, 0, 0.1)" : "var(--lime10)",
              border: `1px solid ${isOrganizer ? "var(--amber)" : "var(--lime35)"}`,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 22,
              marginBottom: 16,
            }}>{isOrganizer ? "🏢" : "🎫"}</div>
            <h1 style={{
              fontWeight: 700,
              fontSize: 24,
              color: "var(--text)",
              marginBottom: 8,
              letterSpacing: "-0.5px",
            }}>
              {isOrganizer ? "Co-Organize Event" : "Join an Event"}
            </h1>
            <p style={{ color: "var(--text3)", fontSize: 14, lineHeight: 1.6, margin: 0 }}>
              {isOrganizer ? "Enter the organizer code to manage the swarm" : "Enter the participant code shared by your organizer"}
            </p>
          </div>

          <form onSubmit={handleJoin} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div>
              <label className="font-mono" style={{ display: "block", fontSize: 10, textTransform: "uppercase", color: "var(--text3)", letterSpacing: "0.06em", marginBottom: 6 }}>
                Join Code
              </label>
              <input
                value={code}
                onChange={e => setCode(e.target.value)}
                placeholder="e.g. NEU-2026"
                required
                style={{
                  width: "100%",
                  background: "var(--bg)",
                  border: "1px solid var(--border)",
                  color: "var(--text)",
                  padding: "12px 14px",
                  borderRadius: 8,
                  fontSize: 15,
                  fontFamily: "inherit",
                  letterSpacing: "1px",
                  textTransform: "uppercase",
                  textAlign: "center",
                  boxSizing: "border-box",
                  outline: "none",
                }}
              />
            </div>

            <div>
              <label className="font-mono" style={{ display: "block", fontSize: 10, textTransform: "uppercase", color: "var(--text3)", letterSpacing: "0.06em", marginBottom: 6 }}>
                Your Email
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@email.com"
                required
                style={{
                  width: "100%",
                  background: "var(--bg)",
                  border: "1px solid var(--border)",
                  color: "var(--text)",
                  padding: "10px 14px",
                  borderRadius: 8,
                  fontSize: 13,
                  boxSizing: "border-box",
                  outline: "none",
                  fontFamily: "inherit",
                }}
              />
            </div>

            <div>
              <label className="font-mono" style={{ display: "block", fontSize: 10, textTransform: "uppercase", color: "var(--text3)", letterSpacing: "0.06em", marginBottom: 6 }}>
                Your Name <span style={{ color: "var(--text2)" }}>(optional)</span>
              </label>
              <input
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="Your name"
                style={{
                  width: "100%",
                  background: "var(--bg)",
                  border: "1px solid var(--border)",
                  color: "var(--text)",
                  padding: "10px 14px",
                  borderRadius: 8,
                  fontSize: 13,
                  boxSizing: "border-box",
                  outline: "none",
                  fontFamily: "inherit",
                }}
              />
            </div>

            {error && (
              <div style={{
                background: "rgba(239,68,68,0.1)",
                border: "1px solid rgba(239,68,68,0.2)",
                color: "var(--red)",
                padding: "10px 14px",
                borderRadius: 8,
                fontSize: 12,
              }}>
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              style={{
                marginTop: 8,
                background: "var(--green)",
                color: "#0a0a0b",
                border: "none",
                padding: "12px",
                borderRadius: 8,
                fontSize: 14,
                fontWeight: 600,
                cursor: loading ? "not-allowed" : "pointer",
                opacity: loading ? 0.7 : 1,
                fontFamily: "inherit",
              }}
            >
              {loading ? "Joining…" : "Join Event →"}
            </button>
          </form>
        </div>

        <p style={{
          textAlign: "center",
          color: "var(--text3)",
          fontSize: 12,
          marginTop: 24,
        }}>
          Are you {isOrganizer ? "a participant" : "an organizer"}?{" "}
          <button
            onClick={() => navigate(isOrganizer ? "/join?type=participant" : "/join?type=organizer")}
            style={{
              background: "none",
              border: "none",
              color: "var(--text)",
              fontSize: 12,
              cursor: "pointer",
              textDecoration: "underline",
              padding: 0,
              fontFamily: "inherit",
            }}
          >
            Go to dashboard
          </button>
        </p>
      </div>
    </div>
  );
}
