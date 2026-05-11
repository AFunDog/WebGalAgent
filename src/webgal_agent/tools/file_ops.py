"""File operation tools for reading/writing project files."""

from __future__ import annotations

import pathlib

from webgal_agent.tools.base import Tool, ToolResult


class ReadFileTool(Tool):
    """Tool to read the contents of a file."""

    def __init__(self, base_dir: str | pathlib.Path = ".") -> None:
        self._base_dir = pathlib.Path(base_dir).resolve()

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Read the contents of a file at the given path."

    async def execute(self, **kwargs: object) -> ToolResult:
        path = kwargs.get("path")
        if not path:
            return ToolResult(success=False, error="Missing 'path' argument")

        target = (self._base_dir / str(path)).resolve()
        if not target.is_relative_to(self._base_dir):
            return ToolResult(success=False, error="Path traversal not allowed")

        try:
            content = target.read_text(encoding="utf-8")
            return ToolResult(success=True, output=content)
        except FileNotFoundError:
            return ToolResult(success=False, error=f"File not found: {path}")
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


class WriteFileTool(Tool):
    """Tool to write content to a file."""

    def __init__(self, base_dir: str | pathlib.Path = ".") -> None:
        self._base_dir = pathlib.Path(base_dir).resolve()

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Write content to a file at the given path."

    async def execute(self, **kwargs: object) -> ToolResult:
        path = kwargs.get("path")
        content = kwargs.get("content")
        if not path or content is None:
            return ToolResult(success=False, error="Missing 'path' or 'content' argument")

        target = (self._base_dir / str(path)).resolve()
        if not target.is_relative_to(self._base_dir):
            return ToolResult(success=False, error="Path traversal not allowed")

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(content), encoding="utf-8")
            return ToolResult(success=True, output=f"Written to {path}")
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))
