"""Workflow info API routes."""

from __future__ import annotations

from fastapi import APIRouter

from webgal_agent.api.models import AgentInfoResponse, WorkflowInfoResponse
from webgal_agent.agents import OutlineWriterAgent, ScriptConverterAgent, ScriptWriterAgent

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.get("", response_model=list[str])
async def list_workflows() -> list[str]:
    """List available workflow types."""
    return ["pipeline"]


@router.get("/pipeline", response_model=WorkflowInfoResponse)
async def get_pipeline_info() -> WorkflowInfoResponse:
    """Get pipeline workflow info."""
    from webgal_agent.api.app import get_task_manager

    info = get_task_manager().get_workflow_info()
    return WorkflowInfoResponse(
        name=info["name"],
        type=info["type"],
        description=info["description"],
        agents=[
            AgentInfoResponse(
                name=a["name"], description=a["description"], state=a["state"]
            )
            for a in info.get("agents", [])
        ],
    )


@router.get("/agents/status", response_model=list[AgentInfoResponse])
async def get_agents_status() -> list[AgentInfoResponse]:
    """Get current status of all agents."""
    agents = [OutlineWriterAgent(), ScriptWriterAgent(), ScriptConverterAgent()]
    return [
        AgentInfoResponse(name=a.name, description=a.description, state=a.state.value)
        for a in agents
    ]
