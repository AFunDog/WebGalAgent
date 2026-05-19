"""demo CLI 参数解析与模式分发。"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import sys
from pathlib import Path

from webgal_agent.browser.demo_session import demo_navigate, demo_record
from webgal_agent.browser.paths import default_demo_output_path, default_recording_log_path


class _TeeStream(io.TextIOBase):
    """同时写入终端和日志文件的简单文本流。"""

    def __init__(self, primary, log_file) -> None:
        self._primary = primary
        self._log_file = log_file

    def write(self, s: str) -> int:
        self._primary.write(s)
        self._log_file.write(s)
        return len(s)

    def flush(self) -> None:
        self._primary.flush()
        self._log_file.flush()

    @property
    def encoding(self):  # type: ignore[override]
        return getattr(self._primary, "encoding", "utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="浏览器模块演示")
    parser.add_argument("mode", choices=["navigate", "record"], help="运行模式")
    parser.add_argument("--url", default="https://example.com", help="目标 URL")
    parser.add_argument("--output", default=str(default_demo_output_path()), help="输出路径")
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
    parser.add_argument(
        "--page-mode",
        default="webgal",
        choices=["webgal", "generic"],
        help="页面模式：webgal 会执行场景切换和配置注入；generic 跳过这些专属逻辑",
    )
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
        "--av-sync-debug-interval",
        type=float,
        default=0.0,
        help="启用音画同步调试；每隔多少秒触发一次纯红闪屏 + 方波脉冲，0 为关闭",
    )
    parser.add_argument(
        "--av-sync-debug-flash-ms",
        type=int,
        default=120,
        help="音画同步调试中纯红闪屏持续时长（毫秒）",
    )
    parser.add_argument(
        "--av-sync-debug-tone-ms",
        type=int,
        default=120,
        help="音画同步调试中方波脉冲持续时长（毫秒）",
    )
    parser.add_argument(
        "--av-sync-debug-frequency",
        type=float,
        default=880.0,
        help="音画同步调试中方波频率（Hz）",
    )
    parser.add_argument("--save-logs", action="store_true", default=False, help="将运行日志保存到输出视频旁边")
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
            orig_stdout = sys.stdout
            orig_stderr = sys.stderr
            log_file = None
            log_path = str(default_recording_log_path(args.output)) if args.save_logs else None
            if log_path:
                Path(log_path).parent.mkdir(parents=True, exist_ok=True)
                log_file = open(log_path, "w", encoding="utf-8")
                sys.stdout = _TeeStream(orig_stdout, log_file)
                sys.stderr = _TeeStream(orig_stderr, log_file)
            if args.json_mode:
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
                        page_mode=args.page_mode,
                        stop_condition=args.stop_condition,
                        browser_type=args.browser,
                        headless=args.headless,
                        screencast_quality=args.screencast_quality,
                        no_record=args.no_record,
                        save_frames=args.save_frames,
                        format=args.format,
                        record_audio=args.record_audio,
                        av_sync_debug_interval=args.av_sync_debug_interval,
                        av_sync_debug_flash_ms=args.av_sync_debug_flash_ms,
                        av_sync_debug_tone_ms=args.av_sync_debug_tone_ms,
                        av_sync_debug_frequency=args.av_sync_debug_frequency,
                        executable_path=args.executable,
                        game_config=game_config,
                        log_path=log_path,
                        json_mode=args.json_mode,
                    )
                )
            finally:
                sys.stdout = orig_stdout
                sys.stderr = orig_stderr
                if log_file is not None:
                    log_file.close()
            if result is not None and log_path:
                result["log_path"] = log_path
            if args.json_mode and result:
                print(json.dumps(result, ensure_ascii=False))
                if not result["success"]:
                    sys.exit(1)
