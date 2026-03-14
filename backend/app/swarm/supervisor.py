"""
LangGraph Supervisor Node — the central routing orchestrator.

Implements Star Topology: all agents report back to the Supervisor,
which evaluates the EventState and routes to the next appropriate
worker via conditional edges.
"""

from typing import Any

from langchain_core.messages import AIMessage

from app.swarm.state import EventState
import logging

logger = logging.getLogger(__name__)

# Agent name constants (must match node names in the graph)
PROBLEM_SOLVER = "problem_solver"
MARKETING = "marketing"
SCHEDULER = "scheduler"
EMAIL = "email"
EMERGENCY_INFO = "emergency_info"
BUDGET_FINANCE = "budget_finance"
END = "end"


async def supervisor_node(state: EventState) -> dict[str, Any]:
    """
    The Supervisor evaluates the current EventState and decides which
    agent should execute next.

    Routing Logic:
    0. If direct_route is set → route there immediately (bypasses triage).
       After that agent reports back, route to END.
    1. If no problem_category yet → Route to Problem_Solver_Agent
    2. If problem_category == "finance" → Route to Budget_Finance_Agent
    3. If problem_category == "reschedule" → Route to Scheduler_Agent
    4. If schedule_changed_flag == True (and hasn't been emailed) →
       Route to Email_Agent for mass notification
    5. If problem_category == "urgent" AND emergency_handled_flag == False →
       Route to Emergency_Info_Agent
    6. If problem_category == "urgent" AND emergency_handled_flag == True →
       Route to Email_Agent for mass alert
    7. If problem_category in ("normal", "human_escalation") →
       Log to DB queue and route to END

    Once a task pipeline completes all required flags → Route to END.
    """

    # --- Direct Route Override ---
    # When a dedicated endpoint sets direct_route, the supervisor sends the
    # request straight to that agent without triage, then ends the graph.
    _agent_display_name = {
        MARKETING: "Marketing_Agent",
        EMAIL: "Email_Agent",
        SCHEDULER: "Scheduler_Agent",
        PROBLEM_SOLVER: "Problem_Solver_Agent",
        EMERGENCY_INFO: "Emergency_Info_Agent",
        BUDGET_FINANCE: "Budget_Finance_Agent",
    }
    direct_route = state.get("direct_route", "")
    if direct_route:
        display_name = _agent_display_name.get(direct_route, "")
        already_ran = any(
            getattr(m, "name", None) == display_name
            for m in state.get("messages", [])
        )
        if not already_ran:
            log_msg = f"[Supervisor] Direct route requested → {direct_route}."
            logger.info(log_msg)
            return {
                "next_agent": direct_route,
                "messages": [AIMessage(content=log_msg, name="Supervisor")],
            }
        else:
            log_msg = f"[Supervisor] Direct route '{direct_route}' completed → END."
            logger.info(log_msg)
            return {
                "next_agent": END,
                "messages": [AIMessage(content=log_msg, name="Supervisor")],
            }

    category = state.get("problem_category", "")
    urgency = state.get("urgency_score", 0)
    schedule_changed = state.get("schedule_changed_flag", False)
    emergency_handled = state.get("emergency_handled_flag", False)

    # Determine routing
    next_agent = END
    routing_reason = ""

    if not category:
        # Step 1: No classification yet — triage first
        next_agent = PROBLEM_SOLVER
        routing_reason = "No classification yet. Routing to Problem Solver for triage."

    elif category == "finance":
        # Check if the Budget Finance Agent has already run in THIS session
        # (not whether a budget report exists in DB — that's always pre-loaded)
        budget_agent_ran = any(
            getattr(m, "name", None) == "Budget_Finance_Agent"
            for m in state.get("messages", [])
        )
        if not budget_agent_ran:
            next_agent = BUDGET_FINANCE
            routing_reason = "Finance issue detected. Routing to Budget Finance Agent."
        else:
            next_agent = END
            routing_reason = "Finance issue resolved. Budget report generated."

    elif category == "reschedule":
        if not schedule_changed:
            next_agent = SCHEDULER
            routing_reason = "Reschedule request. Routing to Scheduler Agent."
        else:
            # Schedule was changed — need to notify participants
            # Check if email already sent by looking at messages
            email_sent = any(
                hasattr(m, "name") and m.name == "Email_Agent"
                for m in state.get("messages", [])
            )
            if not email_sent:
                next_agent = EMAIL
                routing_reason = "Schedule changed. Routing to Email Agent for mass notification."
            else:
                next_agent = END
                routing_reason = "Schedule updated and participants notified."

    elif category == "urgent":
        if not emergency_handled:
            next_agent = EMERGENCY_INFO
            routing_reason = "Urgent issue. Routing to Emergency Info Agent."
        else:
            # Emergency handled — send mass alert via email
            email_sent = any(
                hasattr(m, "name") and m.name == "Email_Agent"
                for m in state.get("messages", [])
            )
            if not email_sent:
                next_agent = EMAIL
                routing_reason = "Emergency handled. Routing to Email Agent for mass alert."
            else:
                next_agent = END
                routing_reason = "Urgent issue fully handled and communicated."

    elif category in ("normal", "human_escalation"):
        next_agent = END
        routing_reason = f"Category '{category}'. Logging to queue and terminating."

    else:
        next_agent = END
        routing_reason = f"Unknown category '{category}'. Terminating."

    log_msg = f"[Supervisor] Decision: {routing_reason} → Next: {next_agent}"
    # Log decision to standard logger as well for observability
    logger.info(log_msg)

    return {
        "next_agent": next_agent,
        "messages": [AIMessage(content=log_msg, name="Supervisor")],
    }


def route_from_supervisor(state: EventState) -> str:
    """
    Conditional edge function used by LangGraph to determine the next
    node after the Supervisor executes.

    Returns the node name string that LangGraph uses for routing.
    """
    return state.get("next_agent", END)
