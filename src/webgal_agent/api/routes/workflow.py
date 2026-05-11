"""Workflow info API routes."""

from __future__ import annotations

from fastapi import APIRouter

from webgal_agent.api.models import AgentInfoResponse, WorkflowInfoResponse

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
    agents_info = info["agents"]
    return WorkflowInfoResponse(
        name=info["name"],
        type=info["type"],
        description=info["description"],
        agents=[
            AgentInfoResponse(
                name=a["name"],
                description=a["description"],
                state=a["state"],
                provider=a.get("provider", ""),
                model=a.get("model", ""),
            )
            for a in agents_info
        ],
    )


@router.get("/agents/status", response_model=list[AgentInfoResponse])
async def get_agents_status() -> list[AgentInfoResponse]:
    """Get current status of all agents."""
    from webgal_agent.api.app import get_task_manager

    agents = get_task_manager()._build_agents()
    return [
        AgentInfoResponse(
            name=a.name,
            description=a.description,
            state=a.state.value,
            provider=a._config.provider,
            model=a._config.model,
        )
        for a in agents.values()
    ]
