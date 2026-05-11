"""Tests for workflow implementations."""

from __future__ import annotations

import pytest

from webgal_agent.core.agent import AgentConfig
from webgal_agent.core.message import Message, MessageType
from webgal_agent.workflows.sequential import SequentialWorkflow
from tests.conftest import StubAgent


async def test_sequential_workflow() -> None:
    agent_a = StubAgent(config=AgentConfig(name="a"))
    agent_b = StubAgent(config=AgentConfig(name="b"))

    workflow = SequentialWorkflow(
        agents={"a": agent_a, "b": agent_b},
        order=["a", "b"],
    )

    initial = Message(sender="user", receiver="a", content="start")
    result = await workflow.execute(initial)

    assert result.success
    assert len(result.messages) == 2


async def test_sequential_workflow_invalid_order() -> None:
    agent_a = StubAgent(config=AgentConfig(name="a"))

    workflow = SequentialWorkflow(
        agents={"a": agent_a},
        order=["a", "nonexistent"],
    )

    initial = Message(sender="user", receiver="a", content="start")
    result = await workflow.execute(initial)

    assert not result.success
    assert len(result.errors) > 0
