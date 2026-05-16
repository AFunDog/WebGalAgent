"""浏览器自动化模块。

提供基于 Playwright 的浏览器自动化能力，支持页面导航、元素操作、截图和视频录制。
"""

from webgal_agent.browser.client import BrowserClient, DefaultBrowserConfig, create_browser
from webgal_agent.browser.models import (
    BrowserType,
    PageState,
    ElementInfo,
    Selector,
    SelectorType,
    BrowserConfig,
    VideoConfig,
    RecordingResult,
)
from webgal_agent.browser.screencast import ScreencastRecorder
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
    "create_browser",
    "PageState",
    "ElementInfo",
    "Selector",
    "SelectorType",
    "BrowserConfig",
    "BrowserType",
    "VideoConfig",
    "RecordingResult",
    "ScreencastRecorder",
    "NavigateTool",
    "ClickTool",
    "ScreenshotTool",
    "FillTool",
    "GetTextTool",
    "WaitForTool",
]
