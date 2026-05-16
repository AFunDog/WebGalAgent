"""CDP Screencast 录制器：从 Chromium compositor 直接拉帧，绕过 MediaRecorder 帧率限制。

通过 Page.startScreencast 从浏览器 compositor 实时拉取 JPEG 帧，
再通过管道喂给 ffmpeg 编码为视频文件。帧率不受 Playwright 内置
MediaRecorder 的 25fps 限制，可达到显示器刷新率。
"""

from __future__ import annotations

import asyncio
import base64
import shutil
from pathlib import Path

from webgal_agent.browser.models import RecordingResult, VideoConfig


def _find_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("未找到 ffmpeg，请安装 ffmpeg 并确保其在 PATH 中。")
    return ffmpeg


def _codec_from_ext(output_path: Path) -> tuple[str, str]:
    """根据输出文件扩展名返回 (容器格式, 编码器)。"""
    suffix = output_path.suffix.lower()
    if suffix == ".webm":
        return "webm", "libvpx-vp9"
    return "mp4", "libx264"


class ScreencastRecorder:
    """CDP Screencast 录制器。

    通过 Chrome DevTools Protocol 的 Page.startScreencast 从 Chromium
    compositor 直接拉取 JPEG 帧，再通过管道喂给 ffmpeg 编码为视频。

    与 VideoRecorder（基于 HeadlessExperimental.beginFrame）的区别：
    - 无需 chrome-headless-shell，普通 Chromium/Edge 即可
    - 帧率由 compositor 决定，可随显示器刷新率
    - 非确定性（真实时间流逝），但帧率上限远高于 MediaRecorder

    用法::

        async with BrowserClient(config) as client:
            await client.new_context()
            await client.navigate("https://example.com")

            recorder = ScreencastRecorder(client, video_cfg)
            result = await recorder.start(duration=5.0)
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
        duration: float,
        context_id: str = "default",
    ) -> RecordingResult:
        """开始录制，阻塞 duration 秒后停止并编码输出。

        Args:
            duration: 录制时长（秒）。
            context_id: 浏览器上下文 ID。
        """
        page = await self._client.get_page(context_id)
        cdp = await self._client.create_cdp_session(context_id)

        viewport = page.viewport_size
        if not viewport:
            raise RuntimeError("无法获取页面 viewport 尺寸")

        frames: list[bytes] = []

        def on_frame(params: dict) -> None:
            data = base64.b64decode(params["data"])
            frames.append(data)
            asyncio.ensure_future(
                cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
            )

        cdp.on("Page.screencastFrame", on_frame)

        await cdp.send(
            "Page.startScreencast",
            {
                "format": "jpeg",
                "quality": self._quality,
                "maxWidth": viewport["width"],
                "maxHeight": viewport["height"],
                "everyNthFrame": 1,
            },
        )

        await asyncio.sleep(duration)

        await cdp.send("Page.stopScreencast")
        # 等待末尾帧的 ack 完成
        await asyncio.sleep(0.1)

        if not frames:
            raise RuntimeError("Screencast 未捕获到任何帧")

        source_fps = len(frames) / duration

        await self._encode(frames, source_fps)

        file_size = self._output_path.stat().st_size / (1024 * 1024)
        return RecordingResult(
            output_path=self._output_path,
            total_frames=len(frames),
            duration=duration,
            actual_fps=self._video_config.fps,
            file_size_mb=file_size,
            source_fps=source_fps,
            output_fps=self._video_config.fps,
        )

    async def _encode(self, frames: list[bytes], source_fps: float) -> None:
        """将 JPEG 帧流式写入 ffmpeg stdin 编码为视频。"""
        ffmpeg = _find_ffmpeg()
        fmt, encoder = _codec_from_ext(self._output_path)

        self._output_path.parent.mkdir(parents=True, exist_ok=True)

        args = [
            ffmpeg, "-y",
            "-f", "image2pipe",
            "-framerate", f"{source_fps:.6f}",
            "-i", "-",
            "-an",
            "-r", str(self._video_config.fps),
            "-c:v", encoder,
            "-crf", str(self._video_config.quality),
        ]

        if fmt == "webm":
            args.extend(["-deadline", "good", "-cpu-used", "2", "-f", "webm"])
        else:
            args.extend(["-preset", "slower", "-pix_fmt", "yuv420p", "-f", "mp4"])

        args.append(str(self._output_path))

        proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        for frame in frames:
            proc.stdin.write(frame)
            await proc.stdin.drain()
        proc.stdin.close()

        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg 编码失败:\n{stderr.decode()}")
