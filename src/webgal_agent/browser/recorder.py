"""视频录制器：使用浏览器内的 CCapture.js 生成视频文件。"""

from __future__ import annotations

from pathlib import Path

from webgal_agent.browser.capture import CanvasCapture
from webgal_agent.browser.models import CaptureConfig, RecordingResult, VideoConfig


class VideoRecorder:
    """视频录制器。"""

    def __init__(
        self,
        page,
        video_config: VideoConfig,
        capture_config: CaptureConfig | None = None,
        enable_time_control: bool = False,
        advance_frame_fn=None,
    ) -> None:
        self._page = page
        self._video_config = video_config
        self._capture_config = capture_config or CaptureConfig(fps=video_config.fps)
        self._enable_time_control = enable_time_control
        self._advance_frame = advance_frame_fn
        self._capture: CanvasCapture | None = None
        self._output_path = Path(video_config.output_path)

    @property
    def capture_config(self) -> CaptureConfig:
        return self._capture_config

    async def start(self) -> RecordingResult:
        """开始录制，阻塞直到完成。"""
        if self._video_config.codec != "webm":
            raise ValueError("CCapture backend currently only supports codec='webm'")

        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        self._capture = CanvasCapture(
            self._page,
            self._capture_config,
            enable_time_control=self._enable_time_control,
            advance_frame_fn=self._advance_frame,
        )

        artifact = await self._capture.start()
        self._output_path.write_bytes(artifact.data)

        stats = self._capture.stats
        file_size = self._output_path.stat().st_size / (1024 * 1024)

        return RecordingResult(
            output_path=self._output_path,
            total_frames=stats.total_frames,
            duration=stats.elapsed_time,
            actual_fps=stats.actual_fps,
            file_size_mb=file_size,
        )

    def stop(self) -> None:
        """立即停止录制。"""
        if self._capture:
            self._capture.stop()
