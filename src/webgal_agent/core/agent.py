"""智能体基类与状态定义。"""

from __future__ import annotations

import abc
from enum import Enum

from pydantic import BaseModel, Field

from webgal_agent.core.memory import Memory, InMemoryMemory
from webgal_agent.core.message import Message


class AgentState(str, Enum):
    """智能体可能的状态。"""

    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    ERROR = "error"
    DONE = "done"


class AgentConfig(BaseModel):
    """智能体实例的配置。"""

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
    """所有智能体的抽象基类。

    智能体是可接收消息、通过 LLM 处理并产生响应的自主单元。
    每个智能体拥有独立的记忆和可选的工具。
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
        """处理传入消息并返回响应。

        这是智能体执行的主入口。子类必须实现此方法以定义行为。
        """

    @abc.abstractmethod
    def system_prompt(self) -> str:
        """返回该智能体的系统提示词。"""

    async def handle(self, message: Message) -> Message:
        """带状态管理的消息处理。

        在 ``run`` 方法外包装状态转换和错误处理。
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
        """重置智能体到空闲状态并清空记忆。"""
        self._state = AgentState.IDLE
        self._memory.clear()
