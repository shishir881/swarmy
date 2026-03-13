"""
CRUD utility functions for the Event Command Center.

All functions accept an AsyncSession and operate within the caller's
transaction scope. Every data access is scoped by event_id to enforce
multi-tenant isolation.
"""

from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    BudgetLog,
    EmailLog,
    EmergencyLog,
    Event,
    MarketingLog,
    Participant,
    SchedulerLog,
    SwarmInteractionLog,
    SwarmLog,
    Ticket,
    UnresolvedQuery,
)


# ---------------------------------------------------------------------------
# Event CRUD
# ---------------------------------------------------------------------------

async def get_event_context(db: AsyncSession, event_id: int) -> Event | None:
    """
    Fetch a single event record by its ID.

    Returns the Event ORM instance or None if not found.
    """
    result = await db.execute(select(Event).where(Event.event_id == event_id))
    return result.scalar_one_or_none()


async def create_event(db: AsyncSession, **kwargs) -> Event:
    """Create a new event and return the persisted record."""
    event = Event(**kwargs)
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def get_all_events(
    db: AsyncSession,
    organizer_name: str | None = None,
    status: str | None = None,
) -> Sequence[Event]:
    """
    List all events, optionally filtered by organizer_name and/or status.

    Returns events ordered by created_at descending (newest first).
    """
    from sqlalchemy import desc
    stmt = select(Event).order_by(desc(Event.created_at))
    if organizer_name:
        stmt = stmt.where(Event.organizer_name == organizer_name)
    if status:
        stmt = stmt.where(Event.status == status)
    result = await db.execute(stmt)
    return result.scalars().all()


async def update_event_status(
    db: AsyncSession, event_id: int, status: str
) -> Event | None:
    """Update the status of an event (active -> completed -> archived)."""
    event = await get_event_context(db, event_id)
    if event is None:
        return None
    event.status = status
    await db.commit()
    await db.refresh(event)
    return event


async def update_event_schedule(
    db: AsyncSession, event_id: int, new_schedule: dict
) -> Event | None:
    """
    Overwrite the master_schedule JSONB for the given event.

    Returns the updated Event or None if the event doesn't exist.
    """
    event = await get_event_context(db, event_id)
    if event is None:
        return None
    event.master_schedule = new_schedule
    await db.commit()
    await db.refresh(event)
    return event


async def update_event_budget_report(
    db: AsyncSession, event_id: int, budget_report: dict
) -> Event | None:
    """
    Overwrite the budget_report JSONB for the given event.

    Returns the updated Event or None if the event doesn't exist.
    """
    event = await get_event_context(db, event_id)
    if event is None:
        return None
    event.budget_report = budget_report
    await db.commit()
    await db.refresh(event)
    return event


# ---------------------------------------------------------------------------
# Ticket CRUD (Priority Queue)
# ---------------------------------------------------------------------------

async def create_ticket(
    db: AsyncSession,
    event_id: int,
    issue_text: str,
    problem_category: str = "normal",
    urgency_score: int = 0,
    status: str = "Open",
) -> Ticket:
    """Create a new support ticket scoped to the given event."""
    ticket = Ticket(
        event_id=event_id,
        issue_text=issue_text,
        problem_category=problem_category,
        urgency_score=urgency_score,
        status=status,
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def get_priority_queue(db: AsyncSession, event_id: int) -> Sequence[Ticket]:
    """
    Fetch all **open** tickets for the event, strictly ordered by
    urgency_score DESC (highest urgency first).

    Only tickets with status='Open' are returned so resolved
    tickets don't pollute the priority queue.
    """
    result = await db.execute(
        select(Ticket)
        .where(Ticket.event_id == event_id, Ticket.status == "Open")
        .order_by(Ticket.urgency_score.desc())
    )
    return result.scalars().all()


async def update_ticket_status(
    db: AsyncSession, ticket_id: int, status: str
) -> Ticket | None:
    """Update the status of a ticket (e.g., Open -> Resolved)."""
    result = await db.execute(select(Ticket).where(Ticket.ticket_id == ticket_id))
    ticket = result.scalar_one_or_none()
    if ticket is None:
        return None
    ticket.status = status
    await db.commit()
    await db.refresh(ticket)
    return ticket


# ---------------------------------------------------------------------------
# Unresolved Query CRUD (HITL)
# ---------------------------------------------------------------------------

async def create_unresolved_query(
    db: AsyncSession, event_id: int, question_text: str
) -> UnresolvedQuery:
    """Save a question the RAG chatbot could not answer."""
    query = UnresolvedQuery(
        event_id=event_id,
        question_text=question_text,
        status="Pending",
    )
    db.add(query)
    await db.commit()
    await db.refresh(query)
    return query


async def resolve_query(
    db: AsyncSession, query_id: int, organizer_answer: str | None = None
) -> UnresolvedQuery | None:
    """Mark an unresolved query as resolved and optionally store the answer."""
    result = await db.execute(
        select(UnresolvedQuery).where(UnresolvedQuery.query_id == query_id)
    )
    query = result.scalar_one_or_none()
    if query is None:
        return None
    query.status = "Resolved"
    if organizer_answer is not None:
        query.organizer_answer = organizer_answer
    await db.commit()
    await db.refresh(query)
    return query


async def get_unresolved_queries(
    db: AsyncSession, event_id: int, status: Optional[str] = None
) -> Sequence[UnresolvedQuery]:
    """Fetch unresolved queries for an event, optionally filtered by status."""
    stmt = select(UnresolvedQuery).where(UnresolvedQuery.event_id == event_id)
    if status:
        stmt = stmt.where(UnresolvedQuery.status == status)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_resolved_queries(
    db: AsyncSession, event_id: int
) -> Sequence[UnresolvedQuery]:
    """Fetch all resolved queries for an event (for public FAQ)."""
    result = await db.execute(
        select(UnresolvedQuery).where(
            UnresolvedQuery.event_id == event_id,
            UnresolvedQuery.status == "Resolved",
            UnresolvedQuery.organizer_answer.isnot(None),
        )
    )
    return result.scalars().all()


# ---------------------------------------------------------------------------
# Swarm Log CRUD
# ---------------------------------------------------------------------------

async def create_swarm_log(
    db: AsyncSession,
    event_id: int,
    agent_name: str,
    action_taken: str,
) -> SwarmLog:
    """Record an action taken by a Swarm agent."""
    log = SwarmLog(
        event_id=event_id,
        timestamp=datetime.now(timezone.utc),
        agent_name=agent_name,
        action_taken=action_taken,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


# ---------------------------------------------------------------------------
# Participant CRUD
# ---------------------------------------------------------------------------

async def get_participants_by_event(
    db: AsyncSession, event_id: int
) -> Sequence[Participant]:
    """Fetch all participants registered under the given event."""
    result = await db.execute(
        select(Participant).where(Participant.event_id == event_id)
    )
    return result.scalars().all()


async def create_participant(
    db: AsyncSession,
    event_id: int,
    name: str,
    email: str,
    segment_category: str = "general",
) -> Participant:
    """Register a new participant under the given event."""
    participant = Participant(
        event_id=event_id,
        name=name,
        email=email,
        segment_category=segment_category,
    )
    db.add(participant)
    await db.commit()
    await db.refresh(participant)
    return participant


async def get_participant_by_email(
    db: AsyncSession, event_id: int, email: str
) -> Participant | None:
    """Check if a participant with the given email is already registered for the event."""
    result = await db.execute(
        select(Participant).where(
            Participant.event_id == event_id,
            Participant.email == email,
        )
    )
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# Agent-Specific Log CRUD
# ---------------------------------------------------------------------------

async def create_swarm_interaction_log(
    db: AsyncSession, event_id: int, command: str, problem_category: str,
    urgency_score: int, schedule_changed: bool, emergency_handled: bool,
    master_schedule: dict, budget_report: dict, agent_response: str,
) -> SwarmInteractionLog:
    log = SwarmInteractionLog(
        event_id=event_id, command=command, problem_category=problem_category,
        urgency_score=urgency_score, schedule_changed=schedule_changed,
        emergency_handled=emergency_handled, master_schedule=master_schedule,
        budget_report=budget_report, agent_response=agent_response,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_swarm_interaction_logs(
    db: AsyncSession, event_id: int,
) -> Sequence[SwarmInteractionLog]:
    from sqlalchemy import desc
    result = await db.execute(
        select(SwarmInteractionLog)
        .where(SwarmInteractionLog.event_id == event_id)
        .order_by(desc(SwarmInteractionLog.created_at))
    )
    return result.scalars().all()


async def create_marketing_log(
    db: AsyncSession, event_id: int, prompt: str, generated_content: str,
    marketing_post: str, marketing_platform: str, marketing_sentiment: str,
    marketing_day: int, hourly_engagement: list, agent_response: str,
) -> MarketingLog:
    log = MarketingLog(
        event_id=event_id, prompt=prompt, generated_content=generated_content,
        marketing_post=marketing_post, marketing_platform=marketing_platform,
        marketing_sentiment=marketing_sentiment, marketing_day=marketing_day,
        hourly_engagement=hourly_engagement, agent_response=agent_response,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_marketing_logs(
    db: AsyncSession, event_id: int,
) -> Sequence[MarketingLog]:
    from sqlalchemy import desc
    result = await db.execute(
        select(MarketingLog)
        .where(MarketingLog.event_id == event_id)
        .order_by(desc(MarketingLog.created_at))
    )
    return result.scalars().all()


async def create_email_log(
    db: AsyncSession, event_id: int, sample_email: str,
    csv_contacts: list, recipients_count: int, agent_response: str,
) -> EmailLog:
    log = EmailLog(
        event_id=event_id, sample_email=sample_email,
        csv_contacts=csv_contacts, recipients_count=recipients_count,
        agent_response=agent_response,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_email_logs(
    db: AsyncSession, event_id: int,
) -> Sequence[EmailLog]:
    from sqlalchemy import desc
    result = await db.execute(
        select(EmailLog)
        .where(EmailLog.event_id == event_id)
        .order_by(desc(EmailLog.created_at))
    )
    return result.scalars().all()


async def create_scheduler_log(
    db: AsyncSession, event_id: int, prompt: str,
    master_schedule: dict, time_constraints: dict, agent_response: str,
) -> SchedulerLog:
    log = SchedulerLog(
        event_id=event_id, prompt=prompt, master_schedule=master_schedule,
        time_constraints=time_constraints, agent_response=agent_response,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_scheduler_logs(
    db: AsyncSession, event_id: int,
) -> Sequence[SchedulerLog]:
    from sqlalchemy import desc
    result = await db.execute(
        select(SchedulerLog)
        .where(SchedulerLog.event_id == event_id)
        .order_by(desc(SchedulerLog.created_at))
    )
    return result.scalars().all()


async def create_emergency_log(
    db: AsyncSession, event_id: int, problem_description: str,
    emergency_handled: bool, agent_response: str,
) -> EmergencyLog:
    log = EmergencyLog(
        event_id=event_id, problem_description=problem_description,
        emergency_handled=emergency_handled, agent_response=agent_response,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_emergency_logs(
    db: AsyncSession, event_id: int,
) -> Sequence[EmergencyLog]:
    from sqlalchemy import desc
    result = await db.execute(
        select(EmergencyLog)
        .where(EmergencyLog.event_id == event_id)
        .order_by(desc(EmergencyLog.created_at))
    )
    return result.scalars().all()


async def create_budget_log(
    db: AsyncSession, event_id: int, request_description: str,
    budget_report: dict, agent_response: str,
) -> BudgetLog:
    log = BudgetLog(
        event_id=event_id, request_description=request_description,
        budget_report=budget_report, agent_response=agent_response,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


async def get_budget_logs(
    db: AsyncSession, event_id: int,
) -> Sequence[BudgetLog]:
    from sqlalchemy import desc
    result = await db.execute(
        select(BudgetLog)
        .where(BudgetLog.event_id == event_id)
        .order_by(desc(BudgetLog.created_at))
    )
    return result.scalars().all()
