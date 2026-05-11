"""工作流编排引擎。"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

from webgal_agent.core.agent import Agent
from webgal_agent.core.message import Message, MessageType


@dataclass
class WorkflowResult:
    """工作流执行结果。"""

    success: bool
    messages: list[Message] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class Workflow(abc.ABC):
    """工作流模式的抽象基类。

    工作流定义了多个智能体如何协作——
    执行顺序、消息流向和结果聚合方式。
    """

    def __init__(self, agents: dict[str, Agent]) -> None:
        self._agents = agents

    @property
    def agents(self) -> dict[str, Agent]:
        return self._agents

    def get_agent(self, name: str) -> Agent:
        """根据名称获取已注册的智能体。"""
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' not found in workflow")
        return self._agents[name]

    @abc.abstractmethod
    async def execute(self, initial_message: Message) -> WorkflowResult:
        """从初始消息开始运行工作流。

        子类实现此方法以定义执行模式（顺序、并行、辩论等）。
        """

    def reset_all(self) -> None:
        """重置工作流中的所有智能体。"""
        for agent in self._agents.values():
            agent.reset()
