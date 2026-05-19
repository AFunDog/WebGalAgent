"""浏览器模块的默认输出路径约定。"""

from __future__ import annotations

import uuid
from pathlib import Path

BROWSER_DATA_DIR = Path("data/browser")
BROWSER_RECORDINGS_DIR = BROWSER_DATA_DIR / "recordings"
BROWSER_TEMP_DIR = BROWSER_DATA_DIR / "temp"


def ensure_browser_dirs() -> None:
    """确保浏览器输出目录存在。"""
    BROWSER_RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    BROWSER_TEMP_DIR.mkdir(parents=True, exist_ok=True)


def default_recording_output_path(suffix: str = ".mp4", prefix: str = "record") -> Path:
    """构造默认录制输出路径。"""
    ensure_browser_dirs()
    return BROWSER_RECORDINGS_DIR / f"{prefix}_{uuid.uuid4().hex[:8]}{suffix}"


def default_demo_output_path(filename: str = "output.mp4") -> Path:
    """构造 demo CLI 默认输出路径。"""
    ensure_browser_dirs()
    return BROWSER_RECORDINGS_DIR / filename


def default_demo_screenshot_path(filename: str = "demo.png") -> Path:
    """构造 demo 导航模式截图路径。"""
    ensure_browser_dirs()
    return BROWSER_TEMP_DIR / filename


def default_recording_log_path(output_path: str | Path) -> Path:
    """为录制输出构造默认日志路径。"""
    path = Path(output_path)
    return Path(f"{path}.log")
