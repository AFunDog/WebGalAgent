"""任务状态模型与工作流响应类型。"""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from webgal_agent.core.message import Message


def extract_title(outline_content: str) -> str:
    """从 outline_writer 的输出中提取标题。"""
    for line in outline_content.strip().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        if stripped.startswith("【") and stripped.endswith("】"):
            return stripped[1:-1]
        if len(stripped) > 50:
            return stripped[:50] + "…"
        return stripped
    return ""


class AgentInfoDict(TypedDict):
    """工作流 API 响应中的智能体信息。"""

    name: str
    description: str
    state: str
    provider: str
    model: str
    tools: list[dict[str, str]]


class WorkflowInfoDict(TypedDict):
    """API 响应中的工作流信息。"""

    name: str
    type: str
    description: str
    agents: list[AgentInfoDict]
    order: list[str]


class TaskInfo:
    """跟踪单个工作流执行。"""

    def __init__(self, task_id: str, content: str) -> None:
        self.id = task_id
        self.workflow_name = "pipeline"
        self.content = content
        self.title: str = ""
        self.status: str = "pending"
        self.current_step: int = 0
        self.step_results: dict[int, str] = {}
        self.messages: list[Message] = []
        self.errors: list[str] = []
        self.created_at = datetime.utcnow()
        self.token_usage_by_step: dict[int, dict[str, int]] = {}
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_tokens: int = 0

    def recalc_token_totals(self) -> None:
        """从 token_usage_by_step 重新计算汇总值。"""
        self.total_prompt_tokens = sum(
            usage.get("prompt_tokens", 0) for usage in self.token_usage_by_step.values()
        )
        self.total_completion_tokens = sum(
            usage.get("completion_tokens", 0) for usage in self.token_usage_by_step.values()
        )
        self.total_tokens = sum(
            usage.get("total_tokens", 0) for usage in self.token_usage_by_step.values()
        )

    def discard_from_step(self, step_index: int, pipeline_order: list[str]) -> None:
        """清理某一步及其之后的结果、消息和 token 统计。"""
        if step_index < 0:
            return

        self.step_results = {
            idx: value for idx, value in self.step_results.items() if idx < step_index
        }
        self.token_usage_by_step = {
            idx: value for idx, value in self.token_usage_by_step.items() if idx < step_index
        }

        affected_agents = set(pipeline_order[step_index:])
        self.messages = [
            msg for msg in self.messages
            if msg.sender not in affected_agents and msg.receiver not in affected_agents
        ]

        self.current_step = step_index
        self.recalc_token_totals()

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "status": self.status,
            "workflow": self.workflow_name,
            "content": self.content,
            "title": self.title,
            "current_step": self.current_step,
            "step_results": {str(k): v for k, v in self.step_results.items()},
            "messages": [
                {
                    "id": m.id,
                    "type": m.type.value,
                    "sender": m.sender,
                    "receiver": m.receiver,
                    "content": m.content,
                    "metadata": m.metadata,
                    "created_at": m.created_at.isoformat(),
                }
                for m in self.messages
            ],
            "errors": self.errors,
            "created_at": self.created_at.isoformat(),
            "token_usage_by_step": {str(k): v for k, v in self.token_usage_by_step.items()},
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
        }
