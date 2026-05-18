"""浏览器注入脚本加载辅助。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).with_name("js")


@lru_cache(maxsize=None)
def load_browser_script(name: str) -> str:
    """从 `browser/js/` 目录读取脚本内容并缓存。"""
    path = _SCRIPTS_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"浏览器脚本不存在: {path}")
    return path.read_text(encoding="utf-8")
