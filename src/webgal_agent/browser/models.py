"""浏览器相关的数据模型。"""

from __future__ import annotations

from enum import Enum

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
