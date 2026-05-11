"""文件操作工具：读写项目文件。"""

from __future__ import annotations

import pathlib

from webgal_agent.tools.base import Tool, ToolResult


class ReadFileTool(Tool):
    """读取文件内容的工具。"""

    def __init__(self, base_dir: str | pathlib.Path = ".") -> None:
        self._base_dir = pathlib.Path(base_dir).resolve()

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "读取指定路径文件的内容。"

    async def execute(self, **kwargs: object) -> ToolResult:
        path = kwargs.get("path")
        if not path:
            return ToolResult(success=False, error="缺少 'path' 参数")

        target = (self._base_dir / str(path)).resolve()
        if not target.is_relative_to(self._base_dir):
            return ToolResult(success=False, error="不允许路径穿越")

        try:
            content = target.read_text(encoding="utf-8")
            return ToolResult(success=True, output=content)
        except FileNotFoundError:
            return ToolResult(success=False, error=f"文件未找到: {path}")
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


class WriteFileTool(Tool):
    """写入文件内容的工具。"""

    def __init__(self, base_dir: str | pathlib.Path = ".") -> None:
        self._base_dir = pathlib.Path(base_dir).resolve()

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "将内容写入指定路径的文件。"

    async def execute(self, **kwargs: object) -> ToolResult:
        path = kwargs.get("path")
        content = kwargs.get("content")
        if not path or content is None:
            return ToolResult(success=False, error="缺少 'path' 或 'content' 参数")

        target = (self._base_dir / str(path)).resolve()
        if not target.is_relative_to(self._base_dir):
            return ToolResult(success=False, error="不允许路径穿越")

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(content), encoding="utf-8")
            return ToolResult(success=True, output=f"已写入 {path}")
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))
