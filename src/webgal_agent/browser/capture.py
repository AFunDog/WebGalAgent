"""Canvas 帧捕获器：定时采集画布内容。"""

from __future__ import annotations

import asyncio
import base64
import time
from dataclasses import dataclass, field
from typing import Callable, AsyncIterator

import numpy as np


@dataclass
class CaptureConfig:
    """捕获配置。"""

    fps: float = 30.0
    canvas_selector: str = "canvas"
    max_duration: float | None = None
    max_frames: int | None = None


@dataclass
class Frame:
    """单帧数据。"""

    data: np.ndarray
    timestamp: float
    frame_index: int


@dataclass
class CaptureStats:
    """捕获统计。"""

    total_frames: int = 0
    dropped_frames: int = 0
    elapsed_time: float = 0.0
    actual_fps: float = 0.0


class CanvasCapture:
    """Canvas 帧捕获器。

    定时从页面的 Canvas 元素采集帧数据，返回 numpy 数组。
    """

    def __init__(
        self,
        page,
        config: CaptureConfig | None = None,
    ) -> None:
        self._page = page
        self._config = config or CaptureConfig()
        self._running = False
        self._stats = CaptureStats()
        self._frame_index = 0
        self._start_time = 0.0

    @property
    def stats(self) -> CaptureStats:
        return self._stats

    async def capture_frame(self) -> np.ndarray | None:
        """从 Canvas 提取当前帧。"""
        try:
            data_url: str = await self._page.evaluate(
                f"""
                () => {{
                    const canvas = document.querySelector('{self._config.canvas_selector}');
                    if (!canvas) return null;
                    return canvas.toDataURL('image/png');
                }}
                """
            )
            if not data_url:
                return None

            # 解码 base64 -> numpy array
            _, data = data_url.split(",", 1)
            raw = base64.b64decode(data)
            nparr = np.frombuffer(raw, np.uint8)
            img = np.frombuffer(nparr, np.uint8).reshape(-1, 3)
            return img
        except Exception:
            return None

    async def _capture_loop(self) -> AsyncIterator[Frame]:
        """内部捕获循环。"""
        interval = 1.0 / self._config.fps
        next_time = time.monotonic()

        while self._running:
            # 检查时间限制
            elapsed = time.monotonic() - self._start_time
            if self._config.max_duration and elapsed >= self._config.max_duration:
                break
            if self._config.max_frames and self._frame_index >= self._config.max_frames:
                break

            frame_data = await self.capture_frame()

            if frame_data is not None:
                yield Frame(
                    data=frame_data,
                    timestamp=elapsed,
                    frame_index=self._frame_index,
                )
                self._frame_index += 1
            else:
                self._stats.dropped_frames += 1

            # 精确计时：等待到下一帧时刻
            next_time += interval
            sleep_time = next_time - time.monotonic()
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

    async def start(self) -> AsyncIterator[Frame]:
        """启动捕获，返回帧迭代器。"""
        self._running = True
        self._start_time = time.monotonic()
        self._frame_index = 0
        self._stats = CaptureStats()

        try:
            async for frame in self._capture_loop():
                self._stats.total_frames += 1
                yield frame
        finally:
            self._stats.elapsed_time = time.monotonic() - self._start_time
            self._stats.actual_fps = (
                self._stats.total_frames / self._stats.elapsed_time
                if self._stats.elapsed_time > 0 else 0.0
            )
            self._running = False

    def stop(self) -> None:
        """停止捕获。"""
        self._running = False
