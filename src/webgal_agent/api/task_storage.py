"""任务持久化与恢复。"""

from __future__ import annotations

import json
import os
from contextlib import suppress
from datetime import datetime
from pathlib import Path

from webgal_agent.api.task_state import TaskInfo
from webgal_agent.api.workflow_definition import PIPELINE_ORDER
from webgal_agent.core.message import Message, MessageType

DEFAULT_TASK_DIR = "data/tasks"


def save_task_to_disk(task: TaskInfo, task_dir: str | Path = DEFAULT_TASK_DIR) -> Path:
    """将任务数据持久化到磁盘。"""
    task_path = Path(task_dir) / task.id
    task_path.mkdir(parents=True, exist_ok=True)

    process_data = {
        "task_id": task.id,
        "status": task.status,
        "workflow": task.workflow_name,
        "user_input": task.content,
        "title": task.title,
        "current_step": task.current_step,
        "step_results": {str(k): v for k, v in task.step_results.items()},
        "created_at": task.created_at.isoformat(),
        "errors": task.errors,
        "token_usage_by_step": {str(k): v for k, v in task.token_usage_by_step.items()},
        "total_prompt_tokens": task.total_prompt_tokens,
        "total_completion_tokens": task.total_completion_tokens,
        "total_tokens": task.total_tokens,
        "steps": [
            {
                "step": i + 1,
                "agent": m.receiver if m.type == MessageType.TASK else m.sender,
                "type": m.type.value,
                "sender": m.sender,
                "receiver": m.receiver,
                "content": m.content,
                "metadata": m.metadata,
                "created_at": m.created_at.isoformat(),
            }
            for i, m in enumerate(task.messages)
        ],
    }

    (task_path / "process.json").write_text(
        json.dumps(process_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    result_file = task_path / "result.txt"
    if task.messages:
        (task_path / "result.txt").write_text(task.messages[-1].content, encoding="utf-8")
    elif result_file.exists():
        result_file.unlink()

    for old_step_file in task_path.glob("step_*_*.txt"):
        with suppress(OSError, PermissionError):
            os.chmod(old_step_file, 0o666)
            old_step_file.unlink()

    for step_index, content in sorted(task.step_results.items()):
        agent_name = PIPELINE_ORDER[step_index] if step_index < len(PIPELINE_ORDER) else str(step_index)
        (task_path / f"step_{step_index + 1}_{agent_name}.txt").write_text(content, encoding="utf-8")

    return task_path


def load_tasks_from_disk(task_dir: str | Path = DEFAULT_TASK_DIR) -> dict[str, TaskInfo]:
    """启动时从磁盘加载之前持久化的任务。"""
    tasks: dict[str, TaskInfo] = {}
    task_path = Path(task_dir)

    if not task_path.exists():
        return tasks

    for task_folder in sorted(task_path.iterdir()):
        process_file = task_folder / "process.json"
        if not process_file.exists():
            continue

        try:
            data = json.loads(process_file.read_text(encoding="utf-8"))
            task = TaskInfo(task_id=data["task_id"], content=data["user_input"])
            task.workflow_name = data.get("workflow", "pipeline")
            task.title = data.get("title", "")
            task.status = data.get("status", "unknown")
            task.current_step = data.get("current_step", 0)
            task.step_results = {int(k): v for k, v in data.get("step_results", {}).items()}
            task.errors = data.get("errors", [])
            task.created_at = datetime.fromisoformat(data["created_at"])
            task.token_usage_by_step = {
                int(k): v for k, v in data.get("token_usage_by_step", {}).items()
            }
            task.total_prompt_tokens = data.get("total_prompt_tokens", 0)
            task.total_completion_tokens = data.get("total_completion_tokens", 0)
            task.total_tokens = data.get("total_tokens", 0)

            if not task.token_usage_by_step:
                for i, step in enumerate(data.get("steps", [])):
                    token_usage = step.get("metadata", {}).get("token_usage", {})
                    if token_usage and token_usage.get("total_tokens", 0) > 0:
                        task.token_usage_by_step[i] = token_usage
                if task.token_usage_by_step:
                    task.recalc_token_totals()

            for step in data.get("steps", []):
                task.messages.append(
                    Message(
                        type=MessageType(step["type"]),
                        sender=step["sender"],
                        receiver=step["receiver"],
                        content=step["content"],
                        metadata=step.get("metadata", {}),
                    )
                )

            tasks[task.id] = task
        except (KeyError, ValueError, json.JSONDecodeError):
            continue

    return tasks
