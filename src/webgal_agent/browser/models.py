"""浏览器相关的数据模型。"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class SelectorType(str, Enum):
    """CSS 选择器类型。"""

    CSS = "css"
    XPATH = "xpath"
    TEXT = "text"
    ROLE = "role"


class Selector(BaseModel):
    """元素选择器配置。"""

    type: SelectorType = SelectorType.CSS
    value: str
    description: str = ""


class PageState(BaseModel):
    """页面状态快照。"""

    url: str
    title: str
    content: str = ""
    visible: bool = True


class ElementInfo(BaseModel):
    """页面元素信息。"""

    tag: str = ""
    text: str = ""
    is_visible: bool = True
    is_enabled: bool = True
    bounding_box: dict[str, float] | None = Field(default=None, description="元素坐标 {x, y, width, height}")
    attributes: dict[str, str] = Field(default_factory=dict)


class BrowserActionType(str, Enum):
    """浏览器操作类型。"""

    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    SCREENSHOT = "screenshot"
    GET_TEXT = "get_text"
    WAIT = "wait"
    SCROLL = "scroll"
    HOVER = "hover"
    SELECT = "select"


# ─────────────────────────── 配置模型 ───────────────────────────

class BrowserType(str, Enum):
    """支持的浏览器类型。"""

    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"
    MSEDGE = "msedge"


class BrowserConfig(BaseModel):
    """浏览器基础配置。"""

    headless: bool = False
    timeout: int = 30000
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: str | None = None
    ignore_https_errors: bool = True


class VideoConfig(BaseModel):
    """视频录制配置。"""

    output_path: Path | str
    fps: float = 30.0
    codec: Literal["webm", "mp4v", "avc1", "XVID", "MJPG", "libx264"] = "webm"
    quality: int = 17
    width: int | None = None
    height: int | None = None
    max_width: int = 1920
    max_height: int = 1080


class RecordingResult(BaseModel):
    """录制结果。"""

    output_path: Path
    total_frames: int
    duration: float
    actual_fps: float
    file_size_mb: float
    wall_time: float = 0.0
    source_fps: float = 0.0
    output_fps: float = 0.0
    has_audio: bool = False
