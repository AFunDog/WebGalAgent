"""Base agent class and agent state definition."""

from __future__ import annotations

import abc
from enum import Enum

from pydantic import BaseModel, Field

from webgal_agent.core.memory import Memory, InMemoryMemory
from webgal_agent.core.message import Message


class AgentState(str, Enum):
    """Possible states of an agent."""

    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    ERROR = "error"
    DONE = "done"


class AgentConfig(BaseModel):
    """Configuration for an agent instance."""

    name: str
    description: str = ""
    provider: str = "openai"
    model: str = "gpt-4o"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    max_retries: int = 3


class Agent(abc.ABC):
    """Abstract base class for all agents.

    An agent is an autonomous unit that can receive messages, process them
    using an LLM, and produce responses. Each agent has its own memory
    and optional tools.
    """

    def __init__(
        self,
        config: AgentConfig,
        memory: Memory | None = None,
    ) -> None:
        self._config = config
        self._state = AgentState.IDLE
        self._memory = memory or InMemoryMemory()

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def description(self) -> str:
        return self._config.description

    @property
    def state(self) -> AgentState:
        return self._state

    @property
    def memory(self) -> Memory:
        return self._memory

    @abc.abstractmethod
    async def run(self, message: Message) -> Message:
        """Process an incoming message and return a response.

        This is the main entry point for agent execution. Subclasses must
        implement this method to define their behavior.
        """

    @abc.abstractmethod
    def system_prompt(self) -> str:
        """Return the system prompt for this agent."""

    async def handle(self, message: Message) -> Message:
        """Handle a message with state management.

        Wraps the ``run`` method with state transitions and error handling.
        """
        self._state = AgentState.RUNNING
        try:
            self._memory.add(message)
            result = await self.run(message)
            self._memory.add(result)
            self._state = AgentState.DONE
            return result
        except Exception:
            self._state = AgentState.ERROR
            raise

    def reset(self) -> None:
        """Reset the agent to idle state and clear memory."""
        self._state = AgentState.IDLE
        self._memory.clear()
