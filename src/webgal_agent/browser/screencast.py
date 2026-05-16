"""CDP Screencast 录制器：从 Chromium compositor 直接拉帧，绕过 MediaRecorder 帧率限制。

录制流程：
1. Page.startScreencast → 帧保存到临时目录（磁盘 I/O，无编码压力）
2. 录制结束后 ffmpeg 批量编码（不受实时帧率限制）
"""

from __future__ import annotations

import asyncio
import base64
import shutil
import time
import uuid
from pathlib import Path

from webgal_agent.browser.models import RecordingResult, VideoConfig


def _find_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("未找到 ffmpeg，请安装 ffmpeg 并确保其在 PATH 中。")
    return ffmpeg


def _codec_from_ext(output_path: Path) -> tuple[str, str]:
    suffix = output_path.suffix.lower()
    if suffix == ".webm":
        return "webm", "libvpx-vp9"
    return "mp4", "libx264"


class ScreencastRecorder:
    """CDP Screencast 录制器。

    通过 Chrome DevTools Protocol 的 Page.startScreencast 从 Chromium
    compositor 直接拉取帧，保存到磁盘后再用 ffmpeg 批量编码为视频。

    与 VideoRecorder（基于 HeadlessExperimental.beginFrame）的区别：
    - 无需 chrome-headless-shell，普通 Chromium/Edge 即可
    - 帧率由 compositor 决定，可随显示器刷新率
    - 非确定性（真实时间流逝），但帧率上限远高于 MediaRecorder

    用法::

        async with BrowserClient(config) as client:
            await client.new_context()
            await client.navigate("https://example.com")

            recorder = ScreencastRecorder(client, video_cfg)
            result = await recorder.start(duration=5.0, format="jpeg")
    """

    def __init__(
        self,
        client,
        video_config: VideoConfig,
        screencast_quality: int = 90,
    ) -> None:
        self._client = client
        self._video_config = video_config
        self._output_path = Path(video_config.output_path)
        self._quality = screencast_quality

    async def start(
        self,
        duration: float = 0,
        context_id: str = "default",
        format: str = "jpeg",
        save_frames_dir: str | Path | None = None,
        stop_condition: str | None = None,
    ) -> RecordingResult:
        """开始录制，阻塞 duration 秒后停止并编码输出。

        Args:
            duration: 录制最大时长（秒），传 0 且设置了 stop_condition 时无限等待。
            context_id: 浏览器上下文 ID。
            format: 截图格式，"jpeg" 或 "png"。
            save_frames_dir: 如果设置，保留帧目录（默认录制完成后清理）。
            stop_condition: 可选 JS 表达式，满足时触发停止。
        """
        if format not in ("jpeg", "png"):
            raise ValueError(f"不支持的格式: {format}，支持 jpeg 和 png")
        if duration <= 0 and not stop_condition:
            raise ValueError("必须指定 duration > 0 或 stop_condition，否则录制无法退出")

        page = await self._client.get_page(context_id)
        cdp = await self._client.create_cdp_session(context_id)

        viewport = page.viewport_size
        if not viewport:
            raise RuntimeError("无法获取页面 viewport 尺寸")

        # 创建帧目录（项目 data/temp 下）
        ext = "png" if format == "png" else "jpg"
        frames_dir = Path("data/temp") / f"webgal_screencast_{uuid.uuid4().hex[:8]}"
        frames_dir.mkdir(parents=True, exist_ok=True)
        frame_index = 0
        start_time = time.monotonic()

        def on_frame(params: dict) -> None:
            nonlocal frame_index
            data = base64.b64decode(params["data"])
            frame_path = frames_dir / f"frame_{frame_index:08d}.{ext}"
            frame_path.write_bytes(data)
            frame_index += 1
            asyncio.ensure_future(
                cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
            )

        cdp.on("Page.screencastFrame", on_frame)

        screencast_opts: dict = {
            "format": format,
            "maxWidth": viewport["width"],
            "maxHeight": viewport["height"],
            "everyNthFrame": 1,
        }
        if format == "jpeg":
            screencast_opts["quality"] = self._quality

        await cdp.send("Page.startScreencast", screencast_opts)

        # 并发等待：最大时长 vs 停止条件
        pending: set[asyncio.Task] = set()
        record_error: str | None = None
        try:
            if duration > 0 and not stop_condition:
                await asyncio.sleep(duration)
            elif duration > 0 and stop_condition:
                t_sleep = asyncio.create_task(asyncio.sleep(duration))
                t_stop = asyncio.create_task(
                    page.wait_for_function(stop_condition, timeout=duration * 1000)
                )
                _, pending = await asyncio.wait([t_sleep, t_stop], return_when=asyncio.FIRST_COMPLETED)
            elif duration <= 0 and stop_condition:
                await asyncio.sleep(1.0)
                await page.wait_for_function(stop_condition, timeout=0)
        except Exception as e:
            record_error = str(e)
            print(f"[ScreencastRecorder] 录制过程异常: {e}")
        for t in pending:
            t.cancel()

        # 安全停止 screencast（页面可能已导航，忽略 target closed 错误）
        try:
            await cdp.send("Page.stopScreencast")
        except Exception:
            pass
        await asyncio.sleep(0.1)

        total_frames = frame_index
        actual_duration = time.monotonic() - start_time
        source_fps = total_frames / actual_duration if actual_duration > 0 else 0

        print(f"[ScreencastRecorder] 捕获帧数: {total_frames}")
        print(f"[ScreencastRecorder] 截图格式: {format.upper()}")
        print(f"[ScreencastRecorder] 实际录制时长: {actual_duration:.2f}s")
        print(f"[ScreencastRecorder] 源帧率: {source_fps:.2f} FPS")

        if total_frames == 0:
            shutil.rmtree(frames_dir, ignore_errors=True)
            if stop_condition:
                return RecordingResult(
                    output_path=self._output_path,
                    total_frames=0,
                    duration=0,
                    actual_fps=0,
                    file_size_mb=0,
                    source_fps=0,
                    output_fps=self._video_config.fps,
                )
            raise RuntimeError("Screencast 未捕获到任何帧")

        output_fps = int(self._video_config.fps)
        print(f"[ScreencastRecorder] 源帧率: {source_fps:.2f} FPS → 输出帧率: {output_fps} FPS")
        print("[ScreencastRecorder] 开始 FFmpeg 编码 (tmix 时间混合 + fps 输出)...")
        encode_start = time.monotonic()

        encode_error: str | None = None
        try:
            await self._encode_from_dir(frames_dir, ext, source_fps, output_fps)
        except Exception as e:
            encode_error = str(e)
            print(f"[ScreencastRecorder] FFmpeg 编码失败: {e}")

        encode_elapsed = time.monotonic() - encode_start
        print(f"[ScreencastRecorder] FFmpeg 编码完成，耗时 {encode_elapsed:.1f}s")

        # 清理临时帧目录
        if save_frames_dir:
            keep_dir = Path(save_frames_dir)
            if keep_dir.exists():
                shutil.rmtree(keep_dir, ignore_errors=True)
            shutil.move(str(frames_dir), str(keep_dir))
            print(f"[ScreencastRecorder] 已保留帧目录: {keep_dir}")
        else:
            shutil.rmtree(frames_dir, ignore_errors=True)

        output_exists = self._output_path.exists()
        file_size = self._output_path.stat().st_size / (1024 * 1024) if output_exists else 0

        return RecordingResult(
            output_path=self._output_path,
            total_frames=total_frames,
            duration=actual_duration,
            actual_fps=source_fps,
            file_size_mb=file_size,
            source_fps=source_fps,
            output_fps=output_fps,
        )

    async def _encode_from_dir(
        self, frames_dir: Path, ext: str, source_fps: float, output_fps: int
    ) -> None:
        """从帧目录批量编码视频（录制完成后离线执行）。"""
        ffmpeg = _find_ffmpeg()
        fmt, encoder = _codec_from_ext(self._output_path)

        self._output_path.parent.mkdir(parents=True, exist_ok=True)

        args = [
            ffmpeg, "-y",
            "-framerate", f"{source_fps:.6f}",
            "-i", str(frames_dir / f"frame_%08d.{ext}"),
            "-an",
            "-vf", f"tmix=2:weights='1 1',fps={output_fps}",
            "-c:v", encoder,
            "-crf", str(self._video_config.quality),
        ]

        if fmt == "webm":
            args.extend(["-deadline", "good", "-cpu-used", "2", "-f", "webm"])
        else:
            args.extend(["-preset", "ultrafast", "-pix_fmt", "yuv420p", "-f", "mp4"])

        args.append(str(self._output_path))

        print(f"[ScreencastRecorder] ffmpeg {' '.join(args[1:])}")

        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg 编码失败:\n{stderr.decode()}")
