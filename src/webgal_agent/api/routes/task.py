"""Task execution API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from webgal_agent.api.models import TaskResponse

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(content: str) -> TaskResponse:
    """Start a new pipeline task."""
    from webgal_agent.api.app import get_task_manager

    manager = get_task_manager()
    task = await manager.start_task(content=content)
    return TaskResponse(**task.to_dict())


@router.get("", response_model=list[TaskResponse])
async def list_tasks() -> list[TaskResponse]:
    """List all tasks."""
    from webgal_agent.api.app import get_task_manager

    manager = get_task_manager()
    return [TaskResponse(**t.to_dict()) for t in manager.list_tasks()]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str) -> TaskResponse:
    """Get a task's execution details."""
    from webgal_agent.api.app import get_task_manager

    manager = get_task_manager()
    task = manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskResponse(**task.to_dict())
