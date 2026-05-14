"""Playwright 浏览器客户端封装。"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from playwright.async_api import (
    async_playwright,
    Browser as PlaywrightBrowser,
    BrowserContext,
    Page,
    ElementHandle,
    TimeoutError as PlaywrightTimeout,
)

from webgal_agent.browser.models import BrowserConfig, PageState, ElementInfo, Selector


@dataclass
class BrowserInstance:
    """单个浏览器实例。"""

    browser: PlaywrightBrowser
    context: BrowserContext
    page: Page


@dataclass
class DefaultBrowserConfig:
    """浏览器默认配置。"""

    headless: bool = True
    timeout: int = 30000
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: str | None = None
    ignore_https_errors: bool = True


class BrowserClient:
    """Playwright 浏览器客户端。

    提供浏览器生命周期管理和页面操作接口。
    """

    def __init__(self, config: DefaultBrowserConfig | None = None) -> None:
        self._config = config or DefaultBrowserConfig()
        self._playwright = None
        self._instances: dict[str, BrowserInstance] = {}

    async def __aenter__(self) -> "BrowserClient":
        """异步上下文管理器入口。"""
        self._playwright = await async_playwright().start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器出口，自动关闭浏览器。"""
        await self.close_all()
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def new_context(
        self,
        context_id: str = "default",
        config: BrowserConfig | None = None,
    ) -> BrowserContext:
        """创建新的浏览器上下文。"""
        if not self._playwright:
            raise RuntimeError("BrowserClient 未初始化，请使用 async with 上下文管理器")

        browser = await self._playwright.chromium.launch(
            headless=self._config.headless,
        )

        context_config = config or BrowserConfig()
        context = await browser.new_context(
            viewport={"width": context_config.viewport_width, "height": context_config.viewport_height},
            user_agent=self._config.user_agent,
            ignore_https_errors=self._config.ignore_https_errors,
        )

        page = await context.new_page()
        self._instances[context_id] = BrowserInstance(
            browser=browser,
            context=context,
            page=page,
        )

        return context

    async def get_page(self, context_id: str = "default") -> Page:
        """获取指定上下文的页面。"""
        if context_id not in self._instances:
            await self.new_context(context_id)
        return self._instances[context_id].page

    async def navigate(
        self,
        url: str,
        context_id: str = "default",
        wait_until: str = "load",
    ) -> PageState:
        """导航到指定 URL。"""
        page = await self.get_page(context_id)
        await page.goto(url, wait_until=wait_until, timeout=self._config.timeout)
        return await self.get_page_state(context_id)

    async def get_page_state(self, context_id: str = "default") -> PageState:
        """获取当前页面状态。"""
        page = await self.get_page(context_id)
        return PageState(
            url=page.url,
            title=await page.title(),
            visible=await page.is_visible(),
        )

    async def click(
        self,
        selector: Selector,
        context_id: str = "default",
        timeout: int | None = None,
    ) -> ElementInfo:
        """点击元素。"""
        page = await self.get_page(context_id)
        element = await self._locate(selector, page, timeout)
        await element.click(timeout=timeout or self._config.timeout)
        return await self._get_element_info(element)

    async def fill(
        self,
        selector: Selector,
        value: str,
        context_id: str = "default",
        timeout: int | None = None,
    ) -> None:
        """填充输入框。"""
        page = await self.get_page(context_id)
        element = await self._locate(selector, page, timeout)
        await element.fill(value, timeout=timeout or self._config.timeout)

    async def get_text(
        self,
        selector: Selector,
        context_id: str = "default",
        timeout: int | None = None,
    ) -> str:
        """获取元素文本内容。"""
        page = await self.get_page(context_id)
        element = await self._locate(selector, page, timeout)
        return await element.inner_text() or ""

    async def screenshot(
        self,
        context_id: str = "default",
        path: str | None = None,
        full_page: bool = False,
    ) -> bytes | str:
        """截图。"""
        page = await self.get_page(context_id)
        if path:
            await page.screenshot(path=path, full_page=full_page)
            return path
        return await page.screenshot(full_page=full_page)

    async def wait_for(
        self,
        selector: Selector,
        context_id: str = "default",
        timeout: int | None = None,
        state: str = "visible",
    ) -> bool:
        """等待元素状态。"""
        page = await self.get_page(context_id)
        locator = self._build_locator(selector, page)
        try:
            await locator.wait_for(state=state, timeout=timeout or self._config.timeout)
            return True
        except PlaywrightTimeout:
            return False

    async def close_context(self, context_id: str = "default") -> None:
        """关闭指定上下文。"""
        if context_id in self._instances:
            instance = self._instances.pop(context_id)
            await instance.context.close()
            await instance.browser.close()

    async def close_all(self) -> None:
        """关闭所有浏览器实例。"""
        for context_id in list(self._instances.keys()):
            await self.close_context(context_id)

    async def _locate(
        self,
        selector: Selector,
        page: Page,
        timeout: int | None = None,
    ) -> ElementHandle:
        """根据选择器定位元素。"""
        locator = self._build_locator(selector, page)
        return await locator.wait_for(timeout=timeout or self._config.timeout)

    def _build_locator(self, selector: Selector, page: Page):
        """构建 Playwright Locator。"""
        match selector.type:
            case SelectorType.CSS:
                return page.locator(selector.value)
            case SelectorType.XPATH:
                return page.locator(f"xpath={selector.value}")
            case SelectorType.TEXT:
                return page.get_by_text(selector.value)
            case SelectorType.ROLE:
                return page.get_by_role(selector.value)
            case _:
                return page.locator(selector.value)

    async def _get_element_info(self, element: ElementHandle) -> ElementInfo:
        """获取元素信息。"""
        tag = await element.evaluate("el => el.tagName.toLowerCase()")
        text = await element.inner_text() or ""
        bbox = await element.bounding_box()
        is_visible = await element.is_visible()
        is_enabled = await element.is_enabled()

        attributes = await element.evaluate(
            """el => {
                const attrs = {};
                for (const attr of el.attributes) {
                    attrs[attr.name] = attr.value;
                }
                return attrs;
            }"""
        )

        return ElementInfo(
            tag=tag,
            text=text,
            is_visible=is_visible,
            is_enabled=is_enabled,
            bounding_box={"x": bbox.x, "y": bbox.y, "width": bbox.width, "height": bbox.height} if bbox else None,
            attributes=attributes,
        )


# 便捷的上下文管理器
@asynccontextmanager
async def create_browser(config: DefaultBrowserConfig | None = None):
    """创建浏览器客户端的便捷函数。"""
    client = BrowserClient(config)
    async with client:
        yield client
