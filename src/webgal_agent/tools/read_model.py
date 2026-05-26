"""模型文件读取工具：读取角色 model.json 提取动作和表情列表。"""

from __future__ import annotations

import json
import pathlib

from webgal_agent.tools.base import Tool, ToolResult
from webgal_agent.tools._paths import resolve_asset_dir


class ReadModelTool(Tool):
    """读取角色 model.json 文件，仅返回 motions（动作）和 expressions（表情）列表。"""

    def __init__(self, figure_dir: str | pathlib.Path | None = None) -> None:
        if figure_dir is not None:
            self._figure_dir = pathlib.Path(figure_dir)
        else:
            self._figure_dir = resolve_asset_dir("figure") or pathlib.Path("data/assets/figure")

    @property
    def name(self) -> str:
        return "read_model"

    @property
    def description(self) -> str:
        return (
            "读取角色模型文件(model.json)，提取可用的动作(motions)和表情(expressions)列表。"
            "传入 query_assets 返回的 model*.json 路径即可。"
        )

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": (
                        "模型文件相对路径，如 soyo/school_winter-2023/model.json "
                        "或 anon/.mtn_exp/model.json"
                    ),
                },
            },
            "required": ["path"],
        }

    async def execute(self, **kwargs: object) -> ToolResult:
        rel_path = kwargs.get("path", "")
        if not rel_path:
            return ToolResult(success=False, error="缺少 'path' 参数")

        target = self._figure_dir / str(rel_path)

        if not target.exists():
            return ToolResult(
                success=False,
                error=f"模型文件不存在: {rel_path}（已尝试 figure_dir）",
            )

        if not target.is_file():
            return ToolResult(success=False, error=f"路径不是文件: {rel_path}")

        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return ToolResult(success=False, error=f"JSON 解析失败: {exc}")
        except Exception as exc:
            return ToolResult(success=False, error=f"读取模型文件失败: {exc}")

        motions: list[str] = []
        expressions: list[str] = []

        motions_data = data.get("motions")
        if isinstance(motions_data, dict):
            motions = sorted(motions_data.keys())

        expressions_data = data.get("expressions")
        if isinstance(expressions_data, list):
            expressions = sorted(
                item["name"] for item in expressions_data
                if isinstance(item, dict) and "name" in item
            )

        output = json.dumps(
            {
                "path": str(rel_path),
                "motions": motions,
                "expressions": expressions,
            },
            ensure_ascii=False,
        )

        return ToolResult(success=True, output=output)
