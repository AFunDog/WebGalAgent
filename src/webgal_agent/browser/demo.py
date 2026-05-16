"""浏览器模块演示脚本。

用法：
    python -m webgal_agent.browser.demo

前置依赖：
    1. playwright install chromium（若使用默认 chromium）
    2. 系统路径中需有 ffmpeg
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# 确保 src 路径在 sys.path 中
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webgal_agent.browser import (
    BrowserClient,
    DefaultBrowserConfig,
    ScreencastRecorder,
    Selector,
    SelectorType,
)
from webgal_agent.browser.models import VideoConfig


async def demo_navigate(
    url: str,
    browser_type: str = "chromium",
    headless: bool = False,
    width: int = 1920,
    height: int = 1080,
) -> None:
    """演示：导航并截图。"""
    config = DefaultBrowserConfig(
        browser_type=browser_type,
        headless=headless,
        viewport_width=width,
        viewport_height=height,
        channel="msedge" if browser_type == "msedge" else None,
    )

    async with BrowserClient(config) as client:
        print("拦截脚本注入 (index-e1b3c40e.js)...")
        await client.add_script_injection(
            url_pattern="**/index-e1b3c40e.js",
            inject_code="window.changeScene = gCe;\nwindow.toggleAuto = wU;",
        )

        print(f"正在使用 {browser_type} 导航到: {url}")
        state = await client.navigate(url)
        print(f"页面标题: {state.title}")
        print(f"当前 URL: {state.url}")

        screenshot_path = Path("data/temp/demo.png")
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        await client.screenshot(path=str(screenshot_path), full_page=False)
        print(f"截图已保存: {screenshot_path}")

        await asyncio.sleep(2)


async def demo_record(
    url: str,
    output_path: str,
    duration: float = 5.0,
    fps: float = 60.0,
    width: int = 1920,
    height: int = 1080,
    selector: str = "auto",
    browser_type: str = "msedge",
    headless: bool = False,
    screencast_quality: int = 90,
    no_record: bool = False,
) -> None:
    """演示：使用 CDP Screencast 从 compositor 直接拉帧 + ffmpeg 编码。"""
    config = DefaultBrowserConfig(
        browser_type=browser_type,
        headless=headless,
        viewport_width=width,
        viewport_height=height,
        channel="msedge" if browser_type == "msedge" else None,
    )

    video_cfg = VideoConfig(
        output_path=output_path,
        fps=fps,
    )

    async with BrowserClient(config) as client:
        await client.new_context(context_id="default")

        print("拦截脚本注入 (index-e1b3c40e.js)...")
        await client.add_script_injection(
            url_pattern="**/index-e1b3c40e.js",
            inject_code="window.changeScene = gCe;\nwindow.toggleAuto = wU;",
        )

        print(f"正在使用 {browser_type} 导航到: {url}")
        try:
            await client.navigate(url, wait_until="load")
        except Exception as e:
            print(f"导航超时，继续等待页面加载... ({e})")
            await asyncio.sleep(5)

        # 等待 changeScene 函数就绪并调用
        print("等待 changeScene 函数就绪...")
        page = await client.get_page()
        try:
            await page.wait_for_function(
                "() => typeof window.changeScene === 'function' && typeof window.toggleAuto === 'function'",
                timeout=10000,
            )
            print("changeScene 已就绪，调用...")
            await page.evaluate("""
                async () => {
                    window.changeScene("发布/AI剧场/爱素补作业/15/Scene1.txt", 1);
                    await new Promise(r => setTimeout(r, 500));
                    window.toggleAuto();
                }
            """)
            print("changeScene 调用完成")
        except Exception as e:
            print(f"警告: changeScene 调用失败: {e}")

        # 等待目标元素可见（确认页面已渲染）
        if selector == "auto":
            for candidate in ("#root", "canvas"):
                found = await client.wait_for(
                    Selector(value=candidate, type=SelectorType.CSS),
                    state="visible",
                    timeout=3000,
                )
                if found:
                    print(f"目标元素已就绪: {candidate}")
                    break
            else:
                print("警告: 未找到 #root 或 canvas 元素，继续录制整个页面")
        else:
            print(f"等待目标元素出现: {selector}")
            found = await client.wait_for(
                Selector(value=selector, type=SelectorType.CSS),
                state="visible",
                timeout=10000,
            )
            if not found:
                print(f"错误: 未找到目标元素 {selector}")
                return

        await asyncio.sleep(1)

        if no_record:
            print(f"跳过录制，等待 {duration}s 观察页面状态...")
            await asyncio.sleep(duration)
            print("观察完成!")
            return

        print(f"开始录制 {duration}s @ {fps} FPS (CDP Screencast)...")
        print(f"输出: {output_path}")

        recorder = ScreencastRecorder(
            client, video_cfg, screencast_quality=screencast_quality
        )
        result = await recorder.start(duration=duration)

        print("录制完成!")
        print(f"  输出路径: {result.output_path}")
        print(f"  源帧率: {result.source_fps:.1f} FPS → 输出帧率: {result.output_fps:.1f} FPS")
        print(f"  总帧数: {result.total_frames}")
        print(f"  时长: {result.duration:.1f}s")
        print(f"  文件大小: {result.file_size_mb:.2f} MB")


def main() -> None:
    parser = argparse.ArgumentParser(description="浏览器模块演示")
    parser.add_argument(
        "mode",
        choices=["navigate", "record"],
        help="运行模式: navigate=导航截图, record=录制视频",
    )
    parser.add_argument("--url", default="https://example.com", help="目标 URL")
    parser.add_argument("--output", default="data/temp/output.mp4", help="输出路径")
    parser.add_argument("--duration", type=float, default=5.0, help="录制时长（秒）")
    parser.add_argument("--fps", type=float, default=60.0, help="输出帧率（ffmpeg 转换）")
    parser.add_argument("--width", type=int, default=1920, help="录制分辨率宽度")
    parser.add_argument("--height", type=int, default=1080, help="录制分辨率高度")
    parser.add_argument(
        "--selector", default="auto",
        help="等待的目标元素 CSS 选择器；auto 会优先尝试 #root，再回退到 canvas",
    )
    parser.add_argument(
        "--browser",
        default="msedge",
        choices=["chromium", "firefox", "webkit", "msedge"],
        help="浏览器类型",
    )
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--no-record", action="store_true", help="不录制，仅等待 duration 时间观察页面")
    parser.add_argument("--screencast-quality", type=int, default=90, help="Screencast JPEG 质量 (0-100)")
    parser.add_argument(
        "--executable",
        default=None,
        help="浏览器可执行文件路径（如 chrome-headless-shell 路径）",
    )

    args = parser.parse_args()

    match args.mode:
        case "navigate":
            asyncio.run(
                demo_navigate(
                    url=args.url,
                    browser_type=args.browser,
                    headless=args.headless,
                    width=args.width,
                    height=args.height,
                )
            )
        case "record":
            asyncio.run(
                demo_record(
                    url=args.url,
                    output_path=args.output,
                    duration=args.duration,
                    fps=args.fps,
                    width=args.width,
                    height=args.height,
                    selector=args.selector,
                    browser_type=args.browser,
                    headless=args.headless,
                    screencast_quality=args.screencast_quality,
                    no_record=args.no_record,
                )
            )


if __name__ == "__main__":
    main()
