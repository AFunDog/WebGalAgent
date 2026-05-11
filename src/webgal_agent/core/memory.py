"""Agent memory abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod

from webgal_agent.core.message import Message


class Memory(ABC):
    """Abstract base class for agent memory.

    Memory stores the conversation history and any shared context
    between agents in a workflow.
    """

    @abstractmethod
    def add(self, message: Message) -> None:
        """Store a message in memory."""

    @abstractmethod
    def get_all(self) -> list[Message]:
        """Retrieve all stored messages."""

    @abstractmethod
    def clear(self) -> None:
        """Clear all stored messages."""

    @abstractmethod
    def get_recent(self, n: int = 10) -> list[Message]:
        """Retrieve the most recent ``n`` messages."""


class InMemoryMemory(Memory):
    """Simple in-memory implementation of agent memory."""

    def __init__(self, max_messages: int = 100) -> None:
        self._messages: list[Message] = []
        self._max_messages = max_messages

    def add(self, message: Message) -> None:
        self._messages.append(message)
        if len(self._messages) > self._max_messages:
            self._messages = self._messages[-self._max_messages :]

    def get_all(self) -> list[Message]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    def get_recent(self, n: int = 10) -> list[Message]:
        return self._messages[-n:]
