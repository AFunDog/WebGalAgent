"""智能体记忆抽象。"""

from __future__ import annotations

from abc import ABC, abstractmethod

from webgal_agent.core.message import Message


class Memory(ABC):
    """智能体记忆的抽象基类。

    记忆存储对话历史和工作流中智能体间的共享上下文。
    """

    @abstractmethod
    def add(self, message: Message) -> None:
        """将消息存入记忆。"""

    @abstractmethod
    def get_all(self) -> list[Message]:
        """检索所有已存储的消息。"""

    @abstractmethod
    def clear(self) -> None:
        """清空所有已存储的消息。"""

    @abstractmethod
    def get_recent(self, n: int = 10) -> list[Message]:
        """检索最近的 ``n`` 条消息。"""


class InMemoryMemory(Memory):
    """基于内存的简单智能体记忆实现。"""

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
