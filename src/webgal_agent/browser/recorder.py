"""视频录制器：将帧序列编码为视频文件。"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator

import cv2
import numpy as np

from webgal_agent.browser.capture import CanvasCapture, CaptureConfig, Frame


@dataclass
class VideoConfig:
    """视频输出配置。"""

    output_path: str | Path
    fps: float = 30.0
    codec: str = "mp4v"
    quality: int = 23
    width: int | None = None
    height: int | None = None


@dataclass
class RecordingResult:
    """录制结果。"""

    output_path: Path
    total_frames: int
    duration: float
    actual_fps: float
    file_size_mb: float


class VideoRecorder:
    """视频录制器。

    接收帧数据流，实时编码为视频文件。
    """

    def __init__(
        self,
        page,
        video_config: VideoConfig,
        capture_config: CaptureConfig | None = None,
    ) -> None:
        self._page = page
        self._video_config = video_config
        self._capture_config = capture_config or CaptureConfig(fps=video_config.fps)
        self._capture: CanvasCapture | None = None
        self._writer: cv2.VideoWriter | None = None
        self._running = False
        self._output_path = Path(video_config.output_path)

    @property
    def capture_config(self) -> CaptureConfig:
        return self._capture_config

    async def _write_frames(self, frames: AsyncIterator[Frame]) -> None:
        """帧写入循环。"""
        frame: Frame | None = None
        pending_frame: Frame | None = None
        write_task: asyncio.Task | None = None

        async for frame in frames:
            if self._writer is None:
                self._init_writer(frame)
                self._running = True

            if write_task and not write_task.done():
                await write_task

            write_task = asyncio.create_task(
                asyncio.to_thread(self._writer.write, frame.data)
            )

        if write_task:
            await write_task

    def _init_writer(self, first_frame: Frame) -> None:
        """初始化 VideoWriter。"""
        self._output_path.parent.mkdir(parents=True, exist_ok=True)

        # 确定尺寸
        if self._video_config.width and self._video_config.height:
            width, height = self._video_config.width, self._video_config.height
        else:
            # 从第一帧推断（opencv 是 h, w, c）
            height, width = first_frame.data.shape[:2]

        fourcc = cv2.VideoWriter_fourcc(*self._video_config.codec)
        self._writer = cv2.VideoWriter(
            str(self._output_path),
            fourcc,
            self._video_config.fps,
            (width, height),
        )

        if not self._writer.isOpened():
            raise RuntimeError(f"VideoWriter 初始化失败: {self._output_path}")

    async def start(self) -> RecordingResult:
        """开始录制，阻塞直到完成。"""
        self._capture = CanvasCapture(self._page, self._capture_config)
        start_time = time.monotonic()

        try:
            await self._write_frames(self._capture.start())
        finally:
            if self._writer:
                self._writer.release()
                self._writer = None

        duration = time.monotonic() - start_time
        stats = self._capture.stats if self._capture else CaptureStats()
        file_size = self._output_path.stat().st_size / (1024 * 1024)

        return RecordingResult(
            output_path=self._output_path,
            total_frames=stats.total_frames,
            duration=duration,
            actual_fps=stats.actual_fps,
            file_size_mb=file_size,
        )

    def stop(self) -> None:
        """立即停止录制。"""
        if self._capture:
            self._capture.stop()
        self._running = False


@dataclass
class CaptureStats:
    """捕获统计。"""

    total_frames: int = 0
    dropped_frames: int = 0
    elapsed_time: float = 0.0
    actual_fps: float = 0.0
