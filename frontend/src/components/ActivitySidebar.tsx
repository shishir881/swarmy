import { AlertTriangle, MessageSquare } from "lucide-react";

export function ActivitySidebar() {
    return (
        <aside className="w-60 min-w-[240px] border-l border-border bg-sidebar flex flex-col overflow-hidden shrink-0">
            {/* Reported Problems */}
            <div className="flex-1 flex flex-col overflow-hidden border-b border-sidebar-border">
                <div className="px-3 py-2.5 flex items-center gap-1.5 shrink-0">
                    <AlertTriangle className="h-3 w-3 text-destructive shrink-0" />
                    <span className="text-[10px] font-mono tracking-wide text-sidebar-foreground uppercase">Problems</span>
                    <span className="ml-auto text-[9px] font-mono bg-destructive/10 text-destructive px-1.5 py-0.5 rounded-md">0</span>
                </div>
                <div className="flex-1 flex items-center justify-center">
                    <p className="text-[10px] text-muted-foreground/50 font-mono">No issues reported</p>
                </div>
            </div>

            {/* User Queries */}
            <div className="flex-1 flex flex-col overflow-hidden">
                <div className="px-3 py-2.5 flex items-center gap-1.5 shrink-0">
                    <MessageSquare className="h-3 w-3 text-accent shrink-0" />
                    <span className="text-[10px] font-mono tracking-wide text-sidebar-foreground uppercase">Queries</span>
                    <span className="ml-auto text-[9px] font-mono bg-accent/10 text-accent px-1.5 py-0.5 rounded-md">0</span>
                </div>
                <div className="flex-1 flex items-center justify-center">
                    <p className="text-[10px] text-muted-foreground/50 font-mono">No queries yet</p>
                </div>
            </div>
        </aside>
    );
}
