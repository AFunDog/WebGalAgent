"""浏览器自动化模块。

提供基于 Playwright 的浏览器自动化能力，支持页面导航、元素操作、截图等。
"""

from webgal_agent.browser.client import BrowserClient, DefaultBrowserConfig, create_browser
from webgal_agent.browser.models import (
    BrowserType,
    PageState,
    ElementInfo,
    Selector,
    SelectorType,
    BrowserConfig,
    CaptureConfig,
    VideoConfig,
    RecordingResult,
)
from webgal_agent.browser.capture import CanvasCapture, CaptureStats, Frame
from webgal_agent.browser.recorder import VideoRecorder
from webgal_agent.browser.tools import (
    NavigateTool,
    ClickTool,
    ScreenshotTool,
    FillTool,
    GetTextTool,
    WaitForTool,
)

__all__ = [
    "BrowserClient",
    "DefaultBrowserConfig",
    "PageState",
    "ElementInfo",
    "Selector",
    "SelectorType",
    "BrowserConfig",
    "CaptureConfig",
    "VideoConfig",
    "RecordingResult",
    "CanvasCapture",
    "VideoRecorder",
    "NavigateTool",
    "ClickTool",
    "ScreenshotTool",
    "FillTool",
    "GetTextTool",
    "WaitForTool",
]
