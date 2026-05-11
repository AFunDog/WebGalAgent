"""Workflow orchestration engine."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

from webgal_agent.core.agent import Agent
from webgal_agent.core.message import Message, MessageType


@dataclass
class WorkflowResult:
    """Result of a workflow execution."""

    success: bool
    messages: list[Message] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class Workflow(abc.ABC):
    """Abstract base class for workflow patterns.

    A workflow defines how multiple agents collaborate — the order
    they execute in, how messages flow, and how results are aggregated.
    """

    def __init__(self, agents: dict[str, Agent]) -> None:
        self._agents = agents

    @property
    def agents(self) -> dict[str, Agent]:
        return self._agents

    def get_agent(self, name: str) -> Agent:
        """Retrieve a registered agent by name."""
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' not found in workflow")
        return self._agents[name]

    @abc.abstractmethod
    async def execute(self, initial_message: Message) -> WorkflowResult:
        """Run the workflow starting from an initial message.

        Subclasses implement this to define the execution pattern
        (sequential, parallel, debate, etc.).
        """

    def reset_all(self) -> None:
        """Reset all agents in the workflow."""
        for agent in self._agents.values():
            agent.reset()
