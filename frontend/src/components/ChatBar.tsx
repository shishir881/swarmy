import { useState, useRef, useEffect } from "react";
import { Send, ArrowLeft, MessageSquarePlus } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import { playMessageSound } from "../utils/sounds";

type ChatMessage = { role: "user" | "bot"; text: string };

export function ChatBar({ eventId, isExpanded, setExpanded, onInputChange }: { eventId?: string, isExpanded?: boolean, setExpanded?: (x: boolean) => void, onInputChange?: (x: string) => void }) {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const chatEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, loading]);

    const sendMessage = async () => {
        if (!input.trim() || loading) return;
        const promptText = input.trim();
        const userMsg: ChatMessage = { role: "user", text: promptText };
        setMessages((prev) => [...prev, userMsg]);
        setInput("");
        onInputChange?.("");
        setLoading(true);
        playMessageSound();

        // Force expand when sending a message if not expanded yet
        if (!isExpanded && setExpanded) setExpanded(true);

        try {
            const evId = eventId || "1";
            const res = await axios.post(`/api/v1/organizer/events/${evId}/trigger_swarm`, {
                command: promptText
            });
            const data = res.data;
            let output = data?.logs?.length ? data.logs.join("\n") : "Task handled by mela.ai.";

            if (data?.state?.problem_category) {
                const category = data.state.problem_category.toLowerCase();
                if (category === "emergency" || category === "urgent") {
                    output = "The problem is emergency, show alert";
                } else if (category === "budget" || category === "reschedule" || category === "logistics") {
                    output = `The problem is ${category}. Fixed, as the agents have fixed it themselves.`;
                } else if (category === "human_escalation" || category === "human" || category === "escalate") {
                    output = "The problem requires human intervention. Your problem is sent to the organizing committee.";
                }
            }

            setMessages((prev) => [
                ...prev,
                { role: "bot", text: output },
            ]);
        } catch (err: unknown) {
            let errorMsg = "Failed to connect to the swarm.";
            if (axios.isAxiosError(err) && err.response?.data?.detail) {
                errorMsg = err.response.data.detail;
            }
            setMessages((prev) => [
                ...prev,
                { role: "bot", text: `Error: ${errorMsg}` },
            ]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: 16, height: isExpanded ? "100%" : "auto" }}>
            {/* Topbar logic for fullscreen back button */}
            {isExpanded && (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                    <h2 style={{ fontSize: 14, fontWeight: 500, margin: 0, color: "var(--text)" }}><span style={{ color: "var(--green)" }}>mela</span><span style={{ color: "var(--text)" }}>.ai Live Execution</span></h2>
                    <button onClick={() => setExpanded?.(false)} style={{ background: "none", border: "none", color: "var(--text3)", cursor: "pointer", display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}>
                        <ArrowLeft size={16} /> Back
                    </button>
                </div>
            )}

            {/* Messages */}
            <AnimatePresence>
                {messages.length > 0 && isExpanded && (
                    <motion.div
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 6 }}
                        style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 12, padding: "0 4px" }}
                    >
                        {messages.map((msg, i) => (
                            <motion.div
                                key={i}
                                initial={{ opacity: 0, y: 4 }}
                                animate={{ opacity: 1, y: 0 }}
                                style={{ display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }}
                            >
                                <span
                                    style={{
                                        fontSize: 13,
                                        padding: "10px 14px",
                                        borderRadius: 8,
                                        maxWidth: "80%",
                                        lineHeight: 1.6,
                                        background: msg.role === "user" ? "rgba(0, 232, 122, 0.1)" : "var(--surface2)",
                                        color: msg.role === "user" ? "var(--green)" : "var(--text)",
                                        border: msg.role === "user" ? "1px solid rgba(0, 232, 122, 0.2)" : "1px solid var(--border)",
                                        whiteSpace: "pre-wrap",
                                        wordBreak: "break-word",
                                        fontFamily: msg.role === "bot" ? "'Geist Mono', monospace" : "inherit"
                                    }}
                                >
                                    {msg.text}
                                </span>
                            </motion.div>
                        ))}
                        {loading && (
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                style={{ display: "flex", justifyContent: "flex-start" }}
                            >
                                <span style={{ fontSize: 12, padding: "8px 14px", borderRadius: 8, background: "var(--surface2)", color: "var(--text3)", border: "1px solid var(--border)", fontStyle: "italic" }}>
                                    <span style={{ color: "var(--green)" }}>mela</span><span style={{ color: "var(--text3)" }}>.ai agents executing...</span>
                                </span>
                            </motion.div>
                        )}
                        <div ref={chatEndRef} />
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Quick Replies for expanded mode */}
            {isExpanded && messages.length === 0 && (
                <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 8, paddingLeft: 4 }}>
                    {[
                        "Draft an announcement email",
                        "Check for scheduling conflicts",
                        "Audit the budget for a 10% cut"
                    ].map(suggestion => (
                        <button
                            key={suggestion}
                            onClick={() => { setInput(suggestion); onInputChange?.(suggestion); }}
                            style={{
                                flexShrink: 0,
                                background: "var(--surface2)",
                                border: "1px solid var(--border)",
                                color: "var(--text2)",
                                padding: "6px 12px",
                                borderRadius: 16,
                                fontSize: 12,
                                display: "flex",
                                alignItems: "center",
                                gap: 6,
                                cursor: "pointer",
                                transition: "all 0.2s"
                            }}
                            onMouseEnter={e => { e.currentTarget.style.color = "var(--text)"; e.currentTarget.style.borderColor = "var(--border2)"; }}
                            onMouseLeave={e => { e.currentTarget.style.color = "var(--text2)"; e.currentTarget.style.borderColor = "var(--border)"; }}
                        >
                            <MessageSquarePlus size={12} />
                            {suggestion}
                        </button>
                    ))}
                </div>
            )}

            {/* Input row */}
            <div
                className="depth-panel"
                style={{ display: "flex", alignItems: isExpanded ? "flex-end" : "center", gap: 8, padding: "12px 14px", position: "relative", zIndex: 10 }}
                onClick={() => { if (!isExpanded && setExpanded) setExpanded(true); }}
            >
                {/* bolt icon removed */}
                {isExpanded ? (
                    <textarea
                        value={input}
                        onChange={(e) => { setInput(e.target.value); onInputChange?.(e.target.value); }}
                        onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), sendMessage())}
                        placeholder="Instruct the swarm to solve a problem..."
                        style={{ flex: 1, background: "transparent", border: "none", outline: "none", fontSize: 13, color: "var(--text)", fontFamily: "inherit", resize: "none", minHeight: 90 }}
                        disabled={loading}
                        autoFocus
                    />
                ) : (
                    <input
                        value={input}
                        onChange={(e) => { setInput(e.target.value); onInputChange?.(e.target.value); }}
                        onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
                        placeholder="Report an event issue to mela.ai..."
                        style={{ flex: 1, background: "transparent", border: "none", outline: "none", fontSize: 13, color: "var(--text)", fontFamily: "inherit" }}
                        disabled={loading}
                    />
                )}

                <button
                    onClick={sendMessage}
                    disabled={!input.trim() || loading}
                    style={{ width: 32, height: 32, borderRadius: 6, background: "var(--text)", border: "none", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", flexShrink: 0, opacity: (!input.trim() || loading) ? 0.4 : 1, transition: "opacity 0.2s" }}
                >
                    <Send size={14} color="#080809" />
                </button>
            </div>
        </div>
    );
}
