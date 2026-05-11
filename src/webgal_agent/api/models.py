"""API request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ---------- Knowledge ----------

class KnowledgeResponse(BaseModel):
    """Knowledge entry returned by the API."""

    id: str
    category: str
    title: str
    tags: list[str]
    body: str
    source: str
    created_at: datetime
    updated_at: datetime


# ---------- Workflow ----------

class AgentInfoResponse(BaseModel):
    """Agent status information."""

    name: str
    description: str
    state: str


class WorkflowInfoResponse(BaseModel):
    """Workflow configuration information."""

    name: str
    agents: list[AgentInfoResponse]
    type: str


# ---------- Task ----------

class TaskCreateRequest(BaseModel):
    """Request body for creating a new task."""

    content: str
    workflow: str = "sequential"


class TaskMessageResponse(BaseModel):
    """A message within a task execution."""

    id: str
    type: str
    sender: str
    receiver: str
    content: str
    created_at: datetime


class TaskResponse(BaseModel):
    """Task execution status and results."""

    id: str
    status: str
    workflow: str
    content: str
    messages: list[TaskMessageResponse]
    errors: list[str]
    created_at: datetime
