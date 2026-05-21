"""工作流执行任务管理器。

TaskManager 现在只保留编排职责，状态模型、落盘恢复、知识上下文构建和
agent 工厂已拆到独立模块中，对外接口保持不变。
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from webgal_agent.api.task_agents import build_agent_info, build_agents
from webgal_agent.api.task_context import build_all_knowledge_contexts, build_step_input
from webgal_agent.api.task_state import TaskInfo, WorkflowInfoDict, extract_title
from webgal_agent.api.task_storage import DEFAULT_TASK_DIR, load_tasks_from_disk, save_task_to_disk
from webgal_agent.api.workflow_definition import PIPELINE_ORDER
from webgal_agent.config.provider_manager import ProviderConfigManager
from webgal_agent.config.prompt_config import (
    extract_knowledge_requirements,
    extract_system_prompts,
    load_prompt_config,
)
from webgal_agent.core.agent import Agent
from webgal_agent.core.message import Message, MessageType
from webgal_agent.knowledge import KnowledgeStore


class TaskManager:
    """管理流水线工作流执行。

    当前对外仍暴露一个聚合型 manager。调用链大致是：

    start_task -> run_step -> _run_step_background

    其中 `_run_step_background()` 是真正的编排核心，会把用户输入、
    知识上下文和前序步骤输出拼成当前 agent 的输入，再触发落盘。
    """

    def __init__(
        self,
        knowledge_store: KnowledgeStore | None = None,
        provider_manager: ProviderConfigManager | None = None,
        task_dir: str | Path = DEFAULT_TASK_DIR,
    ) -> None:
        self._task_dir = Path(task_dir)
        self._knowledge_store = knowledge_store
        self._provider_manager = provider_manager
        prompt_config = load_prompt_config()
        self._prompts = extract_system_prompts(prompt_config)
        self._knowledge_requirements = extract_knowledge_requirements(prompt_config)

        # 加载之前持久化的任务
        self._tasks: dict[str, TaskInfo] = load_tasks_from_disk(self._task_dir)

        # 保存后台 asyncio.Task 引用，用于取消任务
        self._running_task: asyncio.Task | None = None

        # 当前正在运行的智能体实例（供状态查询和取消使用）
        self._active_agents: dict[str, Agent] = {}
        # 运行中任务对应的 task_id，用于取消时定位 agent
        self._running_task_id: str | None = None

    # ---- 元数据与依赖装配 -------------------------------------------------

    @property
    def workflow_types(self) -> list[str]:
        return ["pipeline"]

    def _build_agents(self, task_id: str = "") -> dict[str, Agent]:
        return build_agents(self._prompts, self._provider_manager, self._task_dir, task_id=task_id)

    def _build_knowledge_context(self, agent_name: str = "") -> str:
        return build_all_knowledge_contexts(
            self._knowledge_store, self._knowledge_requirements
        ).get(agent_name, "")

    def _build_all_knowledge_contexts(self) -> dict[str, str]:
        return build_all_knowledge_contexts(self._knowledge_store, self._knowledge_requirements)

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

        # 任务创建阶段只做状态初始化与持久化，不直接触发任何 agent。
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
            task.title = extract_title(task.step_results[0])
        task.status = "pending" if start_step < len(PIPELINE_ORDER) else "completed"

        self._tasks[task_id] = task
        save_task_to_disk(task, self._task_dir)
        return task

    # ---- 运行与后台编排 ---------------------------------------------------

    async def run_step(self, task_id: str) -> TaskInfo:
        """启动任务的下一步执行（后台异步）。

        强制单任务执行模式：同一时间只能有一个任务在运行。
        """
        task = self._tasks.get(task_id)
        if task is None:
            raise ValueError(f"任务 {task_id} 不存在")
        if self._running_task is not None:
            raise ValueError("已有任务正在执行中，请等待完成或取消后再试")
        if task.status == "running":
            raise ValueError("任务正在执行中，请等待完成")
        if task.current_step >= len(PIPELINE_ORDER):
            raise ValueError("所有步骤已执行完毕")

        task.status = "running"
        save_task_to_disk(task, self._task_dir)

        # 后台启动执行，不阻塞当前请求
        self._running_task = asyncio.create_task(self._run_step_background(task))

        return task

    async def revise_step(self, task_id: str, step_index: int, instruction: str) -> TaskInfo:
        """按额外引导提示重生成指定已完成步骤。"""
        task = self._tasks.get(task_id)
        if task is None:
            raise ValueError(f"任务 {task_id} 不存在")
        if self._running_task is not None:
            raise ValueError("已有任务正在执行中，请等待完成或取消后再试")
        if task.status == "running":
            raise ValueError("任务正在执行中，请等待完成")
        if step_index < 0 or step_index >= task.current_step:
            raise ValueError(f"步骤索引 {step_index} 无效（已完成步骤: 0~{task.current_step - 1}）")

        cleaned_instruction = instruction.strip()
        if not cleaned_instruction:
            raise ValueError("修订提示词不能为空")

        task.discard_from_step(step_index, PIPELINE_ORDER)
        task.errors = []
        agent_name = PIPELINE_ORDER[step_index]
        task.messages.append(
            Message(
                type=MessageType.FEEDBACK,
                sender="user",
                receiver=agent_name,
                content=cleaned_instruction,
                metadata={
                    "step": agent_name,
                    "step_index": step_index,
                    "kind": "revision_instruction",
                },
            )
        )
        task.status = "running"
        save_task_to_disk(task, self._task_dir)

        self._running_task = asyncio.create_task(
            self._run_step_background(task, revision_instruction=cleaned_instruction)
        )
        return task

    async def _run_step_background(self, task: TaskInfo, revision_instruction: str | None = None) -> None:
        """在后台执行单步智能体。

        这是任务状态流转的关键节点：

        1. 按当前步骤构建 agent
        2. 拼接用户输入、知识库、前序输出
        3. 调用 agent.handle()
        4. 写回内存状态与磁盘快照
        """
        import logging
        logger = logging.getLogger("webgal_agent.task_manager")

        step_index = task.current_step
        agent_name = PIPELINE_ORDER[step_index]

        try:
            agents = self._build_agents(task_id=task.id)
            self._active_agents = agents
            self._running_task_id = task.id
            agent = agents[agent_name]

            knowledge_contexts = self._build_all_knowledge_contexts()
            context_content = build_step_input(
                task,
                agent_name,
                step_index,
                knowledge_contexts,
                revision_instruction=revision_instruction,
            )

            current_msg = Message(
                type=MessageType.TASK,
                sender="pipeline",
                receiver=agent_name,
                content=context_content,
                metadata={
                    "user_input": task.content,
                    "step": agent_name,
                    "revision_instruction": revision_instruction or "",
                },
            )

            logger.info("步骤 %s 开始执行: task_id=%s", agent_name, task.id)
            result = await agent.handle(current_msg)

            # 保存结果
            task.messages.append(result)
            task.step_results[step_index] = result.content
            task.current_step = step_index + 1

            # 累加 Token 用量
            token_usage_raw = result.metadata.get("token_usage", {})
            if isinstance(token_usage_raw, dict) and token_usage_raw.get("total_tokens", 0) > 0:
                task.token_usage_by_step[step_index] = {
                    "prompt_tokens": int(token_usage_raw.get("prompt_tokens", 0)),
                    "completion_tokens": int(token_usage_raw.get("completion_tokens", 0)),
                    "total_tokens": int(token_usage_raw.get("total_tokens", 0)),
                }
                task.recalc_token_totals()

            # outline_writer 完成后提取标题
            if agent_name == "outline_writer":
                task.title = extract_title(result.content)

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
            self._running_task = None
            save_task_to_disk(task, self._task_dir)

    # ---- 手工编辑与查询 ---------------------------------------------------

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

        save_task_to_disk(task, self._task_dir)
        return task

    def update_task_content(self, task_id: str, content: str) -> TaskInfo:
        """更新任务原始输入内容。"""
        task = self._tasks.get(task_id)
        if task is None:
            raise ValueError(f"任务 {task_id} 不存在")
        if task.status == "running":
            raise ValueError("任务正在执行中，无法修改")

        new_content = content.strip()
        if not new_content:
            raise ValueError("任务输入不能为空")

        task.content = new_content
        save_task_to_disk(task, self._task_dir)
        return task

    def get_task(self, task_id: str) -> TaskInfo | None:
        return self._tasks.get(task_id)

    # ---- 取消与状态视图 ---------------------------------------------------

    async def cancel_task(self, task_id: str) -> bool:
        """取消正在运行的任务。

        返回 True 表示成功取消，False 表示任务不存在或已结束。
        """
        task = self._tasks.get(task_id)
        if task is None:
            return False

        # 如果有后台任务正在执行，取消它
        if self._running_task is not None and not self._running_task.done():
            # 通知 agent 停止
            for agent in self._active_agents.values():
                agent.cancel()
            self._running_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._running_task), timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            return True

        # 如果任务处于 pending/paused 状态，直接标记为 cancelled
        if task.status in ("pending", "paused"):
            task.status = "cancelled"
            task.errors.append("任务已被用户终止")
            save_task_to_disk(task, self._task_dir)
            return True

        return False

    def list_tasks(self) -> list[TaskInfo]:
        return list(self._tasks.values())

    # ---- 工作流说明 -------------------------------------------------------

    def get_workflow_info(self) -> WorkflowInfoDict:
        """返回流水线工作流信息。"""
        agents = self._build_agents()
        return {
            "name": "pipeline",
            "type": "TaskManagerPipeline",
            "description": "三阶段流水线：A(大纲) → B(剧本) → C(WebGal脚本)",
            "agents": build_agent_info(agents),
            "order": PIPELINE_ORDER,
        }

    def get_active_agents_info(self) -> list[dict[str, str]]:
        """返回当前正在运行的智能体信息（反映真实状态）。"""
        if self._active_agents:
            return build_agent_info(self._active_agents)
        # 没有运行中的任务时，返回默认配置的智能体
        return build_agent_info(self._build_agents())
