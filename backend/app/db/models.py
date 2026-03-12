"""
SQLAlchemy ORM models for the Event Command Center.

Defines the relational schema: Events, Participants, Tickets,
UnresolvedQueries, SwarmLogs, and EventCodes — all scoped by
event_id for multi-tenant isolation.
"""

from datetime import datetime, timezone

from sqlalchemy import (
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
    master_schedule = Column(JSON, nullable=True, default=dict)
    budget_report = Column(JSON, nullable=True, default=dict)

    participants = relationship("Participant", back_populates="event", cascade="all, delete-orphan")
    tickets = relationship("Ticket", back_populates="event", cascade="all, delete-orphan")
    unresolved_queries = relationship("UnresolvedQuery", back_populates="event", cascade="all, delete-orphan")
    swarm_logs = relationship("SwarmLog", back_populates="event", cascade="all, delete-orphan")
    event_code = relationship("EventCode", back_populates="event", uselist=False, cascade="all, delete-orphan")


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
    urgency_score = Column(Integer, nullable=False, default=1)
    status = Column(String(50), nullable=False, default="Pending")

    event = relationship("Event", back_populates="tickets")


class UnresolvedQuery(Base):
    __tablename__ = "unresolved_queries"

    query_id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.event_id", ondelete="CASCADE"), nullable=False)
    question_text = Column(String(1000), nullable=False)
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