"""视频录制器：将帧序列编码为视频文件。"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import cv2
import numpy as np

from webgal_agent.browser.capture import CanvasCapture, Frame
from webgal_agent.browser.models import CaptureConfig, VideoConfig, RecordingResult

# Fallback codec 优先级列表
_CODEC_CANDIDATES = ["XVID", "MJPG", "mp4v", "avc1"]


class VideoRecorder:
    """视频录制器。

    接收帧数据流，实时编码为视频文件。
    """

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
        self._writer: cv2.VideoWriter | None = None
        self._running = False
        self._output_path = Path(video_config.output_path)
        self._target_size: tuple[int, int] | None = None

    @property
    def capture_config(self) -> CaptureConfig:
        return self._capture_config

    def _resize_frame(self, frame: np.ndarray) -> np.ndarray:
        """缩放帧到目标尺寸（保持宽高比）。"""
        if self._target_size is None:
            return frame
        tw, th = self._target_size
        h, w = frame.shape[:2]
        if w == tw and h == th:
            return frame
        return cv2.resize(frame, (tw, th), interpolation=cv2.INTER_AREA)

    @staticmethod
    def _fit_size(
        src_w: int, src_h: int, max_w: int, max_h: int,
    ) -> tuple[int, int]:
        """计算适配 max 尺寸的输出 (width, height)，保持宽高比，且宽高为偶数。"""
        if src_w <= max_w and src_h <= max_h:
            # 确保偶数
            return src_w - src_w % 2, src_h - src_h % 2

        scale = min(max_w / src_w, max_h / src_h)
        out_w = int(src_w * scale)
        out_h = int(src_h * scale)
        # 编码器要求宽高为偶数
        out_w -= out_w % 2
        out_h -= out_h % 2
        return out_w, out_h

    async def _write_frames(self, frames: AsyncIterator[Frame]) -> None:
        """帧写入循环。"""
        write_task: asyncio.Task | None = None

        async for frame in frames:
            if self._writer is None:
                if not self._init_writer(frame):
                    self._running = False
                    return
                self._running = True

            resized = self._resize_frame(frame.data)

            if write_task and not write_task.done():
                await write_task

            write_task = asyncio.create_task(
                asyncio.to_thread(self._writer.write, resized)
            )

        if write_task:
            await write_task

    def _init_writer(self, first_frame: Frame) -> bool:
        """初始化 VideoWriter。尝试多个 codec 直到成功。"""
        self._output_path.parent.mkdir(parents=True, exist_ok=True)

        # 确定尺寸
        src_h, src_w = first_frame.data.shape[:2]

        if self._video_config.width and self._video_config.height:
            width, height = self._video_config.width, self._video_config.height
        else:
            width, height = self._fit_size(
                src_w, src_h,
                self._video_config.max_width,
                self._video_config.max_height,
            )

        self._target_size = (width, height)

        # 尝试主 codec + fallback
        codecs_to_try = [self._video_config.codec] + [
            c for c in _CODEC_CANDIDATES if c != self._video_config.codec
        ]

        for codec in codecs_to_try:
            fourcc = cv2.VideoWriter_fourcc(*codec)
            self._writer = cv2.VideoWriter(
                str(self._output_path),
                fourcc,
                self._video_config.fps,
                (width, height),
            )
            if self._writer.isOpened():
                return True

        return False

    async def start(self) -> RecordingResult:
        """开始录制，阻塞直到完成。"""
        self._capture = CanvasCapture(
            self._page,
            self._capture_config,
            enable_time_control=self._enable_time_control,
            advance_frame_fn=self._advance_frame,
        )
        start_time = time.monotonic()

        try:
            await self._write_frames(self._capture.start())
        finally:
            if self._writer:
                self._writer.release()
                self._writer = None
            if self._capture:
                self._capture.stop()

        wall_duration = time.monotonic() - start_time
        stats = self._capture.stats if self._capture else None
        duration = stats.elapsed_time if stats and self._enable_time_control else wall_duration
        file_size = 0.0
        if self._output_path.exists():
            file_size = self._output_path.stat().st_size / (1024 * 1024)

        return RecordingResult(
            output_path=self._output_path,
            total_frames=stats.total_frames if stats else 0,
            duration=duration,
            actual_fps=stats.actual_fps if stats else 0.0,
            file_size_mb=file_size,
        )

    def stop(self) -> None:
        """立即停止录制。"""
        if self._capture:
            self._capture.stop()
        self._running = False
