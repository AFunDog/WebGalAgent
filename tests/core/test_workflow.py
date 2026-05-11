"""Tests for PipelineWorkflow."""

from __future__ import annotations

import pytest

from webgal_agent.core.agent import AgentConfig
from webgal_agent.core.message import Message, MessageType
from webgal_agent.workflows.pipeline import PipelineWorkflow
from tests.conftest import StubAgent


async def test_pipeline_workflow() -> None:
    agent_a = StubAgent(config=AgentConfig(name="a"))
    agent_b = StubAgent(config=AgentConfig(name="b"))

    workflow = PipelineWorkflow(
        agents={"a": agent_a, "b": agent_b},
        order=["a", "b"],
        user_input="hello",
        knowledge_context="some knowledge",
    )

    initial = Message(sender="user", receiver="a", content="start")
    result = await workflow.execute(initial)

    assert result.success
    assert len(result.messages) == 2


async def test_pipeline_accumulates_context() -> None:
    agent_a = StubAgent(config=AgentConfig(name="a"))
    agent_b = StubAgent(config=AgentConfig(name="b"))

    workflow = PipelineWorkflow(
        agents={"a": agent_a, "b": agent_b},
        order=["a", "b"],
        user_input="my task",
        knowledge_context="world info",
    )

    initial = Message(sender="user", receiver="a", content="start")
    result = await workflow.execute(initial)

    assert result.success
    # Second agent's input should contain user_input and knowledge
    second_msg = result.messages[1]
    assert "my task" in second_msg.content or "world info" in second_msg.content


async def test_pipeline_invalid_order() -> None:
    agent_a = StubAgent(config=AgentConfig(name="a"))

    workflow = PipelineWorkflow(
        agents={"a": agent_a},
        order=["a", "nonexistent"],
        user_input="test",
    )

    initial = Message(sender="user", receiver="a", content="start")
    result = await workflow.execute(initial)

    assert not result.success
    assert len(result.errors) > 0
