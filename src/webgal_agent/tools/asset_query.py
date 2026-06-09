"""素材查询工具：按素材类型列出所有可用文件。"""

from __future__ import annotations

import fnmatch
import json
import os
import pathlib
from collections import defaultdict

from webgal_agent.tools.base import Tool, ToolResult
from webgal_agent.tools._paths import resolve_asset_dir


class AssetQueryTool(Tool):
    """按素材类型列出所有可用文件（递归扫描子目录）。

    智能体只需传入素材类型，工具会递归扫描该类型映射的所有文件夹，
    返回按子目录分组的文件列表。
    """

    def __init__(self, assets_dir: str | pathlib.Path | None = None) -> None:
        if assets_dir is not None:
            self._assets_dir = pathlib.Path(assets_dir)
        else:
            self._assets_dir = pathlib.Path("data/assets")

    def _iter_files_following_links(self, root: pathlib.Path) -> list[pathlib.Path]:
        """递归遍历目录，显式跟随符号链接目录。"""
        files: list[pathlib.Path] = []
        stack: list[pathlib.Path] = [root]
        visited_dirs: set[str] = set()

        while stack:
            current = stack.pop()
            try:
                current_key = current.resolve().as_posix()
            except OSError:
                current_key = current.as_posix()
            if current_key in visited_dirs:
                continue
            visited_dirs.add(current_key)

            try:
                with os.scandir(current) as entries:
                    for entry in sorted(entries, key=lambda item: item.name):
                        try:
                            if entry.is_dir(follow_symlinks=True):
                                stack.append(pathlib.Path(entry.path))
                            elif entry.is_file(follow_symlinks=True):
                                files.append(pathlib.Path(entry.path))
                        except OSError:
                            continue
            except (FileNotFoundError, NotADirectoryError, PermissionError):
                continue

        return files

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

        # 素材类型对应的实际扫描目录类别
        type_dirs: dict[str, str] = {
            "character": "figure",
            "background": "background",
            "bgm": "bgm",
            "effect": "animation",
            "voice": "vocal",
        }

        # 每种素材类型对应的文件扩展名
        supported_ext: dict[str, set[str]] = {
            "character": {".json"},
            "background": {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"},
            "bgm": {".mp3", ".ogg", ".wav", ".m4a", ".flac"},
            "effect": {".png", ".webp", ".gif", ".json"},
            "voice": {".mp3", ".ogg", ".wav", ".m4a"},
        }

        resolved_type = type_dirs.get(str(asset_type), "")
        exts = supported_ext.get(str(asset_type), {".png", ".jpg", ".mp3"})

        # 每种素材类型对应的文件名过滤模式（None 表示不过滤）
        type_name_filters: dict[str, list[str] | None] = {
            "character": ["model*.json"],
            "background": None,
            "bgm": None,
            "effect": None,
            "voice": None,
        }
        name_filters = type_name_filters.get(str(asset_type))

        # 每种素材类型对应的路径排除关键字（None 表示不排除）
        type_path_excludes: dict[str, list[str] | None] = {
            "character": [".mtn_exp"],
            "background": None,
            "bgm": None,
            "effect": None,
            "voice": None,
        }
        path_excludes = type_path_excludes.get(str(asset_type))

        if not resolved_type:
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
        asset_dir = resolve_asset_dir(resolved_type) or self._assets_dir / resolved_type

        if asset_dir.exists():
            for f in self._iter_files_following_links(asset_dir):
                if f.is_file() and f.suffix.lower() in exts:
                    if name_filters is not None and not any(
                        fnmatch.fnmatch(f.name, pat) for pat in name_filters
                    ):
                        continue
                    if path_excludes is not None and any(
                        pat in f.as_posix() for pat in path_excludes
                    ):
                        continue
                    rel_path = f.relative_to(asset_dir).as_posix()
                    group_name = rel_path.split("/", 1)[0] if "/" in rel_path else "."
                    groups[group_name].append(rel_path)
                    total_count += 1

        if not groups:
            note = f"素材目录不存在或为空: {asset_dir.as_posix()}"
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
