"""CDP Screencast 录制器：从 Chromium compositor 直接拉帧，绕过 MediaRecorder 帧率限制。

通过 Page.startScreencast 从浏览器 compositor 实时拉取帧，
再通过管道喂给 ffmpeg 编码为视频文件。帧率不受 Playwright 内置
MediaRecorder 的 25fps 限制，可达到显示器刷新率。
"""

from __future__ import annotations

import asyncio
import base64
import shutil
import sys
import time
from pathlib import Path

# Windows: 确保 ProactorEventLoop 支持 subprocess（ffmpeg 管道编码必需）
if sys.platform == "win32":
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

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
    compositor 直接拉取帧，再通过管道喂给 ffmpeg 编码为视频。

    支持的截图格式：
    - "jpeg"：有损压缩，文件小，画质可调（quality 参数）
    - "png"：无损压缩，画质最好，但文件更大

    与 VideoRecorder（基于 HeadlessExperimental.beginFrame）的区别：
    - 无需 chrome-headless-shell，普通 Chromium/Edge 即可
    - 帧率由 compositor 决定，可随显示器刷新率
    - 非确定性（真实时间流逝），但帧率上限远高于 MediaRecorder

    用法::

        async with BrowserClient(config) as client:
            await client.new_context()
            await client.navigate("https://example.com")

            recorder = ScreencastRecorder(client, video_cfg)
            # PNG 无损录制（画质最好）
            result = await recorder.start(duration=5.0, format="png")
            # JPEG 高质量录制（文件更小）
            result = await recorder.start(duration=5.0, format="jpeg", quality=95)
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
        format: str = "jpeg",
        save_frames_dir: str | Path | None = None,
    ) -> RecordingResult:
        """开始录制，阻塞 duration 秒后停止并编码输出。

        Args:
            duration: 录制时长（秒）。
            context_id: 浏览器上下文 ID。
            format: 截图格式，"jpeg"（有损，小文件）或 "png"（无损，画质最好）。
            save_frames_dir: 如果设置，会将原始帧保存到该目录用于调试。
        """
        if format not in ("jpeg", "png"):
            raise ValueError(f"不支持的格式: {format}，支持 jpeg 和 png")

        page = await self._client.get_page(context_id)
        cdp = await self._client.create_cdp_session(context_id)

        viewport = page.viewport_size
        if not viewport:
            raise RuntimeError("无法获取页面 viewport 尺寸")

        frames: list[tuple[float, bytes]] = []
        start_time = time.monotonic()

        def on_frame(params: dict) -> None:
            timestamp = time.monotonic() - start_time
            data = base64.b64decode(params["data"])
            frames.append((timestamp, data))
            asyncio.ensure_future(
                cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})
            )

        cdp.on("Page.screencastFrame", on_frame)

        # 启动 Screencast
        screencast_opts: dict = {
            "format": format,
            "maxWidth": viewport["width"],
            "maxHeight": viewport["height"],
            "everyNthFrame": 1,
        }
        if format == "jpeg":
            screencast_opts["quality"] = self._quality

        await cdp.send("Page.startScreencast", screencast_opts)

        await asyncio.sleep(duration)

        await cdp.send("Page.stopScreencast")
        # 等待末尾帧的 ack 完成
        await asyncio.sleep(0.1)

        if not frames:
            raise RuntimeError("Screencast 未捕获到任何帧")

        # 保存原始帧用于调试
        if save_frames_dir:
            await self._save_frames(frames, Path(save_frames_dir), format)

        # 统计帧信息
        total_frames = len(frames)
        actual_duration = frames[-1][0] - frames[0][0] if total_frames > 1 else duration
        source_fps = total_frames / actual_duration if actual_duration > 0 else total_frames / duration

        print(f"[ScreencastRecorder] 捕获帧数: {total_frames}")
        print(f"[ScreencastRecorder] 截图格式: {format.upper()}")
        print(f"[ScreencastRecorder] 实际录制时长: {actual_duration:.2f}s (期望: {duration}s)")
        print(f"[ScreencastRecorder] 源帧率: {source_fps:.2f} FPS")

        # 提取纯帧数据用于编码
        frame_data = [f[1] for f in frames]

        await self._encode(frame_data, source_fps, format)

        file_size = self._output_path.stat().st_size / (1024 * 1024)
        return RecordingResult(
            output_path=self._output_path,
            total_frames=total_frames,
            duration=actual_duration,
            actual_fps=source_fps,
            file_size_mb=file_size,
            source_fps=source_fps,
            output_fps=self._video_config.fps,
        )

    async def _save_frames(
        self,
        frames: list[tuple[float, bytes]],
        output_dir: Path,
        format: str,
    ) -> None:
        """保存原始帧到目录用于调试。"""
        output_dir.mkdir(parents=True, exist_ok=True)
        ext = "png" if format == "png" else "jpg"
        for i, (timestamp, data) in enumerate(frames):
            frame_path = output_dir / f"frame_{i:06d}_{timestamp:.3f}s.{ext}"
            frame_path.write_bytes(data)
        print(f"[ScreencastRecorder] 已保存 {len(frames)} 帧到 {output_dir}")

    async def _encode(self, frames: list[bytes], source_fps: float, format: str) -> None:
        """将帧流式写入 ffmpeg stdin 编码为视频。"""
        ffmpeg = _find_ffmpeg()
        fmt, encoder = _codec_from_ext(self._output_path)
        target_fps = self._video_config.fps

        self._output_path.parent.mkdir(parents=True, exist_ok=True)

        # 根据输入格式选择 ffmpeg 输入格式
        input_fmt = "png_pipe" if format == "png" else "mjpeg"

        # 构建 ffmpeg 命令
        # 使用 -framerate 指定输入帧率，使用 -r 转换为目标帧率
        args = [
            ffmpeg, "-y",
            "-f", input_fmt,
            "-framerate", f"{source_fps:.6f}",
            "-i", "-",
            "-an",
            "-r", str(target_fps),  # 输出帧率转换
            "-c:v", encoder,
            "-crf", str(self._video_config.quality),
        ]

        if fmt == "webm":
            args.extend(["-deadline", "good", "-cpu-used", "2", "-f", "webm"])
        else:
            args.extend(["-preset", "fast", "-pix_fmt", "yuv420p", "-f", "mp4"])

        args.append(str(self._output_path))

        print(f"[ScreencastRecorder] 源帧率: {source_fps:.2f} FPS → 输出帧率: {target_fps:.0f} FPS")

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
        else:
            print(f"[ScreencastRecorder] FFmpeg 编码完成")
