"""工具基类抽象。"""

from __future__ import annotations

import abc

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """工具执行返回的结果。"""

    success: bool
    output: str = ""
    error: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class Tool(abc.ABC):
    """智能体工具的抽象基类。

    工具扩展智能体的能力——例如文件读写、网络搜索或 WebGal 引擎操作。
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """工具的唯一标识符。"""

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """工具功能的可读描述。"""

    @abc.abstractmethod
    async def execute(self, **kwargs: object) -> ToolResult:
        """使用给定参数运行工具。"""

    def schema(self) -> dict[str, object]:
        """返回用于 LLM 函数调用的 JSON Schema 风格描述。"""
        return {
            "name": self.name,
            "description": self.description,
        }
