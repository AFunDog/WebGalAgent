"""模型文件读取工具：读取角色 model.json 提取动作、表情和附加描述。"""

from __future__ import annotations

import json
import os
import pathlib

from webgal_agent.tools._paths import resolve_asset_dir
from webgal_agent.tools.base import Tool, ToolResult

DEFAULT_KNOWLEDGE_DIR = pathlib.Path("data/knowledge")


def _resolve_knowledge_dir() -> pathlib.Path:
    knowledge_dir = os.getenv("WEBGAL_KNOWLEDGE_DIR", str(DEFAULT_KNOWLEDGE_DIR)).strip()
    return pathlib.Path(knowledge_dir)


def _load_expression_motion_descriptions(character_id: str) -> tuple[dict[str, str], str | None]:
    knowledge_root = _resolve_knowledge_dir() / "characters"
    if not knowledge_root.exists():
        return {}, None

    best_descriptions: dict[str, str] = {}
    best_source: str | None = None
    best_score = 0

    for path in sorted(knowledge_root.rglob("expression_motion.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        if not isinstance(data, list):
            continue

        descriptions: dict[str, str] = {}
        score = 0
        for item in data:
            if not isinstance(item, dict):
                continue
            action = item.get("action")
            description = item.get("description")
            if not isinstance(action, str) or not isinstance(description, str):
                continue
            if action.startswith(f"{character_id}/"):
                descriptions[action] = description
                score += 1

        if score > best_score and descriptions:
            best_score = score
            best_descriptions = descriptions
            best_source = path.relative_to(knowledge_root.parent).as_posix()

    return best_descriptions, best_source


def _extract_character_id(rel_path: str) -> str:
    path = pathlib.PurePosixPath(rel_path.replace("\\", "/"))
    parts = path.parts
    if parts:
        return parts[0]
    return path.stem or ""


class ReadModelTool(Tool):
    """读取角色 model.json 文件，返回 motions、expressions 和附加描述。"""

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
            "读取角色模型文件(model.json)，提取可用的动作(motions)、表情(expressions)"
            "以及同角色 expression_motion.json 中的描述映射。传入 query_assets 返回的 "
            "model*.json 路径即可。"
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
        descriptions: dict[str, str] = {}
        description_source: str | None = None

        motions_data = data.get("motions")
        if isinstance(motions_data, dict):
            motions = sorted(motions_data.keys())

        expressions_data = data.get("expressions")
        if isinstance(expressions_data, list):
            expressions = sorted(
                item["name"] for item in expressions_data
                if isinstance(item, dict) and "name" in item
            )

        character_id = _extract_character_id(str(rel_path))
        if character_id:
            descriptions, description_source = _load_expression_motion_descriptions(character_id)

        payload: dict[str, object] = {
            "path": str(rel_path),
            "motions": motions,
            "expressions": expressions,
            "descriptions": descriptions,
        }
        if description_source:
            payload["description_source"] = description_source

        output = json.dumps(payload, ensure_ascii=False)

        return ToolResult(success=True, output=output)
