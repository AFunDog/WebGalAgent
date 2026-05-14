"""Playwright 浏览器客户端封装。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncIterator

from playwright.async_api import (
    async_playwright,
    Browser as PlaywrightBrowser,
    BrowserContext,
    ElementHandle,
    Page,
    Route,
    TimeoutError as PlaywrightTimeout,
)

from webgal_agent.browser.models import BrowserConfig, PageState, ElementInfo, Selector, SelectorType


async def create_browser(
    browser_type: str = "chromium",
    headless: bool = True,
    viewport_width: int = 1920,
    viewport_height: int = 1080,
) -> BrowserClient:
    """创建浏览器客户端的快捷函数。"""
    config = DefaultBrowserConfig(
        browser_type=browser_type,
        headless=headless,
        viewport_width=viewport_width,
        viewport_height=viewport_height,
    )
    client = BrowserClient(config)
    await client.__aenter__()
    return client

# Hook 脚本：控制虚拟时间，实现逐帧确定性渲染
_TIME_CONTROL_SOURCE = """
(() => {
    if (window.__timeControlReady) {
        return;
    }

    let currentTime = 0;
    let rafId = 0;
    const rafQueue = new Map();

    const originalPerformanceNow = performance.now.bind(performance);
    const originalDateNow = Date.now.bind(Date);
    const originalRequestAnimationFrame = window.requestAnimationFrame.bind(window);
    const originalCancelAnimationFrame = window.cancelAnimationFrame.bind(window);

    const getFrameTime = () => 1000 / (window.__targetFPS || 30);

    performance.now = () => currentTime;
    Date.now = () => Math.floor(currentTime);

    window.requestAnimationFrame = (callback) => {
        rafId += 1;
        rafQueue.set(rafId, callback);
        return rafId;
    };

    window.cancelAnimationFrame = (id) => {
        rafQueue.delete(id);
    };

    window.__advanceFrame = async (frameCount = 1) => {
        const steps = Math.max(1, Number(frameCount) || 1);

        for (let i = 0; i < steps; i += 1) {
            currentTime += getFrameTime();

            const callbacks = Array.from(rafQueue.values());
            rafQueue.clear();

            for (const callback of callbacks) {
                try {
                    callback(currentTime);
                } catch (error) {
                    console.error("requestAnimationFrame callback failed", error);
                }
            }

            await Promise.resolve();
        }
    };

    window.__disableTimeControl = () => {
        performance.now = originalPerformanceNow;
        Date.now = originalDateNow;
        window.requestAnimationFrame = originalRequestAnimationFrame;
        window.cancelAnimationFrame = originalCancelAnimationFrame;
        rafQueue.clear();
        window.__timeControlReady = false;
    };

    window.__timeControlReady = true;
})();
"""

_TIME_CONTROL_SCRIPT = f"() => {{ {_TIME_CONTROL_SOURCE} }}"


@dataclass
class BrowserInstance:
    """单个浏览器实例。"""

    browser: PlaywrightBrowser
    context: BrowserContext
    page: Page


@dataclass
class DefaultBrowserConfig:
    """浏览器默认配置。"""

    browser_type: str = "chromium"
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
        self._time_control_prepared: set[str] = set()

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

        channel = "msedge" if self._config.browser_type == "msedge" else None
        browser_engine = getattr(self._playwright, "chromium")
        browser = await browser_engine.launch(
            headless=self._config.headless,
            channel=channel,
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

    # ---- 脚本拦截注入 ----

    async def add_script_injection(
        self,
        url_pattern: str,
        inject_code: str,
        context_id: str = "default",
    ) -> None:
        """为指定 URL 模式的资源添加注入代码。

        在页面加载前调用，拦截匹配的 JS 文件并在末尾注入自定义代码。
        支持通配符，如 `**/index-e1b3c40e.js`。

        Args:
            url_pattern: URL 匹配模式（支持 glob，如 `**/*.js` 或部分路径）
            inject_code: 要追加到文件末尾的 JavaScript 代码
            context_id: 目标上下文 ID
        """
        if context_id not in self._instances:
            await self.new_context(context_id)

        page = await self.get_page(context_id)

        async def handle_route(route: Route) -> None:
            try:
                response = await route.fetch()
                original_body = await response.body()
                content_type = response.headers.get("content-type", "")

                # 追加注入代码
                modified_body = original_body + f"\n/* injected */\n{inject_code}\n/* end inject */\n".encode("utf-8")

                await route.fulfill(
                    status=response.status,
                    content_type=content_type,
                    body=modified_body,
                )
            except Exception as e:
                # 如果拦截失败，放行原始请求
                print(f"警告: 脚本注入失败 ({url_pattern}): {e}")
                await route.continue_()

        await page.route(url_pattern, handle_route)

    # --------------------

    async def get_page(self, context_id: str = "default") -> Page:
        """获取指定上下文的页面。"""
        if context_id not in self._instances:
            await self.new_context(context_id)
        return self._instances[context_id].page

    async def navigate(
        self,
        url: str,
        context_id: str = "default",
        wait_until: str = "domcontentloaded",
    ) -> PageState:
        """导航到指定 URL。"""
        page = await self.get_page(context_id)
        await page.goto(url, wait_until=wait_until, timeout=self._config.timeout)
        return await self.get_page_state(context_id)

    # ---- 时间控制 ----

    async def enable_time_control(self, fps: float = 30.0) -> bool:
        """为当前页面启用虚拟时间控制。若要完全确定性，请在导航前先 prepare_time_control。"""
        page = await self.get_page()

        # 先注入时间控制脚本
        await page.evaluate(_TIME_CONTROL_SCRIPT)

        # 设置 FPS（通过 evaluate 参数传递，不走 f-string 插值）
        await page.evaluate(
            "(f) => { window.__targetFPS = f; }",
            fps,
        )

        # 验证注入是否成功
        result = await page.evaluate(
            "() => typeof window.__advanceFrame"
        )
        if result != "function":
            raise RuntimeError(
                f"时间控制脚本注入失败: __advanceFrame type={result}。"
                "页面可能不支持或被重写了 window 对象。"
            )
        return True

    async def prepare_time_control(
        self,
        fps: float = 30.0,
        context_id: str = "default",
    ) -> bool:
        """为上下文预装时间控制脚本，确保后续导航在页面脚本执行前接管 RAF。"""
        if context_id not in self._instances:
            await self.new_context(context_id)

        instance = self._instances[context_id]
        if context_id not in self._time_control_prepared:
            await instance.context.add_init_script(script=_TIME_CONTROL_SOURCE)
            self._time_control_prepared.add(context_id)

        await instance.context.add_init_script(
            script=f"window.__targetFPS = {float(fps)!r};"
        )
        return await self.enable_time_control(fps=fps)

    async def advance_frame(self, frame_count: int = 1) -> None:
        """推进虚拟时间（逐帧控制，无真实等待）。必须在 enable_time_control 后调用。"""
        page = await self.get_page()
        await page.evaluate("(count) => window.__advanceFrame(count)", frame_count)

    async def disable_time_control(self) -> None:
        """停止时间控制，恢复原生时间函数。"""
        page = await self.get_page()
        await page.evaluate("() => window.__disableTimeControl && window.__disableTimeControl()")

    async def verify_time_control(
        self,
        fps: float = 30.0,
        frames: int = 3,
        context_id: str = "default",
    ) -> bool:
        """验证 RAF hook 与逐帧推进是否按预期生效。"""
        await self.enable_time_control(fps=fps)
        page = await self.get_page(context_id)
        result = await page.evaluate(
            """async ({ fps, frames }) => {
                const frameTime = 1000 / fps;
                const seen = [];

                function step(ts) {
                    seen.push(ts);
                    if (seen.length < frames) {
                        requestAnimationFrame(step);
                    }
                }

                requestAnimationFrame(step);
                await window.__advanceFrame(frames);

                const expected = Array.from(
                    { length: frames },
                    (_, index) => frameTime * (index + 1),
                );

                return (
                    seen.length === frames &&
                    seen.every((value, index) => Math.abs(value - expected[index]) < 0.001)
                );
            }""",
            {"fps": fps, "frames": frames},
        )
        return bool(result)

    # --------------------

    async def get_page_state(self, context_id: str = "default") -> PageState:
        """获取当前页面状态。"""
        page = await self.get_page(context_id)
        return PageState(
            url=page.url,
            title=await page.title(),
            visible=True,
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
        """填写表单。"""
        page = await self.get_page(context_id)
        element = await self._locate(selector, page, timeout)
        await element.fill(value, timeout=timeout or self._config.timeout)

    async def get_text(
        self,
        selector: Selector,
        context_id: str = "default",
        timeout: int | None = None,
    ) -> str:
        """获取元素文本。"""
        page = await self.get_page(context_id)
        element = await self._locate(selector, page, timeout)
        return await element.inner_text() or ""

    async def screenshot(
        self,
        path: str,
        context_id: str = "default",
        full_page: bool = False,
    ) -> bytes:
        """页面截图。"""
        page = await self.get_page(context_id)
        return await page.screenshot(path=path, full_page=full_page)

    async def wait_for(
        self,
        selector: Selector,
        state: str = "visible",
        timeout: int = 10000,
        context_id: str = "default",
    ) -> bool:
        """等待元素出现或消失。"""
        page = await self.get_page(context_id)
        element = await self._locate(selector, page, timeout)
        try:
            if state == "visible":
                await element.wait_for(state="visible", timeout=timeout)
            elif state == "hidden":
                await element.wait_for(state="hidden", timeout=timeout)
            elif state == "attached":
                await element.wait_for(state="attached", timeout=timeout)
            elif state == "detached":
                await element.wait_for(state="detached", timeout=timeout)
            return True
        except PlaywrightTimeout:
            return False

    async def close_all(self) -> None:
        """关闭所有浏览器实例。"""
        for instance in self._instances.values():
            await instance.context.close()
        self._instances.clear()

    async def _locate(
        self,
        selector: Selector,
        page: Page,
        timeout: int | None = None,
    ) -> ElementHandle:
        """根据类型定位元素。"""
        if selector.type == SelectorType.CSS:
            return page.locator("css=" + selector.value).first
        elif selector.type == SelectorType.XPATH:
            return page.locator("xpath=" + selector.value).first
        elif selector.type == SelectorType.TEXT:
            return page.get_by_text(selector.value).first
        elif selector.type == SelectorType.ROLE:
            return page.get_by_role(selector.value).first
        return page.locator(selector.value).first

    @staticmethod
    async def _get_element_info(element: ElementHandle) -> ElementInfo:
        """获取元素信息。"""
        tag = await element.evaluate("el => el.tagName") or ""
        text = await element.inner_text() or ""
        bbox = await element.bounding_box()
        attrs: dict = {}
        try:
            attrs = await element.evaluate("el => Object.fromEntries(Array.from(el.attributes).map(a => [a.name, a.value]))") or {}
        except Exception:
            pass
        return ElementInfo(
            tag=tag,
            text=text,
            is_visible=await element.is_visible(),
            is_enabled=await element.is_enabled(),
            bounding_box=bbox or None,
            attributes=attrs,
        )
