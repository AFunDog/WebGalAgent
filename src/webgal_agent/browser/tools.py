"""浏览器自动化工具：供智能体调用的工具封装。"""

from __future__ import annotations

import pathlib

from webgal_agent.browser.client import BrowserClient
from webgal_agent.browser.models import Selector, SelectorType
from webgal_agent.tools.base import Tool, ToolResult


class NavigateTool(Tool):
    """导航到指定 URL。

    支持 http/https 链接和相对路径。
    """

    def __init__(self, client: BrowserClient) -> None:
        self._client = client

    @property
    def name(self) -> str:
        return "navigate"

    @property
    def description(self) -> str:
        return (
            "导航到指定的 URL 页面。"
            "支持 http/https 链接。"
            "返回页面标题和当前 URL。"
        )

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "目标 URL，必须以 http:// 或 https:// 开头",
                },
                "wait_until": {
                    "type": "string",
                    "description": "等待时机：load（默认）、domcontentloaded、networkidle",
                    "enum": ["load", "domcontentloaded", "networkidle"],
                },
            },
            "required": ["url"],
        }

    async def execute(self, **kwargs: object) -> ToolResult:
        url = kwargs.get("url")
        wait_until = kwargs.get("wait_until", "load")

        if not url:
            return ToolResult(success=False, error="缺少 'url' 参数")

        try:
            state = await self._client.navigate(url, wait_until=wait_until)
            return ToolResult(
                success=True,
                output=f"已导航到 {state.url}\n标题: {state.title}",
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"导航失败: {exc}")


class ClickTool(Tool):
    """点击页面元素。"""

    def __init__(self, client: BrowserClient) -> None:
        self._client = client

    @property
    def name(self) -> str:
        return "click"

    @property
    def description(self) -> str:
        return "点击页面上的元素（按钮、链接等）。"

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS 选择器，如 #id、.class、tagname",
                },
                "selector_type": {
                    "type": "string",
                    "description": "选择器类型：css（默认）、xpath、text（按文本查找）、role（按角色查找）",
                    "enum": ["css", "xpath", "text", "role"],
                },
                "timeout": {
                    "type": "number",
                    "description": "超时时间（毫秒），默认 30000",
                },
            },
            "required": ["selector"],
        }

    async def execute(self, **kwargs: object) -> ToolResult:
        selector_str = kwargs.get("selector")
        if not selector_str:
            return ToolResult(success=False, error="缺少 'selector' 参数")

        selector_type = kwargs.get("selector_type", "css")
        timeout = kwargs.get("timeout")

        try:
            selector = Selector(
                type=SelectorType(selector_type),
                value=selector_str,
            )
            info = await self._client.click(
                selector,
                timeout=timeout if timeout is not None else None,
            )
            return ToolResult(
                success=True,
                output=f"已点击元素: <{info.tag}>{info.text[:50]}</>",
            )
        except Exception as exc:
            return ToolResult(success=False, error=f"点击失败: {exc}")


class FillTool(Tool):
    """填写表单输入框。"""

    def __init__(self, client: BrowserClient) -> None:
        self._client = client

    @property
    def name(self) -> str:
        return "fill"

    @property
    def description(self) -> str:
        return "填写表单输入框内容。"

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "输入框的 CSS 选择器",
                },
                "value": {
                    "type": "string",
                    "description": "要填写的内容",
                },
                "selector_type": {
                    "type": "string",
                    "description": "选择器类型：css（默认）、xpath、text、role",
                    "enum": ["css", "xpath", "text", "role"],
                },
            },
            "required": ["selector", "value"],
        }

    async def execute(self, **kwargs: object) -> ToolResult:
        selector_str = kwargs.get("selector")
        value = kwargs.get("value")

        if not selector_str or value is None:
            return ToolResult(success=False, error="缺少 'selector' 或 'value' 参数")

        selector_type = kwargs.get("selector_type", "css")

        try:
            selector = Selector(
                type=SelectorType(selector_type),
                value=selector_str,
            )
            await self._client.fill(selector, str(value))
            return ToolResult(success=True, output=f"已填写: {value[:50]}")
        except Exception as exc:
            return ToolResult(success=False, error=f"填写失败: {exc}")


class GetTextTool(Tool):
    """获取元素文本内容。"""

    def __init__(self, client: BrowserClient) -> None:
        self._client = client

    @property
    def name(self) -> str:
        return "get_text"

    @property
    def description(self) -> str:
        return "获取页面上元素的文本内容。"

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS 选择器",
                },
                "selector_type": {
                    "type": "string",
                    "description": "选择器类型：css（默认）、xpath、text、role",
                    "enum": ["css", "xpath", "text", "role"],
                },
                "max_length": {
                    "type": "number",
                    "description": "最大返回字符数，默认 2000",
                },
            },
            "required": ["selector"],
        }

    async def execute(self, **kwargs: object) -> ToolResult:
        selector_str = kwargs.get("selector")
        if not selector_str:
            return ToolResult(success=False, error="缺少 'selector' 参数")

        selector_type = kwargs.get("selector_type", "css")
        max_length = kwargs.get("max_length", 2000)

        try:
            selector = Selector(
                type=SelectorType(selector_type),
                value=selector_str,
            )
            text = await self._client.get_text(selector)
            truncated = text[:max_length] + ("..." if len(text) > max_length else "")
            return ToolResult(success=True, output=truncated)
        except Exception as exc:
            return ToolResult(success=False, error=f"获取文本失败: {exc}")


class ScreenshotTool(Tool):
    """页面截图。"""

    def __init__(
        self,
        client: BrowserClient,
        output_dir: str | pathlib.Path = "data/screenshots",
    ) -> None:
        self._client = client
        self._output_dir = pathlib.Path(output_dir)

    @property
    def name(self) -> str:
        return "screenshot"

    @property
    def description(self) -> str:
        return "对当前页面进行截图保存。"

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "截图文件名，如 screenshot.png",
                },
                "full_page": {
                    "type": "boolean",
                    "description": "是否截取整个页面（滚动到底部截图拼接），默认 false",
                },
            },
            "required": ["filename"],
        }

    async def execute(self, **kwargs: object) -> ToolResult:
        filename = kwargs.get("filename")
        full_page = kwargs.get("full_page", False)

        if not filename:
            return ToolResult(success=False, error="缺少 'filename' 参数")

        try:
            self._output_dir.mkdir(parents=True, exist_ok=True)
            path = str(self._output_dir / filename)
            await self._client.screenshot(path=path, full_page=full_page)
            return ToolResult(success=True, output=f"截图已保存: {path}")
        except Exception as exc:
            return ToolResult(success=False, error=f"截图失败: {exc}")


class WaitForTool(Tool):
    """等待元素出现或消失。"""

    def __init__(self, client: BrowserClient) -> None:
        self._client = client

    @property
    def name(self) -> str:
        return "wait_for"

    @property
    def description(self) -> str:
        return "等待页面元素变为可见/隐藏/存在。"

    @property
    def parameters(self) -> dict[str, object]:
        return {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS 选择器",
                },
                "selector_type": {
                    "type": "string",
                    "description": "选择器类型：css（默认）、xpath、text、role",
                    "enum": ["css", "xpath", "text", "role"],
                },
                "state": {
                    "type": "string",
                    "description": "等待状态：visible（默认）、hidden、attached、detached",
                    "enum": ["visible", "hidden", "attached", "detached"],
                },
                "timeout": {
                    "type": "number",
                    "description": "超时时间（毫秒），默认 30000",
                },
            },
            "required": ["selector"],
        }

    async def execute(self, **kwargs: object) -> ToolResult:
        selector_str = kwargs.get("selector")
        if not selector_str:
            return ToolResult(success=False, error="缺少 'selector' 参数")

        selector_type = kwargs.get("selector_type", "css")
        state = kwargs.get("state", "visible")
        timeout = kwargs.get("timeout")

        try:
            selector = Selector(
                type=SelectorType(selector_type),
                value=selector_str,
            )
            found = await self._client.wait_for(
                selector,
                state=state,
                timeout=timeout if timeout is not None else None,
            )
            if found:
                return ToolResult(success=True, output=f"元素已{state}")
            return ToolResult(success=False, error=f"等待超时，元素未变为 {state}")
        except Exception as exc:
            return ToolResult(success=False, error=f"等待失败: {exc}")
