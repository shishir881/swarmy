import { useState, useRef } from "react";
import { ArrowRightCircle } from "lucide-react";
import axios from "axios";

interface CreateEventFormProps {
    onSuccess: (event: any) => void;
}

const eventTypes = ["Hackathon", "Conference", "Workshop", "Sprint", "Tournament"];

export const CreateEventForm = ({ onSuccess }: CreateEventFormProps) => {
    const [eventName, setEventName] = useState("");
    const [organizerName, setOrganizerName] = useState("");
    const [eventType, setEventType] = useState("");
    const [rules, setRules] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [showValidation, setShowValidation] = useState(false);

    const nameInputRef = useRef<HTMLInputElement>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setShowValidation(true);

        if (!eventName.trim()) {
            nameInputRef.current?.focus();
            return;
        }

        setLoading(true);
        setError("");

        const combinedRules = eventType
            ? `[Event Type: ${eventType}]\n${rules}`
            : rules;

        try {
            const res = await axios.post("/api/v1/organizer/events", {
                event_name: eventName,
                organizer_name: organizerName || "Organizer",
                event_rules_and_context: combinedRules,
                total_budget_allocated: 0,
                master_schedule: {},
                budget_report: {},
            });

            onSuccess(res.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message || "An error occurred");
            setLoading(false);
        }
    };

    const isNameInvalid = showValidation && !eventName.trim();

    return (
        <div style={{ width: "100%", maxWidth: 520, margin: "0 auto", background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 20, padding: 32 }}>
            {/* Header Section */}
            <div style={{ borderBottom: "1px solid var(--border)", paddingBottom: 24, marginBottom: 24 }}>
                <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, letterSpacing: "0.1em", textTransform: "uppercase", color: "#1D9E75", marginBottom: 8, fontWeight: 600 }}>
                    Orchestrator Setup
                </div>
                <h2 style={{ fontFamily: "'Syne', sans-serif", fontWeight: 800, fontSize: 32, color: "#fff", margin: "0 0 6px 0", lineHeight: 1.1 }}>
                    Create Event
                </h2>
                <p style={{ fontSize: 14, color: "var(--text3)", margin: 0 }}>
                    Configure your swarm's context and rules.
                </p>
            </div>

            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                {error && (
                    <div style={{ padding: 12, background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)", color: "#ef4444", fontSize: 12, borderRadius: 6 }}>
                        {error}
                    </div>
                )}

                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    <label style={{ fontSize: 11, fontFamily: "'JetBrains Mono', monospace", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text2)", display: "flex", alignItems: "center", gap: 6 }}>
                        Event Name
                        <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#1D9E75" }} />
                    </label>
                    <input
                        ref={nameInputRef}
                        type="text"
                        value={eventName}
                        onChange={(e) => {
                            setEventName(e.target.value);
                            if (showValidation) setShowValidation(false);
                        }}
                        style={{
                            width: "100%",
                            background: "var(--bg)",
                            border: isNameInvalid ? "1px solid #ef4444" : "1px solid var(--border)",
                            boxShadow: isNameInvalid ? "0 0 0 3px rgba(239,68,68,0.15)" : "none",
                            color: "#fff",
                            padding: "12px 16px",
                            fontSize: 14,
                            borderRadius: 8,
                            fontFamily: "inherit",
                            outline: "none",
                            transition: "all 0.2s"
                        }}
                        onFocus={(e) => !isNameInvalid && (e.target.style.background = "var(--surface2)")}
                        onBlur={(e) => (e.target.style.background = "var(--bg)")}
                        placeholder="e.g. Hackathon Spring 2025"
                    />
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    <label style={{ fontSize: 11, fontFamily: "'JetBrains Mono', monospace", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text2)" }}>
                        Organizer
                    </label>
                    <input
                        type="text"
                        value={organizerName}
                        onChange={(e) => setOrganizerName(e.target.value)}
                        style={{
                            width: "100%",
                            background: "var(--bg)",
                            border: "1px solid var(--border)",
                            color: "#fff",
                            padding: "12px 16px",
                            fontSize: 14,
                            borderRadius: 8,
                            fontFamily: "inherit",
                            outline: "none",
                            transition: "all 0.2s"
                        }}
                        onFocus={(e) => (e.target.style.background = "var(--surface2)")}
                        onBlur={(e) => (e.target.style.background = "var(--bg)")}
                        placeholder="e.g. Computer Science Club"
                    />
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    <label style={{ fontSize: 11, fontFamily: "'JetBrains Mono', monospace", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text2)" }}>
                        Event Type
                    </label>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                        {eventTypes.map(type => (
                            <button
                                key={type}
                                type="button"
                                onClick={() => setEventType(t => t === type ? "" : type)}
                                style={{
                                    padding: "6px 14px",
                                    borderRadius: 20,
                                    fontSize: 12,
                                    background: eventType === type ? "rgba(29, 158, 117, 0.1)" : "transparent",
                                    color: eventType === type ? "#1D9E75" : "var(--text2)",
                                    border: eventType === type ? "1px solid #1D9E75" : "1px solid var(--border)",
                                    cursor: "pointer",
                                    transition: "all 0.2s",
                                    fontFamily: "inherit"
                                }}
                            >
                                {type}
                            </button>
                        ))}
                    </div>
                </div>

                <div style={{ height: 1, background: "var(--border)", margin: "8px 0" }} />

                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    <label style={{ fontSize: 11, fontFamily: "'JetBrains Mono', monospace", textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text2)" }}>
                        Rules & Context
                    </label>
                    <textarea
                        value={rules}
                        onChange={(e) => setRules(e.target.value)}
                        style={{
                            width: "100%",
                            background: "var(--bg)",
                            border: "1px solid var(--border)",
                            color: "#fff",
                            padding: "12px 16px",
                            fontSize: 13,
                            borderRadius: 8,
                            fontFamily: "inherit",
                            lineHeight: 1.5,
                            minHeight: 100,
                            resize: "none",
                            outline: "none",
                            transition: "all 0.2s"
                        }}
                        onFocus={(e) => (e.target.style.background = "var(--surface2)")}
                        onBlur={(e) => (e.target.style.background = "var(--bg)")}
                        placeholder="Target metrics, themes, schedules, constraints..."
                    />
                </div>

                {/* Footer Section */}
                <div style={{ marginTop: 8 }}>
                    <button
                        type="submit"
                        disabled={loading}
                        style={{
                            width: "100%",
                            background: loading ? "var(--border2)" : "#fff",
                            color: loading ? "var(--text3)" : "#000",
                            fontFamily: "'Syne', sans-serif",
                            fontWeight: 700,
                            height: 52,
                            borderRadius: 10,
                            fontSize: 16,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: 10,
                            border: "none",
                            cursor: loading ? "not-allowed" : "pointer",
                            transition: "all 0.2s"
                        }}
                    >
                        {loading ? "Initializing..." : <>Initialize Swarm <ArrowRightCircle size={18} /></>}
                    </button>
                    <p style={{ textAlign: "center", fontSize: 12, color: "var(--text3)", margin: "14px 0 0 0" }}>
                        Your context will be distributed to all agents in the swarm.
                    </p>
                </div>
            </form>
        </div>
    );
};
