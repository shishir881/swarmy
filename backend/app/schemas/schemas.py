"""
Pydantic V2 request/response schemas for the Event Command Center API.

These models enforce strict validation on all incoming requests and
provide clean serialization for API responses.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Event Schemas
# ---------------------------------------------------------------------------

class EventBase(BaseModel):
    """Base schema for event data."""
    event_name: str = Field(..., max_length=255, description="Name of the event")
    organizer_name: str = Field(..., max_length=255, description="Name of the organizer")
    event_rules_and_context: str = Field(default="", description="Rules and context injected into agent prompts")
    total_budget_allocated: float = Field(default=0.0, ge=0, description="Total budget for the event")
    master_schedule: dict[str, Any] = Field(default_factory=dict, description="Master schedule as JSON")
    budget_report: dict[str, Any] = Field(default_factory=dict, description="Budget report as JSON")


class EventCreate(EventBase):
    """Schema for creating a new event."""
    pass


class EventResponse(EventBase):
    """Schema for event API responses."""
    event_id: int

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Participant Schemas
# ---------------------------------------------------------------------------

class ParticipantBase(BaseModel):
    """Base schema for participant data."""
    name: str = Field(..., max_length=255)
    email: str = Field(..., max_length=255)
    segment_category: str = Field(default="general", max_length=100)


class ParticipantCreate(ParticipantBase):
    """Schema for registering a participant to an event."""
    event_id: int


class ParticipantResponse(ParticipantBase):
    """Schema for participant API responses."""
    participant_id: int
    event_id: int

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Chat / RAG Schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    """Request body for the RAG chatbot endpoint."""
    question: str = Field(..., min_length=1, max_length=1000, description="User question for the chatbot")


class ChatResponse(BaseModel):
    """Response from the RAG chatbot endpoint."""
    answer: str
    confidence: float
    source: str = Field(description="'rag' if answered from knowledge base, 'fallback' if escalated")


# ---------------------------------------------------------------------------
# Issue Report / Ticket Schemas
# ---------------------------------------------------------------------------

class IssueReportRequest(BaseModel):
    """Request body for reporting an issue (triggers Swarm)."""
    issue_text: str = Field(..., min_length=1, max_length=1000, description="Description of the issue")


class TicketResponse(BaseModel):
    """Response schema for a support ticket."""
    ticket_id: int
    event_id: int
    issue_text: str
    problem_category: str
    urgency_score: int = Field(ge=1, le=10)
    status: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Swarm Trigger Schemas
# ---------------------------------------------------------------------------

class SwarmTriggerRequest(BaseModel):
    """Request body for organizer-triggered Swarm commands."""
    command: str = Field(..., min_length=1, max_length=2000, description="Command or issue to process")


class SwarmResult(BaseModel):
    """Response from a Swarm execution."""
    event_id: int
    problem_category: str
    urgency_score: int
    schedule_changed: bool
    emergency_handled: bool
    master_schedule: dict[str, Any]
    budget_estimate_report: dict[str, Any]
    logs: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Resolve Query Schemas (HITL)
# ---------------------------------------------------------------------------

class ResolveQueryRequest(BaseModel):
    """Request body for organizer resolving an unresolved query."""
    query_id: int = Field(..., description="ID of the unresolved query to resolve")
    organizer_answer: str = Field(..., min_length=1, max_length=2000, description="Organizer-provided answer")


class ResolveQueryResponse(BaseModel):
    """Response after resolving a query."""
    query_id: int
    status: str
    message: str


# ---------------------------------------------------------------------------
# Unresolved Query Schemas
# ---------------------------------------------------------------------------

class UnresolvedQueryResponse(BaseModel):
    """Response schema for an unresolved query."""
    query_id: int
    event_id: int
    question_text: str
    status: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Timeline / Schedule Schemas
# ---------------------------------------------------------------------------

class TimelineResponse(BaseModel):
    """Response schema for the event timeline endpoint."""
    event_id: int
    event_name: str
    master_schedule: dict[str, Any]


# ---------------------------------------------------------------------------
# Swarm Log Schemas
# ---------------------------------------------------------------------------

class SwarmLogResponse(BaseModel):
    """Response schema for swarm audit logs."""
    log_id: int
    event_id: int
    timestamp: datetime
    agent_name: str
    action_taken: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Agent-Specific Request / Response Schemas
# ---------------------------------------------------------------------------

class MarketingRequest(BaseModel):
    """Request for the dedicated marketing agent endpoint."""
    prompt: str = Field(..., min_length=1, max_length=2000, description="Promotional prompt — describe the event and tone desired")


class MarketingResult(BaseModel):
    """Response from the marketing agent with hourly engagement predictions."""
    event_id: int
    generated_content: str
    hourly_engagement: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of hourly engagement predictions. Each item: {'hour': 0-23, 'engagement': 'Viral'|'High'|'Medium'|'Low'}"
    )
    logs: list[str] = Field(default_factory=list)


class ScheduleAgentRequest(BaseModel):
    """Request for the dedicated scheduling agent endpoint."""
    prompt: str = Field(..., min_length=1, max_length=2000, description="Scheduling constraint or change request")
    time_constraints: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional explicit time overrides, e.g. {'keynote': '14:00'}",
    )


class ScheduleAgentResult(BaseModel):
    """Response from the scheduling agent."""
    event_id: int
    master_schedule: dict[str, Any]
    logs: list[str] = Field(default_factory=list)


class EmailCampaignResult(BaseModel):
    """Response from the email campaign agent."""
    event_id: int
    recipients_count: int
    logs: list[str] = Field(default_factory=list)


class EmergencyAgentRequest(BaseModel):
    """Request for the dedicated emergency agent endpoint."""
    problem_description: str = Field(
        ..., min_length=1, max_length=2000,
        description="Description of the emergency or crisis situation",
    )


class EmergencyAgentResult(BaseModel):
    """Response from the emergency agent."""
    event_id: int
    emergency_handled: bool
    emergency_alert_message: str = Field(
        default="",
        description="High-visibility emergency alert text for organizer dashboard UI",
    )
    logs: list[str] = Field(default_factory=list)


class BudgetAgentRequest(BaseModel):
    """Request for the dedicated budget/finance agent endpoint."""
    request_description: str = Field(
        ..., min_length=1, max_length=2000,
        description="Budget question, cost query, or financial breakdown request",
    )


class BudgetAgentResult(BaseModel):
    """Response from the budget/finance agent."""
    event_id: int
    budget_estimate_report: dict[str, Any]
    logs: list[str] = Field(default_factory=list)

class EventCodeResponse(BaseModel):
    """
    Response schema for the participant join code.
    Returned both on event creation and via the dedicated
    GET /organizer/events/{event_id}/code endpoint.
    """
    event_id: int
    code: str = Field(description="Shareable join code, e.g. NEU-2026-7X3K")
    join_link: str = Field(description="Full frontend URL to share with participants")
    created_at: datetime
 
    model_config = {"from_attributes": True}
 
 
class JoinEventRequest(BaseModel):
    """Request body for a participant joining via code."""
    code: str = Field(..., min_length=3, max_length=20, description="Event join code shared by organizer")
    email: str = Field(..., max_length=255, description="Participant's email address")
 
 
class JoinEventResponse(BaseModel):
    """
    Response after a participant successfully joins via code.
    Contains enough context to render the participant portal.
    """
    event_id: int
    event_name: str
    organizer_name: str
    master_schedule: dict[str, Any]
    message: str


class EventInfoResponse(BaseModel):
    """Full event info returned to participants."""
    event_id: int
    event_name: str
    organizer_name: str
    event_rules_and_context: str
    total_budget_allocated: float
    master_schedule: dict[str, Any]

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Organizer Event History Schemas
# ---------------------------------------------------------------------------

class EventListItem(BaseModel):
    """Summary item for the organizer's event list / history."""
    event_id: int
    event_name: str
    organizer_name: str
    status: str
    created_at: datetime
    total_budget_allocated: float

    model_config = {"from_attributes": True}


class EventDetailResponse(BaseModel):
    """Full event detail with related data for the organizer dashboard."""
    event_id: int
    event_name: str
    organizer_name: str
    event_rules_and_context: str
    total_budget_allocated: float
    status: str
    created_at: datetime
    master_schedule: dict[str, Any]
    budget_report: dict[str, Any]
    participant_count: int
    ticket_count: int
    unresolved_query_count: int


class EventStatusUpdate(BaseModel):
    """Request body for updating event status."""
    status: str = Field(
        ..., pattern="^(active|completed|archived)$",
        description="New status: 'active', 'completed', or 'archived'"
    )


# ---------------------------------------------------------------------------
# Agent-Specific Log Response Schemas
# ---------------------------------------------------------------------------

class SwarmInteractionLogResponse(BaseModel):
    id: int
    event_id: int
    command: str
    problem_category: str
    urgency_score: int
    schedule_changed: bool
    emergency_handled: bool
    master_schedule: dict[str, Any]
    budget_report: dict[str, Any]
    agent_response: str
    created_at: datetime
    model_config = {"from_attributes": True}


class MarketingLogResponse(BaseModel):
    id: int
    event_id: int
    prompt: str
    generated_content: str
    marketing_post: str
    marketing_platform: str
    marketing_sentiment: str
    marketing_day: int
    hourly_engagement: list[Any]
    agent_response: str
    created_at: datetime
    model_config = {"from_attributes": True}


class EmailLogResponse(BaseModel):
    id: int
    event_id: int
    sample_email: str
    csv_contacts: list[Any]
    recipients_count: int
    agent_response: str
    created_at: datetime
    model_config = {"from_attributes": True}


class SchedulerLogResponse(BaseModel):
    id: int
    event_id: int
    prompt: str
    master_schedule: dict[str, Any]
    time_constraints: dict[str, Any]
    agent_response: str
    created_at: datetime
    model_config = {"from_attributes": True}


class EmergencyLogResponse(BaseModel):
    id: int
    event_id: int
    problem_description: str
    emergency_handled: bool
    agent_response: str
    created_at: datetime
    model_config = {"from_attributes": True}


class BudgetLogResponse(BaseModel):
    id: int
    event_id: int
    request_description: str
    budget_report: dict[str, Any]
    agent_response: str
    created_at: datetime
    model_config = {"from_attributes": True}