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


def _extract_emergency_alert(text: str) -> str:
    """
    Normalize LLM output into a single dashboard alert line.

    Rules enforced:
    - Must begin with the red alert emoji.
    - Must be <= 100 characters.
    - Must be single-line, no markdown wrappers.
    """
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:text)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())

    first_line = ""
    for line in cleaned.splitlines():
        candidate = line.strip()
        if candidate:
            first_line = candidate
            break

    if not first_line:
        first_line = "Emergency reported. Organizer action required."

    first_line = re.sub(r"^(?:ALERT\s*MESSAGE|ALERT)\s*:\s*", "", first_line, flags=re.IGNORECASE)
    first_line = first_line.strip().strip('"').strip("'")

    if first_line.startswith("🚨"):
        alert = first_line
    else:
        alert = f"🚨 {first_line}"

    if len(alert) > 100:
        alert = alert[:100].rstrip()

    return alert


# ---------------------------------------------------------------------------
# 1. Problem Solver Agent (Classifier & Triage)
# ---------------------------------------------------------------------------

async def problem_solver_agent(state: EventState) -> dict[str, Any]:
    """
    Classify the input issue into a problem_category and assign an
    urgency_score (1-10) based on severity.

    Categories: finance, reschedule, urgent, normal, human_escalation
    """
    llm = _get_llm()

    system_prompt = f"""You are the Problem Solver Agent for an event management system.

EVENT CONTEXT:
{state['event_context']}

Your task is to analyze the user's issue and:
1. Classify it into exactly ONE category: finance, reschedule, urgent, normal, or human_escalation
2. Assign an urgency_score from 1 (lowest) to 10 (highest)

Respond ONLY with valid JSON in this exact format:
{{"problem_category": "<category>", "urgency_score": <1-10>, "reasoning": "<brief explanation>"}}

Classification guidelines:
- "finance": Budget concerns, payment issues, cost overruns, sponsorship queries
- "reschedule": Time changes, venue conflicts, schedule clashes, timeline adjustments
- "urgent": Safety hazards, medical emergencies, security threats, critical infrastructure failure
- "normal": General inquiries, feedback, minor logistical issues
- "human_escalation": Complex issues requiring human judgment, policy decisions, VIP complaints
"""

    # Get the latest user message (the issue being reported)
    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    issue_text = user_messages[-1].content if user_messages else "No issue provided"

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Classify this issue: {issue_text}"),
    ])

    # Parse the LLM response
    try:
        parsed = _parse_json(response.content)
        category = parsed.get("problem_category", "normal")
        score = int(parsed.get("urgency_score", 5))
        reasoning = parsed.get("reasoning", "")
    except (json.JSONDecodeError, ValueError):
        category = "normal"
        score = 5
        reasoning = "Could not parse LLM response; defaulting to normal category."

    # Clamp urgency score
    score = max(1, min(10, score))

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

    The LLM generates a unique subject + body for each segment found in
    the CSV. Recipients are filtered per segment before dispatch, so no
    participant receives a generic "one-size-fits-all" message.

    When invoked via the dedicated /run_email endpoint:
      - email_csv_data supplies the recipient list parsed from CSV
      - email_sample_template provides a style/tone reference
    """
    llm = _get_llm()

    csv_contacts = state.get("email_csv_data") or []

    # Collect the distinct segments present in the CSV
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

    system_prompt = f"""You are the Email Communication Agent for an event management system.

EVENT NAME: {event_name}

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

    for segment_name, email_data in segment_emails.items():
        subject = email_data.get("subject", "Event Update Notification")
        body = email_data.get("body", "")

        # Filter CSV contacts whose segment matches this key (case-insensitive)
        if csv_contacts:
            segment_recipients = [
                c["email"] for c in csv_contacts
                if c.get("email")
                and (c.get("segment") or c.get("status") or "General").title().lower()
                == segment_name.lower()
            ]
        else:
            segment_recipients = ["participant@example.com"]

        if not segment_recipients:
            send_log_lines.append(f"  - Segment '{segment_name}': 0 recipients (skipped)")
            continue

        send_bulk_email(
            event_id=state["event_id"],
            recipients=segment_recipients,
            subject=subject,
            body=body,
        )
        total_sent += len(segment_recipients)
        send_log_lines.append(
            f"  - Segment '{segment_name}': {len(segment_recipients)} recipient(s)"
            f" | Subject: \"{subject}\""
        )

    log_msg = (
        f"[Email_Agent] Segmented email campaign complete. "
        f"{total_sent} total recipient(s) across {len(send_log_lines)} segment(s).\n"
        + "\n".join(send_log_lines)
    )

    return {
        "messages": [AIMessage(content=log_msg, name="Email_Agent")],
    }


# ---------------------------------------------------------------------------
# 5. Emergency Info Agent (Crisis Manager)
# ---------------------------------------------------------------------------

async def emergency_info_agent(state: EventState) -> dict[str, Any]:
    """
    Handle urgent/crisis situations by generating a high-visibility
    dashboard alert for organizers.
    """
    llm = _get_llm()

    system_prompt = f"""You are the Emergency UI Dispatcher for an event management dashboard.

EVENT CONTEXT:
{state['event_context']}

URGENCY SCORE: {state.get('urgency_score', 0)}/10

Your ONLY job is to draft one short RED ALERT message for the Organizer Dashboard.

STRICT RULES:
- Output exactly one plain-text line (no JSON, no markdown, no labels).
- The line MUST start with "🚨".
- The line MUST be under 100 characters.
- No greetings, no filler, no conversational text.
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
    Read the total_budget_allocated and produce a logical percentage-based
    financial breakdown using LLM reasoning.
    """
    llm = _get_llm()

    system_prompt = f"""You are the Budget & Finance Agent for an event management system.

EVENT CONTEXT:
{state['event_context']}

CURRENT BUDGET REPORT: {json.dumps(state.get('budget_estimate_report', {}), indent=2)}

Your task is to:
1. Analyze the event context to understand budget requirements
2. Produce a logical percentage-based financial breakdown
3. Ensure all percentages sum to 100%

Respond ONLY with valid JSON in this format:
{{
    "total_budget": <amount>,
    "currency": "USD",
    "breakdown": [
        {{"category": "Venue & Infrastructure", "percentage": 30, "amount": <calculated>}},
        {{"category": "Catering", "percentage": 20, "amount": <calculated>}},
        {{"category": "Marketing & Promotion", "percentage": 15, "amount": <calculated>}},
        {{"category": "Speaker Fees & Travel", "percentage": 15, "amount": <calculated>}},
        {{"category": "Technology & AV", "percentage": 10, "amount": <calculated>}},
        {{"category": "Contingency", "percentage": 10, "amount": <calculated>}}
    ],
    "recommendations": ["list of budget optimization suggestions"]
}}

Adjust categories and percentages based on the specific event type and context.
"""

    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    request = user_messages[-1].content if user_messages else "Provide a budget breakdown"

    response = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Create budget analysis for: {request}"),
    ])

    # Parse the budget report
    try:
        budget_report = _parse_json(response.content)
    except (json.JSONDecodeError, ValueError):
        budget_report = {
            "error": "Could not parse LLM budget response",
            "raw_response": response.content,
        }

    log_msg = f"[Budget_Finance_Agent] Budget breakdown generated: {json.dumps(budget_report, indent=2)}"

    return {
        "budget_estimate_report": budget_report,
        "messages": [AIMessage(content=log_msg, name="Budget_Finance_Agent")],
    }
