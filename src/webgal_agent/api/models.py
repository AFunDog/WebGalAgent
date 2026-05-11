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


class AgentKnowledgeRequirementsResponse(BaseModel):
    """Per-agent knowledge requirements from prompts.yaml."""

    agent: str
    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


# ---------- Workflow ----------

class AgentInfoResponse(BaseModel):
    """Agent status information."""

    name: str
    description: str
    state: str
    provider: str = ""
    model: str = ""


class WorkflowInfoResponse(BaseModel):
    """Workflow configuration information."""

    name: str
    agents: list[AgentInfoResponse]
    type: str
    description: str = ""


# ---------- Task ----------

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
