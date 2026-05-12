"""素材查询工具：按素材类型列出所有可用文件。"""

from __future__ import annotations

import json
import os
import pathlib
from collections import defaultdict

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
    """按素材类型列出所有可用文件（递归扫描子目录）。

    智能体只需传入素材类型，工具会递归扫描该类型映射的所有文件夹，
    返回按子目录分组的文件列表。
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
            "按素材类型查询所有可用文件。传入类型即可递归列出映射文件夹下的所有文件。"
            "可用类型：character（角色立绘）、background（背景图）、"
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
            },
            "required": ["asset_type"],
        }

    async def execute(self, **kwargs: object) -> ToolResult:
        asset_type = kwargs.get("asset_type", "")

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

        # 按子目录分组收集文件
        groups: dict[str, list[str]] = defaultdict(list)
        total_count = 0
        base = self._assets_dir

        # 素材类型对应的 WebGal 引用根目录（changeBg/changeFigure 等指令的路径基准）
        type_ref_roots: dict[str, str] = {
            "character": "figure",
            "background": "background",
            "bgm": "bgm",
            "effect": "animation",
            "voice": "vocal",
        }

        for subdir in subdirs:
            type_dir = base / subdir
            if not type_dir.exists():
                continue
            # 计算引用路径时的基准目录：对于 background 类型是 base/background，
            # 这样返回的路径可以直接用于 changeBg: 等指令
            ref_root = base / type_ref_roots.get(str(asset_type), subdir)
            for f in sorted(type_dir.rglob("*")):
                if f.is_file() and f.suffix.lower() in exts:
                    rel_path = f.relative_to(ref_root).as_posix()
                    groups[subdir].append(rel_path)
                    total_count += 1

        if not groups:
            note = f"素材目录不存在或为空: {', '.join(subdirs)}"
        else:
            note = f"共找到 {total_count} 个文件"

        # 构建分组输出
        grouped_files: dict[str, list[str]] = {}
        for key in sorted(groups.keys()):
            grouped_files[key] = groups[key]

        return ToolResult(
            success=True,
            output=json.dumps(
                {
                    "asset_type": asset_type,
                    "total_count": total_count,
                    "groups": grouped_files,
                    "note": note,
                },
                ensure_ascii=False,
            ),
        )
