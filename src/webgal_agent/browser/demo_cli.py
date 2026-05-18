"""demo CLI 参数解析与模式分发。"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from webgal_agent.browser.demo_session import demo_navigate, demo_record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="浏览器模块演示")
    parser.add_argument("mode", choices=["navigate", "record"], help="运行模式")
    parser.add_argument("--url", default="https://example.com", help="目标 URL")
    parser.add_argument("--output", default="data/temp/output.mp4", help="输出路径")
    parser.add_argument("--duration", type=float, default=0, help="录制最大时长（秒）")
    parser.add_argument("--fps", type=float, default=60.0, help="输出帧率（ffmpeg 转换）")
    parser.add_argument("--width", type=int, default=1920, help="录制分辨率宽度")
    parser.add_argument("--height", type=int, default=1080, help="录制分辨率高度")
    parser.add_argument(
        "--selector",
        default="auto",
        help="等待的目标元素 CSS 选择器；auto 会优先尝试 #root，再回退到 canvas",
    )
    parser.add_argument("--scene", default="index.txt", dest="scene_path", help="场景路径")
    parser.add_argument("--stop-on", default=None, dest="stop_condition", help="停止条件 JS 表达式")
    parser.add_argument(
        "--browser",
        default="msedge",
        choices=["chromium", "firefox", "webkit", "msedge"],
        help="浏览器类型",
    )
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--no-record", action="store_true", help="不录制，仅等待观察")
    parser.add_argument(
        "--screencast-quality", type=int, default=90, help="Screencast JPEG 质量 (0-100)"
    )
    parser.add_argument("--save-frames", default=None, help="保存原始帧目录")
    parser.add_argument(
        "--format",
        default="jpeg",
        choices=["jpeg", "png"],
        help="截图格式：jpeg 或 png",
    )
    parser.add_argument("--executable", default=None, help="浏览器可执行文件路径")
    parser.add_argument(
        "--record-audio",
        action="store_true",
        default=False,
        help="录制页面音频输出",
    )
    parser.add_argument(
        "--debug-sync",
        action="store_true",
        default=False,
        help="启用音视频同步调试：注入闪烁+beep marker，并输出 sync_debug.json",
    )
    parser.add_argument(
        "--sync-debug-path",
        default=None,
        help="同步调试 JSON 输出路径，默认写到输出视频旁边",
    )
    parser.add_argument(
        "--game-config",
        default=None,
        help='游戏 IndexedDB 配置覆盖 (JSON), 如 {"optionData.autoSpeed":50}',
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_mode",
        help="以 JSON 格式输出结果到 stdout（日志输出到 stderr）",
    )
    return parser


def run_cli(args: argparse.Namespace) -> None:
    """按模式分发 demo CLI。"""
    game_config: dict[str, int] | None = None
    if getattr(args, "game_config", None):
        game_config = json.loads(args.game_config)

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
            saved_stdout = None
            if args.json_mode:
                saved_stdout = sys.stdout
                sys.stdout = sys.stderr
            try:
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
                        executable_path=args.executable,
                        game_config=game_config,
                        debug_sync=args.debug_sync,
                        sync_debug_path=args.sync_debug_path,
                        json_mode=args.json_mode,
                    )
                )
            finally:
                if saved_stdout is not None:
                    sys.stdout = saved_stdout
            if args.json_mode and result:
                print(json.dumps(result, ensure_ascii=False))
                if not result["success"]:
                    sys.exit(1)
