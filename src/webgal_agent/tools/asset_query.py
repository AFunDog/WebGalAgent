"""素材查询工具：让智能体主动查询可用素材信息。"""

from __future__ import annotations

import json
import pathlib

from webgal_agent.tools.base import Tool, ToolResult


class AssetQueryTool(Tool):
    """查询本地可用素材的工具。

    智能体可以通过此工具主动查询角色立绘、背景图、BGM 等素材，
    以便在生成 WebGal 脚本时引用正确的素材文件名。
    """

    def __init__(self, assets_dir: str | pathlib.Path = "data/assets") -> None:
        self._assets_dir = pathlib.Path(assets_dir)

    @property
    def name(self) -> str:
        return "query_assets"

    @property
    def description(self) -> str:
        return (
            "查询可用的素材资源列表。可按素材类型筛选："
            "character（角色立绘）、background（背景图）、"
            "bgm（背景音乐）、effect（特效）、voice（语音）。"
        )

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "asset_type": {
                    "type": "string",
                    "description": "素材类型：character / background / bgm / effect / voice",
                    "enum": ["character", "background", "bgm", "effect", "voice"],
                },
                "keyword": {
                    "type": "string",
                    "description": "按关键词筛选素材名称（可选）",
                },
            },
            "required": ["asset_type"],
        }

    async def execute(self, **kwargs: object) -> ToolResult:
        asset_type = kwargs.get("asset_type", "")
        keyword = str(kwargs.get("keyword", "")).lower()

        if not asset_type:
            return ToolResult(success=False, error="缺少 'asset_type' 参数")

        # 查找对应目录
        type_dir = self._assets_dir / str(asset_type)
        if not type_dir.exists():
            # 返回空结果而非报错，让 LLM 知道没有这类素材
            return ToolResult(
                success=True,
                output=json.dumps(
                    {"asset_type": asset_type, "files": [], "note": "该类型素材目录不存在"},
                    ensure_ascii=False,
                ),
            )

        # 扫描文件
        supported_ext = {
            "character": {".png", ".jpg", ".webp", ".gif"},
            "background": {".png", ".jpg", ".webp"},
            "bgm": {".mp3", ".ogg", ".wav"},
            "effect": {".png", ".webp", ".gif"},
            "voice": {".mp3", ".ogg", ".wav"},
        }
        exts = supported_ext.get(str(asset_type), {".png", ".jpg", ".mp3"})

        files: list[str] = []
        for f in sorted(type_dir.rglob("*")):
            if f.is_file() and f.suffix.lower() in exts:
                rel_path = f.relative_to(self._assets_dir).as_posix()
                if not keyword or keyword in rel_path.lower():
                    files.append(rel_path)

        return ToolResult(
            success=True,
            output=json.dumps(
                {"asset_type": asset_type, "count": len(files), "files": files},
                ensure_ascii=False,
            ),
        )
