"""浏览器录制 CLI 工具。

用法：
    python -m webgal_agent.browser.demo record --url ... --output ... [--json]

前置依赖：
    1. playwright install chromium（若使用默认 chromium）
    2. 系统路径中需有 ffmpeg

--json 模式：
    所有日志输出到 stderr，最终结果以 JSON 行输出到 stdout，供父进程解析。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Windows: 必须在 import playwright 前设置 ProactorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

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


def _log(msg: str, *, json_mode: bool = False) -> None:
    """json 模式下日志输出到 stderr，避免污染 stdout 的 JSON 结果。"""
    if json_mode:
        print(msg, file=sys.stderr)
    else:
        print(msg)


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
    scene_path: str = "index.txt",
    stop_condition: str | None = None,
    browser_type: str = "msedge",
    headless: bool = False,
    screencast_quality: int = 90,
    no_record: bool = False,
    save_frames: str | None = None,
    format: str = "jpeg",
    record_audio: bool = False,
    json_mode: bool = False,
) -> dict | None:
    """CDP Screencast 录制。json_mode=True 时返回结果 dict 而非直接打印。"""
    launch_args = None
    if record_audio:
        launch_args = ["--autoplay-policy=no-user-gesture-required"]

    config = DefaultBrowserConfig(
        browser_type=browser_type,
        headless=headless,
        viewport_width=width,
        viewport_height=height,
        channel="msedge" if browser_type == "msedge" else None,
        launch_args=launch_args,
    )

    video_cfg = VideoConfig(
        output_path=output_path,
        fps=fps,
    )

    async with BrowserClient(config) as client:
        await client.new_context(context_id="default")

        if record_audio:
            _log("注入 WebAudio 全局捕获 (masterGain 方案)...", json_mode=json_mode)
            await client.prepare_webaudio_capture()

        _log("拦截脚本注入 (index-e1b3c40e.js)...", json_mode=json_mode)
        await client.add_script_injection(
            url_pattern="**/index-e1b3c40e.js",
            inject_code="""
            window.changeScene = gCe;
            window.toggleAuto = wU;
            window.__webgal = L;
            window.hideInfo = () => {
                const el = document.querySelector(`.${ke.main}`);
                el.style.visibility = 'hidden';
            };

            """,
        )

        _log(f"正在使用 {browser_type} 导航到: {url}", json_mode=json_mode)
        try:
            await client.navigate(url, wait_until="load")
        except Exception as e:
            _log(f"导航超时，继续等待页面加载... ({e})", json_mode=json_mode)
            await asyncio.sleep(5)

        _log("等待 changeScene 函数就绪...", json_mode=json_mode)
        page = await client.get_page()
        try:
            await page.wait_for_function(
                """() =>
                typeof window.changeScene === 'function' &&
                typeof window.toggleAuto === 'function' &&
                typeof window.__webgal === 'object' &&
                typeof window.hideInfo === 'function'
                """,
                timeout=10000,
            )
            _log(f"changeScene 已就绪，调用 changeScene(\"{scene_path}\", 1)...", json_mode=json_mode)
            await page.evaluate(
                """async (path) => {
                    window.changeScene(path, 1);
                    await new Promise(r => setTimeout(r, 500));
                    window.toggleAuto();
                    window.hideInfo();
                }""",
                scene_path,
            )
            _log("changeScene 调用完成", json_mode=json_mode)
        except Exception as e:
            _log(f"警告: changeScene 调用失败: {e}", json_mode=json_mode)

        if selector == "auto":
            for candidate in ("#root", "canvas"):
                found = await client.wait_for(
                    Selector(value=candidate, type=SelectorType.CSS),
                    state="visible",
                    timeout=3000,
                )
                if found:
                    _log(f"目标元素已就绪: {candidate}", json_mode=json_mode)
                    break
            else:
                _log("警告: 未找到 #root 或 canvas 元素，继续录制整个页面", json_mode=json_mode)
        else:
            _log(f"等待目标元素出现: {selector}", json_mode=json_mode)
            found = await client.wait_for(
                Selector(value=selector, type=SelectorType.CSS),
                state="visible",
                timeout=10000,
            )
            if not found:
                msg = f"未找到目标元素 {selector}"
                _log(f"错误: {msg}", json_mode=json_mode)
                if json_mode:
                    return {"success": False, "message": msg}
                return None

        await asyncio.sleep(1)

        if no_record:
            _log(f"跳过录制，等待 {duration}s 观察页面状态...", json_mode=json_mode)
            await asyncio.sleep(duration)
            _log("观察完成!", json_mode=json_mode)
            return None

        _log(f"开始录制 {duration}s @ {fps} FPS (CDP Screencast)...", json_mode=json_mode)
        _log(f"输出: {output_path}", json_mode=json_mode)

        recorder = ScreencastRecorder(
            client, video_cfg, screencast_quality=screencast_quality, record_audio=record_audio
        )
        result = await recorder.start(duration=duration, format=format, save_frames_dir=save_frames, stop_condition=stop_condition)

        _log("录制完成!", json_mode=json_mode)
        _log(f"  输出路径: {result.output_path}", json_mode=json_mode)
        _log(f"  源帧率: {result.source_fps:.1f} FPS → 输出帧率: {result.output_fps:.1f} FPS", json_mode=json_mode)
        _log(f"  总帧数: {result.total_frames}", json_mode=json_mode)
        _log(f"  时长: {result.duration:.1f}s", json_mode=json_mode)
        _log(f"  文件大小: {result.file_size_mb:.2f} MB", json_mode=json_mode)

        if json_mode:
            return {
                "success": True,
                "message": "录制完成",
                "output_path": str(result.output_path),
                "total_frames": result.total_frames,
                "duration": result.duration,
                "source_fps": result.source_fps,
                "output_fps": result.output_fps,
                "file_size_mb": result.file_size_mb,
                "has_audio": result.has_audio,
            }
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="浏览器模块演示")
    parser.add_argument(
        "mode",
        choices=["navigate", "record"],
        help="运行模式: navigate=导航截图, record=录制视频",
    )
    parser.add_argument("--url", default="https://example.com", help="目标 URL")
    parser.add_argument("--output", default="data/temp/output.mp4", help="输出路径")
    parser.add_argument("--duration", type=float, default=0, help="录制最大时长（秒），0 表示无限等待 --stop-on 条件")
    parser.add_argument("--fps", type=float, default=60.0, help="输出帧率（ffmpeg 转换）")
    parser.add_argument("--width", type=int, default=1920, help="录制分辨率宽度")
    parser.add_argument("--height", type=int, default=1080, help="录制分辨率高度")
    parser.add_argument(
        "--selector", default="auto",
        help="等待的目标元素 CSS 选择器；auto 会优先尝试 #root，再回退到 canvas",
    )
    parser.add_argument(
        "--scene", default="index.txt", dest="scene_path",
        help="调用 changeScene 时传入的场景路径",
    )
    parser.add_argument(
        "--stop-on", default=None, dest="stop_condition",
        help="JS 表达式，录制期间每 0.5 秒求值一次，返回 truthy 时提前终止录制",
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
        "--save-frames",
        default=None,
        help="保存原始帧到指定目录（用于调试）",
    )
    parser.add_argument(
        "--format",
        default="jpeg",
        choices=["jpeg", "png"],
        help="截图格式：jpeg（有损，小文件）或 png（无损，画质最好）",
    )
    parser.add_argument(
        "--executable",
        default=None,
        help="浏览器可执行文件路径（如 chrome-headless-shell 路径）",
    )
    parser.add_argument(
        "--record-audio",
        action="store_true",
        default=False,
        help="录制 WebAudio 音频输出（Hook AudioNode.prototype.connect，捕获后与视频合流）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_mode",
        help="以 JSON 格式输出结果到 stdout（日志输出到 stderr）",
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
            result = asyncio.run(
                demo_record(
                    url=args.url,
                    output_path=args.output,
                    duration=args.duration,
                    fps=args.fps,
                    width=args.width,
                    height=args.height,
                    selector=args.selector,
                    scene_path=args.scene_path,
                    stop_condition=args.stop_condition,
                    browser_type=args.browser,
                    headless=args.headless,
                    screencast_quality=args.screencast_quality,
                    no_record=args.no_record,
                    save_frames=args.save_frames,
                    format=args.format,
                    record_audio=args.record_audio,
                    json_mode=args.json_mode,
                )
            )
            if args.json_mode and result:
                print(json.dumps(result, ensure_ascii=False))
                if not result["success"]:
                    sys.exit(1)


if __name__ == "__main__":
    main()
