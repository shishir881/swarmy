import { motion } from "framer-motion";
import type { LucideIcon } from "lucide-react";

interface AgentCardProps {
    title: string;
    description: string;
    icon: LucideIcon;
    colorVar: string;
    onClick: () => void;
    index: number;
}

const colorMap: Record<string, string> = {
    "agent-content": "hsl(160, 80%, 48%)",
    "agent-email": "hsl(270, 60%, 60%)",
    "agent-schedule": "hsl(35, 90%, 55%)",
};

export function AgentCard({ title, description, icon: Icon, colorVar, onClick, index }: AgentCardProps) {
    const glowColor = colorMap[colorVar] || "hsl(160, 80%, 48%)";

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1], delay: index * 0.1 }}
            onClick={onClick}
            className="group relative cursor-pointer rounded-2xl border border-border/40 bg-card p-7 transition-all duration-500 hover:border-transparent min-w-[280px] max-w-[320px] w-full min-h-[280px] flex flex-col will-change-transform"
            style={{
                boxShadow: `0 0 0px ${glowColor}00`,
            }}
            whileHover={{
                boxShadow: `0 0 30px ${glowColor}20, 0 0 60px ${glowColor}10`,
                borderColor: glowColor,
                y: -6,
                scale: 1.02,
            }}
        >
            <div
                className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl"
                style={{ backgroundColor: `${glowColor}18` }}
            >
                <Icon className="h-6 w-6" style={{ color: glowColor }} />
            </div>

            <h3 className="mb-2 text-lg font-semibold text-foreground">{title}</h3>
            <p className="text-sm leading-relaxed text-muted-foreground">{description}</p>

            <div className="mt-4 flex items-center gap-1.5">
                <div className="h-2 w-2 rounded-full animate-pulse" style={{ backgroundColor: glowColor }} />
                <span className="text-xs font-mono" style={{ color: glowColor }}>
                    Ready
                </span>
            </div>
        </motion.div>
    );
}
