"""任务执行 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from webgal_agent.api.models import CreateTaskRequest, TaskResponse

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(req: CreateTaskRequest) -> TaskResponse:
    """启动新的流水线任务。"""
    from webgal_agent.api.app import get_task_manager

    manager = get_task_manager()
    task = await manager.start_task(content=req.content)
    return TaskResponse(**task.to_dict())


@router.get("", response_model=list[TaskResponse])
async def list_tasks() -> list[TaskResponse]:
    """列出所有任务。"""
    from webgal_agent.api.app import get_task_manager

    manager = get_task_manager()
    return [TaskResponse(**t.to_dict()) for t in manager.list_tasks()]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str) -> TaskResponse:
    """获取任务执行详情。"""
    from webgal_agent.api.app import get_task_manager

    manager = get_task_manager()
    task = manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务未找到")
    return TaskResponse(**task.to_dict())
