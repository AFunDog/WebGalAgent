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


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(task_id: str) -> TaskResponse:
    """终止正在运行的任务。"""
    from webgal_agent.api.app import get_task_manager

    manager = get_task_manager()
    task = manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务未找到")
    if task.status not in ("running", "pending"):
        raise HTTPException(status_code=400, detail="任务已结束，无法终止")

    await manager.cancel_task(task_id)
    # 重新获取更新后的任务状态
    task = manager.get_task(task_id)
    return TaskResponse(**task.to_dict())
