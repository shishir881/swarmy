"""
Participant-facing API endpoints.

These endpoints are used by event attendees to:
  - Join an event via organizer-shared code
  - View event timelines
  - Ask questions via the RAG chatbot
  - Report issues (triggering the LangGraph Swarm)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import HumanMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.rag import query_rag
from app.db import crud
from app.db.models import EventCode
from app.schemas.schemas import (
    ChatRequest,
    ChatResponse,
    EventInfoResponse,
    IssueReportRequest,
    JoinEventRequest,
    JoinEventResponse,
    SwarmResult,
    TimelineResponse,
)
from app.swarm.graph import swarm_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events/{event_id}", tags=["Participant"])

# Separate router for routes that don't require event_id (e.g. join via code)
join_router = APIRouter(prefix="/events", tags=["Participant"])

# RAG confidence threshold
RAG_CONFIDENCE_THRESHOLD = 0.75


# ---------------------------------------------------------------------------
# POST /events/join  — participant joins via organizer-shared code
# ---------------------------------------------------------------------------

@join_router.post("/join", response_model=JoinEventResponse)
async def join_event(
    request: JoinEventRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Participant joins an event using the code shared by the organizer.

    Looks up the event code, validates it, persists the participant
    (idempotent — skips if the email is already registered), and returns
    enough event context to render the participant portal.
    """
    try:
        # Look up the code
        result = await db.execute(
            select(EventCode).where(EventCode.code == request.code.upper().strip())
        )
        event_code = result.scalar_one_or_none()

        if event_code is None:
            raise HTTPException(
                status_code=404,
                detail="Invalid event code. Please check the code shared by your organizer."
            )

        # Fetch the associated event
        event = await crud.get_event_context(db, event_code.event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Event not found.")

        # Persist participant if they don't already exist for this event
        existing_participant = await crud.get_participant_by_email(
            db, event_id=event.event_id, email=request.email
        )
        if not existing_participant:
            # Derive name from email if not provided
            name = request.name or request.email.split("@")[0]
            await crud.create_participant(
                db,
                event_id=event.event_id,
                name=name,
                email=request.email,
                segment_category="general",
            )
            logger.info(f"New participant {request.email} joined event {event.event_id} via code {request.code}")
        else:
            logger.info(f"Existing participant {request.email} rejoined event {event.event_id} via code {request.code}")

        return JoinEventResponse(
            event_id=event.event_id,
            event_name=event.event_name,
            event_type=event.event_type or "general",
            organizer_name=event.organizer_name,
            master_schedule=event.master_schedule or {},
            message=f"Welcome to {event.event_name}! You can view the schedule and ask questions below.",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error joining event with code {request.code}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error joining event.")


# ---------------------------------------------------------------------------
# GET /events/{event_id}/timeline
# ---------------------------------------------------------------------------

@router.get("/timeline", response_model=TimelineResponse)
async def get_event_timeline(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch the latest master_schedule JSON from the database.

    Returns the event name and its current master schedule.
    """
    try:
        event = await crud.get_event_context(db, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")

        return TimelineResponse(
            event_id=event.event_id,
            event_name=event.event_name,
            event_type=event.event_type or "general",
            master_schedule=event.master_schedule or {},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching timeline for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error fetching timeline.")



# POST /events/{event_id}/chat

@router.post("/chat", response_model=ChatResponse)
async def chat_with_rag(
    event_id: int,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Context-aware RAG Chatbot endpoint for Participants.

    Queries ChromaDB (which now contains synced schedule + rules chunks)
    for the best matching answer, then asks the LLM to form a clean
    natural-language response.

    SECURE: Budget data and internal financial info are never exposed.
    """
    try:
        event = await crud.get_event_context(db, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")

        # ── 1. Query ChromaDB for any matching data (rules, schedule, QA) ──
        # Since we sync Postgres data to Chroma on create/update, it will
        # find the exact session or rule without needing raw JSON in the prompt.
        rag_answer, rag_confidence = query_rag(event_id=event_id, question=request.question)

        participants = await crud.get_participants_by_event(db, event_id)
        open_tickets = await crud.get_priority_queue(db, event_id)
        pending_queries = await crud.get_unresolved_queries(db, event_id, status="Pending")

        # ── 2. Build safe Postgres context (budget NEVER included) ───────────
        pg_context = f"""EVENT NAME: {event.event_name}
EVENT TYPE: {event.event_type or 'general'}
EVENT STATUS: {event.status or 'active'}
ORGANIZER: {event.organizer_name}
REGISTERED PARTICIPANTS: {len(participants)}
OPEN SUPPORT TICKETS: {len(open_tickets)}
PENDING UNRESOLVED QUERIES: {len(pending_queries)}"""

        rag_section = ""
        if rag_answer and rag_confidence >= 0.5:
            rag_section = f"\n\nRETRIEVED KNOWLEDGE BASE RESULTS:\n{rag_answer}"

        # ── 3. Ask LLM to answer using safe context ─────────────────────────
        from langchain_groq import ChatGroq
        from langchain_core.messages import SystemMessage as _Sys, HumanMessage as _Hum
        from app.config import settings

        llm = ChatGroq(
            model=settings.LLM_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=0.3,
        )

        system_prompt = f"""You are a helpful and polite Q&A assistant for participants of '{event.event_name}'.
Answer the participant's question using ONLY the provided knowledge base context below.
If the context does not contain the answer, say so honestly. Do NOT make up schedules, rules, or locations.

{pg_context}{rag_section}"""

        response = await llm.ainvoke([
            _Sys(content=system_prompt),
            _Hum(content=request.question),
        ])

        answer_text = response.content.strip()

        # ── 4. Determine confidence & escalation ─────────────────────────────
        no_answer_phrases = [
            "not available", "don't have", "no information",
            "cannot find", "not provided", "not mentioned",
            "i'm not sure", "i don't know", "does not contain",
        ]
        is_uncertain = any(phrase in answer_text.lower() for phrase in no_answer_phrases)

        if is_uncertain or rag_confidence < 0.4:
            await crud.create_unresolved_query(
                db=db,
                event_id=event_id,
                question_text=request.question,
            )
            return ChatResponse(
                answer=(
                    "I don't have that info right now — your question has been forwarded to the organizers!"
                ),
                confidence=0.3,
                source="fallback",
            )

        return ChatResponse(
            answer=answer_text,
            confidence=max(rag_confidence, 0.85),
            source="rag" if rag_confidence >= 0.5 else "llm_context",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error processing chat.")



# POST /events/{event_id}/report

@router.post("/report", response_model=SwarmResult)
async def report_issue(
    event_id: int,
    request: IssueReportRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Accept a user issue and trigger the LangGraph Swarm.

    The Swarm classifies the issue, routes it through the appropriate
    agent pipeline, and returns the results.
    """
    try:
        event = await crud.get_event_context(db, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")

        event_context = (
            f"{event.event_name}\n"
            f"Event Type: {event.event_type or 'general'}\n"
            f"Organizer: {event.organizer_name}\n"
            f"Rules & Context: {event.event_rules_and_context}\n"
            f"Budget: ${event.total_budget_allocated:,.2f}"
        )

        initial_state = {
            "event_id": event_id,
            "event_context": event_context,
            "messages": [HumanMessage(content=request.issue_text)],
            "next_agent": "",
            "problem_category": "",
            "urgency_score": 0,
            "schedule_changed_flag": False,
            "emergency_handled_flag": False,
            "emergency_alert_message": "",
            "master_schedule": event.master_schedule or {},
            "budget_estimate_report": event.budget_report or {},
            # Required EventState fields — zero-value defaults for participant reports
            "direct_route": "",
            "marketing_prompt": "",
            "marketing_post": "",
            "marketing_platform": "twitter",
            "marketing_sentiment": "Positive/High Energy",
            "marketing_day": 0,
            "hourly_engagement": [],
            "email_csv_data": [],
            "email_sample_template": "",
            "schedule_prompt": "",
            "schedule_time_constraints": {},
        }

        result = await swarm_graph.ainvoke(initial_state)

        await crud.create_ticket(
            db=db,
            event_id=event_id,
            issue_text=request.issue_text,
            problem_category=result.get("problem_category", "normal"),
            urgency_score=result.get("urgency_score", 1),
            status="Resolved" if result.get("next_agent") == "end" else "Open",
        )

        if result.get("schedule_changed_flag"):
            await crud.update_event_schedule(db, event_id, result.get("master_schedule", {}))

        if result.get("budget_estimate_report"):
            await crud.update_event_budget_report(db, event_id, result.get("budget_estimate_report", {}))

        log_messages = [
            m.content for m in result.get("messages", [])
            if hasattr(m, "content") and hasattr(m, "name")
        ]
        for log_msg in log_messages:
            agent_name = "Swarm"
            if log_msg.startswith("["):
                agent_name = log_msg.split("]")[0].strip("[")
            await crud.create_swarm_log(
                db=db,
                event_id=event_id,
                agent_name=agent_name,
                action_taken=log_msg,
            )

        return SwarmResult(
            event_id=event_id,
            problem_category=result.get("problem_category", ""),
            urgency_score=result.get("urgency_score", 0),
            schedule_changed=result.get("schedule_changed_flag", False),
            emergency_handled=result.get("emergency_handled_flag", False),
            master_schedule=result.get("master_schedule", {}),
            budget_estimate_report=result.get("budget_estimate_report", {}),
            logs=log_messages,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reporting issue for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error processing issue report: {str(e)}")



# GET /events/{event_id}/info  — full event info for participant portal

@router.get("/info", response_model=EventInfoResponse)
async def get_event_info(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Return full event details for the participant portal.

    Includes event name, organizer, rules/context, budget, and schedule.
    """
    try:
        event = await crud.get_event_context(db, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")

        return EventInfoResponse(
            event_id=event.event_id,
            event_name=event.event_name,
            event_type=event.event_type or "general",
            organizer_name=event.organizer_name,
            event_rules_and_context=event.event_rules_and_context or "",
            total_budget_allocated=event.total_budget_allocated,
            master_schedule=event.master_schedule or {},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching info for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error fetching event info.")