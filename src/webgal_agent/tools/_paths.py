"""共享路径解析工具。"""

from __future__ import annotations

import os
import pathlib
from typing import Any

import yaml

CONFIG_PATH = pathlib.Path("src/configs/default.yaml")

ASSET_ENV_KEYS: dict[str, str] = {
    "animation": "WEBGAL_ANIMATION_DIR",
    "background": "WEBGAL_BACKGROUND_DIR",
    "bgm": "WEBGAL_BGM_DIR",
    "figure": "WEBGAL_FIGURE_DIR",
    "vocal": "WEBGAL_VOCAL_DIR",
}

ASSET_CONFIG_KEYS: dict[str, str] = {
    "animation": "animation_dir",
    "background": "background_dir",
    "bgm": "bgm_dir",
    "figure": "figure_dir",
    "vocal": "vocal_dir",
}

ASSET_ROOT_SUBDIRS: dict[str, str] = {
    "animation": "animation",
    "background": "background",
    "bgm": "bgm",
    "figure": "figure",
    "vocal": "vocal",
}

ASSET_TYPE_ALIASES: dict[str, str] = {
    "character": "figure",
    "effect": "animation",
    "voice": "vocal",
}


def _load_assets_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}

    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}

    assets_cfg = data.get("assets", {})
    return assets_cfg if isinstance(assets_cfg, dict) else {}


def normalize_asset_kind(asset_kind: str) -> str:
    """将工具层别名归一化到实际目录类别。"""
    return ASSET_TYPE_ALIASES.get(asset_kind, asset_kind)


def resolve_game_dir() -> pathlib.Path | None:
    """从环境变量或配置解析游戏根目录路径。"""
    game_dir = os.getenv("WEBGAL_GAME_DIR")
    if game_dir:
        return pathlib.Path(game_dir)

    assets_cfg = _load_assets_config()
    dir_str = str(assets_cfg.get("game_dir", "")).strip()
    if dir_str:
        return pathlib.Path(dir_str)

    return None


def resolve_asset_dir(asset_kind: str) -> pathlib.Path | None:
    """解析某类素材的根目录。

    优先级：
    1. 对应环境变量，例如 ``WEBGAL_BACKGROUND_DIR``
    2. ``assets.<type>_dir`` 单独配置
    3. ``assets.game_dir`` + 约定子目录
    """
    normalized = normalize_asset_kind(asset_kind)
    env_key = ASSET_ENV_KEYS.get(normalized)
    if env_key:
        env_value = os.getenv(env_key)
        if env_value:
            return pathlib.Path(env_value)

    assets_cfg = _load_assets_config()
    config_key = ASSET_CONFIG_KEYS.get(normalized)
    if config_key:
        dir_str = str(assets_cfg.get(config_key, "")).strip()
        if dir_str:
            return pathlib.Path(dir_str)

    game_dir = resolve_game_dir()
    subdir = ASSET_ROOT_SUBDIRS.get(normalized)
    if game_dir is not None and subdir:
        return game_dir / subdir

    return None


def resolve_asset_dirs() -> dict[str, pathlib.Path]:
    """解析全部已配置的素材目录。"""
    dirs: dict[str, pathlib.Path] = {}
    for asset_kind in ASSET_ROOT_SUBDIRS:
        resolved = resolve_asset_dir(asset_kind)
        if resolved is not None:
            dirs[asset_kind] = resolved
    return dirs
