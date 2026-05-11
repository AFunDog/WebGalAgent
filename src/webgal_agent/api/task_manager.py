"""工作流执行任务管理器。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import TypedDict

import yaml

from webgal_agent.agents import OutlineWriterAgent, ScriptConverterAgent, ScriptWriterAgent
from webgal_agent.config.provider_manager import ProviderConfigManager
from webgal_agent.core.agent import Agent
from webgal_agent.core.message import Message, MessageType
from webgal_agent.core.workflow import WorkflowResult
from webgal_agent.knowledge import KnowledgeStore
from webgal_agent.knowledge.models import KnowledgeEntry
from webgal_agent.workflows.pipeline import PipelineWorkflow

# 流水线步骤顺序：A → B → C
PIPELINE_ORDER = ["outline_writer", "script_writer", "script_converter"]

# 智能体描述
AGENT_DESCRIPTIONS: dict[str, str] = {
    "outline_writer": "接受用户输入和知识库，编写剧本大纲",
    "script_writer": "接受用户输入、剧本大纲和知识库，生成各章节剧本",
    "script_converter": "接受用户输入、剧本和知识库，转换为 WebGal 引擎脚本",
}

# 持久化任务数据的输出目录
DEFAULT_TASK_DIR = "data/tasks"


class AgentInfoDict(TypedDict):
    """工作流 API 响应中的智能体信息。"""

    name: str
    description: str
    state: str
    provider: str
    model: str


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
        self.status: str = "pending"
        self.messages: list[Message] = []
        self.errors: list[str] = []
        self.created_at = datetime.utcnow()

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "status": self.status,
            "workflow": self.workflow_name,
            "content": self.content,
            "messages": [
                {
                    "id": m.id,
                    "type": m.type.value,
                    "sender": m.sender,
                    "receiver": m.receiver,
                    "content": m.content,
                    "created_at": m.created_at.isoformat(),
                }
                for m in self.messages
            ],
            "errors": self.errors,
            "created_at": self.created_at.isoformat(),
        }


def _load_prompts() -> dict[str, str]:
    """从 configs/prompts.yaml 加载智能体提示词。"""
    prompts_path = Path("configs/prompts.yaml")
    if not prompts_path.exists():
        return {}

    data = yaml.safe_load(prompts_path.read_text(encoding="utf-8"))
    if not data or not isinstance(data, dict):
        return {}

    result: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(value, dict) and "system_prompt" in value:
            result[key] = value["system_prompt"].strip()
    return result


def _load_knowledge_requirements() -> dict[str, dict[str, list[str]]]:
    """从 configs/prompts.yaml 加载各智能体的知识库需求配置。

    返回智能体名称到知识筛选配置的映射::

        {
            "outline_writer": {"categories": ["character", "setting"], "tags": []},
            "script_converter": {"categories": ["reference"], "tags": ["webgal"]},
        }
    """
    prompts_path = Path("configs/prompts.yaml")
    if not prompts_path.exists():
        return {}

    data = yaml.safe_load(prompts_path.read_text(encoding="utf-8"))
    if not data or not isinstance(data, dict):
        return {}

    result: dict[str, dict[str, list[str]]] = {}
    for key, value in data.items():
        if isinstance(value, dict) and "knowledge" in value:
            knowledge_cfg = value["knowledge"]
            result[key] = {
                "categories": knowledge_cfg.get("categories", []),
                "tags": knowledge_cfg.get("tags", []),
            }
    return result


def _save_task_to_disk(task: TaskInfo, task_dir: str | Path = DEFAULT_TASK_DIR) -> Path:
    """将任务数据持久化到磁盘。

    保存内容：
      - ``{task_id}/process.json`` — 完整的中间过程（所有消息）
      - ``{task_id}/result.txt``   — 最后一个智能体的输出（WebGal 脚本）

    返回任务目录路径。
    """
    task_path = Path(task_dir) / task.id
    task_path.mkdir(parents=True, exist_ok=True)

    # --- 保存中间过程为 JSON ---
    process_data = {
        "task_id": task.id,
        "status": task.status,
        "workflow": task.workflow_name,
        "user_input": task.content,
        "created_at": task.created_at.isoformat(),
        "errors": task.errors,
        "steps": [
            {
                "step": i + 1,
                "agent": m.receiver if m.type == MessageType.TASK else m.sender,
                "type": m.type.value,
                "sender": m.sender,
                "receiver": m.receiver,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for i, m in enumerate(task.messages)
        ],
    }

    process_file = task_path / "process.json"
    process_file.write_text(
        json.dumps(process_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # --- 保存最终结果为 .txt（WebGal 脚本）---
    if task.messages:
        last_msg = task.messages[-1]
        result_file = task_path / "result.txt"
        result_file.write_text(last_msg.content, encoding="utf-8")

    # --- 同时保存每个步骤的独立输出 ---
    for i, msg in enumerate(task.messages):
        if msg.type == MessageType.RESULT:
            step_name = msg.sender
            step_file = task_path / f"step_{i + 1}_{step_name}.txt"
            step_file.write_text(msg.content, encoding="utf-8")

    return task_path


def _load_tasks_from_disk(task_dir: str | Path = DEFAULT_TASK_DIR) -> dict[str, TaskInfo]:
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
            task.status = data.get("status", "unknown")
            task.errors = data.get("errors", [])
            task.created_at = datetime.fromisoformat(data["created_at"])

            # 从步骤重建消息
            for step in data.get("steps", []):
                msg = Message(
                    type=MessageType(step["type"]),
                    sender=step["sender"],
                    receiver=step["receiver"],
                    content=step["content"],
                )
                task.messages.append(msg)

            tasks[task.id] = task
        except (KeyError, ValueError, json.JSONDecodeError):
            continue

    return tasks


class TaskManager:
    """管理流水线工作流执行。"""

    def __init__(
        self,
        knowledge_store: KnowledgeStore | None = None,
        provider_manager: ProviderConfigManager | None = None,
        task_dir: str | Path = DEFAULT_TASK_DIR,
    ) -> None:
        self._task_dir = Path(task_dir)
        self._knowledge_store = knowledge_store
        self._provider_manager = provider_manager
        self._prompts = _load_prompts()
        self._knowledge_requirements = _load_knowledge_requirements()

        # 加载之前持久化的任务
        self._tasks: dict[str, TaskInfo] = _load_tasks_from_disk(self._task_dir)

    @property
    def workflow_types(self) -> list[str]:
        return ["pipeline"]

    def _build_agents(self) -> dict[str, Agent]:
        agents: dict[str, Agent] = {}
        for name in PIPELINE_ORDER:
            # 从供应商管理器构建 AgentConfig（如果可用）
            if self._provider_manager:
                config = self._provider_manager.to_agent_config(
                    name, AGENT_DESCRIPTIONS.get(name, "")
                )
            else:
                from webgal_agent.core.agent import AgentConfig
                config = AgentConfig(
                    name=name,
                    description=AGENT_DESCRIPTIONS.get(name, ""),
                )

            prompt = self._prompts.get(name, "")

            if name == "outline_writer":
                agents[name] = OutlineWriterAgent(config=config, system_prompt=prompt)
            elif name == "script_writer":
                agents[name] = ScriptWriterAgent(config=config, system_prompt=prompt)
            elif name == "script_converter":
                agents[name] = ScriptConverterAgent(config=config, system_prompt=prompt)

        return agents

    def _build_knowledge_context(self, agent_name: str = "") -> str:
        """将知识库条目格式化为指定智能体的上下文文本。

        如果该智能体在 prompts.yaml 中配置了知识需求，
        则仅包含匹配的条目；否则返回全部条目。

        对于 script_converter，还会追加可用素材上下文。
        """
        if self._knowledge_store is None:
            return ""

        # 确定该智能体的筛选条件
        requirements = self._knowledge_requirements.get(agent_name, {}) if agent_name else {}
        categories = requirements.get("categories", [])
        tags = requirements.get("tags", [])

        if categories or tags:
            # 按类别和标签筛选（并集：匹配任一类别或任一标签）
            entries_by_category: list[KnowledgeEntry] = []
            entries_by_tags: list[KnowledgeEntry] = []
            if categories:
                for cat in categories:
                    entries_by_category.extend(self._knowledge_store.query(category=cat))
            if tags:
                entries_by_tags = self._knowledge_store.query(tags=tags)

            # 合并并去重
            seen_ids: set[str] = set()
            entries: list[KnowledgeEntry] = []
            for entry in entries_by_category + entries_by_tags:
                if entry.id not in seen_ids:
                    seen_ids.add(entry.id)
                    entries.append(entry)
        else:
            # 未配置需求 — 返回全部条目
            entries = self._knowledge_store.list_all()

        if not entries:
            return ""

        parts: list[str] = []
        for entry in entries:
            header = f"### {entry.title}"
            if entry.category:
                header += f" [{entry.category}]"
            parts.append(f"{header}\n{entry.body}")

        # 对于 script_converter，追加可用素材上下文
        if agent_name == "script_converter":
            from webgal_agent.api.routes.assets import build_assets_context
            assets_context = build_assets_context()
            if assets_context:
                parts.append(assets_context)

        return "\n\n".join(parts)

    def _build_all_knowledge_contexts(self) -> dict[str, str]:
        """为流水线中的每个智能体构建知识库上下文。"""
        return {name: self._build_knowledge_context(name) for name in PIPELINE_ORDER}

    async def start_task(self, content: str) -> TaskInfo:
        """创建并启动新的流水线任务。"""
        task_id = uuid.uuid4().hex[:12]
        task = TaskInfo(task_id=task_id, content=content)
        self._tasks[task_id] = task

        agents = self._build_agents()
        knowledge_contexts = self._build_all_knowledge_contexts()

        workflow = PipelineWorkflow(
            agents=agents,
            order=PIPELINE_ORDER,
            user_input=content,
            knowledge_contexts=knowledge_contexts,
        )

        initial = Message(
            type=MessageType.TASK,
            sender="user",
            receiver="outline_writer",
            content=content,
        )

        task.status = "running"

        try:
            result: WorkflowResult = await workflow.execute(initial)
            task.messages = result.messages
            task.errors = result.errors
            task.status = "completed" if result.success else "failed"
        except Exception as exc:
            task.errors.append(str(exc))
            task.status = "failed"

        # 持久化到磁盘
        _save_task_to_disk(task, self._task_dir)

        return task

    def get_task(self, task_id: str) -> TaskInfo | None:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[TaskInfo]:
        return list(self._tasks.values())

    def get_workflow_info(self) -> WorkflowInfoDict:
        """返回流水线工作流信息。"""
        agents = self._build_agents()
        agent_list: list[AgentInfoDict] = [
            {
                "name": a.name,
                "description": a.description,
                "state": a.state.value,
                "provider": a._config.provider,
                "model": a._config.model,
            }
            for a in agents.values()
        ]
        return {
            "name": "pipeline",
            "type": "PipelineWorkflow",
            "description": "三阶段流水线：A(大纲) → B(剧本) → C(WebGal脚本)",
            "agents": agent_list,
            "order": PIPELINE_ORDER,
        }
