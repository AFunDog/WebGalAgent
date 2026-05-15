"""浏览器模块演示脚本。

用法：
    python -m webgal_agent.browser.demo

前置依赖：
    1. playwright install chromium（若使用默认 chromium）
    2. 系统路径中需有 ffmpeg
    3. 若使用 chrome-headless-shell，需通过 --executable 指定路径
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
    VideoRecorder,
    Selector,
    SelectorType,
)
from webgal_agent.browser.models import CaptureConfig, VideoConfig


async def demo_navigate(
    url: str,
    browser_type: str = "chromium",
    headless: bool = False,
    executable_path: str | None = None,
) -> None:
    """演示：导航并截图。"""
    config = DefaultBrowserConfig(
        browser_type=browser_type,
        headless=headless,
        viewport_width=1280,
        viewport_height=720,
        executable_path=executable_path,
    )

    async with BrowserClient(config) as client:
        # 拦截 index-e1b3c40e.js 并注入
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
    fps: float = 30.0,
    canvas_selector: str = "div._MainStage_main_9enex_1",
    browser_type: str = "chromium",
    headless: bool = False,
    no_record: bool = False,
    executable_path: str | None = None,
) -> None:
    """演示：使用 CDP 虚拟时间 + FFmpeg 逐帧确定性录制。"""
    config = DefaultBrowserConfig(
        browser_type=browser_type,
        headless=headless,
        viewport_width=1280,
        viewport_height=720,
        executable_path=executable_path,
    )

    async with BrowserClient(config) as client:
        # 拦截 index-e1b3c40e.js 并注入
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
                    await new Promise(r => setTimeout(r, 1000));
                    window.toggleAuto();
                }
            """)
            print("changeScene 调用完成")
        except Exception as e:
            print(f"警告: changeScene 调用失败: {e}")

        selected_selector = canvas_selector
        if canvas_selector == "auto":
            for candidate in ("div._MainStage_main_9enex_1", "#root", "canvas"):
                found = await client.wait_for(
                    Selector(value=candidate, type=SelectorType.CSS),
                    state="visible",
                    timeout=3000,
                )
                if found:
                    selected_selector = candidate
                    break
            else:
                print("错误: 未找到可录制目标（已尝试 div._MainStage_main_9enex_1, #root, canvas）")
                return
        else:
            print(f"等待目标元素出现: {canvas_selector}")
            found = await client.wait_for(
                Selector(value=canvas_selector, type=SelectorType.CSS),
                state="visible",
                timeout=10000,
            )
            if not found:
                print(f"错误: 未找到目标元素 {canvas_selector}")
                return

        print(f"录制目标元素: {selected_selector}")

        # 等待目标元素内部渲染初始化
        await asyncio.sleep(1)

        if no_record:
            print(f"跳过录制，等待 {duration}s 观察页面状态...")
            await asyncio.sleep(duration)
            print("观察完成!")
            return

        # 创建 CDP Session
        print("创建 CDP Session...")
        cdp = await client.create_cdp_session()

        # 配置录制
        capture_cfg = CaptureConfig(
            fps=fps,
            canvas_selector=selected_selector,
            max_duration=duration,
        )
        video_cfg = VideoConfig(
            output_path=output_path,
            fps=fps,
            codec="libx264",
        )

        total_frames = max(1, int(round(duration * fps)))
        print(f"开始录制 {duration}s @ {fps} FPS (CDP + FFmpeg 模式)...")
        print(f"输出: {output_path}")
        print(f"总帧数: {total_frames}")

        recorder = VideoRecorder(cdp, page, video_cfg, capture_cfg)
        result = await recorder.start()

        print("录制完成!")
        print(f"  输出路径: {result.output_path}")
        print(f"  总帧数: {result.total_frames}")
        print(f"  实际帧率: {result.actual_fps:.1f} FPS")
        print(f"  视频时长: {result.duration:.1f}s")
        print(f"  实际录制时间: {result.wall_time:.2f}s")
        if result.wall_time > 0:
            print(f"  时间比: {result.duration / result.wall_time:.2f}x")
        print(f"  文件大小: {result.file_size_mb:.2f} MB")


def main() -> None:
    parser = argparse.ArgumentParser(description="浏览器模块演示")
    parser.add_argument(
        "mode",
        choices=["navigate", "record"],
        help="运行模式: navigate=导航截图, record=录制视频",
    )
    parser.add_argument("--url", default="https://example.com", help="目标 URL")
    parser.add_argument("--output", default="data/temp/output.mp4", help="输出路径 (默认 .mp4)")
    parser.add_argument("--duration", type=float, default=5.0, help="录制时长（秒）")
    parser.add_argument("--fps", type=float, default=30.0, help="帧率")
    parser.add_argument("--selector", default="div._MainStage_main_9enex_1", help="录制目标元素 CSS 选择器")
    parser.add_argument("--canvas", dest="selector_legacy", default=None, help="兼容旧参数：等同于 --selector")
    parser.add_argument(
        "--browser",
        default="chromium",
        choices=["chromium", "firefox", "webkit"],
        help="浏览器类型",
    )
    parser.add_argument(
        "--executable",
        default=None,
        help="浏览器可执行文件路径（如 chrome-headless-shell 路径）",
    )
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--no-record", action="store_true", help="不录制，仅等待 duration 时间观察页面")

    args = parser.parse_args()

    match args.mode:
        case "navigate":
            asyncio.run(demo_navigate(args.url, args.browser, args.headless, args.executable))
        case "record":
            asyncio.run(
                demo_record(
                    url=args.url,
                    output_path=args.output,
                    duration=args.duration,
                    fps=args.fps,
                    canvas_selector=args.selector_legacy or args.selector,
                    browser_type=args.browser,
                    headless=args.headless,
                    no_record=args.no_record,
                    executable_path=args.executable,
                )
            )


if __name__ == "__main__":
    main()
