import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { AnimatePresence, motion } from "framer-motion";
import { useLocation } from "react-router-dom";
import {
    Sparkles, Mail, CalendarClock, ChevronLeft, Plus, Send,
    ArrowLeft, Loader2, CheckCircle2, AlertCircle, Paperclip, X, Clock, Menu,
    CircleDollarSign, Bell, Zap, MessageSquarePlus
} from "lucide-react";
import { CreateEventForm } from "@/components/CreateEventForm";
import { ChatBar } from "@/components/ChatBar";

const API = "/api/v1";

/* ── Types ─────────────────────────────────────────── */
interface EventItem { id: string; name: string; date?: string; status?: string; }

const agents = [
    { id: "content", title: "Content Generator", description: "Social posts, captions & promo copy.", icon: Sparkles, color: "var(--green)", svgSrc: "/file(1).svg" },
    { id: "email", title: "Email Automator", description: "Campaigns to students, faculty & sponsors.", icon: Mail, color: "#a78bfa" },
    { id: "schedule", title: "Event Scheduler", description: "Venues, timeslots & conflict resolution.", icon: CalendarClock, color: "var(--yellow)" },
    { id: "budget", title: "Budget Manager", description: "Expense audits, ROI & financial oversight.", icon: CircleDollarSign, color: "#38bdf8" },
];

const endpointMap: Record<string, string> = { content: "run_marketing", email: "run_email", schedule: "run_scheduler", budget: "run_budget" };

/* ── Agent output parser ───────────────────────────── */
function parseOutput(agentId: string, data: Record<string, unknown>): string {
    if (agentId === "content") {
        const c = (data?.generated_content as string) || "";
        const logs = (data?.logs as string[]) || [];
        const parts: string[] = [];
        if (c) parts.push(c);
        if (logs.length) parts.push("\n📋 Logs:\n" + logs.map(l => `  • ${l}`).join("\n"));
        return parts.join("\n\n") || JSON.stringify(data, null, 2);
    }
    if (agentId === "email") {
        const n = data?.recipients_count as number;
        const logs = (data?.logs as string[]) || [];
        const parts: string[] = [];
        if (n !== undefined) parts.push(`✉️ Campaign sent to ${n} recipient(s).`);
        if (logs.length) parts.push("\n📋 Logs:\n" + logs.map(l => `  • ${l}`).join("\n"));
        return parts.join("\n") || JSON.stringify(data, null, 2);
    }
    if (agentId === "schedule") {
        const sched = data?.master_schedule as Record<string, unknown>;
        const logs = (data?.logs as string[]) || [];
        const parts: string[] = [];
        if (sched && Object.keys(sched).length) {
            parts.push("📅 Schedule:\n" + Object.entries(sched).map(([k, v]) => `  ${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join("\n"));
        }
        if (logs.length) parts.push("\n📋 Logs:\n" + logs.map(l => `  • ${l}`).join("\n"));
        return parts.join("\n\n") || JSON.stringify(data, null, 2);
    }
    if (agentId === "budget") {
        const report = data?.budget_report as Record<string, unknown>;
        const logs = (data?.logs as string[]) || [];
        const parts: string[] = [];
        if (report && Object.keys(report).length) {
            parts.push("💰 Budget Report:\n" + Object.entries(report).map(([k, v]) => `  ${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join("\n"));
        }
        if (logs.length) parts.push("\n📋 Logs:\n" + logs.map(l => `  • ${l}`).join("\n"));
        return parts.join("\n\n") || JSON.stringify(data, null, 2);
    }
    return JSON.stringify(data, null, 2);
}

/* ── Data for panels ─────────────────────────── */
const problems: any[] = [];
const queries: any[] = [];

/* ── Main Component ────────────────────────────────── */
const Index = () => {
    const [collapsed, setCollapsed] = useState(false);
    const [activeAgent, setActiveAgent] = useState<string | null>(null);
    const [events, setEvents] = useState<EventItem[]>([]);
    const [selectedEvent, setSelectedEvent] = useState<EventItem | null>(null);
    const [loadingEvents, setLoadingEvents] = useState(true);
    const location = useLocation();
    const queryParams = new URLSearchParams(location.search);
    const shouldCreate = queryParams.get("create") === "true";
    const [showCreateForm, setShowCreateForm] = useState(shouldCreate);
    const [chatExpanded, setChatExpanded] = useState(false);
    const [showEmergencyModal, setShowEmergencyModal] = useState(false);
    const [emergencyInput, setEmergencyInput] = useState("");
    const [emergencyLoading, setEmergencyLoading] = useState(false);
    const [emergencySuccess, setEmergencySuccess] = useState(false);

    // Agent prompt state
    const [prompt, setPrompt] = useState("");
    const [csvFile, setCsvFile] = useState<File | null>(null);
    const [agentLoading, setAgentLoading] = useState(false);
    const [agentResult, setAgentResult] = useState<string | null>(null);
    const [agentError, setAgentError] = useState<string | null>(null);
    const fileRef = useRef<HTMLInputElement>(null);

    // Chat bar

    useEffect(() => {
        (async () => {
            try {
                const res = await axios.get(`${API}/organizer/events`);
                const data = res.data;
                const list: EventItem[] = Array.isArray(data)
                    ? data.map((e: Record<string, unknown>) => ({
                        id: String(e.event_id ?? e.id),
                        name: String(e.event_name ?? e.name ?? `Event ${e.event_id ?? e.id}`),
                        date: typeof e.created_at === "string" ? new Date(e.created_at as string).toLocaleDateString() : undefined,
                        status: typeof e.status === "string" ? e.status : undefined,
                    })) : [];
                setEvents(list);
                if (list.length > 0) setSelectedEvent(list[0]);
            } catch { /* silent */ }
            setLoadingEvents(false);
        })();
    }, []);

    const agentObj = agents.find(a => a.id === activeAgent);

    const handleRunAgent = async () => {
        if (!activeAgent || !prompt.trim()) return;
        if (activeAgent === "email" && !csvFile) return;
        setAgentLoading(true); setAgentResult(null); setAgentError(null);
        try {
            const evId = selectedEvent?.id || "1";
            const ep = endpointMap[activeAgent] || "run_swarm";
            let res;
            if (activeAgent === "email") {
                const form = new FormData();
                form.append("csv_file", csvFile as File);
                form.append("sample_email", prompt);
                res = await axios.post(`${API}/organizer/events/${evId}/${ep}`, form, { headers: { "Content-Type": "multipart/form-data" } });
            } else {
                res = await axios.post(`${API}/organizer/events/${evId}/${ep}`, { prompt, event_id: Number(evId) });
            }
            setAgentResult(parseOutput(activeAgent, res.data as Record<string, unknown>));
        } catch (err: unknown) {
            if (axios.isAxiosError(err)) setAgentError(err.response?.data?.detail || err.message);
            else setAgentError("Something went wrong.");
        } finally { setAgentLoading(false); }
    };

    const goBackToAgents = () => { setActiveAgent(null); setPrompt(""); setCsvFile(null); setAgentResult(null); setAgentError(null); };

    const handleEmergencySubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!emergencyInput.trim() || emergencyLoading) return;
        setEmergencyLoading(true);
        try {
            await axios.post(`${API}/organizer/events/${selectedEvent?.id}/run_emergency`, { prompt: emergencyInput });
            setEmergencySuccess(true);
            setTimeout(() => {
                setShowEmergencyModal(false);
                setEmergencySuccess(false);
                setEmergencyInput("");
            }, 3000);
        } catch (err: unknown) {
            console.error("Emergency trigger failed.", err);
            alert("Failed to run emergency protocol. Check logs.");
        } finally {
            setEmergencyLoading(false);
        }
    };

    /* ── Render ─ */
    return (
        <div style={{ position: "relative", display: "flex", height: "100vh", background: "var(--bg)", color: "var(--text)" }}>

            {/* ══ LEFT SIDEBAR ══ */}
            <aside className={`sidebar-main ${collapsed ? "collapsed" : ""}`}
                style={{ position: "relative", zIndex: 10, width: collapsed ? 48 : 210, background: "var(--surface)", borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column" }}>

                {/* Brand row */}
                <div style={{ padding: "14px 12px", display: "flex", alignItems: "center", gap: 10, borderBottom: "1px solid var(--border)" }}>
                    <div style={{ width: 22, height: 22, background: "var(--lime10)", border: "1px solid var(--lime35)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                        <Zap size={12} color="var(--green)" fill="var(--green)" />
                    </div>
                    <span className="sidebar-text" style={{ fontSize: 13, fontWeight: 700, color: "var(--text)", letterSpacing: "0.02em" }}>SwarmOS</span>
                    <button onClick={() => setCollapsed(c => !c)}
                        style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", color: "var(--text3)", padding: 2, flexShrink: 0 }}>
                        <ChevronLeft size={14} style={{ transform: collapsed ? "rotate(180deg)" : "none", transition: "transform 0.2s" }} />
                    </button>
                </div>

                {/* Event lists */}
                <div style={{ flex: 1, overflowY: "auto", padding: "10px 0" }}>
                    {selectedEvent && !collapsed && (
                        <div style={{ margin: "0 12px 8px", padding: "12px 14px", background: "var(--card)", border: "1px solid var(--border2)", borderLeft: "4px solid var(--green)", borderRadius: 2 }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 5 }}>
                                <div style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--red)", boxShadow: "0 0 8px var(--red)", flexShrink: 0 }} />
                                <span className="font-mono" style={{ fontSize: 10, fontWeight: 700, color: "var(--green)", textTransform: "uppercase", letterSpacing: "0.1em" }}>Live Event</span>
                            </div>
                            <div className="sidebar-text" style={{ fontSize: 13, fontWeight: 700, color: "var(--text)", marginBottom: 6, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{selectedEvent.name}</div>
                            <div className="font-mono sidebar-text" style={{ fontSize: 13, fontWeight: 700, color: "var(--green)", letterSpacing: "0.06em" }}>T&#8209;minus 14:02:45</div>
                        </div>
                    )}

                    <div style={{ margin: "0 12px 6px", borderTop: "1px solid var(--border)" }} />

                    <div style={{ padding: "0 12px 4px" }}>
                        <span className="sidebar-text font-mono" style={{ fontSize: 10, textTransform: "uppercase", color: "var(--text3)", letterSpacing: "0.08em" }}>Your Events</span>
                    </div>
                    {events.map((ev, i) => {
                        const isSelected = selectedEvent?.id === ev.id;
                        return (
                            <div key={`ev-${i}`} onClick={() => { setSelectedEvent(ev); setShowCreateForm(false); setActiveAgent(null); setAgentResult(null); setAgentError(null); }}
                                style={{ display: "flex", alignItems: "center", gap: 8, padding: "7px 14px", cursor: "pointer", borderLeft: isSelected ? "3px solid var(--green)" : "3px solid transparent", background: isSelected ? "var(--lime10)" : "transparent", transition: "all 0.15s" }}
                                onMouseEnter={e => !isSelected && (e.currentTarget.style.background = "rgba(184,255,87,0.04)")}
                                onMouseLeave={e => !isSelected && (e.currentTarget.style.background = "transparent")}>
                                <span className="sidebar-text" style={{ fontSize: 12, color: isSelected ? "var(--green)" : "var(--text3)", fontWeight: isSelected ? 600 : 400, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{ev.name}</span>
                            </div>
                        );
                    })}
                </div>

                {/* New event button */}
                <div style={{ padding: "10px 12px", borderTop: "1px solid var(--border)" }}>
                    <button onClick={() => setShowCreateForm(true)}
                        style={{ width: "100%", padding: "7px 0", border: "1px dashed var(--border2)", background: "transparent", color: "var(--text3)", fontSize: 11, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}>
                        <Plus size={12} />
                        <span className="sidebar-text">New event</span>
                    </button>
                </div>
            </aside>

            {/* ══ MAIN CONTENT ══ */}
            <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflow: "hidden" }}>

                {/* Topbar */}
                {!(events.length === 0 || showCreateForm) && (
                    <div style={{ padding: "0 24px", height: 58, borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0, background: "var(--surface)" }}>
                        {/* Left: title */}
                        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
                            {collapsed && (
                                <button onClick={() => setCollapsed(false)} style={{ background: "transparent", border: "1px solid var(--border)", padding: 6, color: "var(--text)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
                                    <Menu size={16} />
                                </button>
                            )}
                            <div>
                                <h1 style={{ fontSize: 15, fontWeight: 700, color: "var(--text)", letterSpacing: "0.02em", margin: 0 }}>AI Agent Swarm</h1>
                                <p style={{ fontSize: 10, color: "var(--text3)", margin: "2px 0 0", letterSpacing: "0.02em" }}>Autonomous orchestration layer</p>
                            </div>
                        </div>

                        {/* Center: event breadcrumb pill */}
                        {selectedEvent && (
                            <div style={{ display: "flex", alignItems: "center", gap: 7, background: "var(--lime10)", border: "1px solid var(--lime35)", padding: "5px 13px", borderRadius: 20 }}>
                                <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--green)", flexShrink: 0 }} />
                                <span className="font-mono" style={{ fontSize: 11, color: "var(--green)", fontWeight: 600, letterSpacing: "0.02em", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{selectedEvent.name}</span>
                            </div>
                        )}

                        {/* Right: actions */}
                        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                            <button style={{ background: "transparent", border: "1px solid var(--border)", padding: 8, color: "var(--text2)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", transition: "all 0.2s" }}>
                                <Bell size={14} />
                            </button>

                            {selectedEvent && (
                                <button
                                    onClick={() => setShowEmergencyModal(true)}
                                    style={{
                                        display: "flex", alignItems: "center", gap: 7, padding: "6px 14px",
                                        borderRadius: 14, background: "rgba(239,68,68,0.18)",
                                        border: "1.5px solid rgba(239,68,68,0.55)", color: "var(--red)",
                                        fontSize: 11, fontWeight: 700, cursor: "pointer",
                                        letterSpacing: "0.04em", transition: "all 0.2s"
                                    }}
                                >
                                    <AlertCircle size={13} />
                                    EMERGENCY
                                </button>
                            )}
                        </div>
                    </div>
                )}

                {/* Scrollable body */}
                <div style={{ flex: 1, overflowY: "auto", padding: 28 }}>

                    {loadingEvents ? (
                        <div style={{ textAlign: "center", color: "var(--text3)", paddingTop: 80, fontSize: 13 }}>Loading orchestrator...</div>
                    ) : events.length === 0 || showCreateForm ? (
                        <CreateEventForm onSuccess={(newEvent) => {
                            const mapped = { id: String(newEvent.event_id || newEvent.id), name: String(newEvent.event_name || newEvent.name) };
                            setEvents(prev => [mapped, ...prev]);
                            setSelectedEvent(mapped);
                            setShowCreateForm(false);
                        }} />
                    ) : chatExpanded ? (
                        <div /> // ChatBar takes over
                    ) : (
                        <>
                            {/* ── Agent Cards or Prompt ── */}
                            <AnimatePresence mode="wait">
                                {activeAgent && agentObj ? (
                                    <motion.div key="prompt" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 12 }}
                                        transition={{ duration: 0.3 }} style={{ maxWidth: 640, position: "relative", zIndex: 10 }}>
                                        <button onClick={goBackToAgents}
                                            style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--text3)", background: "none", border: "none", cursor: "pointer", marginBottom: 16, padding: 0 }}>
                                            <ArrowLeft size={14} /> Back to agents
                                        </button>
                                        <div className="depth-panel" style={{ padding: 20 }}>
                                            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
                                                <div style={{ width: 28, height: 28, borderRadius: 6, background: "var(--bg)", border: "1px solid var(--border2)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                                                    <agentObj.icon size={14} color={agentObj.color} />
                                                </div>
                                                <span style={{ fontSize: 13, fontWeight: 500, color: "var(--text)" }}>{agentObj.title}</span>
                                                <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 4 }}>
                                                    <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--green)" }} />
                                                    <span className="font-mono" style={{ fontSize: 10, color: "var(--green)" }}>ready</span>
                                                </div>
                                            </div>
                                            <textarea value={prompt} onChange={e => setPrompt(e.target.value)}
                                                placeholder={activeAgent === "email" ? "Write a sample email body (tone/style reference)..." : `Describe what you want ${agentObj.title} to do...`}
                                                style={{ width: "100%", minHeight: 120, background: "var(--bg)", border: "1px solid var(--border)", borderRadius: 6, padding: "10px 12px", fontSize: 12, color: "var(--text)", resize: "none", outline: "none", lineHeight: 1.6 }} />

                                            {/* CSV upload for email */}
                                            {activeAgent === "email" && (
                                                <div style={{ marginTop: 10 }}>
                                                    <input type="file" accept=".csv" ref={fileRef} style={{ display: "none" }} onChange={e => setCsvFile(e.target.files?.[0] ?? null)} />
                                                    {!csvFile ? (
                                                        <button onClick={() => fileRef.current?.click()}
                                                            style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: 6, padding: "9px 14px", border: "1px dashed var(--border2)", borderRadius: 6, background: "transparent", color: "var(--text3)", fontSize: 11, cursor: "pointer" }}>
                                                            <Paperclip size={13} /> Upload recipient CSV (name, email, segment)
                                                        </button>
                                                    ) : (
                                                        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 12px", border: "1px solid var(--green)", borderRadius: 6, background: "rgba(0, 232, 122, 0.05)", fontSize: 12, color: "var(--text)" }}>
                                                            <Paperclip size={13} color="var(--green)" />
                                                            <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{csvFile.name}</span>
                                                            <button onClick={() => { setCsvFile(null); if (fileRef.current) fileRef.current.value = ""; }} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text3)" }}><X size={12} /></button>
                                                        </div>
                                                    )}
                                                </div>
                                            )}

                                            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 12 }}>
                                                <button onClick={handleRunAgent} disabled={!prompt.trim() || (activeAgent === "email" && !csvFile) || agentLoading}
                                                    style={{ display: "flex", alignItems: "center", gap: 6, padding: "7px 18px", borderRadius: 6, border: "none", background: agentObj.color, color: "#0a0a0b", fontSize: 12, fontWeight: 500, cursor: "pointer", opacity: (!prompt.trim() || agentLoading) ? 0.4 : 1 }}>
                                                    {agentLoading ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
                                                    {agentLoading ? "Running…" : "Run Agent"}
                                                </button>
                                            </div>
                                        </div>

                                        {/* Loading */}
                                        {agentLoading && (
                                            <div className="depth-panel" style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 8, padding: "10px 14px" }}>
                                                <Clock size={13} color="var(--text3)" className="animate-spin" />
                                                <span className="font-mono" style={{ fontSize: 11, color: "var(--text3)" }}>Swarm agents running…</span>
                                            </div>
                                        )}

                                        {/* Output */}
                                        {(agentResult || agentError) && !agentLoading && (
                                            <div className="depth-panel" style={{ marginTop: 12, padding: 16 }}>
                                                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
                                                    {agentError ? <AlertCircle size={14} color="var(--red)" /> : <CheckCircle2 size={14} color="var(--green)" />}
                                                    <span style={{ fontSize: 12, fontWeight: 500, color: agentError ? "var(--red)" : "var(--text)" }}>
                                                        {agentError ? "Error" : `${agentObj.title} Output`}
                                                    </span>
                                                </div>
                                                <pre style={{ fontSize: 12, color: "var(--text2)", whiteSpace: "pre-wrap", lineHeight: 1.6, margin: 0, fontFamily: "inherit", wordBreak: "break-word" }}>
                                                    {agentError || agentResult}
                                                </pre>
                                            </div>
                                        )}
                                    </motion.div>
                                ) : (
                                    <motion.div key="cards" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                                        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 14 }}>
                                            {agents.map((agent) => {
                                                const AgIcon = agent.icon;
                                                return (
                                                    <div key={agent.id} className="depth-panel" onClick={() => setActiveAgent(agent.id)}
                                                        style={{ padding: 20, cursor: "pointer" }}>
                                                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                                                            <div style={{ width: 36, height: 36, background: "var(--lime10)", border: "1px solid var(--lime35)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                                                                {(agent as { id: string; svgSrc?: string }).svgSrc ? (
                                                                    <img src={(agent as { svgSrc: string }).svgSrc} alt={agent.title} style={{ width: 20, height: 20, objectFit: "contain" }} />
                                                                ) : (
                                                                    <AgIcon size={16} color="var(--green)" />
                                                                )}
                                                            </div>
                                                            <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                                                                <div style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--green)" }} />
                                                                <span className="font-mono" style={{ fontSize: 10, color: "var(--text3)", letterSpacing: "0.04em" }}>ready</span>
                                                            </div>
                                                        </div>
                                                        <p style={{ fontSize: 14, fontWeight: 700, color: "var(--text)", margin: "0 0 4px", letterSpacing: "0.01em" }}>{agent.title}</p>
                                                        <p style={{ fontSize: 11, color: "var(--text3)", lineHeight: 1.5, margin: 0 }}>{agent.description}</p>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </>
                    )}
                </div>

                {/* ── Bottom input bar ── */}
                {selectedEvent && !showCreateForm && (
                    <div style={{
                        padding: "20px 40px",
                        borderTop: "1px solid var(--border)",
                        flexShrink: 0,
                        position: "sticky",
                        bottom: 0,
                        background: "var(--surface)",
                        zIndex: 50,
                        ...(chatExpanded ? { flex: 1, display: "flex", flexDirection: "column", borderTop: "none", padding: 0 } : {})
                    }}>
                        <ChatBar eventId={selectedEvent?.id} isExpanded={chatExpanded} setExpanded={setChatExpanded} />
                    </div>
                )}
            </div>

            {/* ══ RIGHT SIDEBAR ══ */}
            {!activeAgent && !chatExpanded && events.length > 0 && !showCreateForm && (
                // ... rest of aside block from Line 384 remains identical ... (we will append the modal instead of replacing everything)
                // Replacing lines down to 435 to just insert the modal before the final closing divs.
                <aside style={{ width: 260, borderLeft: "1px solid var(--border)", background: "var(--surface)", display: "flex", flexDirection: "column", padding: 16, gap: 16, flexShrink: 0 }}>
                    {/* Problems */}
                    <div style={{ border: "1px solid var(--border)", padding: "14px", display: "flex", flexDirection: "column", flex: 1.3, background: "var(--card)", overflow: "hidden" }}>
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, flexShrink: 0 }}>
                            <span className="font-mono" style={{ fontSize: 10, textTransform: "uppercase", color: "var(--text3)", letterSpacing: "0.08em", fontWeight: 700 }}>Problems</span>
                            <span className="font-mono" style={{ fontSize: 10, background: "var(--red10)", border: "1px solid var(--red30)", color: "var(--red)", padding: "2px 7px", fontWeight: 700 }}>{problems.length}</span>
                        </div>
                        <div style={{ overflowY: "auto", display: "flex", flexDirection: "column", gap: 8, flex: 1 }}>
                            {problems.length === 0 ? (
                                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flex: 1, padding: "32px 0", gap: 10 }}>
                                    <CheckCircle2 size={22} color="var(--text3)" strokeWidth={1.5} />
                                    <span style={{ fontSize: 11, color: "var(--text3)" }}>No issues reported</span>
                                </div>
                            ) : (
                                problems.map((p) => (
                                    <div key={p.id} style={{ background: "var(--bg)", border: "1px solid var(--border)", padding: "9px 11px", display: "flex", alignItems: "flex-start", gap: 9, cursor: "pointer" }}>
                                        <div style={{ width: 8, height: 8, borderRadius: "50%", background: p.tag === "urgent" ? "var(--red)" : "var(--yellow)", boxShadow: p.tag === "urgent" ? "0 0 6px var(--red)" : "none", flexShrink: 0, marginTop: 4 }} />
                                        <div>
                                            <p style={{ fontSize: 12, fontWeight: 600, color: "var(--text)", margin: 0 }}>{p.title}</p>
                                            <p style={{ fontSize: 11, color: "var(--text3)", margin: "3px 0 0" }}>{p.meta}</p>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    {/* Queries */}
                    <div style={{ border: "1px solid var(--border)", padding: "14px", display: "flex", flexDirection: "column", flex: 1, background: "var(--card)", overflow: "hidden" }}>
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12, flexShrink: 0 }}>
                            <span className="font-mono" style={{ fontSize: 10, textTransform: "uppercase", color: "var(--text3)", letterSpacing: "0.08em", fontWeight: 700 }}>Queries</span>
                            <span className="font-mono" style={{ fontSize: 10, background: "var(--pur10)", border: "1px solid var(--pur30)", color: "var(--purple)", padding: "2px 7px", fontWeight: 700 }}>{queries.length}</span>
                        </div>
                        <div style={{ overflowY: "auto", display: "flex", flexDirection: "column", gap: 8, flex: 1 }}>
                            {queries.length === 0 ? (
                                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flex: 1, padding: "28px 0", gap: 10 }}>
                                    <MessageSquarePlus size={22} color="var(--text3)" strokeWidth={1.5} />
                                    <span style={{ fontSize: 11, color: "var(--text3)" }}>No queries yet</span>
                                </div>
                            ) : (
                                queries.map((q) => (
                                    <div key={q.id} style={{ background: "var(--bg)", border: "1px solid var(--border)", padding: "9px 11px", cursor: "pointer" }}>
                                        <p style={{ fontSize: 12, color: "var(--text2)", margin: 0 }}>"{q.text}"</p>
                                        <p className="font-mono" style={{ fontSize: 10, color: "var(--purple)", margin: "5px 0 0" }}>{q.sender} · {q.time}</p>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </aside>
            )}
            {/* ── Emergency Modal ── */}
            {showEmergencyModal && (
                <div style={{
                    position: "fixed", inset: 0,
                    background: "rgba(0,0,0,0.6)", backdropFilter: "blur(4px)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    zIndex: 100,
                }}
                    onClick={(e) => { if (e.target === e.currentTarget) setShowEmergencyModal(false); }}
                >
                    <div className="depth-panel" style={{
                        padding: "28px", width: 480,
                        animation: "fadeIn 0.2s ease-out"
                    }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
                            <div className="font-mono" style={{
                                background: "var(--red10)", border: "1px solid var(--red30)",
                                padding: "4px 8px", borderRadius: 4, fontSize: 10, fontWeight: 600, color: "var(--red)"
                            }}>EMERGENCY</div>
                            <div>
                                <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text)", margin: 0 }}>Trigger Emergency Protocol</p>
                                <p style={{ fontSize: 11, color: "var(--text3)", margin: 0 }}>Agents will prioritize and resolve this immediately</p>
                            </div>
                            <button
                                onClick={() => setShowEmergencyModal(false)}
                                style={{ marginLeft: "auto", background: "none", border: "none", color: "var(--text3)", fontSize: 18, cursor: "pointer" }}
                            >✕</button>
                        </div>

                        {emergencySuccess ? (
                            <div style={{ textAlign: "center", padding: "30px 20px", color: "var(--red)" }}>
                                <p className="font-mono" style={{ fontSize: 24, fontWeight: 600, marginBottom: 8 }}>[ DISPATCHED ]</p>
                                <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text)" }}>Emergency protocol successfully triggered.</p>
                                <p className="font-mono" style={{ fontSize: 10, color: "var(--text3)", marginTop: 4 }}>Agents are resolving the issue.</p>
                            </div>
                        ) : (
                            <form onSubmit={handleEmergencySubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                                <textarea
                                    value={emergencyInput}
                                    onChange={e => setEmergencyInput(e.target.value)}
                                    placeholder="Describe the critical issue... e.g. Registration server is down"
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
                                    disabled={emergencyLoading}
                                    style={{
                                        background: "var(--red)", color: "#0a0a0b", border: "none",
                                        padding: "10px", borderRadius: 8, fontSize: 12,
                                        fontWeight: 600, cursor: emergencyLoading ? "not-allowed" : "pointer",
                                        opacity: emergencyLoading ? 0.7 : 1, alignSelf: "flex-start",
                                        paddingLeft: 24, paddingRight: 24, fontFamily: "inherit"
                                    }}
                                >
                                    {emergencyLoading ? "DISPATCHING..." : "TRIGGER OVERRIDE"}
                                </button>
                            </form>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};

export default Index;
