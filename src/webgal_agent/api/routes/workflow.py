"""工作流信息 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter

from webgal_agent.api.models import AgentInfoResponse, WorkflowInfoResponse

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.get("", response_model=list[str])
async def list_workflows() -> list[str]:
    """列出可用的工作流类型。"""
    return ["pipeline"]


@router.get("/pipeline", response_model=WorkflowInfoResponse)
async def get_pipeline_info() -> WorkflowInfoResponse:
    """获取流水线工作流信息。"""
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
    """获取所有智能体的当前状态。"""
    from webgal_agent.api.app import get_task_manager

    agents_info = get_task_manager().get_active_agents_info()
    return [
        AgentInfoResponse(
            name=a["name"],
            description=a["description"],
            state=a["state"],
            provider=a.get("provider", ""),
            model=a.get("model", ""),
        )
        for a in agents_info
    ]
