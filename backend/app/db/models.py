"""
SQLAlchemy ORM models for the Event Command Center.

Defines the relational schema: Events, Participants, Tickets,
UnresolvedQueries, SwarmLogs, and EventCodes — all scoped by
event_id for multi-tenant isolation.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Event(Base):
    __tablename__ = "events"

    event_id = Column(Integer, primary_key=True, autoincrement=True)
    event_name = Column(String(255), nullable=False)
    organizer_name = Column(String(255), nullable=False)
    event_rules_and_context = Column(Text, nullable=True, default="")
    total_budget_allocated = Column(Float, nullable=False, default=0.0)
    status = Column(String(50), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    master_schedule = Column(JSON, nullable=True, default=dict)
    budget_report = Column(JSON, nullable=True, default=dict)

    participants = relationship("Participant", back_populates="event", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="event", cascade="all, delete-orphan")
    unresolved_queries = relationship("UnresolvedQuery", back_populates="event", cascade="all, delete-orphan")
    swarm_logs = relationship("SwarmLog", back_populates="event", cascade="all, delete-orphan")
    event_code = relationship("EventCode", back_populates="event", uselist=False, cascade="all, delete-orphan")

    # Agent-specific log relationships
    swarm_interaction_logs = relationship("SwarmInteractionLog", back_populates="event", cascade="all, delete-orphan")
    marketing_logs = relationship("MarketingLog", back_populates="event", cascade="all, delete-orphan")
    email_logs = relationship("EmailLog", back_populates="event", cascade="all, delete-orphan")
    scheduler_logs = relationship("SchedulerLog", back_populates="event", cascade="all, delete-orphan")
    emergency_logs = relationship("EmergencyLog", back_populates="event", cascade="all, delete-orphan")
    budget_logs = relationship("BudgetLog", back_populates="event", cascade="all, delete-orphan")


class Participant(Base):
    __tablename__ = "participants"

    participant_id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.event_id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    segment_category = Column(String(100), nullable=True, default="general")

    event = relationship("Event", back_populates="participants")


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.event_id", ondelete="CASCADE"), nullable=False)
    issue_text = Column(String(1000), nullable=False)
    problem_category = Column(String(100), nullable=True, default="normal")
    urgency_score = Column(Integer, nullable=False, default=0)
    status = Column(String(50), nullable=False, default="Open")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    event = relationship("Event", back_populates="tickets")


class UnresolvedQuery(Base):
    __tablename__ = "unresolved_queries"

    query_id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.event_id", ondelete="CASCADE"), nullable=False)
    question_text = Column(String(1000), nullable=False)
    organizer_answer = Column(Text, nullable=True, default=None)
    status = Column(String(50), nullable=False, default="Pending")

    event = relationship("Event", back_populates="unresolved_queries")


class SwarmLog(Base):
    __tablename__ = "swarm_logs"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.event_id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    agent_name = Column(String(100), nullable=False)
    action_taken = Column(Text, nullable=False)

    event = relationship("Event", back_populates="swarm_logs")


class EventCode(Base):
    __tablename__ = "event_codes"

    code_id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.event_id", ondelete="CASCADE"), nullable=False, unique=True)
    code = Column(String(20), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    event = relationship("Event", back_populates="event_code")


# ---------------------------------------------------------------------------
# Agent-Specific Interaction Logs
# ---------------------------------------------------------------------------

class SwarmInteractionLog(Base):
    """Logs for the general-purpose Problem Solver (trigger_swarm)."""
    __tablename__ = "swarm_interaction_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.event_id", ondelete="CASCADE"), nullable=False)
    command = Column(Text, nullable=False)
    problem_category = Column(String(100), nullable=True, default="")
    urgency_score = Column(Integer, nullable=True, default=0)
    schedule_changed = Column(Boolean, nullable=False, default=False)
    emergency_handled = Column(Boolean, nullable=False, default=False)
    master_schedule = Column(JSON, nullable=True, default=dict)
    budget_report = Column(JSON, nullable=True, default=dict)
    agent_response = Column(Text, nullable=True, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    event = relationship("Event", back_populates="swarm_interaction_logs")


class MarketingLog(Base):
    """Logs for the Marketing Agent (run_marketing)."""
    __tablename__ = "marketing_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.event_id", ondelete="CASCADE"), nullable=False)
    prompt = Column(Text, nullable=False)
    generated_content = Column(Text, nullable=True, default="")
    marketing_post = Column(Text, nullable=True, default="")
    marketing_platform = Column(String(100), nullable=True, default="")
    marketing_sentiment = Column(String(100), nullable=True, default="")
    marketing_day = Column(Integer, nullable=True, default=0)
    hourly_engagement = Column(JSON, nullable=True, default=list)
    agent_response = Column(Text, nullable=True, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    event = relationship("Event", back_populates="marketing_logs")


class EmailLog(Base):
    """Logs for the Email Agent (run_email)."""
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.event_id", ondelete="CASCADE"), nullable=False)
    sample_email = Column(Text, nullable=False)
    csv_contacts = Column(JSON, nullable=True, default=list)
    recipients_count = Column(Integer, nullable=False, default=0)
    agent_response = Column(Text, nullable=True, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    event = relationship("Event", back_populates="email_logs")


class SchedulerLog(Base):
    """Logs for the Scheduler Agent (run_scheduler)."""
    __tablename__ = "scheduler_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.event_id", ondelete="CASCADE"), nullable=False)
    prompt = Column(Text, nullable=False)
    master_schedule = Column(JSON, nullable=True, default=dict)
    time_constraints = Column(JSON, nullable=True, default=dict)
    agent_response = Column(Text, nullable=True, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    event = relationship("Event", back_populates="scheduler_logs")


class EmergencyLog(Base):
    """Logs for the Emergency Agent (run_emergency)."""
    __tablename__ = "emergency_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.event_id", ondelete="CASCADE"), nullable=False)
    problem_description = Column(Text, nullable=False)
    emergency_handled = Column(Boolean, nullable=False, default=False)
    agent_response = Column(Text, nullable=True, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    event = relationship("Event", back_populates="emergency_logs")


class BudgetLog(Base):
    """Logs for the Budget Agent (run_budget)."""
    __tablename__ = "budget_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.event_id", ondelete="CASCADE"), nullable=False)
    request_description = Column(Text, nullable=False)
    budget_report = Column(JSON, nullable=True, default=dict)
    agent_response = Column(Text, nullable=True, default="")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    event = relationship("Event", back_populates="budget_logs")