"""工作流执行任务管理器。"""

from __future__ import annotations

import asyncio
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
from webgal_agent.tools.base import Tool
from webgal_agent.workflows.pipeline import PipelineWorkflow

# 流水线步骤顺序：A → B → C
PIPELINE_ORDER = ["outline_writer", "script_writer", "script_converter"]

# 智能体描述
AGENT_DESCRIPTIONS: dict[str, str] = {
    "outline_writer": "接受用户输入和知识库，编写剧本大纲",
    "script_writer": "接受用户输入、剧本大纲和知识库，生成各章节剧本",
    "script_converter": "接受用户输入、剧本和知识库，转换为 WebGal 引擎脚本",
}

# 每个智能体需要的前序步骤输出（None 表示需要所有前序步骤）
AGENT_PREV_DEPS: dict[str, list[str] | None] = {
    "outline_writer": None,       # 第一步，无前序
    "script_writer": None,        # 需要大纲
    "script_converter": ["script_writer"],  # 只需要剧本，不需要大纲
}

# 持久化任务数据的输出目录
DEFAULT_TASK_DIR = "data/tasks"


def _extract_title(outline_content: str) -> str:
    """从 outline_writer 的输出中提取标题。

    期望格式：第一行为 # 标题 或 【标题】 或纯文本标题行，
    下一空行之前的内容作为标题。
    """
    for line in outline_content.strip().splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # # 标题 格式
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        # 【标题】 格式
        if stripped.startswith("【") and stripped.endswith("】"):
            return stripped[1:-1]
        # 其他：取第一个非空行作为标题（截断过长的）
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
        self.current_step: int = 0  # 下一步要执行的步骤索引 (0-based)
        self.step_results: dict[int, str] = {}  # step_index → 结果内容（可编辑）
        self.messages: list[Message] = []
        self.errors: list[str] = []
        self.created_at = datetime.utcnow()

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
        "title": task.title,
        "current_step": task.current_step,
        "step_results": {str(k): v for k, v in task.step_results.items()},
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
                "metadata": m.metadata,
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

    # --- 保存最终结果 ---
    # write_result 工具已将脚本直接写入 result/ 目录
    # 这里将最后一个智能体的文本输出保存为 result.txt 作为摘要/备份
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
            task.title = data.get("title", "")
            task.status = data.get("status", "unknown")
            task.current_step = data.get("current_step", 0)
            # 恢复 step_results（键从字符串转回整数）
            raw_results = data.get("step_results", {})
            task.step_results = {int(k): v for k, v in raw_results.items()}
            task.errors = data.get("errors", [])
            task.created_at = datetime.fromisoformat(data["created_at"])

            # 从步骤重建消息
            for step in data.get("steps", []):
                msg = Message(
                    type=MessageType(step["type"]),
                    sender=step["sender"],
                    receiver=step["receiver"],
                    content=step["content"],
                    metadata=step.get("metadata", {}),
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

        # 保存后台 asyncio.Task 引用，防止被 GC 回收
        self._background_tasks: set[asyncio.Task] = set()

        # 保存 task_id → asyncio.Task 映射，用于取消任务
        self._running_tasks: dict[str, asyncio.Task] = {}

        # 当前正在运行的智能体实例（供状态查询和取消使用）
        self._active_agents: dict[str, Agent] = {}
        # 运行中任务对应的 task_id，用于取消时定位 agent
        self._running_task_id: str | None = None

    @property
    def workflow_types(self) -> list[str]:
        return ["pipeline"]

    def _build_agents(self, task_id: str = "") -> dict[str, Agent]:
        from webgal_agent.tools.asset_query import AssetQueryTool
        from webgal_agent.tools.file_ops import ReadFileTool, WriteResultTool

        # 通用工具（只读，所有智能体都可以使用）
        common_tools: list[Tool] = [
            ReadFileTool(),
        ]

        # 素材查询工具（script_converter 专用）
        asset_tool = AssetQueryTool()

        # 结果写入工具（仅 script_converter 使用）
        write_result_tool = WriteResultTool(task_id=task_id, task_dir=self._task_dir) if task_id else None

        # 每个智能体可用的工具配置
        agent_tools: dict[str, list[Tool]] = {
            "outline_writer": [],
            "script_writer": [],
            "script_converter": [asset_tool] + ([write_result_tool] if write_result_tool else []),
        }

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
            # 合并通用工具 + 智能体专属工具
            tools = common_tools + agent_tools.get(name, [])

            if name == "outline_writer":
                agents[name] = OutlineWriterAgent(config=config, system_prompt=prompt, tools=tools)
            elif name == "script_writer":
                agents[name] = ScriptWriterAgent(config=config, system_prompt=prompt, tools=tools)
            elif name == "script_converter":
                agents[name] = ScriptConverterAgent(config=config, system_prompt=prompt, tools=tools)

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

        return "\n\n".join(parts)

    def _build_all_knowledge_contexts(self) -> dict[str, str]:
        """为流水线中的每个智能体构建知识库上下文。"""
        return {name: self._build_knowledge_context(name) for name in PIPELINE_ORDER}

    async def start_task(
        self,
        content: str,
        start_step: int = 0,
        step_inputs: dict[str, str] | None = None,
    ) -> TaskInfo:
        """创建新的流水线任务。

        Args:
            content: 用户输入/任务描述。
            start_step: 从第几步开始执行（0-based），跳过前面的步骤。
            step_inputs: 跳过步骤的预填充输出，key 为步骤索引字符串（如 "0", "1"）。
        """
        start_step = max(0, min(start_step, len(PIPELINE_ORDER) - 1))

        task_id = uuid.uuid4().hex[:12]
        task = TaskInfo(task_id=task_id, content=content)

        # 预填充跳过步骤的结果
        if step_inputs:
            for idx_str, output in step_inputs.items():
                idx = int(idx_str)
                if 0 <= idx < start_step:
                    task.step_results[idx] = output
                    # 添加对应的 RESULT 消息
                    agent_name = PIPELINE_ORDER[idx]
                    msg = Message(
                        type=MessageType.RESULT,
                        sender=agent_name,
                        receiver="pipeline",
                        content=output,
                        metadata={"skipped": True},
                    )
                    task.messages.append(msg)

        # 设置当前步骤和标题
        task.current_step = start_step
        if task.step_results.get(0):
            task.title = _extract_title(task.step_results[0])
        task.status = "pending" if start_step < len(PIPELINE_ORDER) else "completed"

        self._tasks[task_id] = task
        _save_task_to_disk(task, self._task_dir)
        return task

    async def run_step(self, task_id: str) -> TaskInfo:
        """启动任务的下一步执行（后台异步）。"""
        task = self._tasks.get(task_id)
        if task is None:
            raise ValueError(f"任务 {task_id} 不存在")
        if task.status == "running":
            raise ValueError("任务正在执行中，请等待完成")
        if task.current_step >= len(PIPELINE_ORDER):
            raise ValueError("所有步骤已执行完毕")

        task.status = "running"
        _save_task_to_disk(task, self._task_dir)

        # 后台启动执行，不阻塞当前请求
        bg_task = asyncio.create_task(self._run_step_background(task))
        self._background_tasks.add(bg_task)
        bg_task.add_done_callback(self._background_tasks.discard)
        self._running_tasks[task_id] = bg_task
        bg_task.add_done_callback(lambda _: self._running_tasks.pop(task_id, None))

        return task

    async def _run_step_background(self, task: TaskInfo) -> None:
        """在后台执行单步智能体。"""
        import logging
        logger = logging.getLogger("webgal_agent.task_manager")

        step_index = task.current_step
        agent_name = PIPELINE_ORDER[step_index]

        try:
            agents = self._build_agents(task_id=task.id)
            self._active_agents = agents
            self._running_task_id = task.id
            agent = agents[agent_name]

            # 构建累积上下文
            knowledge_contexts = self._build_all_knowledge_contexts()
            context_parts: list[str] = []

            if task.content:
                context_parts.append(f"【用户输入】\n{task.content}")

            # 知识库上下文
            agent_knowledge = knowledge_contexts.get(agent_name, "")
            if agent_knowledge:
                context_parts.append(f"【知识库】\n{agent_knowledge}")

            # 前序步骤的输出（使用可编辑的 step_results）
            prev_deps = AGENT_PREV_DEPS.get(agent_name)
            for idx in range(step_index):
                prev_name = PIPELINE_ORDER[idx]
                # 如果配置了依赖列表，只注入指定的前序步骤
                if prev_deps is not None and prev_name not in prev_deps:
                    continue
                prev_output = task.step_results.get(idx, "")
                if prev_output:
                    context_parts.append(f"【{prev_name} 的输出】\n{prev_output}")

            context_content = "\n\n".join(context_parts) if context_parts else task.content

            current_msg = Message(
                type=MessageType.TASK,
                sender="pipeline",
                receiver=agent_name,
                content=context_content,
                metadata={
                    "user_input": task.content,
                    "step": agent_name,
                },
            )

            logger.info("步骤 %s 开始执行: task_id=%s", agent_name, task.id)
            result = await agent.handle(current_msg)

            # 保存结果
            task.messages.append(result)
            task.step_results[step_index] = result.content
            task.current_step = step_index + 1

            # outline_writer 完成后提取标题
            if agent_name == "outline_writer" and not task.title:
                task.title = _extract_title(result.content)

            # 判断是否全部完成
            if task.current_step >= len(PIPELINE_ORDER):
                task.status = "completed"
            else:
                task.status = "paused"

            logger.info("步骤 %s 完成: task_id=%s, status=%s", agent_name, task.id, task.status)

        except asyncio.CancelledError:
            logger.info("步骤被取消: task_id=%s", task.id)
            task.errors.append("步骤被用户终止")
            task.status = "cancelled"
        except Exception as exc:
            logger.exception("步骤执行失败: task_id=%s", task.id)
            task.errors.append(str(exc))
            task.status = "failed"
        finally:
            self._active_agents = {}
            self._running_task_id = None
            _save_task_to_disk(task, self._task_dir)

    def update_step_result(self, task_id: str, step_index: int, content: str) -> TaskInfo:
        """更新某一步的结果内容（用于手动修改中间结果）。"""
        task = self._tasks.get(task_id)
        if task is None:
            raise ValueError(f"任务 {task_id} 不存在")
        if step_index < 0 or step_index >= task.current_step:
            raise ValueError(f"步骤索引 {step_index} 无效（已完成步骤: 0~{task.current_step - 1}）")
        if task.status == "running":
            raise ValueError("任务正在执行中，无法修改")

        task.step_results[step_index] = content

        # 同步更新 messages 中对应的 RESULT 消息
        agent_name = PIPELINE_ORDER[step_index]
        for m in task.messages:
            if m.type == MessageType.RESULT and m.sender == agent_name:
                m.content = content
                break

        _save_task_to_disk(task, self._task_dir)
        return task

    def get_task(self, task_id: str) -> TaskInfo | None:
        return self._tasks.get(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        """取消正在运行的任务。

        返回 True 表示成功取消，False 表示任务不存在或已结束。
        """
        task = self._tasks.get(task_id)
        if task is None:
            return False

        # 如果有后台任务正在执行，取消它
        bg_task = self._running_tasks.get(task_id)
        if bg_task is not None and not bg_task.done():
            # 先通知 agent 停止，以便在当前轮次快速响应
            if self._running_task_id == task_id:
                for agent in self._active_agents.values():
                    agent.cancel()
            bg_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(bg_task), timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            return True

        # 如果任务处于 pending/paused 状态，直接标记为 cancelled
        if task.status in ("pending", "paused"):
            task.status = "cancelled"
            task.errors.append("任务已被用户终止")
            _save_task_to_disk(task, self._task_dir)
            return True

        return False

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

    def get_active_agents_info(self) -> list[AgentInfoDict]:
        """返回当前正在运行的智能体信息（反映真实状态）。"""
        if self._active_agents:
            return [
                {
                    "name": a.name,
                    "description": a.description,
                    "state": a.state.value,
                    "provider": a._config.provider,
                    "model": a._config.model,
                }
                for a in self._active_agents.values()
            ]
        # 没有运行中的任务时，返回默认配置的智能体
        agents = self._build_agents()
        return [
            {
                "name": a.name,
                "description": a.description,
                "state": a.state.value,
                "provider": a._config.provider,
                "model": a._config.model,
            }
            for a in agents.values()
        ]
