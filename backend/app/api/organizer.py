"""
Organizer-facing API endpoints.

These endpoints are used by event organizers to:
    - Create events (auto-generates participant + organizer-team join codes)
    - Join organizer teams via organizer code
    - Retrieve both join codes for an event
  - Trigger the Swarm with direct commands
  - Resolve unresolved queries (HITL active learning)
  - View the priority queue of support tickets
"""

import csv
import io
import logging
import random
import string
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from langchain_core.messages import HumanMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.rag import add_to_rag, sync_event_data_to_rag
from app.db import crud
from app.db.models import Event, EventCode, OrganizerCode
from app.schemas.schemas import (
    BudgetAgentRequest,
    BudgetAgentResult,
    BudgetLogResponse,
    EmailCampaignResult,
    EmailLogResponse,
    EmergencyAgentRequest,
    EmergencyAgentResult,
    EmergencyLogResponse,
    EventCodeResponse,
    EventCreate,
    EventDetailResponse,
    EventListItem,
    EventResponse,
    EventStatusUpdate,
    MarketingLogResponse,
    MarketingRequest,
    MarketingResult,
    OrganizerTeamJoinRequest,
    OrganizerTeamJoinResponse,
    ResolveQueryRequest,
    ResolveQueryResponse,
    ScheduleAgentRequest,
    ScheduleAgentResult,
    SchedulerLogResponse,
    SwarmInteractionLogResponse,
    SwarmResult,
    SwarmTriggerRequest,
    TicketResponse,
)
from app.swarm.graph import swarm_graph

logger = logging.getLogger(__name__)

# Router for event-scoped operations (all require event_id in path)
router = APIRouter(prefix="/organizer/events/{event_id}", tags=["Organizer"])

# Separate router for top-level event management (no event_id in path)
events_router = APIRouter(prefix="/organizer/events", tags=["Organizer"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_code(event_name: str) -> str:
    """
    Generate a short, readable join code.

    Participant format: <3-letter prefix>-<year>-<4 random chars>
    Organizer format:   <3-letter prefix>-ORG-<4 random chars>
    """
    prefix = "".join(
        c for c in event_name.upper().replace(" ", "")[:3] if c.isalpha()
    ).ljust(3, "X")  # pad with X if name is too short
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    year = datetime.now(timezone.utc).year
    return f"{prefix}-{year}-{suffix}"


def _generate_organizer_code(event_name: str) -> str:
    """Generate a readable organizer-team join code."""
    prefix = "".join(
        c for c in event_name.upper().replace(" ", "")[:3] if c.isalpha()
    ).ljust(3, "X")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{prefix}-ORG-{suffix}"


def _participant_join_link(code: str) -> str:
    """Return the frontend participant portal URL for this code."""
    return f"/join/{code}"


def _organizer_join_link(code: str) -> str:
    """Return the frontend organizer-team join URL for this code."""
    return f"/organizer/join/{code}"


async def _generate_unique_participant_code(db: AsyncSession, event_name: str) -> str:
    """Generate a participant join code that does not collide with existing rows."""
    for _ in range(10):
        code = _generate_code(event_name)
        existing = (await db.execute(select(EventCode).where(EventCode.code == code))).scalar_one_or_none()
        if existing is None:
            return code
    raise HTTPException(status_code=500, detail="Could not generate a unique participant code. Try again.")


async def _generate_unique_organizer_code(db: AsyncSession, event_name: str) -> str:
    """Generate an organizer-team join code that does not collide with existing rows."""
    for _ in range(10):
        code = _generate_organizer_code(event_name)
        existing = (await db.execute(select(OrganizerCode).where(OrganizerCode.code == code))).scalar_one_or_none()
        if existing is None:
            return code
    raise HTTPException(status_code=500, detail="Could not generate a unique organizer code. Try again.")


async def _ensure_join_codes(db: AsyncSession, event: Event) -> tuple[EventCode, OrganizerCode]:
    """Ensure both participant and organizer join codes exist for an event."""
    participant_code = (await db.execute(
        select(EventCode).where(EventCode.event_id == event.event_id)
    )).scalar_one_or_none()

    organizer_code = (await db.execute(
        select(OrganizerCode).where(OrganizerCode.event_id == event.event_id)
    )).scalar_one_or_none()

    created_any = False
    if participant_code is None:
        code = await _generate_unique_participant_code(db, event.event_name)
        participant_code = EventCode(event_id=event.event_id, code=code)
        db.add(participant_code)
        created_any = True

    if organizer_code is None:
        code = await _generate_unique_organizer_code(db, event.event_name)
        organizer_code = OrganizerCode(event_id=event.event_id, code=code)
        db.add(organizer_code)
        created_any = True

    if created_any:
        await db.commit()
        await db.refresh(participant_code)
        await db.refresh(organizer_code)

    return participant_code, organizer_code


async def _sync_event_to_rag_from_postgres(
    db: AsyncSession,
    event: Event,
    schedule_override: dict | None = None,
) -> int:
    """
    Build a richer RAG payload from current PostgreSQL state and sync to Chroma.

    This includes event metadata, operational counts, and resolved organizer FAQs.
    """
    participants = await crud.get_participants_by_event(db, event.event_id)
    open_tickets = await crud.get_priority_queue(db, event.event_id)
    pending_queries = await crud.get_unresolved_queries(db, event.event_id, status="Pending")
    resolved_queries = await crud.get_resolved_queries(db, event.event_id)

    resolved_faqs = [
        {
            "question": q.question_text,
            "answer": q.organizer_answer or "",
        }
        for q in resolved_queries
        if q.organizer_answer
    ]

    return sync_event_data_to_rag(
        event_id=event.event_id,
        event_name=event.event_name,
        event_type=event.event_type or "general",
        organizer=event.organizer_name,
        rules=event.event_rules_and_context or "",
        schedule=schedule_override if schedule_override is not None else (event.master_schedule or {}),
        status=event.status or "active",
        participant_count=len(participants),
        open_ticket_count=len(open_tickets),
        pending_query_count=len(pending_queries),
        resolved_faqs=resolved_faqs,
    )


# ---------------------------------------------------------------------------
# GET /organizer/events  — list all events (with optional filters)
# ---------------------------------------------------------------------------

@events_router.get("", response_model=list[EventListItem])
async def list_events(
    status: str | None = None,
    organizer_name: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List all events, optionally filtered by status and/or organizer_name.

    Returns a summary list ordered by created_at descending (newest first).
    Use ?status=active|completed|archived to filter.
    """
    try:
        events = await crud.get_all_events(db, organizer_name=organizer_name, status=status)
        return [
            EventListItem(
                event_id=e.event_id,
                event_name=e.event_name,
                event_type=e.event_type or "general",
                organizer_name=e.organizer_name,
                status=e.status or "active",
                created_at=e.created_at,
                total_budget_allocated=e.total_budget_allocated,
            )
            for e in events
        ]
    except Exception as e:
        logger.error(f"Error listing events: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {repr(e)}")


# ---------------------------------------------------------------------------
# POST /organizer/events  — create a new event
# ---------------------------------------------------------------------------

@events_router.post("", response_model=EventResponse, status_code=201)
async def create_event(
    request: EventCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new event (tenant).

    Automatically generates and persists both participant and organizer-team
    join codes. Participant code is shared with attendees, while organizer
    code is shared only with co-organizers.

    Returns the created event including its event_id, participant_code,
    and join_link — all required for downstream operations.
    """
    try:
        normalized_event_type = (request.event_type or "general").strip().lower()

        # Create the event record
        organizer_email = (request.organizer_email or "").strip().lower()
        event = await crud.create_event(
            db,
            event_name=request.event_name,
            event_type=normalized_event_type,
            organizer_name=request.organizer_name,
            organizer_email=organizer_email,
            event_rules_and_context=request.event_rules_and_context,
            total_budget_allocated=request.total_budget_allocated,
            master_schedule=request.master_schedule,
            budget_report=request.budget_report,
        )

        participant_code_value = await _generate_unique_participant_code(db, request.event_name)
        organizer_code_value = await _generate_unique_organizer_code(db, request.event_name)

        participant_code = EventCode(event_id=event.event_id, code=participant_code_value)
        organizer_code = OrganizerCode(event_id=event.event_id, code=organizer_code_value)
        db.add(participant_code)
        db.add(organizer_code)
        await db.commit()
        await db.refresh(participant_code)
        await db.refresh(organizer_code)

        if organizer_email:
            await crud.create_organizer_member(
                db=db,
                event_id=event.event_id,
                name=request.organizer_name,
                email=organizer_email,
                role="owner",
            )

        logger.info(
            f"Created event {event.event_id} with participant code {participant_code_value} "
            f"and organizer code {organizer_code_value}"
        )

        # Sync richer Postgres event context to ChromaDB for stronger retrieval.
        await _sync_event_to_rag_from_postgres(db, event)

        return EventResponse(
            event_id=event.event_id,
            event_name=event.event_name,
            event_type=event.event_type or "general",
            organizer_name=event.organizer_name,
            organizer_email=event.organizer_email,
            event_rules_and_context=event.event_rules_and_context or "",
            total_budget_allocated=event.total_budget_allocated,
            master_schedule=event.master_schedule or {},
            budget_report=event.budget_report or {},
            participant_code=participant_code_value,
            participant_join_link=_participant_join_link(participant_code_value),
            organizer_code=organizer_code_value,
            organizer_join_link=_organizer_join_link(organizer_code_value),
        )
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {repr(e)}")


# ---------------------------------------------------------------------------
# POST /organizer/events/join-team  — organizer team joins via organizer code
# ---------------------------------------------------------------------------

@events_router.post("/join-team", response_model=OrganizerTeamJoinResponse)
async def join_organizer_team(
    request: OrganizerTeamJoinRequest,
    db: AsyncSession = Depends(get_db),
):
    """Join an existing event as an organizer-team member using organizer code."""
    try:
        normalized_code = request.code.upper().strip()
        normalized_email = request.email.strip().lower()
        if not normalized_email:
            raise HTTPException(status_code=400, detail="Email is required.")

        code_result = await db.execute(
            select(OrganizerCode).where(OrganizerCode.code == normalized_code)
        )
        organizer_code = code_result.scalar_one_or_none()

        if organizer_code is None:
            raise HTTPException(
                status_code=404,
                detail="Invalid organizer code. Please check the code and try again.",
            )

        event = await crud.get_event_context(db, organizer_code.event_id)
        if event is None:
            raise HTTPException(status_code=404, detail="Event not found.")

        existing_member = await crud.get_organizer_member_by_email(
            db=db,
            event_id=event.event_id,
            email=normalized_email,
        )
        if existing_member is None:
            display_name = request.name or normalized_email.split("@")[0]
            await crud.create_organizer_member(
                db=db,
                event_id=event.event_id,
                name=display_name,
                email=normalized_email,
                role="member",
            )
            logger.info(
                f"Organizer team member {normalized_email} joined event {event.event_id} "
                f"via organizer code {normalized_code}"
            )
        else:
            logger.info(
                f"Existing organizer team member {normalized_email} rejoined event {event.event_id} "
                f"via organizer code {normalized_code}"
            )

        members = await crud.get_organizer_members_by_event(db, event.event_id)

        return OrganizerTeamJoinResponse(
            event_id=event.event_id,
            event_name=event.event_name,
            organizer_name=event.organizer_name,
            team_member_count=len(members),
            message=(
                f"You joined {event.event_name} as organizer team member. "
                "You now share organizer-level event context with your team."
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error joining organizer team with code {request.code}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error joining organizer team.")


# ---------------------------------------------------------------------------
# GET /organizer/events/{event_id}/detail  — full event detail with counts
# ---------------------------------------------------------------------------

@router.get("/detail", response_model=EventDetailResponse)
async def get_event_detail(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch full event details including participant, ticket,
    and unresolved query counts for the organizer dashboard.
    """
    try:
        event = await crud.get_event_context(db, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")

        from sqlalchemy import func, select as sa_select
        from app.db.models import Participant, Ticket, UnresolvedQuery

        p_count = (await db.execute(
            sa_select(func.count()).where(Participant.event_id == event_id)
        )).scalar() or 0

        t_count = (await db.execute(
            sa_select(func.count()).where(Ticket.event_id == event_id)
        )).scalar() or 0

        uq_count = (await db.execute(
            sa_select(func.count()).where(
                UnresolvedQuery.event_id == event_id,
                UnresolvedQuery.status == "Pending",
            )
        )).scalar() or 0

        return EventDetailResponse(
            event_id=event.event_id,
            event_name=event.event_name,
            event_type=event.event_type or "general",
            organizer_name=event.organizer_name,
            event_rules_and_context=event.event_rules_and_context or "",
            total_budget_allocated=event.total_budget_allocated,
            status=event.status or "active",
            created_at=event.created_at,
            master_schedule=event.master_schedule or {},
            budget_report=event.budget_report or {},
            participant_count=p_count,
            ticket_count=t_count,
            unresolved_query_count=uq_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching detail for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {repr(e)}")


# ---------------------------------------------------------------------------
# PATCH /organizer/events/{event_id}/status  — update event status
# ---------------------------------------------------------------------------

@router.patch("/status", response_model=EventListItem)
async def update_event_status(
    event_id: int,
    request: EventStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update the status of an event (active → completed → archived).

    Use this to mark an event as completed after it ends, or archive
    old events. Archived events are still accessible in the history.
    """
    try:
        event = await crud.update_event_status(db, event_id, request.status)
        if event is None:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")

        return EventListItem(
            event_id=event.event_id,
            event_name=event.event_name,
            event_type=event.event_type or "general",
            organizer_name=event.organizer_name,
            status=event.status,
            created_at=event.created_at,
            total_budget_allocated=event.total_budget_allocated,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating status for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {repr(e)}")


# ---------------------------------------------------------------------------
# GET /organizer/events/{event_id}/code  — retrieve participant + organizer codes
# ---------------------------------------------------------------------------

@router.get("/code", response_model=EventCodeResponse)
async def get_event_code(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve participant and organizer-team join codes for an event.

    Use this if the organizer needs to look up or re-share the code
    after the event was created. The code and join link are displayed
    prominently on the organizer dashboard.
    """
    try:
        event = await crud.get_event_context(db, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")

        participant_code, organizer_code = await _ensure_join_codes(db, event)

        return EventCodeResponse(
            event_id=event_id,
            code=participant_code.code,
            join_link=_participant_join_link(participant_code.code),
            created_at=participant_code.created_at,
            organizer_code=organizer_code.code,
            organizer_join_link=_organizer_join_link(organizer_code.code),
            organizer_created_at=organizer_code.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching code for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {repr(e)}")


# ---------------------------------------------------------------------------
# POST /organizer/events/{event_id}/trigger_swarm
# ---------------------------------------------------------------------------

@router.post("/trigger_swarm", response_model=SwarmResult)
async def trigger_swarm(
    event_id: int,
    request: SwarmTriggerRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger the LangGraph Swarm for direct organizer commands.

    Accepts a command string, fetches the event context, initializes
    the Swarm state, invokes the graph, and persists all results.
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
            "messages": [HumanMessage(content=request.command)],
            "next_agent": "",
            "problem_category": "",
            "urgency_score": 0,
            "schedule_changed_flag": False,
            "emergency_handled_flag": False,
            "emergency_alert_message": "",
            "master_schedule": event.master_schedule or {},
            "budget_estimate_report": event.budget_report or {},
            "direct_route": "",
            "organizer_email": event.organizer_email or "",
            "marketing_prompt": "",
            "email_csv_data": [],
            "email_sample_template": "",
            "schedule_prompt": "",
            "schedule_time_constraints": {},
        }

        result = await swarm_graph.ainvoke(initial_state)

        if result.get("schedule_changed_flag"):
            new_schedule = result.get("master_schedule", {})
            await crud.update_event_schedule(db, event_id, new_schedule)
            # Re-sync updated schedule + latest Postgres context to ChromaDB.
            await _sync_event_to_rag_from_postgres(db, event, schedule_override=new_schedule)

        if result.get("budget_estimate_report"):
            await crud.update_event_budget_report(db, event_id, result.get("budget_estimate_report", {}))

        log_messages = [
            m.content for m in result.get("messages", [])
            if getattr(m, "name", None) is not None
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

        # Persist a Ticket with the LLM-generated classification
        await crud.create_ticket(
            db=db,
            event_id=event_id,
            issue_text=request.command,
            problem_category=result.get("problem_category", "normal"),
            urgency_score=result.get("urgency_score", 0),
            status="Open",
        )

        # Persist to agent-specific table
        await crud.create_swarm_interaction_log(
            db=db, event_id=event_id, command=request.command,
            problem_category=result.get("problem_category", ""),
            urgency_score=result.get("urgency_score", 0),
            schedule_changed=result.get("schedule_changed_flag", False),
            emergency_handled=result.get("emergency_handled_flag", False),
            master_schedule=result.get("master_schedule", {}),
            budget_report=result.get("budget_estimate_report", {}),
            agent_response="\n".join(log_messages),
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
        logger.error(f"Error triggering swarm for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error triggering swarm: {str(e)}")


# ---------------------------------------------------------------------------
# POST /organizer/events/{event_id}/resolve_query
# ---------------------------------------------------------------------------

@router.post("/resolve_query", response_model=ResolveQueryResponse)
async def resolve_unresolved_query(
    event_id: int,
    request: ResolveQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Resolve an unresolved query with an organizer-provided answer.

    Steps:
      1. Fetch the unresolved query record.
      2. Concatenate Q&A into a document.
      3. Embed and save to ChromaDB with event_id metadata.
      4. Update the DB record status to 'Resolved'.
    """
    try:
        event = await crud.get_event_context(db, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")

        from sqlalchemy import select
        from app.db.models import UnresolvedQuery

        result = await db.execute(
            select(UnresolvedQuery).where(
                UnresolvedQuery.query_id == request.query_id,
                UnresolvedQuery.event_id == event_id,
            )
        )
        query_record = result.scalar_one_or_none()

        if query_record is None:
            raise HTTPException(
                status_code=404,
                detail=f"Unresolved query {request.query_id} not found for event {event_id}.",
            )

        if query_record.status == "Resolved":
            raise HTTPException(
                status_code=400,
                detail=f"Query {request.query_id} is already resolved.",
            )

        doc_id = add_to_rag(
            event_id=event_id,
            question=query_record.question_text,
            answer=request.organizer_answer,
        )

        await crud.resolve_query(db, request.query_id, organizer_answer=request.organizer_answer)

        await crud.create_swarm_log(
            db=db,
            event_id=event_id,
            agent_name="Organizer_HITL",
            action_taken=(
                f"Resolved query #{request.query_id}. "
                f"Q: {query_record.question_text} | A: {request.organizer_answer}. "
                f"Added to RAG as doc: {doc_id}"
            ),
        )

        return ResolveQueryResponse(
            query_id=request.query_id,
            status="Resolved",
            message=(
                f"Query resolved successfully. The Q&A has been added to the "
                f"knowledge base (doc: {doc_id}) and will be available for "
                f"future chatbot queries."
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving query for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error resolving query: {str(e)}")


# ---------------------------------------------------------------------------
# POST /organizer/events/{event_id}/sync_rag
# ---------------------------------------------------------------------------

@router.post("/sync_rag")
async def sync_event_to_rag(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Backfill an existing event's rules and master schedule into ChromaDB.

    This is idempotent — safe to call multiple times. Call this once for
    any event that was created before the RAG sync feature was added, or
    any time you want to force a fresh re-sync.

    Returns the number of chunks written to ChromaDB.
    """
    try:
        event = await crud.get_event_context(db, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")

        chunks = await _sync_event_to_rag_from_postgres(db, event)

        logger.info(f"Synced event {event_id} to RAG: {chunks} chunks written.")
        return {"event_id": event_id, "chunks_written": chunks, "status": "synced"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing event {event_id} to RAG: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {repr(e)}")


# ---------------------------------------------------------------------------
# GET /organizer/events/{event_id}/priority_queue
# ---------------------------------------------------------------------------

@router.get("/priority_queue", response_model=list[TicketResponse])
async def get_priority_queue(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch all support tickets for the event, strictly ordered by
    urgency_score DESC (highest urgency first).
    """
    try:
        event = await crud.get_event_context(db, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")

        tickets = await crud.get_priority_queue(db, event_id)

        return [
            TicketResponse(
                ticket_id=t.ticket_id,
                event_id=t.event_id,
                issue_text=t.issue_text,
                problem_category=t.problem_category or "normal",
                urgency_score=t.urgency_score,
                status=t.status,
            )
            for t in tickets
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching priority queue for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error fetching priority queue.")


# ---------------------------------------------------------------------------
# POST /organizer/events/{event_id}/run_marketing
# ---------------------------------------------------------------------------

@router.post("/run_marketing", response_model=MarketingResult)
async def run_marketing_agent(
    event_id: int,
    request: MarketingRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Invoke the Marketing & Social Media agent directly.

    Accepts a raw promotional prompt and returns AI-generated
    social media / promotional content with optimal posting schedules.
    """
    try:
        event = await crud.get_event_context(db, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")

        event_context = (
            f"{event.event_name}\n"
            f"Organizer: {event.organizer_name}\n"
            f"Rules & Context: {event.event_rules_and_context}\n"
            f"Budget: ${event.total_budget_allocated:,.2f}"
        )

        initial_state = {
            "event_id": event_id,
            "event_context": event_context,
            "messages": [HumanMessage(content=request.prompt)],
            "next_agent": "",
            "problem_category": "",
            "urgency_score": 0,
            "schedule_changed_flag": False,
            "emergency_handled_flag": False,
            "emergency_alert_message": "",
            "master_schedule": event.master_schedule or {},
            "budget_estimate_report": event.budget_report or {},
            "direct_route": "marketing",
            "organizer_email": event.organizer_email or "",
            "marketing_prompt": request.prompt,
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

        log_messages = [
            m.content for m in result.get("messages", [])
            if getattr(m, "name", None) is not None
        ]

        generated = next(
            (m for m in log_messages if m.startswith("[Marketing_Agent]")),
            "",
        ).replace("[Marketing_Agent] Promotional Content Created", "", 1).strip()

        # Extract hourly engagement data from the result state
        hourly_engagement = result.get("hourly_engagement", [])

        for log_msg in log_messages:
            agent_name = log_msg.split("]")[0].strip("[") if log_msg.startswith("[") else "Swarm"
            await crud.create_swarm_log(db=db, event_id=event_id, agent_name=agent_name, action_taken=log_msg)

        # Persist to agent-specific table
        await crud.create_marketing_log(
            db=db, event_id=event_id, prompt=request.prompt,
            generated_content=generated,
            marketing_post=result.get("marketing_post", ""),
            marketing_platform=result.get("marketing_platform", ""),
            marketing_sentiment=result.get("marketing_sentiment", ""),
            marketing_day=result.get("marketing_day", 0),
            hourly_engagement=hourly_engagement,
            agent_response="\n".join(log_messages),
        )

        return MarketingResult(
            event_id=event_id,
            generated_content=generated,
            hourly_engagement=hourly_engagement,
            logs=log_messages
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running marketing agent for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {repr(e)}")


# ---------------------------------------------------------------------------
# POST /organizer/events/{event_id}/run_email
# ---------------------------------------------------------------------------

@router.post("/run_email", response_model=EmailCampaignResult)
async def run_email_agent(
    event_id: int,
    csv_file: UploadFile = File(..., description="CSV file with columns: name, email, segment (segment is optional)"),
    sample_email: str = Form(..., description="Sample email body to use as style/tone reference"),
    db: AsyncSession = Depends(get_db),
):
    """
    Invoke the Email agent directly with a recipient CSV and a sample email.

    The CSV must have at minimum an 'email' column.
    Optional columns: 'name', 'segment'.
    The agent uses the sample email as a style/tone reference when drafting.
    """
    try:
        event = await crud.get_event_context(db, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")

        if csv_file.content_type not in ("text/csv", "application/csv", "application/octet-stream", "text/plain"):
            raise HTTPException(status_code=400, detail="Uploaded file must be a CSV.")

        raw_bytes = await csv_file.read()
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = raw_bytes.decode("latin-1")

        reader = csv.DictReader(io.StringIO(text))
        csv_contacts = [{k.strip().lower(): v.strip() for k, v in row.items()} for row in reader]

        if not csv_contacts:
            raise HTTPException(status_code=400, detail="CSV file is empty or has no valid rows.")
        if not csv_contacts[0].get("email"):
            raise HTTPException(status_code=400, detail="CSV must contain an 'email' column.")

        event_context = (
            f"{event.event_name}\n"
            f"Organizer: {event.organizer_name}\n"
            f"Rules & Context: {event.event_rules_and_context}\n"
            f"Budget: ${event.total_budget_allocated:,.2f}"
        )

        initial_state = {
            "event_id": event_id,
            "event_context": event_context,
            "messages": [HumanMessage(content=f"Send email campaign to {len(csv_contacts)} recipient(s).")],
            "next_agent": "",
            "problem_category": "",
            "urgency_score": 0,
            "schedule_changed_flag": False,
            "emergency_handled_flag": False,
            "emergency_alert_message": "",
            "master_schedule": event.master_schedule or {},
            "budget_estimate_report": event.budget_report or {},
            "direct_route": "email",
            "organizer_email": event.organizer_email or "",
            "marketing_prompt": "",
            "email_csv_data": csv_contacts,
            "email_sample_template": sample_email,
            "schedule_prompt": "",
            "schedule_time_constraints": {},
        }

        result = await swarm_graph.ainvoke(initial_state)

        log_messages = [
            m.content for m in result.get("messages", [])
            if getattr(m, "name", None) is not None
        ]

        for log_msg in log_messages:
            agent_name = log_msg.split("]")[0].strip("[") if log_msg.startswith("[") else "Swarm"
            await crud.create_swarm_log(db=db, event_id=event_id, agent_name=agent_name, action_taken=log_msg)

        return EmailCampaignResult(
            event_id=event_id,
            recipients_count=len(csv_contacts),
            logs=log_messages,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running email agent for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {repr(e)}")


# ---------------------------------------------------------------------------
# POST /organizer/events/{event_id}/run_scheduler
# ---------------------------------------------------------------------------

@router.post("/run_scheduler", response_model=ScheduleAgentResult)
async def run_scheduler_agent(
    event_id: int,
    request: ScheduleAgentRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Invoke the Scheduler agent directly.

    Accepts a scheduling constraint text and optional time overrides.
    Returns the updated master schedule.
    """
    try:
        event = await crud.get_event_context(db, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")

        event_context = (
            f"{event.event_name}\n"
            f"Organizer: {event.organizer_name}\n"
            f"Rules & Context: {event.event_rules_and_context}\n"
            f"Budget: ${event.total_budget_allocated:,.2f}"
        )

        initial_state = {
            "event_id": event_id,
            "event_context": event_context,
            "messages": [HumanMessage(content=request.prompt)],
            "next_agent": "",
            "problem_category": "",
            "urgency_score": 0,
            "schedule_changed_flag": False,
            "emergency_handled_flag": False,
            "emergency_alert_message": "",
            "master_schedule": event.master_schedule or {},
            "budget_estimate_report": event.budget_report or {},
            "direct_route": "scheduler",
            "organizer_email": event.organizer_email or "",
            "marketing_prompt": "",
            "email_csv_data": [],
            "email_sample_template": "",
            "schedule_prompt": request.prompt,
            "schedule_time_constraints": request.time_constraints,
        }

        result = await swarm_graph.ainvoke(initial_state)

        if result.get("schedule_changed_flag"):
            new_schedule = result.get("master_schedule", {})
            await crud.update_event_schedule(db, event_id, new_schedule)
            # Re-sync updated schedule + latest Postgres context to ChromaDB.
            await _sync_event_to_rag_from_postgres(db, event, schedule_override=new_schedule)

        log_messages = [
            m.content for m in result.get("messages", [])
            if getattr(m, "name", None) is not None
        ]

        for log_msg in log_messages:
            agent_name = log_msg.split("]")[0].strip("[") if log_msg.startswith("[") else "Swarm"
            await crud.create_swarm_log(db=db, event_id=event_id, agent_name=agent_name, action_taken=log_msg)

        # Persist to agent-specific table
        await crud.create_scheduler_log(
            db=db, event_id=event_id, prompt=request.prompt,
            master_schedule=result.get("master_schedule", {}),
            time_constraints=request.time_constraints or {},
            agent_response="\n".join(log_messages),
        )

        return ScheduleAgentResult(
            event_id=event_id,
            master_schedule=result.get("master_schedule", {}),
            logs=log_messages,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running scheduler agent for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {repr(e)}")


# ---------------------------------------------------------------------------
# POST /organizer/events/{event_id}/run_emergency
# ---------------------------------------------------------------------------

@router.post("/run_emergency", response_model=EmergencyAgentResult)
async def run_emergency_agent(
    event_id: int,
    request: EmergencyAgentRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Invoke the Emergency Info agent directly.

    Generates a high-visibility dashboard alert for organizers.
    """
    try:
        event = await crud.get_event_context(db, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")

        event_context = (
            f"{event.event_name}\n"
            f"Organizer: {event.organizer_name}\n"
            f"Rules & Context: {event.event_rules_and_context}\n"
            f"Budget: ${event.total_budget_allocated:,.2f}"
        )

        initial_state = {
            "event_id": event_id,
            "event_context": event_context,
            "messages": [HumanMessage(content=request.problem_description)],
            "next_agent": "",
            "problem_category": "urgent",
            "urgency_score": 10,
            "schedule_changed_flag": False,
            "emergency_handled_flag": False,
            "emergency_alert_message": "",
            "master_schedule": event.master_schedule or {},
            "budget_estimate_report": event.budget_report or {},
            "direct_route": "",
            "organizer_email": event.organizer_email or "",
            "marketing_prompt": "",
            "email_csv_data": [],
            "email_sample_template": "",
            "schedule_prompt": "",
            "schedule_time_constraints": {},
        }

        result = await swarm_graph.ainvoke(initial_state)

        log_messages = [
            m.content for m in result.get("messages", [])
            if getattr(m, "name", None) is not None
        ]

        for log_msg in log_messages:
            agent_name = log_msg.split("]")[0].strip("[") if log_msg.startswith("[") else "Swarm"
            await crud.create_swarm_log(db=db, event_id=event_id, agent_name=agent_name, action_taken=log_msg)

        # Persist an urgent Ticket for the priority queue
        await crud.create_ticket(
            db=db,
            event_id=event_id,
            issue_text=request.problem_description,
            problem_category="urgent",
            urgency_score=10,
            status="Open",
        )

        # Persist to agent-specific table
        await crud.create_emergency_log(
            db=db, event_id=event_id,
            problem_description=request.problem_description,
            emergency_handled=result.get("emergency_handled_flag", False),
            agent_response="\n".join(log_messages),
        )

        return EmergencyAgentResult(
            event_id=event_id,
            emergency_handled=result.get("emergency_handled_flag", False),
            emergency_alert_message=result.get("emergency_alert_message", ""),
            logs=log_messages,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running emergency agent for event {event_id}: {repr(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {repr(e)}")


# ---------------------------------------------------------------------------
# POST /organizer/events/{event_id}/run_budget
# ---------------------------------------------------------------------------

@router.post("/run_budget", response_model=BudgetAgentResult)
async def run_budget_agent(
    event_id: int,
    request: BudgetAgentRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Invoke the Budget & Finance agent directly.

    Accepts a budget question or cost breakdown request and returns
    a percentage-based financial analysis report.
    """
    try:
        event = await crud.get_event_context(db, event_id)
        if event is None:
            raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")

        event_context = (
            f"{event.event_name}\n"
            f"Organizer: {event.organizer_name}\n"
            f"Rules & Context: {event.event_rules_and_context}\n"
            f"Budget: ${event.total_budget_allocated:,.2f}"
        )

        initial_state = {
            "event_id": event_id,
            "event_context": event_context,
            "messages": [HumanMessage(content=request.request_description)],
            "next_agent": "",
            "problem_category": "finance",
            "urgency_score": 0,
            "schedule_changed_flag": False,
            "emergency_handled_flag": False,
            "emergency_alert_message": "",
            "master_schedule": event.master_schedule or {},
            "budget_estimate_report": {},
            "direct_route": "budget_finance",
            "organizer_email": event.organizer_email or "",
            "marketing_prompt": "",
            "email_csv_data": [],
            "email_sample_template": "",
            "schedule_prompt": "",
            "schedule_time_constraints": {},
        }

        result = await swarm_graph.ainvoke(initial_state)

        if result.get("budget_estimate_report"):
            await crud.update_event_budget_report(db, event_id, result.get("budget_estimate_report", {}))

        log_messages = [
            m.content for m in result.get("messages", [])
            if getattr(m, "name", None) is not None
        ]

        for log_msg in log_messages:
            agent_name = log_msg.split("]")[0].strip("[") if log_msg.startswith("[") else "Swarm"
            await crud.create_swarm_log(db=db, event_id=event_id, agent_name=agent_name, action_taken=log_msg)

        # Persist to agent-specific table
        await crud.create_budget_log(
            db=db, event_id=event_id,
            request_description=request.request_description,
            budget_report=result.get("budget_estimate_report", {}),
            agent_response="\n".join(log_messages),
        )

        return BudgetAgentResult(
            event_id=event_id,
            budget_estimate_report=result.get("budget_estimate_report", {}),
            logs=log_messages,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running budget agent for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {repr(e)}")


# ---------------------------------------------------------------------------
# Agent-Specific GET Log Endpoints
# ---------------------------------------------------------------------------

@router.get("/logs/swarm", response_model=list[SwarmInteractionLogResponse])
async def get_swarm_logs(event_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve all Problem Solver (swarm) interaction logs for an event."""
    logs = await crud.get_swarm_interaction_logs(db, event_id)
    return logs


@router.get("/logs/marketing", response_model=list[MarketingLogResponse])
async def get_marketing_logs(event_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve all Marketing Agent logs for an event."""
    logs = await crud.get_marketing_logs(db, event_id)
    return logs


@router.get("/logs/email", response_model=list[EmailLogResponse])
async def get_email_logs(event_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve all Email Agent logs for an event."""
    logs = await crud.get_email_logs(db, event_id)
    return logs


@router.get("/logs/scheduler", response_model=list[SchedulerLogResponse])
async def get_scheduler_logs(event_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve all Scheduler Agent logs for an event."""
    logs = await crud.get_scheduler_logs(db, event_id)
    return logs


@router.get("/logs/emergency", response_model=list[EmergencyLogResponse])
async def get_emergency_logs(event_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve all Emergency Agent logs for an event."""
    logs = await crud.get_emergency_logs(db, event_id)
    return logs


@router.get("/logs/budget", response_model=list[BudgetLogResponse])
async def get_budget_logs(event_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieve all Budget Agent logs for an event."""
    logs = await crud.get_budget_logs(db, event_id)
    return logs