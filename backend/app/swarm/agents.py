"""
LangGraph Swarm Worker Agents.

Each agent is an async node function that:
  1. Prepends the event_context to its system prompt.
  2. Uses LLM reasoning (Groq Llama-3) to perform its specialized task.
  3. Updates the global EventState and appends log messages.

All 6 agents follow the Star Topology — they return control to the
Supervisor after completing their work.
"""

import json
import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from app.config import settings
from app.swarm.state import EventState
from app.swarm.tools import predict_best_posting_times, send_bulk_email


def _parse_json(text: str) -> Any:
    """
    Parse JSON from an LLM response, stripping markdown code fences if present.
    Raises json.JSONDecodeError if the content is not valid JSON after stripping.
    """
    text = text.strip()
    # Strip ```json ... ``` or ``` ... ``` fences
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text.strip())
    return json.loads(text.strip())


def _get_llm() -> ChatGroq:
    """Create a ChatGroq LLM instance with the configured model."""
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name=settings.LLM_MODEL,
        temperature=0.3,
        max_tokens=2048,
    )


# Allowed problem categories for validation
_VALID_CATEGORIES = {"finance", "reschedule", "urgent", "normal", "human_escalation"}


def _extract_emergency_alert(text: str) -> str:
    """
    Normalize LLM output into a single dashboard alert line.

    Rules enforced:
    - Must begin with "🚨 CRITICAL ALERT: ".
    - Must be <= 100 characters.
    - Must be single-line, no markdown wrappers.
    """
    cleaned = text.strip()
    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:text)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())

    # Extract the first non-empty line
    first_line = ""
    for line in cleaned.splitlines():
        candidate = line.strip()
        if candidate:
            first_line = candidate
            break

    if not first_line:
        first_line = "Emergency reported. Organizer action required."

    # Strip common LLM preamble labels
    first_line = re.sub(
        r"^(?:ALERT\s*MESSAGE|ALERT|CRITICAL\s*ALERT)\s*:\s*",
        "", first_line, flags=re.IGNORECASE,
    )
    first_line = first_line.strip().strip('"').strip("'")

    # Strip any existing leading emoji / prefix so we can re-apply canonically
    first_line = re.sub(r"^🚨\s*(?:CRITICAL\s+ALERT\s*:?\s*)?", "", first_line).strip()

    # Apply the canonical prefix
    alert = f"🚨 CRITICAL ALERT: {first_line}"

    if len(alert) > 100:
        alert = alert[:100].rstrip()

    return alert


# ---------------------------------------------------------------------------
# 1. Problem Solver Agent (Classifier & Triage — Anti-Panic Gatekeeper)
# ---------------------------------------------------------------------------

async def problem_solver_agent(state: EventState) -> dict[str, Any]:
    """
    Classify the input issue into a problem_category and assign an
    urgency_score based on severity.

    Acts as an Anti-Panic Gatekeeper: only genuine life-threatening or
    severe venue-safety issues are classified as "urgent".  Technical
    glitches, lost items, and angry attendees are downgraded.

    Categories: finance, reschedule, urgent, normal, human_escalation
    """
    llm = _get_llm()

    system_prompt = f"""You are the Problem Solver Agent — the Anti-Panic Gatekeeper — for an event management system.

EVENT CONTEXT:
{state['event_context']}

Your task is to analyze the user's issue and:
1. Classify it into exactly ONE category.
2. Assign an urgency_score (integer).

You MUST respond with ONLY valid JSON — no markdown code fences, no preamble, no explanation outside the JSON.
Exact format:
{{"problem_category": "<category>", "urgency_score": <integer>, "reasoning": "<brief explanation>"}}

CLASSIFICATION & SCORING RULES (follow these EXACTLY):

• "finance"  — Budget concerns, payment issues, cost overruns, sponsorship queries.
  urgency_score MUST be 0.

• "reschedule"  — Delays, timetable clashes, venue conflicts, timeline adjustments.
  urgency_score MUST be 0.

• "urgent"  — ONLY for immediate physical threats to life, health, or severe venue safety
  (fire, medical emergency, structural collapse, active security threat).
  urgency_score MUST be an integer between 8 and 10.
  *** ANTI-PANIC GUARDRAIL ***
  Do NOT classify the following as "urgent" — downgrade to "normal" or "human_escalation":
    - Technical glitches (projector broken, Wi-Fi down, mic not working)
    - Lost or stolen personal items
    - Angry or upset attendees / interpersonal conflicts
    - Catering complaints or minor logistical hiccups

• "human_escalation"  — Complex manual problems requiring human judgment (repairs, legal,
  VIP complaints, policy decisions).
  urgency_score MUST be an integer between 1 and 7.

• "normal"  — General inquiries, feedback, tech glitches, minor complaints.
  urgency_score MUST be an integer between 1 and 7.
"""

    # Get the latest user message (the issue being reported)
    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    issue_text = user_messages[-1].content if user_messages else "No issue provided"

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Classify this issue: {issue_text}"),
    ])

    # Parse the LLM response (strip markdown fences if present)
    try:
        parsed = _parse_json(response.content)
        category = parsed.get("problem_category", "normal")
        score = int(parsed.get("urgency_score", 5))
        reasoning = parsed.get("reasoning", "")
    except (json.JSONDecodeError, ValueError):
        category = "normal"
        score = 5
        reasoning = "Could not parse LLM response; defaulting to normal category."

    # Validate category against allowed set
    if category not in _VALID_CATEGORIES:
        reasoning = (
            f"LLM returned unknown category '{category}'; "
            f"defaulting to 'normal'. Original reasoning: {reasoning}"
        )
        category = "normal"
        score = 5

    # Enforce per-category urgency clamping rules
    if category == "finance":
        score = 0
    elif category == "reschedule":
        score = 0
    elif category == "urgent":
        score = max(8, min(10, score))
    elif category in ("normal", "human_escalation"):
        score = max(1, min(7, score))

    log_msg = f"[Problem_Solver] Category: {category}, Urgency: {score}/10. {reasoning}"

    return {
        "problem_category": category,
        "urgency_score": score,
        "messages": [AIMessage(content=log_msg, name="Problem_Solver_Agent")],
    }


# ---------------------------------------------------------------------------
# 2. Marketing Agent (Promoter)
# ---------------------------------------------------------------------------

async def marketing_agent(state: EventState) -> dict[str, Any]:
    """
    Draft promotional copy tailored to the specific event and use ML-powered
    prediction to determine the best posting times based on engagement forecasting.
    
    Returns both formatted text and hourly engagement predictions for charting.
    The LLM outputs JSON containing:
    - promotional_post: The drafted social media content
    - ml_features: Platform, sentiment, day_of_week, hashtag_count for ML prediction
    """
    llm = _get_llm()

    system_prompt = f"""You are an Expert Event Marketing Agent with deep knowledge of social media engagement.

EVENT CONTEXT:
{state['event_context']}

Your task is to:
1. Draft a compelling promotional post for the event
2. Extract features needed for ML-based engagement prediction

You MUST respond with STRICTLY VALID JSON in this exact format:
{{
    "promotional_post": "Your drafted promotional text here with hashtags",
    "ml_features": {{
        "platform": "twitter|linkedin|instagram|facebook",
        "sentiment_group": "Positive/High Energy|Negative/Low Energy|Professional/Motivational|Neutral/Informational|General",
        "day_of_week": 0-6,
        "hashtag_count": <number_of_hashtags_in_post>
    }}
}}

CRITICAL RULES:
- sentiment_group MUST be exactly one of: 'Positive/High Energy', 'Negative/Low Energy', 'Professional/Motivational', 'Neutral/Informational', 'General'
- platform should be lowercase: twitter, linkedin, instagram, or facebook
- day_of_week: 0=Monday, 1=Tuesday, ..., 6=Sunday
- hashtag_count: Count the number of hashtags you include in the promotional_post
- Do NOT include any text outside the JSON structure
- Do NOT use markdown code fences

Make the post compelling, relevant to the event context, and optimized for engagement.
"""

    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    # Prefer the dedicated marketing_prompt from a direct-route request
    context = (
        state.get("marketing_prompt")
        or (user_messages[-1].content if user_messages else "Create a promotional post for the event")
    )

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Draft promotional content based on: {context}"),
    ])

    # Parse the LLM's JSON response
    try:
        parsed = _parse_json(response.content)
        promotional_post = parsed.get("promotional_post", "")
        ml_features = parsed.get("ml_features", {})
        
        # Extract features with defaults
        platform = ml_features.get("platform", "twitter")
        sentiment_group = ml_features.get("sentiment_group", "Positive/High Energy")
        day_of_week = int(ml_features.get("day_of_week", 0))
        hashtag_count = int(ml_features.get("hashtag_count", 0))

        # Validate and clamp day_of_week
        day_of_week = max(0, min(6, day_of_week))

        # Call the ML prediction tool (now returns tuple: text, hourly_data)
        ml_prediction_text, hourly_engagement_data = predict_best_posting_times(
            llm_text=promotional_post,
            llm_platform=platform,
            llm_sentiment=sentiment_group,
            llm_day_of_week=day_of_week,
            llm_hashtag_count=hashtag_count,
        )

        # Format the final output with all details
        log_msg = f"""[Marketing_Agent] Promotional Content Created

📝 DRAFTED POST:
{promotional_post}

🎯 EXTRACTED FEATURES:
• Platform: {platform.title()}
• Sentiment: {sentiment_group}
• Target Day: {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][day_of_week]}
• Hashtags: {hashtag_count}

{ml_prediction_text}
"""

        # Return with hourly engagement data for frontend charting
        return {
            "messages": [AIMessage(content=log_msg, name="Marketing_Agent")],
            "marketing_post": promotional_post,
            "marketing_platform": platform,
            "marketing_sentiment": sentiment_group,
            "marketing_day": day_of_week,
            "hourly_engagement": hourly_engagement_data.get("hours", []),
        }

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        # Fallback if JSON parsing fails
        log_msg = f"""[Marketing_Agent] ⚠️  JSON Parsing Error

The LLM did not return valid JSON. Raw response:
{response.content}

Error: {str(e)}

Please try again or check the system prompt configuration.
"""
        return {
            "messages": [AIMessage(content=log_msg, name="Marketing_Agent")],
            "marketing_post": "",
            "marketing_platform": "twitter",
            "marketing_sentiment": "Positive/High Energy",
            "marketing_day": 0,
            "hourly_engagement": [{"hour": h, "engagement": "Unknown"} for h in range(24)],
        }


# ---------------------------------------------------------------------------
# 3. Scheduler Agent (Mastermind)
# ---------------------------------------------------------------------------

async def scheduler_agent(state: EventState) -> dict[str, Any]:
    """
    Ingest constraints, read the current master_schedule, resolve time
    clashes without double-booking, and produce a new timeline.
    """
    llm = _get_llm()

    current_schedule = json.dumps(state.get("master_schedule", {}), indent=2)

    system_prompt = f"""You are the Scheduler Agent for an event management system.

EVENT CONTEXT:
{state['event_context']}

CURRENT MASTER SCHEDULE:
{current_schedule}

Your task is to:
1. Analyze the current schedule for any conflicts or issues
2. Resolve time clashes without double-booking any venues or resources
3. Incorporate any new scheduling constraints from the user's request
4. Output a complete, updated schedule

Respond ONLY with valid JSON representing the updated master_schedule.
The JSON should have this structure:
{{
    "sessions": [
        {{
            "id": "session_1",
            "title": "Session Title",
            "start_time": "YYYY-MM-DD HH:MM",
            "end_time": "YYYY-MM-DD HH:MM",
            "venue": "Venue Name",
            "speaker": "Speaker Name",
            "notes": "Any relevant notes"
        }}
    ],
    "last_updated": "ISO timestamp",
    "conflicts_resolved": ["list of resolved conflicts if any"]
}}
"""

    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    # Prefer the dedicated schedule_prompt from a direct-route request
    constraint = (
        state.get("schedule_prompt")
        or (user_messages[-1].content if user_messages else "Review and optimize the schedule")
    )

    # Append explicit time constraints if provided via the dedicated endpoint
    time_constraints = state.get("schedule_time_constraints") or {}
    if time_constraints:
        constraint = f"{constraint}\n\nTime constraints to enforce: {json.dumps(time_constraints)}"

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Update schedule with this constraint: {constraint}"),
    ])

    # Parse the updated schedule
    try:
        new_schedule = _parse_json(response.content)
    except (json.JSONDecodeError, ValueError):
        new_schedule = {"_scheduler_note": response.content}

    log_msg = f"[Scheduler_Agent] Schedule updated. Conflicts resolved."

    return {
        "master_schedule": new_schedule,
        "schedule_changed_flag": True,
        "messages": [AIMessage(content=log_msg, name="Scheduler_Agent")],
    }



# ---------------------------------------------------------------------------
# 4. Email Agent (Communicator)
# ---------------------------------------------------------------------------

async def email_agent(state: EventState) -> dict[str, Any]:
    """
    Format and send personalized bulk emails segmented by audience type.

    Supports two modes:
      - CSV mode: When email_csv_data is populated (via /run_email), sends
        invitations to all CSV contacts.
      - Participant mode: When email_csv_data is empty (chained from
        emergency/scheduler agents), fetches joined participants from the
        DB and sends updates only to them.
    """
    llm = _get_llm()

    csv_contacts = state.get("email_csv_data") or []
    is_update = False

    # When chained from Scheduler/Emergency (no CSV provided), fetch
    # joined participants from the database so they receive the update.
    if not csv_contacts and (
        state.get("schedule_changed_flag") or state.get("emergency_handled_flag")
    ):
        is_update = True
        try:
            from app.db.session import async_session_factory
            from app.db.crud import get_participants_by_event

            async with async_session_factory() as db:
                participants = await get_participants_by_event(db, state["event_id"])
                csv_contacts = [
                    {
                        "name": p.name,
                        "email": p.email,
                        "segment": p.segment_category or "General",
                    }
                    for p in participants
                ]
        except Exception as e:
            csv_contacts = []
            # Log the error but don't crash the agent
            import logging
            logging.getLogger(__name__).warning(
                f"[Email_Agent] Could not fetch participants from DB: {e}"
            )

    # Collect the distinct segments present in the contacts
    if csv_contacts:
        segments = sorted({
            (c.get("segment") or c.get("status") or "General").title()
            for c in csv_contacts
        })
    else:
        segments = ["General"]

    # Only expose the public event name — never internal budget or rules
    event_name = (state.get("event_context") or "").split("\n")[0].strip() or "the event"

    sample_template = state.get("email_sample_template", "")
    template_section = (
        f"\n\nSAMPLE EMAIL TEMPLATE (match this style and tone):\n{sample_template}"
        if sample_template
        else ""
    )

    segments_json_keys = ", ".join(f'"{s}"' for s in segments)

    # Adjust prompt context based on whether this is an invitation or update
    email_type_context = (
        "You are sending an UPDATE/ALERT email to participants who have already joined this event."
        if is_update
        else "You are sending INVITATION emails to potential attendees."
    )

    system_prompt = f"""You are the Email Communication Agent for an event management system.

EVENT NAME: {event_name}

EMAIL TYPE: {email_type_context}
SCHEDULE CHANGED: {state.get('schedule_changed_flag', False)}
EMERGENCY FOLLOW-UP: {state.get('emergency_handled_flag', False)}
RECIPIENT SEGMENTS: {segments_json_keys}{template_section}

STRICT RULES — you MUST follow these without exception:
1. Do NOT reveal or reference any internal budget figures, cost breakdowns, or financial data.
2. Do NOT mention organizer names, backend rules, internal policies, or operational details.
3. Write directly to the participants — professional, warm, and audience-appropriate.
4. Generate a UNIQUE, tailored email for EACH segment listed above.

OUTPUT FORMAT — respond ONLY with a strictly valid JSON object:
- Keys are the exact segment names listed above (case-sensitive).
- Each value is an object with exactly two fields: "subject" (string) and "body" (string).
- Use \\n for newlines inside strings. No trailing commas. No markdown.

Example:
{{
  "Student": {{"subject": "Important Update for Student Attendees", "body": "Dear Student,\\n\\n..."}},
  "Professional": {{"subject": "Event Update for Professionals", "body": "Dear Professional,\\n\\n..."}}
}}

Output ONLY the JSON object — no preamble, no explanation, no markdown fences.
"""

    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    context = user_messages[-1].content if user_messages else "General notification"

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Draft segmented notification emails for: {context}"),
    ])

    # Safely parse the LLM's JSON output (strips ```json fences if present)
    try:
        segment_emails: dict = _parse_json(response.content)
    except (json.JSONDecodeError, ValueError):
        # Graceful fallback: treat the raw response as a single General email
        segment_emails = {
            "General": {
                "subject": "Event Update Notification",
                "body": response.content,
            }
        }

    # Dispatch one bulk send per segment and collect results
    send_log_lines: list[str] = []
    total_sent = 0
    delivery_results: list[dict[str, Any]] = []

    for segment_name, email_data in segment_emails.items():
        subject = email_data.get("subject", "Event Update Notification")
        body = email_data.get("body", "")

        # Filter contacts whose segment matches this key (case-insensitive)
        if csv_contacts:
            segment_recipients = [
                c["email"] for c in csv_contacts
                if c.get("email")
                and (c.get("segment") or c.get("status") or "General").title().lower()
                == segment_name.lower()
            ]
        else:
            segment_recipients = []

        if not segment_recipients:
            send_log_lines.append(f"  - Segment '{segment_name}': 0 recipients (skipped)")
            continue

        send_result = send_bulk_email(
            event_id=state["event_id"],
            recipients=segment_recipients,
            subject=subject,
            body=body,
            display_name=f"{event_name} Team",
            reply_to=state.get("organizer_email", ""),
        )
        delivery_results.append({
            "segment": segment_name,
            "attempted": len(segment_recipients),
            "subject": subject,
            "status": send_result.get("status", "unknown"),
            "message": send_result.get("message", ""),
            "sent": int(send_result.get("recipients_count", 0)),
        })
        total_sent += int(send_result.get("recipients_count", 0))
        send_log_lines.append(
            f"  - Segment '{segment_name}': {send_result.get('recipients_count', 0)}/{len(segment_recipients)} sent"
            f" | Status: {send_result.get('status', 'unknown')}"
            f" | Subject: \"{subject}\""
        )

    audience_label = "participant update" if is_update else "invitation"
    delivery_issue = any(
        r.get("status") in {"mock_sent", "auth_error", "connection_error", "partial"}
        for r in delivery_results
    )
    log_msg = (
        f"[Email_Agent] Segmented {audience_label} email campaign complete. "
        f"{total_sent} total recipient(s) across {len(send_log_lines)} segment(s).\n"
        + "\n".join(send_log_lines)
    )
    if delivery_issue:
        log_msg += (
            "\n[Email_Agent] Delivery warning: SMTP may be unconfigured or had errors. "
            "Check SMTP_USER/SMTP_APP_PASSWORD and App Password settings."
        )

    # Persist email runs for every invocation path (direct endpoint + supervisor chains).
    try:
        from app.db.crud import create_email_log
        from app.db.session import async_session_factory

        async with async_session_factory() as db:
            await create_email_log(
                db=db,
                event_id=state["event_id"],
                sample_email=sample_template,
                csv_contacts=csv_contacts,
                recipients_count=total_sent,
                agent_response=log_msg,
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(
            f"[Email_Agent] Failed to persist email log: {e}"
        )

    return {
        "messages": [AIMessage(content=log_msg, name="Email_Agent")],
    }


# ---------------------------------------------------------------------------
# 5. Emergency Info Agent (UI Alert Generator)
# ---------------------------------------------------------------------------

async def emergency_info_agent(state: EventState) -> dict[str, Any]:
    """
    Generate a high-visibility RED ALERT for the Organizer Dashboard.

    This agent does NOT send SMS or email — its ONLY job is to draft
    a concise UI alert string. The Supervisor routes to Email_Agent
    afterwards if mass notification is needed.
    """
    llm = _get_llm()

    system_prompt = f"""You are the Emergency UI Dispatcher for an event management dashboard.

EVENT CONTEXT:
{state['event_context']}

URGENCY SCORE: {state.get('urgency_score', 0)}/10

Your ONLY job is to draft one short, critical RED ALERT message for the
Organizer Dashboard.  Do NOT send emails, SMS, or any notifications yourself.

STRICT RULES — follow without exception:
1. Output exactly ONE plain-text line.  No JSON, no markdown, no labels.
2. The line MUST start with "🚨 CRITICAL ALERT: " (including the space after the colon).
3. The TOTAL line length MUST be under 100 characters.
4. No greetings, no filler, no conversational text.
5. Be specific about the threat and its location / nature.
"""

    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    emergency = user_messages[-1].content if user_messages else "Emergency situation"

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Create a dashboard red alert for: {emergency}"),
    ])

    alert_message = _extract_emergency_alert(response.content)
    log_msg = f"[Emergency_Info_Agent] UI alert generated: {alert_message}"

    return {
        "emergency_handled_flag": True,
        "emergency_alert_message": alert_message,
        "messages": [AIMessage(content=log_msg, name="Emergency_Info_Agent")],
    }


# ---------------------------------------------------------------------------
# 6. Budget Finance Agent (Accountant)
# ---------------------------------------------------------------------------

async def budget_finance_agent(state: EventState) -> dict[str, Any]:
    """
    Smart CFO & Financial Advisor agent.

    Reads the initial total budget from event_context and the user's requested
    expense breakdown from the latest HumanMessage. Returns a structured JSON
    report with a category breakdown (percentages sum to 100), over/under-budget
    status, a strict warning if over budget, and 2-3 actionable suggestions.
    """
    llm = _get_llm()

    # ── Extract latest user request ──────────────────────────────────────────
    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    request = user_messages[-1].content if user_messages else "Provide a budget breakdown"

    # ── Build system prompt ──────────────────────────────────────────────────
    system_prompt = f"""You are the Smart CFO & Financial Advisor for an event management system.

EVENT CONTEXT (the initial total budget is on the line labeled "Budget: $..."):
{state['event_context']}

YOUR TASK
---------
The organizer has described a set of requested expenses. You must:
1. Extract EVERY expense item and its amount from the organizer's request.
2. Sum them to compute total_requested_expense.
3. Read initial_total_budget from the event context above.
4. Build a breakdown array — one entry per category. For each entry compute:
       percentage = round((amount / total_requested_expense) * 100, 2)
   Percentages MUST sum to exactly 100.
5. Set budget_status to "Over Budget" if total_requested_expense > initial_total_budget,
   otherwise "Within Budget".
6. If "Over Budget", write a strict warning_message stating the exact overage amount
   (e.g. "You are $X,XXX over budget. Immediate cost cuts required."). Otherwise "".
7. Write 2-3 concrete, actionable smart_suggestions suited to the budget situation.

OUTPUT FORMAT
-------------
Respond ONLY with a strictly valid JSON object — no markdown fences, no extra text:
{{
    "initial_total_budget": <number>,
    "total_requested_expense": <number>,
    "budget_status": "Over Budget" | "Within Budget",
    "breakdown": [
        {{"category": "<string>", "amount": <number>, "percentage": <number>}}
    ],
    "warning_message": "<string or empty string>",
    "smart_suggestions": ["<string>", "<string>"]
}}
"""

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Analyse and report on this budget request: {request}"),
    ])

    # ── Parse LLM JSON output ────────────────────────────────────────────────
    try:
        budget_report = _parse_json(response.content)
    except (json.JSONDecodeError, ValueError):
        budget_report = {
            "initial_total_budget": 0,
            "total_requested_expense": 0,
            "budget_status": "Unknown",
            "breakdown": [],
            "warning_message": "",
            "smart_suggestions": [],
            "parse_error": "Could not parse LLM response.",
            "raw_response": response.content,
        }

    # ── Build human-readable log message ─────────────────────────────────────
    status = budget_report.get("budget_status", "Unknown")
    status_icon = "🔴" if status == "Over Budget" else "🟢"
    initial = budget_report.get("initial_total_budget", 0)
    requested = budget_report.get("total_requested_expense", 0)
    warning = budget_report.get("warning_message", "")

    log_msg = (
        f"[Budget_Finance_Agent] {status_icon} {status} | "
        f"Initial Budget: ${initial:,.2f} | "
        f"Requested: ${requested:,.2f}"
    )
    if warning:
        log_msg += f" | {warning}"

    return {
        "budget_estimate_report": budget_report,
        "messages": [AIMessage(content=log_msg, name="Budget_Finance_Agent")],
    }
