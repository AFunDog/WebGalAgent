"""浏览器模块测试。"""

from __future__ import annotations

import pytest
import asyncio

from webgal_agent.browser import (
    BrowserClient,
    DefaultBrowserConfig,
    BrowserConfig,
    Selector,
    SelectorType,
    CaptureConfig,
    VideoConfig,
)
from webgal_agent.browser.capture import CanvasCapture
from webgal_agent.browser.recorder import VideoRecorder


@pytest.fixture
def browser_config() -> DefaultBrowserConfig:
    """无头浏览器配置。"""
    return DefaultBrowserConfig(headless=True, viewport_width=1280, viewport_height=720)


@pytest.fixture
async def browser(browser_config: DefaultBrowserConfig) -> BrowserClient:
    """浏览器客户端 fixture。"""
    client = BrowserClient(browser_config)
    await client.new_context("test")
    yield client
    await client.close_context("test")


class TestBrowserClient:
    """浏览器客户端测试。"""

    async def test_navigate(self, browser: BrowserClient) -> None:
        """测试页面导航。"""
        state = await browser.navigate("https://example.com")
        assert "example" in state.title.lower()
        assert "example.com" in state.url

    async def test_navigate_and_get_title(self, browser: BrowserClient) -> None:
        """测试导航后获取页面标题。"""
        state = await browser.navigate("https://example.com", wait_until="domcontentloaded")
        assert state.title == "Example Domain"

    async def test_click_link(self, browser: BrowserClient) -> None:
        """测试点击链接。"""
        await browser.navigate("https://example.com")
        selector = Selector(type=SelectorType.CSS, value="a")
        info = await browser.click(selector, timeout=5000)
        assert info.tag in ("a", "link")

    async def test_get_text(self, browser: BrowserClient) -> None:
        """测试获取文本。"""
        await browser.navigate("https://example.com")
        selector = Selector(type=SelectorType.CSS, value="h1")
        text = await browser.get_text(selector)
        assert "example" in text.lower()

    async def test_wait_for_element(self, browser: BrowserClient) -> None:
        """测试等待元素。"""
        await browser.navigate("https://example.com")
        selector = Selector(type=SelectorType.CSS, value="body")
        found = await browser.wait_for(selector, state="visible", timeout=5000)
        assert found is True


class TestCanvasCapture:
    """Canvas 捕获测试（需要真实页面）。"""

    async def test_capture_frame_structure(self) -> None:
        """测试帧数据结构。"""
        config = CaptureConfig(fps=1, canvas_selector="canvas")
        assert config.fps == 1.0
        assert config.canvas_selector == "canvas"


class TestVideoConfig:
    """视频配置测试。"""

    def test_video_config_defaults(self) -> None:
        """测试视频配置默认值。"""
        config = VideoConfig(output_path="test.mp4")
        assert config.fps == 30.0
        assert config.codec == "webm"
        assert config.quality == 23
