"""Base tool abstraction."""

from __future__ import annotations

import abc

from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """Result returned by a tool execution."""

    success: bool
    output: str = ""
    error: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class Tool(abc.ABC):
    """Abstract base class for agent tools.

    Tools extend an agent's capabilities — for example, file I/O,
    web searches, or WebGal engine operations.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Unique identifier for this tool."""

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """Human-readable description of what this tool does."""

    @abc.abstractmethod
    async def execute(self, **kwargs: object) -> ToolResult:
        """Run the tool with the given arguments."""

    def schema(self) -> dict[str, object]:
        """Return a JSON-schema-style description for LLM function calling."""
        return {
            "name": self.name,
            "description": self.description,
        }
