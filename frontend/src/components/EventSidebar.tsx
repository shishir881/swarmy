import { Calendar, ChevronRight } from "lucide-react";
import {
    Sidebar,
    SidebarContent,
    SidebarGroup,
    SidebarGroupContent,
    SidebarGroupLabel,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
} from "@/components/ui/sidebar";

const pastEvents = [
    { id: 1, title: "Tech Fest 2025", date: "Feb 15, 2025", status: "completed" },
    { id: 2, title: "Hackathon Spring", date: "Jan 28, 2025", status: "completed" },
    { id: 3, title: "Cultural Night", date: "Jan 10, 2025", status: "completed" },
    { id: 4, title: "Workshop: AI/ML", date: "Dec 5, 2024", status: "completed" },
    { id: 5, title: "Sports Meet", date: "Nov 20, 2024", status: "completed" },
    { id: 6, title: "Fresher's Party", date: "Oct 8, 2024", status: "completed" },
];

export function EventSidebar() {
    return (
        <Sidebar collapsible="offcanvas" className="border-r border-border">
            <SidebarContent className="pt-4">
                {/* Brand */}
                <div className="px-4 pb-4 flex items-center gap-2">
                    <span className="text-sm font-semibold tracking-tight text-foreground"><span style={{ color: 'var(--green)' }}>mela</span><span style={{ color: 'var(--text)' }}>.ai</span></span>
                </div>

                <SidebarGroup>
                    <SidebarGroupLabel className="text-muted-foreground text-[10px] uppercase tracking-widest px-3 flex items-center gap-1.5">
                        <Calendar className="h-3 w-3" />
                        Previous Events
                    </SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {pastEvents.map((event) => (
                                <SidebarMenuItem key={event.id}>
                                    <SidebarMenuButton className="group cursor-pointer hover:bg-sidebar-accent transition-colors h-auto py-2">
                                        <div className="flex items-center justify-between w-full">
                                            <div className="flex flex-col gap-0.5 min-w-0">
                                                <span className="text-sm text-sidebar-accent-foreground group-hover:text-foreground transition-colors truncate">
                                                    {event.title}
                                                </span>
                                                <span className="text-xs text-muted-foreground">{event.date}</span>
                                            </div>
                                            <ChevronRight className="h-3 w-3 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0 ml-2" />
                                        </div>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            ))}
                        </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>
            </SidebarContent>
        </Sidebar>
    );
}
