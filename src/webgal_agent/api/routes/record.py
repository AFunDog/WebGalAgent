"""浏览器录制 API 路由。"""

from __future__ import annotations

import asyncio
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from webgal_agent.browser import (
    BrowserClient,
    DefaultBrowserConfig,
    VideoRecorder,
    CaptureConfig,
    VideoConfig,
    Selector,
    SelectorType,
)

router = APIRouter(prefix="/record", tags=["record"])


class RecordConfigRequest(BaseModel):
    """录制配置请求。"""

    url: str
    output_path: str | None = None
    duration: float = 5.0
    fps: float = 30.0
    canvas_selector: str = "div._MainStage_main_9enex_1"
    browser_type: str = "chromium"
    headless: bool = False
    executable_path: str | None = None


class RecordResultResponse(BaseModel):
    """录制结果响应。"""

    success: bool
    message: str
    output_path: str | None = None
    total_frames: int = 0
    duration: float = 0.0
    file_size_mb: float = 0.0


class RecordStatusResponse(BaseModel):
    """录制状态响应。"""

    recording: bool
    progress: float | None = None
    message: str | None = None


# 全局录制状态
_recording_state: dict[str, Any] = {
    "recording": False,
    "task": None,
    "client": None,
    "recorder": None,
}


@router.post("/start", response_model=RecordResultResponse)
async def start_record(req: RecordConfigRequest, background_tasks: BackgroundTasks) -> RecordResultResponse:
    """开始录制。"""
    if _recording_state["recording"]:
        return RecordResultResponse(
            success=False,
            message="已有录制任务正在进行中",
        )

    output_path = req.output_path
    if not output_path:
        output_path = str(Path("data/temp") / f"record_{uuid.uuid4().hex[:8]}.mp4")
    else:
        output_path = str(Path(output_path))

    _recording_state["recording"] = True
    _recording_state["progress"] = 0.0

    try:
        # 构建确定性录制所需的 Chrome 启动参数
        deterministic_args: list[str] | None = None
        if req.executable_path:
            deterministic_args = [
                "--run-all-compositor-stages-before-draw",
                "--enable-begin-frame-control",
                "--disable-threaded-animation",
                "--disable-threaded-scrolling",
                "--disable-frame-rate-limit",
                "--disable-gpu-vsync",
                "--disable-background-timer-throttling",
                "--disable-renderer-backgrounding",
                "--force-color-profile=srgb",
            ]

        config = DefaultBrowserConfig(
            browser_type=req.browser_type,
            headless=req.headless,
            viewport_width=1280,
            viewport_height=720,
            executable_path=req.executable_path,
            launch_args=deterministic_args,
        )

        async with BrowserClient(config) as client:
            # 拦截脚本注入
            await client.add_script_injection(
                url_pattern="**/index-e1b3c40e.js",
                inject_code="window.changeScene = gCe;\nwindow.toggleAuto = wU;",
            )

            # 导航到目标 URL
            try:
                await client.navigate(req.url, wait_until="load")
            except Exception:
                await asyncio.sleep(5)

            # 等待 changeScene 函数就绪
            page = await client.get_page()
            try:
                await page.wait_for_function(
                    "() => typeof window.changeScene === 'function' && typeof window.toggleAuto === 'function'",
                    timeout=10000,
                )
                await page.evaluate("""
                    async () => {
                        window.toggleAuto();
                    }
                """)
            except Exception:
                pass

            # 等待目标元素出现
            found = await client.wait_for(
                Selector(type=SelectorType.CSS, value=req.canvas_selector),
                state="visible",
                timeout=10000,
            )
            if not found:
                _recording_state["recording"] = False
                return RecordResultResponse(
                    success=False,
                    message=f"未找到目标元素: {req.canvas_selector}",
                )

            await asyncio.sleep(1)

            # 创建 CDP Session
            cdp = await client.create_cdp_session()
            await client.prepare_time_control(fps=req.fps)

            # 配置录制
            capture_cfg = CaptureConfig(
                fps=req.fps,
                canvas_selector=req.canvas_selector,
                max_duration=req.duration,
            )
            video_cfg = VideoConfig(
                output_path=output_path,
                fps=req.fps,
                codec="libx264",
            )

            recorder = VideoRecorder(
                cdp,
                page,
                video_cfg,
                capture_cfg,
                advance_frame_fn=client.advance_frame,
            )

            result = await recorder.start()

            _recording_state["recording"] = False
            _recording_state["progress"] = 100.0

            return RecordResultResponse(
                success=True,
                message="录制完成",
                output_path=str(result.output_path),
                total_frames=result.total_frames,
                duration=result.duration,
                file_size_mb=result.file_size_mb,
            )

    except Exception as e:
        _recording_state["recording"] = False
        return RecordResultResponse(
            success=False,
            message=f"录制失败: {str(e)}",
        )


@router.post("/stop")
async def stop_record() -> dict:
    """停止录制。"""
    # VideoRecorder.stop() 是同步方法，需要在事件循环中调用
    recorder = _recording_state.get("recorder")
    if recorder:
        recorder.stop()
    _recording_state["recording"] = False
    return {"success": True, "message": "已停止录制"}


@router.get("/status", response_model=RecordStatusResponse)
async def get_record_status() -> RecordStatusResponse:
    """获取录制状态。"""
    return RecordStatusResponse(
        recording=_recording_state["recording"],
        progress=_recording_state.get("progress"),
    )
