"""TaskManager 的最小保护测试。"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest

from webgal_agent.api.task_manager import TaskManager
from webgal_agent.core.agent import Agent, AgentConfig
from webgal_agent.core.message import Message, MessageType


class StubAgent(Agent):
    """返回固定结果的轻量测试 agent。"""

    def __init__(self, name: str, content: str, token_usage: dict[str, int] | None = None) -> None:
        super().__init__(AgentConfig(name=name))
        self._content = content
        self._token_usage = token_usage or {}

    async def run(self, message: Message) -> Message:
        return message.reply(self._content, msg_type=MessageType.RESULT).model_copy(
            update={"metadata": {"token_usage": self._token_usage}}
        )


class CapturingStubAgent(StubAgent):
    """额外记录收到的输入内容。"""

    def __init__(self, name: str, content: str, token_usage: dict[str, int] | None = None) -> None:
        super().__init__(name, content, token_usage=token_usage)
        self.last_message: Message | None = None

    async def run(self, message: Message) -> Message:
        self.last_message = message
        return await super().run(message)


def _make_task_dir() -> Path:
    task_dir = Path("data/temp") / f"pytest_task_manager_{uuid.uuid4().hex[:8]}"
    task_dir.mkdir(parents=True, exist_ok=True)
    return task_dir


@pytest.mark.asyncio
async def test_start_task_prefills_skipped_steps_and_extracts_title() -> None:
    task_dir = _make_task_dir()
    try:
        manager = TaskManager(task_dir=task_dir)

        task = await manager.start_task(
            "写一个校园题材故事",
            start_step=2,
            step_inputs={
                "0": "# 星光下的约定\n大纲内容",
                "1": "剧本正文",
            },
        )

        assert task.current_step == 2
        assert task.status == "pending"
        assert task.title == "星光下的约定"
        assert task.step_results[0].startswith("# 星光下的约定")
        assert task.step_results[1] == "剧本正文"
        assert [msg.sender for msg in task.messages] == ["outline_writer", "script_writer"]
        assert all(msg.metadata.get("skipped") is True for msg in task.messages)

        process_file = task_dir / task.id / "process.json"
        assert process_file.exists()
        assert '"current_step": 2' in process_file.read_text(encoding="utf-8")
    finally:
        shutil.rmtree(task_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_run_step_records_result_and_token_usage() -> None:
    task_dir = _make_task_dir()
    try:
        manager = TaskManager(task_dir=task_dir)
        task = await manager.start_task("生成一个恋爱喜剧大纲")

        manager._build_agents = lambda task_id="": {  # type: ignore[method-assign]
            "outline_writer": StubAgent(
                "outline_writer",
                "# 雨夜便利店\n第一章大纲",
                {"prompt_tokens": 12, "completion_tokens": 20, "total_tokens": 32},
            ),
            "script_writer": StubAgent("script_writer", "unused"),
            "script_converter": StubAgent("script_converter", "unused"),
        }
        manager._build_all_knowledge_contexts = lambda: {}  # type: ignore[method-assign]

        updated = await manager.run_step(task.id)
        background_task = manager._running_task
        assert updated.status == "running"
        assert background_task is not None

        await background_task

        stored = manager.get_task(task.id)
        assert stored is not None
        assert stored.status == "paused"
        assert stored.current_step == 1
        assert stored.title == "雨夜便利店"
        assert stored.step_results[0] == "# 雨夜便利店\n第一章大纲"
        assert stored.total_tokens == 32
        assert stored.token_usage_by_step[0]["prompt_tokens"] == 12
        assert (task_dir / task.id / "result.txt").exists()
    finally:
        shutil.rmtree(task_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_cancel_pending_task_marks_task_cancelled() -> None:
    task_dir = _make_task_dir()
    try:
        manager = TaskManager(task_dir=task_dir)
        task = await manager.start_task("只创建不运行")

        cancelled = await manager.cancel_task(task.id)

        assert cancelled is True
        stored = manager.get_task(task.id)
        assert stored is not None
        assert stored.status == "cancelled"
        assert stored.errors[-1] == "任务已被用户终止"
    finally:
        shutil.rmtree(task_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_revise_step_restarts_from_target_step_and_appends_instruction() -> None:
    task_dir = _make_task_dir()
    try:
        manager = TaskManager(task_dir=task_dir)
        task = await manager.start_task(
            "把校园故事转换成脚本",
            start_step=2,
            step_inputs={
                "0": "# 初稿标题\n大纲内容",
                "1": "旧剧本正文",
            },
        )
        task.step_results[2] = "旧 WebGal 脚本"
        task.current_step = 3
        task.status = "completed"
        converter = CapturingStubAgent(
            "script_converter",
            "新 WebGal 脚本",
            {"prompt_tokens": 9, "completion_tokens": 11, "total_tokens": 20},
        )

        manager._build_agents = lambda task_id="": {  # type: ignore[method-assign]
            "outline_writer": StubAgent("outline_writer", "unused"),
            "script_writer": StubAgent("script_writer", "unused"),
            "script_converter": converter,
        }
        manager._build_all_knowledge_contexts = lambda: {}  # type: ignore[method-assign]

        updated = await manager.revise_step(task.id, 2, "请减少旁白，增加对白张力")
        background_task = manager._running_task
        assert updated.status == "running"
        assert updated.current_step == 2
        assert 2 not in updated.step_results
        assert background_task is not None

        await background_task

        stored = manager.get_task(task.id)
        assert stored is not None
        assert stored.status == "completed"
        assert stored.current_step == 3
        assert stored.step_results[2] == "新 WebGal 脚本"
        assert 2 in stored.step_output_history
        assert len(stored.step_output_history[2]) == 2
        assert stored.step_output_history[2][0]["content"] == "旧 WebGal 脚本"
        assert stored.step_output_history[2][1]["content"] == "新 WebGal 脚本"
        assert stored.total_tokens == 20
        assert converter.last_message is not None
        assert "【上一次输出】\n旧 WebGal 脚本" in converter.last_message.content
        assert "【script_writer 的输出】\n旧剧本正文" in converter.last_message.content
        assert "【本轮修订要求】" in converter.last_message.content
        assert "请减少旁白，增加对白张力" in converter.last_message.content
        assert any(msg.type == MessageType.FEEDBACK for msg in stored.messages)
        process_file = task_dir / task.id / "process.json"
        assert '"step_output_history"' in process_file.read_text(encoding="utf-8")
    finally:
        shutil.rmtree(task_dir, ignore_errors=True)
