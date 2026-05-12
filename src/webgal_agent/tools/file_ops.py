"""文件操作工具：读写项目文件。"""

from __future__ import annotations

import pathlib

from webgal_agent.tools.base import Tool, ToolResult
from webgal_agent.tools._paths import resolve_game_dir


def _resolve_allowed_dirs() -> list[pathlib.Path]:
    """解析允许读取的目录列表。

    包括项目根目录和配置的 WebGal 游戏目录。
    """
    dirs: list[pathlib.Path] = [pathlib.Path(".").resolve()]

    game_dir = resolve_game_dir()
    if game_dir:
        dirs.append(game_dir.resolve())

    return dirs


class ReadFileTool(Tool):
    """读取文件内容的工具。"""

    def __init__(
        self,
        base_dir: str | pathlib.Path = ".",
        result_dir: str | pathlib.Path | None = None,
    ) -> None:
        self._base_dir = pathlib.Path(base_dir).resolve()
        self._allowed_dirs = _resolve_allowed_dirs()
        if result_dir is not None:
            self._result_dir = pathlib.Path(result_dir).resolve()
            self._allowed_dirs.append(self._result_dir)
        else:
            self._result_dir = None

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "读取指定路径文件的内容。路径相对于项目根目录、游戏素材目录或任务结果目录（result/）。"

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "要读取的文件路径，相对于项目根目录、游戏素材目录或任务结果目录",
                },
            },
            "required": ["path"],
        }

    async def execute(self, **kwargs: object) -> ToolResult:
        path = kwargs.get("path")
        if not path:
            return ToolResult(success=False, error="缺少 'path' 参数")

        path_str = str(path)

        # 如果是绝对路径，直接检查是否在允许的目录内
        if pathlib.Path(path_str).is_absolute():
            target = pathlib.Path(path_str).resolve()
            allowed = any(target.is_relative_to(d) for d in self._allowed_dirs if d.exists())
            if not allowed:
                return ToolResult(success=False, error=f"路径不在允许的目录内: {path}")
        else:
            # 相对路径：优先尝试 result_dir（匹配 write_result 的输出位置）
            target = None
            if self._result_dir is not None and self._result_dir.exists():
                candidate = (self._result_dir / path_str).resolve()
                if candidate.is_relative_to(self._result_dir) and candidate.exists():
                    target = candidate

            if target is None:
                # 再尝试 base_dir
                target = (self._base_dir / path_str).resolve()
                if not target.is_relative_to(self._base_dir):
                    # 尝试其他允许的目录
                    for allowed_dir in self._allowed_dirs:
                        if allowed_dir.exists():
                            candidate = (allowed_dir / path_str).resolve()
                            if candidate.is_relative_to(allowed_dir):
                                target = candidate
                                break
                    else:
                        return ToolResult(success=False, error="不允许路径穿越")

        try:
            content = target.read_text(encoding="utf-8")
            return ToolResult(success=True, output=content)
        except FileNotFoundError:
            return ToolResult(success=False, error=f"文件未找到: {path}")
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


class WriteResultTool(Tool):
    """将结果文件写入当前任务的 result 目录。

    文件只能写入 data/tasks/{task_id}/result/ 目录下，
    LLM 只需提供相对于 result/ 的文件名即可。
    """

    def __init__(self, task_id: str, task_dir: str | pathlib.Path = "data/tasks") -> None:
        self._task_id = task_id
        self._result_dir = pathlib.Path(task_dir) / task_id / "result"

    @property
    def name(self) -> str:
        return "write_result"

    @property
    def description(self) -> str:
        return (
            "将内容写入当前任务的结果目录。"
            "文件会保存到任务专属的 result/ 目录下，只需提供文件名即可。"
            "会自动创建不存在的目录。"
        )

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "文件名，如 Chapter1.txt、index.txt，也可包含子目录如 scene/Chapter1.txt",
                },
                "content": {
                    "type": "string",
                    "description": "要写入的文件内容",
                },
            },
            "required": ["filename", "content"],
        }

    async def execute(self, **kwargs: object) -> ToolResult:
        filename = kwargs.get("filename")
        content = kwargs.get("content")
        if not filename or content is None:
            return ToolResult(success=False, error="缺少 'filename' 或 'content' 参数")

        # 安全检查：禁止路径穿越
        filename_str = str(filename)
        if ".." in pathlib.PurePosixPath(filename_str).parts or filename_str.startswith(("/", "\\")):
            return ToolResult(success=False, error="文件名不允许包含路径穿越（..）或绝对路径")

        target = (self._result_dir / filename_str).resolve()
        if not target.is_relative_to(self._result_dir.resolve()):
            return ToolResult(success=False, error="不允许路径穿越")

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(content), encoding="utf-8")
            return ToolResult(success=True, output=f"已写入 result/{filename_str}")
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))
