"""共享路径解析工具。"""

from __future__ import annotations

import os
import pathlib


def resolve_game_dir() -> pathlib.Path | None:
    """从环境变量或配置解析游戏目录路径。

    查找优先级：
    1. 环境变量 WEBGAL_GAME_DIR
    2. src/configs/default.yaml 中的 assets.game_dir

    Returns:
        游戏目录路径，未配置则返回 None。
    """
    game_dir = os.getenv("WEBGAL_GAME_DIR")
    if game_dir:
        return pathlib.Path(game_dir)

    config_path = pathlib.Path("src/configs/default.yaml")
    if config_path.exists():
        import yaml

        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if data and isinstance(data, dict):
            assets_cfg = data.get("assets", {})
            dir_str = assets_cfg.get("game_dir", "")
            if dir_str:
                return pathlib.Path(dir_str)

    return None
