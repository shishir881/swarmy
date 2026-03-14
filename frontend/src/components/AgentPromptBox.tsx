import { useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Send, Paperclip, X, Loader2, CheckCircle2, AlertCircle, Clock } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import axios from "axios";

interface AgentPromptBoxProps {
    title: string;
    icon: LucideIcon;
    colorVar: string;
    onBack: () => void;
    eventId?: string;
}

const colorMap: Record<string, string> = {
    "agent-content": "hsl(160, 80%, 48%)",
    "agent-email": "hsl(270, 60%, 60%)",
    "agent-schedule": "hsl(35, 90%, 55%)",
};

/** Extract a human-readable string from each agent's specific response schema. */
function parseAgentOutput(colorVar: string, data: Record<string, unknown>): string {
    if (colorVar === "agent-content") {
        // MarketingResult: generated_content + logs
        const content = (data?.generated_content as string) || "";
        const logs = (data?.logs as string[]) || [];
        const parts: string[] = [];
        if (content) parts.push(content);
        if (logs.length) parts.push("\n📋 Agent Logs:\n" + logs.map((l) => `  • ${l}`).join("\n"));
        return parts.join("\n\n") || JSON.stringify(data, null, 2);
    }

    if (colorVar === "agent-email") {
        // EmailCampaignResult: recipients_count + logs
        const count = data?.recipients_count as number;
        const logs = (data?.logs as string[]) || [];
        const parts: string[] = [];
        if (count !== undefined) parts.push(`✉️ Campaign sent to ${count} recipient(s).`);
        if (logs.length) parts.push("\n📋 Agent Logs:\n" + logs.map((l) => `  • ${l}`).join("\n"));
        return parts.join("\n") || JSON.stringify(data, null, 2);
    }

    if (colorVar === "agent-schedule") {
        // ScheduleAgentResult: master_schedule + logs
        const schedule = data?.master_schedule as Record<string, unknown>;
        const logs = (data?.logs as string[]) || [];
        const parts: string[] = [];
        if (schedule && Object.keys(schedule).length) {
            parts.push("📅 Generated Schedule:\n" +
                Object.entries(schedule).map(([k, v]) => `  ${k}: ${typeof v === "object" ? JSON.stringify(v) : v}`).join("\n")
            );
        }
        if (logs.length) parts.push("\n📋 Agent Logs:\n" + logs.map((l) => `  • ${l}`).join("\n"));
        return parts.join("\n\n") || JSON.stringify(data, null, 2);
    }

    // Fallback
    return (data?.generated_content as string)
        || (data?.message as string)
        || (data?.result as string)
        || JSON.stringify(data, null, 2);
}

export function AgentPromptBox({ title, icon: Icon, colorVar, onBack, eventId }: AgentPromptBoxProps) {
    const [prompt, setPrompt] = useState("");
    const [csvFile, setCsvFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const fileRef = useRef<HTMLInputElement>(null);

    const glowColor = colorMap[colorVar] || "hsl(160, 80%, 48%)";
    const isEmail = colorVar === "agent-email";

    const endpointMap: Record<string, string> = {
        "agent-content": "run_marketing",
        "agent-email": "run_email",
        "agent-schedule": "run_scheduler",
    };
    const endpoint = endpointMap[colorVar] || "run_swarm";

    const handleRun = async () => {
        if (!prompt.trim()) return;
        if (isEmail && !csvFile) return;
        setLoading(true);
        setResult(null);
        setError(null);
        try {
            const API = "/api/v1";
            const evId = eventId || "1";
            let res;
            if (isEmail) {
                const form = new FormData();
                form.append("csv_file", csvFile as File);
                form.append("sample_email", prompt);
                res = await axios.post(`${API}/organizer/events/${evId}/${endpoint}`, form, {
                    headers: { "Content-Type": "multipart/form-data" },
                });
            } else {
                res = await axios.post(`${API}/organizer/events/${evId}/${endpoint}`, {
                    prompt,
                    event_id: Number(evId),
                });
            }
            setResult(parseAgentOutput(colorVar, res.data as Record<string, unknown>));
        } catch (err: unknown) {
            if (axios.isAxiosError(err)) {
                setError(err.response?.data?.detail || err.message || "Agent run failed");
            } else {
                setError("Something went wrong. Please try again.");
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <motion.div
            layout
            initial={{ opacity: 0, scale: 0.96, y: 16 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 16 }}
            transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] }}
            className="w-full max-w-2xl mx-auto"
        >
            <button
                onClick={onBack}
                className="mb-5 flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors group"
            >
                <ArrowLeft className="h-4 w-4 transition-transform group-hover:-translate-x-1" />
                Back to agents
            </button>

            <div
                className="rounded-2xl border border-border/60 bg-card p-6 space-y-4"
                style={{ boxShadow: `0 0 50px ${glowColor}10` }}
            >
                {/* Header */}
                <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-xl flex items-center justify-center shrink-0"
                        style={{ backgroundColor: `${glowColor}18` }}>
                        <Icon className="h-5 w-5" style={{ color: glowColor }} />
                    </div>
                    <div>
                        <h2 className="text-base font-semibold text-foreground">{title}</h2>
                        <div className="flex items-center gap-1.5 mt-0.5">
                            <div className="h-1.5 w-1.5 rounded-full animate-pulse" style={{ backgroundColor: glowColor }} />
                            <span className="text-xs text-muted-foreground font-mono">Active · Ready</span>
                        </div>
                    </div>
                </div>

                {/* Prompt textarea */}
                <Textarea
                    value={prompt}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setPrompt(e.target.value)}
                    placeholder={
                        isEmail
                            ? "Write a sample email body (used as tone/style reference)..."
                            : `Describe what you want the ${title} to do...`
                    }
                    className="min-h-[140px] resize-none bg-muted/40 border-border/50 text-foreground placeholder:text-muted-foreground focus-visible:ring-1 focus-visible:ring-offset-0 rounded-xl text-sm leading-relaxed"
                />

                {/* CSV upload — email only */}
                {isEmail && (
                    <>
                        <input type="file" accept=".csv,text/csv" ref={fileRef} className="hidden"
                            onChange={(e) => setCsvFile(e.target.files?.[0] ?? null)} />
                        {!csvFile ? (
                            <button type="button" onClick={() => fileRef.current?.click()}
                                className="w-full flex items-center justify-center gap-2 rounded-xl border border-dashed border-border/60 bg-muted/20 px-4 py-3 text-sm text-muted-foreground hover:border-primary/50 hover:text-foreground transition-colors">
                                <Paperclip className="h-4 w-4" />
                                Upload recipient CSV (name, email, segment)
                            </button>
                        ) : (
                            <div className="flex items-center gap-2 rounded-xl border border-primary/30 bg-primary/5 px-4 py-2.5 text-sm">
                                <Paperclip className="h-4 w-4 text-primary shrink-0" />
                                <span className="text-foreground truncate flex-1">{csvFile.name}</span>
                                <button onClick={() => { setCsvFile(null); if (fileRef.current) fileRef.current.value = ""; }}
                                    className="text-muted-foreground hover:text-foreground transition-colors">
                                    <X className="h-3.5 w-3.5" />
                                </button>
                            </div>
                        )}
                    </>
                )}

                {/* Run button */}
                <div className="flex justify-end">
                    <Button onClick={handleRun}
                        disabled={!prompt.trim() || (isEmail && !csvFile) || loading}
                        className="gap-2 rounded-xl px-6 font-medium text-sm disabled:opacity-40 transition-all"
                        style={{ backgroundColor: glowColor, color: "hsl(230, 25%, 7%)" }}>
                        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                        {loading ? "Running..." : "Run Agent"}
                    </Button>
                </div>
            </div>

            {/* Loading indicator */}
            <AnimatePresence>
                {loading && (
                    <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 8 }}
                        className="mt-4 rounded-2xl border border-border/40 bg-card p-5 flex items-center gap-3"
                    >
                        <Clock className="h-4 w-4 text-muted-foreground animate-spin" />
                        <span className="text-sm text-muted-foreground font-mono">Swarm agents running...</span>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Output panel */}
            <AnimatePresence>
                {(result || error) && !loading && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 10 }}
                        transition={{ duration: 0.35 }}
                        className={`mt-4 rounded-2xl border p-5 ${error
                            ? "border-destructive/30 bg-destructive/5"
                            : "border-border/50 bg-card"}`}
                    >
                        <div className="flex items-center gap-2 mb-4">
                            {error
                                ? <AlertCircle className="h-4 w-4 text-destructive shrink-0" />
                                : <CheckCircle2 className="h-4 w-4 text-primary shrink-0" />}
                            <span className={`text-sm font-semibold ${error ? "text-destructive" : "text-foreground"}`}>
                                {error ? "Agent Error" : `${title} Output`}
                            </span>
                        </div>
                        <pre className="text-sm text-muted-foreground whitespace-pre-wrap leading-relaxed font-sans break-words">
                            {error || result}
                        </pre>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
}
