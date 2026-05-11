"""任务执行 API 路由。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

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


@router.get("/{task_id}/results")
async def list_result_files(task_id: str) -> list[str]:
    """列出任务结果目录下的所有文件。"""
    from webgal_agent.api.app import get_task_manager

    manager = get_task_manager()
    task = manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务未找到")

    result_dir = Path(manager._task_dir) / task_id / "result"
    if not result_dir.exists():
        return []

    files: list[str] = []
    for f in sorted(result_dir.rglob("*")):
        if f.is_file():
            files.append(f.relative_to(result_dir).as_posix())
    return files


@router.get("/{task_id}/results/{file_path:path}", response_class=PlainTextResponse)
async def get_result_file(task_id: str, file_path: str) -> str:
    """获取任务结果文件内容。"""
    from webgal_agent.api.app import get_task_manager

    manager = get_task_manager()
    task = manager.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="任务未找到")

    result_dir = (Path(manager._task_dir) / task_id / "result").resolve()
    target = (result_dir / file_path).resolve()

    if not target.is_relative_to(result_dir):
        raise HTTPException(status_code=403, detail="不允许路径穿越")
    if not target.exists():
        raise HTTPException(status_code=404, detail="文件未找到")

    return target.read_text(encoding="utf-8")


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
