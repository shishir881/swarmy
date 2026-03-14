import { useState, useRef, useEffect } from "react";
import { Send, Zap, ArrowLeft, MessageSquarePlus } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";

type ChatMessage = { role: "user" | "bot"; text: string };

export function ChatBar({ eventId, isExpanded, setExpanded }: { eventId?: string, isExpanded?: boolean, setExpanded?: (x: boolean) => void }) {
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
        setLoading(true);

        // Force expand when sending a message if not expanded yet
        if (!isExpanded && setExpanded) setExpanded(true);

        try {
            const evId = eventId || "1";
            const res = await axios.post(`/api/v1/organizer/events/${evId}/run_emergency`, {
                problem_description: promptText
            });
            const data = res.data;
            const output = data?.emergency_alert_message
                || (data?.logs?.length ? data.logs.join("\n") : "Emergency handled by Swarm.");

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
                    <h2 style={{ fontSize: 14, fontWeight: 500, margin: 0, color: "var(--text)" }}>Swarm Live Execution</h2>
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
                                    Swarm agents executing...
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
                            onClick={() => setInput(suggestion)}
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
                <Zap size={14} color="var(--text3)" style={{ flexShrink: 0, marginBottom: isExpanded ? 6 : 0 }} />
                {isExpanded ? (
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), sendMessage())}
                        placeholder="Instruct the swarm to solve a problem..."
                        style={{ flex: 1, background: "transparent", border: "none", outline: "none", fontSize: 13, color: "var(--text)", fontFamily: "inherit", resize: "none", minHeight: 90 }}
                        disabled={loading}
                        autoFocus
                    />
                ) : (
                    <input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && sendMessage()}
                        placeholder="Report an event issue to the Swarm..."
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
