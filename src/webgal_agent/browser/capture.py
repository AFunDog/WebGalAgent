"""Canvas 帧捕获器：定时采集画布内容。"""

from __future__ import annotations

import asyncio
import base64
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass

import cv2
import numpy as np

from webgal_agent.browser.models import CaptureConfig


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

    支持两种模式：
    - 时间控制模式（enable_time_control=True）：逐帧推进虚拟时间，稳定输出帧率
    - 实时模式（默认）：按目标 FPS 采样真实浏览器帧
    """

    def __init__(
        self,
        page,
        config: CaptureConfig | None = None,
        enable_time_control: bool = False,
        advance_frame_fn=None,  # 可选：外部提供的 advance_frame 函数
    ) -> None:
        self._page = page
        self._config = config or CaptureConfig()
        self._enable_time_control = enable_time_control
        self._advance_frame = advance_frame_fn
        self._running = False
        self._stats = CaptureStats()
        self._frame_index = 0
        self._start_time = 0.0
        self._canvas_box: dict | None = None
        self._virtual_elapsed_time = 0.0

    @property
    def stats(self) -> CaptureStats:
        return self._stats

    async def _ensure_canvas_box(self) -> dict | None:
        """获取 canvas 在视口中的位置和尺寸（绝对坐标）。"""
        if self._canvas_box:
            return self._canvas_box
        try:
            box: dict | None = await self._page.evaluate(
                f"""
                () => {{
                    const canvas = document.querySelector('{self._config.canvas_selector}');
                    if (!canvas) return null;
                    const rect = canvas.getBoundingClientRect();
                    return {{
                        x: rect.left,
                        y: rect.top,
                        width: Math.floor(rect.width),
                        height: Math.floor(rect.height)
                    }};
                }}
                """
            )
            self._canvas_box = box
            return box
        except Exception:
            return None

    async def _snapshot_canvas(self) -> np.ndarray | None:
        """优先直接导出 canvas 位图，失败时再回退到元素截图。"""
        try:
            data_url: str | None = await self._page.evaluate(
                """(selector) => {
                    const canvas = document.querySelector(selector);
                    if (!canvas || typeof canvas.toDataURL !== "function") {
                        return null;
                    }
                    try {
                        return canvas.toDataURL("image/png");
                    } catch (error) {
                        return null;
                    }
                }""",
                self._config.canvas_selector,
            )
            if data_url and "," in data_url:
                encoded = data_url.split(",", 1)[1]
                img = cv2.imdecode(
                    np.frombuffer(base64.b64decode(encoded), np.uint8),
                    cv2.IMREAD_COLOR,
                )
                if img is not None:
                    return img

            locator = self._page.locator(self._config.canvas_selector).first
            png_bytes: bytes = await locator.screenshot(type="png", timeout=5000)
            return cv2.imdecode(np.frombuffer(png_bytes, np.uint8), cv2.IMREAD_COLOR)
        except Exception:
            return None

    async def capture_frame(self) -> np.ndarray | None:
        """采集一帧。"""
        return await self._snapshot_canvas()

    async def _capture_loop_real_time(self) -> AsyncIterator[Frame]:
        """实时模式：按目标 FPS 采样，有丢帧但不需要外部控制。"""
        interval = 1.0 / self._config.fps
        next_time = time.monotonic() + interval

        while self._running:
            elapsed = time.monotonic() - self._start_time
            if self._config.max_duration and elapsed >= self._config.max_duration:
                break
            if self._config.max_frames and self._frame_index >= self._config.max_frames:
                break

            sleep_time = next_time - time.monotonic()
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            next_time += interval

            frame_data = await self.capture_frame()
            elapsed_now = time.monotonic() - self._start_time

            if frame_data is not None:
                yield Frame(
                    data=frame_data,
                    timestamp=elapsed_now,
                    frame_index=self._frame_index,
                )
                self._frame_index += 1
            else:
                self._stats.dropped_frames += 1

    async def _capture_loop_time_controlled(self) -> AsyncIterator[Frame]:
        """时间控制模式：推进虚拟时间 -> 截图，无真实等待。"""
        if self._config.max_frames is not None:
            total = self._config.max_frames
        elif self._config.max_duration is not None:
            total = max(1, int(round(self._config.max_duration * self._config.fps)))
        else:
            total = 1

        while self._running and self._frame_index < total:
            # 推进虚拟时间（无需等待）
            if self._advance_frame:
                await self._advance_frame(1)
            else:
                await self._page.evaluate("() => window.__advanceFrame && window.__advanceFrame()")

            self._virtual_elapsed_time = (self._frame_index + 1) / self._config.fps

            # 立即截图（虚拟时间已推进，RAF 回调会被同步执行）
            frame_data = await self.capture_frame()

            if frame_data is not None:
                yield Frame(
                    data=frame_data,
                    timestamp=self._virtual_elapsed_time,
                    frame_index=self._frame_index,
                )
                self._frame_index += 1
            else:
                self._stats.dropped_frames += 1

    async def start(self) -> AsyncIterator[Frame]:
        """启动捕获，返回帧迭代器。"""
        self._running = True
        self._start_time = time.monotonic()
        self._frame_index = 0
        self._stats = CaptureStats()
        self._virtual_elapsed_time = 0.0

        await self._ensure_canvas_box()

        loop = self._capture_loop_time_controlled() if self._enable_time_control else self._capture_loop_real_time()

        try:
            async for frame in loop:
                self._stats.total_frames += 1
                yield frame
        finally:
            if self._enable_time_control:
                self._stats.elapsed_time = self._virtual_elapsed_time
                self._stats.actual_fps = self._config.fps if self._stats.total_frames else 0.0
            else:
                self._stats.elapsed_time = time.monotonic() - self._start_time
                self._stats.actual_fps = (
                    self._stats.total_frames / self._stats.elapsed_time
                    if self._stats.elapsed_time > 0 else 0.0
                )
            self._running = False

    def stop(self) -> None:
        """停止捕获。"""
        self._running = False
