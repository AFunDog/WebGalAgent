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

    子类必须实现：
    - ``name``: 工具唯一标识
    - ``description``: 功能描述（LLM 根据此描述决定何时调用）
    - ``parameters``: JSON Schema 风格的参数定义
    - ``execute``: 实际执行逻辑
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """工具的唯一标识符。"""

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """工具功能的可读描述（LLM 会看到这段文字）。"""

    @property
    def parameters(self) -> dict[str, object]:
        """JSON Schema 风格的参数定义。

        格式示例::

            {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要读取的文件路径",
                    },
                },
                "required": ["path"],
            }
        """
        return {"type": "object", "properties": {}, "required": []}

    @abc.abstractmethod
    async def execute(self, **kwargs: object) -> ToolResult:
        """使用给定参数运行工具。"""

    def schema(self) -> dict[str, object]:
        """返回 OpenAI function calling 兼容的工具描述。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
