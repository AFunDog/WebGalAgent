"""任务执行 API 路由。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from webgal_agent.api.models import CreateTaskRequest, ReviseStepRequest, TaskResponse, UpdateStepRequest
from webgal_agent.api.workflow_definition import PIPELINE_ORDER

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TokenSummaryResponse(BaseModel):
    """全局 Token 消耗汇总。"""

    total_tasks: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    by_step: dict[str, dict[str, int]] = Field(default_factory=dict)


@router.get("/token-summary", response_model=TokenSummaryResponse)
async def get_token_summary() -> TokenSummaryResponse:
    """获取全局 Token 消耗汇总。"""
    from webgal_agent.api.app import get_task_manager

    manager = get_task_manager()
    tasks = manager.list_tasks()

    summary = TokenSummaryResponse(total_tasks=len(tasks))
    by_step: dict[str, dict[str, int]] = {}

    for task in tasks:
        summary.total_prompt_tokens += task.total_prompt_tokens
        summary.total_completion_tokens += task.total_completion_tokens
        summary.total_tokens += task.total_tokens

        for step_idx, usage in task.token_usage_by_step.items():
            step_name = PIPELINE_ORDER[step_idx] if step_idx < len(PIPELINE_ORDER) else str(step_idx)
            if step_name not in by_step:
                by_step[step_name] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            by_step[step_name]["prompt_tokens"] += usage.get("prompt_tokens", 0)
            by_step[step_name]["completion_tokens"] += usage.get("completion_tokens", 0)
            by_step[step_name]["total_tokens"] += usage.get("total_tokens", 0)

    summary.by_step = by_step
    return summary


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(req: CreateTaskRequest) -> TaskResponse:
    """创建新的流水线任务（不自动执行）。"""
    from webgal_agent.api.app import get_task_manager

    manager = get_task_manager()
    task = await manager.start_task(
        content=req.content,
        start_step=req.start_step,
        step_inputs=req.step_inputs,
    )
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


@router.post("/{task_id}/run-step", response_model=TaskResponse)
async def run_step(task_id: str) -> TaskResponse:
    """执行任务的下一步智能体。"""
    from webgal_agent.api.app import get_task_manager

    manager = get_task_manager()
    try:
        task = await manager.run_step(task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return TaskResponse(**task.to_dict())


@router.put("/{task_id}/steps/{step_index}", response_model=TaskResponse)
async def update_step_result(task_id: str, step_index: int, req: UpdateStepRequest) -> TaskResponse:
    """更新某一步的结果内容。"""
    from webgal_agent.api.app import get_task_manager

    manager = get_task_manager()
    try:
        task = manager.update_step_result(task_id, step_index, req.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return TaskResponse(**task.to_dict())


@router.post("/{task_id}/steps/{step_index}/revise", response_model=TaskResponse)
async def revise_step(task_id: str, step_index: int, req: ReviseStepRequest) -> TaskResponse:
    """按额外引导提示重生成某一步。"""
    from webgal_agent.api.app import get_task_manager

    manager = get_task_manager()
    try:
        task = await manager.revise_step(task_id, step_index, req.instruction)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
    if task.status not in ("running", "pending", "paused"):
        raise HTTPException(status_code=400, detail="任务已结束，无法终止")

    await manager.cancel_task(task_id)
    # 重新获取更新后的任务状态
    task = manager.get_task(task_id)
    return TaskResponse(**task.to_dict())
