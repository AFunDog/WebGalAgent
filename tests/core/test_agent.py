"""Tests for the Agent base class."""

from __future__ import annotations

import pytest

from webgal_agent.core.agent import AgentConfig, AgentState


async def test_agent_initial_state(stub_agent) -> None:
    assert stub_agent.state == AgentState.IDLE


async def test_agent_handle_sets_state(stub_agent, sample_message) -> None:
    result = await stub_agent.handle(sample_message)
    assert stub_agent.state == AgentState.DONE
    assert "Echo" in result.content


async def test_agent_reset(stub_agent, sample_message) -> None:
    await stub_agent.handle(sample_message)
    stub_agent.reset()
    assert stub_agent.state == AgentState.IDLE
    assert len(stub_agent.memory.get_all()) == 0


async def test_agent_name_from_config() -> None:
    from tests.conftest import StubAgent

    config = AgentConfig(name="custom", description="Custom agent")
    agent = StubAgent(config=config)
    assert agent.name == "custom"
