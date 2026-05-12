"""素材查询工具：让智能体主动查询可用素材信息。"""

from __future__ import annotations

import json
import os
import pathlib

from webgal_agent.tools.base import Tool, ToolResult


def _resolve_assets_base_dir() -> pathlib.Path:
    """从环境变量或配置解析游戏素材根目录。

    查找优先级：
    1. 环境变量 WEBGAL_GAME_DIR
    2. configs/default.yaml 中的 assets.game_dir
    3. 回退到 data/assets
    """
    game_dir = os.getenv("WEBGAL_GAME_DIR")
    if game_dir:
        return pathlib.Path(game_dir)

    config_path = pathlib.Path("configs/default.yaml")
    if config_path.exists():
        import yaml
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if data and isinstance(data, dict):
            assets_cfg = data.get("assets", {})
            dir_str = assets_cfg.get("game_dir", "")
            if dir_str:
                return pathlib.Path(dir_str)

    return pathlib.Path("data/assets")


class AssetQueryTool(Tool):
    """查询本地可用素材的工具。

    智能体可以通过此工具主动查询角色立绘、背景图、BGM 等素材，
    以便在生成 WebGal 脚本时引用正确的素材文件名。
    """

    def __init__(self, assets_dir: str | pathlib.Path | None = None) -> None:
        if assets_dir is not None:
            self._assets_dir = pathlib.Path(assets_dir)
        else:
            self._assets_dir = _resolve_assets_base_dir()

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

        # WebGal 游戏目录下的素材子目录映射
        type_subdirs: dict[str, list[str]] = {
            "character": ["figure"],
            "background": ["background/BandDream背景与BGM/背景整理合集"],
            "bgm": ["bgm"],
            "effect": ["animation"],
            "voice": ["vocal"],
        }

        # 每种素材类型对应的文件扩展名
        supported_ext: dict[str, set[str]] = {
            "character": {".png", ".jpg", ".webp", ".gif", ".json"},
            "background": {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"},
            "bgm": {".mp3", ".ogg", ".wav", ".m4a", ".flac"},
            "effect": {".png", ".webp", ".gif", ".json"},
            "voice": {".mp3", ".ogg", ".wav", ".m4a"},
        }

        subdirs = type_subdirs.get(str(asset_type), [])
        exts = supported_ext.get(str(asset_type), {".png", ".jpg", ".mp3"})

        if not subdirs:
            return ToolResult(
                success=True,
                output=json.dumps(
                    {"asset_type": asset_type, "files": [], "note": f"未知素材类型: {asset_type}"},
                    ensure_ascii=False,
                ),
            )

        files: list[str] = []
        base = self._assets_dir
        for subdir in subdirs:
            type_dir = base / subdir
            if not type_dir.exists():
                continue
            for f in sorted(type_dir.rglob("*")):
                if f.is_file() and f.suffix.lower() in exts:
                    # 返回相对于 base 的路径，如 figure/anon/model.json
                    rel_path = f.relative_to(base).as_posix()
                    if not keyword or keyword in rel_path.lower():
                        files.append(rel_path)

        if not files and not any((base / s).exists() for s in subdirs):
            note = f"素材目录不存在: {', '.join(subdirs)}"
        else:
            note = f"在 {'/'.join(subdirs)} 目录下找到 {len(files)} 个文件"

        return ToolResult(
            success=True,
            output=json.dumps(
                {"asset_type": asset_type, "count": len(files), "files": files, "note": note},
                ensure_ascii=False,
            ),
        )
