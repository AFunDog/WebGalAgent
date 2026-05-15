"""视频录制器：使用 CDP 虚拟时间 + FFmpeg 管道逐帧确定性录制。"""

from __future__ import annotations

import asyncio
import base64
import subprocess
import time
from pathlib import Path
from typing import Any

from webgal_agent.browser.models import CaptureConfig, RecordingResult, VideoConfig


class VideoRecorder:
    """基于 CDP HeadlessExperimental.beginFrame 的确定性视频录制器。

    工作流程：
    1. 通过 CDP Emulation.setVirtualTimePolicy 暂停虚拟时间
    2. 每帧调用 HeadlessExperimental.beginFrame 推进时间并截图
    3. 将 PNG 帧数据通过管道喂给 FFmpeg 编码为视频
    """

    def __init__(
        self,
        cdp_session: Any,
        page: Any,
        video_config: VideoConfig,
        capture_config: CaptureConfig | None = None,
        advance_frame_fn: Any | None = None,
    ) -> None:
        self._cdp = cdp_session
        self._page = page
        self._video_config = video_config
        self._capture_config = capture_config or CaptureConfig(fps=video_config.fps)
        self._output_path = Path(video_config.output_path)
        self._advance_frame_fn = advance_frame_fn
        self._running = False

    async def start(self) -> RecordingResult:
        """开始逐帧录制，阻塞直到完成。"""
        fps = self._capture_config.fps
        duration = self._capture_config.max_duration or 5.0
        selector = self._capture_config.canvas_selector
        total_frames = max(1, int(round(duration * fps)))
        frame_interval = 1000.0 / fps

        # 获取目标元素裁剪区域
        clip = await self._resolve_clip(selector)

        ffmpeg = self._start_ffmpeg(fps)

        last_frame: bytes | None = None
        dropped = 0

        self._running = True
        record_start = time.monotonic()

        try:
            try:
                dropped, last_frame = await self._record_with_cdp(
                    ffmpeg=ffmpeg,
                    total_frames=total_frames,
                    frame_interval=frame_interval,
                    clip=clip,
                )
            except Exception as exc:
                if not self._advance_frame_fn:
                    raise RuntimeError(
                        "CDP beginFrame 录制失败，且未提供兼容降级方案。"
                        "请使用支持 begin-frame-control 的 chrome-headless-shell，"
                        "或传入 JS 帧推进回调以启用截图降级模式。"
                    ) from exc

                print(f"警告: CDP beginFrame 不可用，切换到兼容降级模式: {exc}")
                dropped, last_frame = await self._record_with_screenshot_fallback(
                    ffmpeg=ffmpeg,
                    total_frames=total_frames,
                    clip=clip,
                )

        finally:
            self._running = False

        # 结束 FFmpeg
        try:
            ffmpeg.stdin.close()  # type: ignore[union-attr]
        except BrokenPipeError:
            pass
        ffmpeg.wait()

        record_wall_time = time.monotonic() - record_start
        captured_frames = total_frames - dropped
        video_duration = captured_frames / fps if captured_frames else 0.0
        file_size = 0.0
        if self._output_path.exists():
            file_size = self._output_path.stat().st_size / (1024 * 1024)

        return RecordingResult(
            output_path=self._output_path,
            total_frames=captured_frames,
            duration=video_duration,
            actual_fps=fps if captured_frames else 0.0,
            file_size_mb=file_size,
            wall_time=record_wall_time,
        )

    async def _resolve_clip(self, selector: str) -> dict[str, Any]:
        """获取目标元素的裁剪区域。"""
        element = self._page.locator(selector).first
        await element.wait_for(state="visible", timeout=10000)
        box = await element.bounding_box()
        if not box:
            raise RuntimeError(f"元素不可见或无 bounding box: {selector}")

        width = int(box["width"])
        height = int(box["height"])
        # FFmpeg 要求偶数
        if width % 2:
            width += 1
        if height % 2:
            height += 1

        return {
            "x": box["x"],
            "y": box["y"],
            "width": width,
            "height": height,
            "scale": 1,
        }

    def _start_ffmpeg(self, fps: float) -> subprocess.Popen:
        """启动 FFmpeg 进程。"""
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_cmd = self._build_ffmpeg_command(fps)
        return subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

    async def _record_with_cdp(
        self,
        ffmpeg: subprocess.Popen,
        total_frames: int,
        frame_interval: float,
        clip: dict[str, Any],
    ) -> tuple[int, bytes | None]:
        """优先使用 CDP beginFrame 进行确定性录制。"""
        begin_frame_timeout = 2.0

        await self._cdp.send("Emulation.setVirtualTimePolicy", {"policy": "pause"})

        for _ in range(2):
            await asyncio.wait_for(
                self._cdp.send(
                    "HeadlessExperimental.beginFrame",
                    {"interval": frame_interval},
                ),
                timeout=begin_frame_timeout,
            )

        last_frame: bytes | None = None
        dropped = 0

        for frame_idx in range(total_frames):
            if not self._running:
                break

            virtual_time = frame_idx * frame_interval
            result = await asyncio.wait_for(
                self._cdp.send(
                    "HeadlessExperimental.beginFrame",
                    {
                        "frameTimeTicks": virtual_time,
                        "interval": frame_interval,
                        "screenshot": {
                            "format": "png",
                            "clip": clip,
                        },
                    },
                ),
                timeout=begin_frame_timeout,
            )

            img, last_frame = await self._decode_or_capture_frame(result, clip, last_frame)
            if self._write_frame(ffmpeg, img):
                if img is None:
                    dropped += 1
            else:
                break

            self._report_progress(frame_idx=frame_idx, total_frames=total_frames, fps=self._capture_config.fps, img=img)

        return dropped, last_frame

    async def _record_with_screenshot_fallback(
        self,
        ffmpeg: subprocess.Popen,
        total_frames: int,
        clip: dict[str, Any],
    ) -> tuple[int, bytes | None]:
        """降级到 JS 帧推进 + Playwright screenshot。"""
        last_frame: bytes | None = None
        dropped = 0

        for frame_idx in range(total_frames):
            if not self._running:
                break

            await self._advance_frame_fn(1)
            img = await self._page.screenshot(clip=clip, type="png")
            if img:
                last_frame = img

            if self._write_frame(ffmpeg, img):
                if img is None:
                    dropped += 1
            else:
                break

            self._report_progress(frame_idx=frame_idx, total_frames=total_frames, fps=self._capture_config.fps, img=img)

        return dropped, last_frame

    async def _decode_or_capture_frame(
        self,
        result: dict[str, Any],
        clip: dict[str, Any],
        last_frame: bytes | None,
    ) -> tuple[bytes | None, bytes | None]:
        """解码 beginFrame 截图；必要时回退到 page.screenshot。"""
        img: bytes | None = None
        if result.get("screenshotData"):
            img = base64.b64decode(result["screenshotData"])
            last_frame = img
        elif last_frame:
            img = last_frame
        else:
            img = await self._page.screenshot(clip=clip, type="png")
            last_frame = img
        return img, last_frame

    def _write_frame(self, ffmpeg: subprocess.Popen, img: bytes | None) -> bool:
        """将一帧写入 FFmpeg。"""
        if not img:
            return True
        try:
            ffmpeg.stdin.write(img)  # type: ignore[union-attr]
            return True
        except BrokenPipeError:
            return False

    @staticmethod
    def _report_progress(frame_idx: int, total_frames: int, fps: float, img: bytes | None) -> None:
        """输出进度。"""
        if (frame_idx + 1) % 5 != 0 and frame_idx + 1 != total_frames:
            return
        elapsed_sec = (frame_idx + 1) / fps
        img_size = len(img) if img else 0
        print(f"  帧 {frame_idx + 1}/{total_frames} | 已处理 {elapsed_sec:.1f}s | 截图 {img_size} bytes")

    def _build_ffmpeg_command(self, fps: float) -> list[str]:
        """构建 FFmpeg 命令行。"""
        return [
            "ffmpeg",
            "-y",
            "-f", "image2pipe",
            "-vcodec", "png",
            "-r", str(fps),
            "-i", "-",
            "-an",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "slow",
            "-crf", "18",
            "-fps_mode", "cfr",
            str(self._output_path),
        ]

    def stop(self) -> None:
        """立即停止录制。"""
        self._running = False
