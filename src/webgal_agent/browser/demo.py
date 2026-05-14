"""浏览器模块演示脚本。

用法：
    python -m webgal_agent.browser.demo

前置依赖：
    playwright install msedge
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
    browser_type: str = "msedge",
    headless: bool = False,
) -> None:
    """演示：导航并截图。"""
    config = DefaultBrowserConfig(
        browser_type=browser_type,
        headless=headless,
        viewport_width=1280,
        viewport_height=720,
    )

    async with BrowserClient(config) as client:
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
    canvas_selector: str = "canvas",
    browser_type: str = "msedge",
    codec: str = "XVID",
    headless: bool = False,
) -> None:
    """演示：录制画布视频（时间控制模式）。"""
    config = DefaultBrowserConfig(
        browser_type=browser_type,
        headless=headless,
        viewport_width=1280,
        viewport_height=720,
    )

    async with BrowserClient(config) as client:
        print(f"正在使用 {browser_type} 导航到: {url}")
        try:
            await client.navigate(url, wait_until="domcontentloaded")
        except Exception as e:
            print(f"导航超时，继续等待页面加载... ({e})")
            await asyncio.sleep(5)

        print("等待 canvas 元素出现...")
        found = await client.wait_for(
            Selector(value=canvas_selector, type=SelectorType.CSS),
            state="visible",
            timeout=10000,
        )
        if not found:
            print("错误: 未找到 canvas 元素")
            return

        # 等待画布初始化
        await asyncio.sleep(1)

        # 启用虚拟时间控制
        print(f"启用时间控制 ({fps} FPS)...")
        ok = await client.enable_time_control(fps=fps)
        print(f"注入验证: {ok}")

        # 配置录制
        capture_cfg = CaptureConfig(
            fps=fps,
            canvas_selector=canvas_selector,
            max_duration=duration,
        )
        video_cfg = VideoConfig(
            output_path=output_path,
            fps=fps,
            codec=codec,
        )

        print(f"开始录制 {duration}s @ {fps} FPS (时间控制模式)...")
        print(f"输出: {output_path}")

        page = await client.get_page()
        recorder = VideoRecorder(
            page,
            video_cfg,
            capture_cfg,
            enable_time_control=True,
            advance_frame_fn=client.advance_frame,
        )
        result = await recorder.start()

        # 恢复原生时间
        await client.disable_time_control()

        print("录制完成!")
        print(f"  输出路径: {result.output_path}")
        print(f"  总帧数: {result.total_frames}")
        print(f"  实际帧率: {result.actual_fps:.1f} FPS")
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
    parser.add_argument("--output", default="data/temp/output.avi", help="输出路径 (XVID 建议用 .avi 扩展名)")
    parser.add_argument("--duration", type=float, default=5.0, help="录制时长（秒）")
    parser.add_argument("--fps", type=float, default=30.0, help="帧率")
    parser.add_argument("--canvas", default="canvas", help="Canvas 选择器")
    parser.add_argument(
        "--browser",
        default="msedge",
        choices=["chromium", "firefox", "webkit", "msedge"],
        help="浏览器类型",
    )
    parser.add_argument(
        "--codec",
        default="XVID",
        choices=["XVID", "MJPG", "mp4v", "avc1"],
        help="视频编码器 (XVID 最稳定，mp4v/avc1 大尺寸可能失败)",
    )
    parser.add_argument("--headless", action="store_true", help="无头模式")

    args = parser.parse_args()

    match args.mode:
        case "navigate":
            asyncio.run(demo_navigate(args.url, args.browser, args.headless))
        case "record":
            asyncio.run(
                demo_record(
                    url=args.url,
                    output_path=args.output,
                    duration=args.duration,
                    fps=args.fps,
                    canvas_selector=args.canvas,
                    browser_type=args.browser,
                    codec=args.codec,
                    headless=args.headless,
                )
            )


if __name__ == "__main__":
    main()
