"""Workflow info API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from webgal_agent.api.models import AgentInfoResponse, WorkflowInfoResponse

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.get("", response_model=list[str])
async def list_workflows() -> list[str]:
    """List available workflow types."""
    from webgal_agent.api.app import get_task_manager

    return get_task_manager().workflow_types


@router.get("/{workflow_name}", response_model=WorkflowInfoResponse)
async def get_workflow_info(workflow_name: str) -> WorkflowInfoResponse:
    """Get detailed info about a workflow type."""
    from webgal_agent.api.app import get_task_manager

    info = get_task_manager().get_workflow_info(workflow_name)
    if info is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return WorkflowInfoResponse(
        name=info["name"],
        type=info["type"],
        description=info.get("description", ""),
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
    from webgal_agent.agents import ArtistAgent, DirectorAgent, ReviewerAgent, WriterAgent

    agents = [DirectorAgent(), WriterAgent(), ArtistAgent(), ReviewerAgent()]
    return [
        AgentInfoResponse(name=a.name, description=a.description, state=a.state.value)
        for a in agents
    ]
