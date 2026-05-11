"""Shared test fixtures."""

from __future__ import annotations

import pytest

from webgal_agent.core.agent import Agent, AgentConfig
from webgal_agent.core.message import Message, MessageType
from webgal_agent.core.memory import InMemoryMemory


class StubAgent(Agent):
    """A simple stub agent for testing that echoes the input."""

    def system_prompt(self) -> str:
        return "You are a stub agent."

    async def run(self, message: Message) -> Message:
        return message.reply(
            content=f"Echo: {message.content}",
            msg_type=MessageType.RESULT,
        )


@pytest.fixture
def stub_agent() -> StubAgent:
    return StubAgent(config=AgentConfig(name="stub", description="Test agent"))


@pytest.fixture
def sample_message() -> Message:
    return Message(
        type=MessageType.TASK,
        sender="user",
        receiver="stub",
        content="Hello, agent!",
    )


@pytest.fixture
def memory() -> InMemoryMemory:
    return InMemoryMemory()
