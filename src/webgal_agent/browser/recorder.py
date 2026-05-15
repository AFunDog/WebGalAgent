"""视频录制器：使用 CDP 虚拟时间 + FFmpeg 管道逐帧确定性录制。"""

from __future__ import annotations

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
    ) -> None:
        self._cdp = cdp_session
        self._page = page
        self._video_config = video_config
        self._capture_config = capture_config or CaptureConfig(fps=video_config.fps)
        self._output_path = Path(video_config.output_path)
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

        # 启动虚拟时间（暂停）
        await self._cdp.send("Emulation.setVirtualTimePolicy", {"policy": "pause"})

        # compositor 预热
        for _ in range(5):
            await self._cdp.send(
                "HeadlessExperimental.beginFrame",
                {"interval": frame_interval},
            )

        # 启动 FFmpeg
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        ffmpeg_cmd = self._build_ffmpeg_command(fps)
        ffmpeg = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

        last_frame: bytes | None = None
        dropped = 0

        self._running = True
        record_start = time.monotonic()

        try:
            for frame_idx in range(total_frames):
                if not self._running:
                    break

                virtual_time = frame_idx * frame_interval

                result = await self._cdp.send(
                    "HeadlessExperimental.beginFrame",
                    {
                        "frameTimeTicks": virtual_time,
                        "interval": frame_interval,
                        "screenshot": {
                            "format": "png",
                            "clip": clip,
                        },
                    },
                )

                img: bytes | None = None
                if result.get("screenshotData"):
                    img = base64.b64decode(result["screenshotData"])
                    last_frame = img
                elif last_frame:
                    img = last_frame
                else:
                    # 首帧 fallback：使用 Playwright 截图
                    png_bytes = await self._page.screenshot(clip=clip, type="png")
                    img = png_bytes
                    last_frame = img

                if img:
                    try:
                        ffmpeg.stdin.write(img)  # type: ignore[union-attr]
                    except BrokenPipeError:
                        break
                else:
                    dropped += 1

                # 进度提示（每秒一次）
                if (frame_idx + 1) % int(fps) == 0:
                    elapsed_sec = (frame_idx + 1) / fps
                    print(f"  进度: {elapsed_sec:.0f}/{duration:.0f} 秒")

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
            "-vsync", "cfr",
            str(self._output_path),
        ]

    def stop(self) -> None:
        """立即停止录制。"""
        self._running = False
