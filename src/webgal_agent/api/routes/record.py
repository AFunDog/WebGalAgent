"""浏览器录制 API 路由。"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from webgal_agent.browser import (
    BrowserClient,
    DefaultBrowserConfig,
    ScreencastRecorder,
    VideoConfig,
    Selector,
    SelectorType,
)

router = APIRouter(prefix="/api/record", tags=["record"])

# 加载配置文件 — 尝试多个可能的路径
def _resolve_config_path() -> Path | None:
    """解析录制配置文件路径。"""
    candidates = [
        Path("src/configs/record.yaml"),  # 从项目根目录运行
        Path(__file__).parent.parent.parent / "configs" / "record.yaml",  # 绝对路径
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


_CONFIG_PATH = _resolve_config_path()


def _load_config() -> dict:
    """加载录制配置文件。"""
    if _CONFIG_PATH and _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


# 模块导入时预加载，但 API 接口每次请求时都会重新读取
def _record_defaults() -> dict:
    """获取录制配置默认值（每次调用都重新读取文件）。"""
    return _load_config()


class RecordConfigRequest(BaseModel):
    """录制配置请求。"""

    url: str
    output_path: str | None = None
    duration: float = 5.0
    fps: float = 30.0
    canvas_selector: str = "div._MainStage_main_9enex_1"
    browser_type: str = "chromium"
    headless: bool = False
    viewport_width: int = 1920
    viewport_height: int = 1080
    channel: str | None = None
    format: str = "jpeg"
    quality: int = 90


class RecordResultResponse(BaseModel):
    """录制结果响应。"""

    success: bool
    message: str
    output_path: str | None = None
    total_frames: int = 0
    duration: float = 0.0
    source_fps: float = 0.0
    output_fps: float = 0.0
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
        config = DefaultBrowserConfig(
            browser_type=req.browser_type,
            headless=req.headless,
            viewport_width=req.viewport_width,
            viewport_height=req.viewport_height,
            channel=req.channel,
        )

        async with BrowserClient(config) as client:
            # 创建上下文
            await client.new_context(context_id="default")

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

            # 配置录制
            video_cfg = VideoConfig(
                output_path=output_path,
                fps=req.fps,
            )

            recorder = ScreencastRecorder(
                client,
                video_cfg,
                screencast_quality=req.quality,
            )

            result = await recorder.start(
                duration=req.duration,
                format=req.format,
            )

            _recording_state["recording"] = False
            _recording_state["progress"] = 100.0

            return RecordResultResponse(
                success=True,
                message="录制完成",
                output_path=str(result.output_path),
                total_frames=result.total_frames,
                duration=result.duration,
                source_fps=result.source_fps,
                output_fps=result.output_fps,
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
    _recording_state["recording"] = False
    return {"success": True, "message": "已停止录制"}


@router.get("/status", response_model=RecordStatusResponse)
async def get_record_status() -> RecordStatusResponse:
    """获取录制状态。"""
    return RecordStatusResponse(
        recording=_recording_state["recording"],
        progress=_recording_state.get("progress"),
    )


@router.get("/config")
async def get_record_config() -> dict:
    """获取录制配置默认值（每次请求都重新读取配置文件）。"""
    defaults = _record_defaults()
    return {
        "format": defaults.get("format", "jpeg"),
        "quality": defaults.get("quality", 90),
        "fps": defaults.get("fps", 30),
        "duration": defaults.get("duration", 5.0),
        "canvas_selector": defaults.get("canvas_selector", "div._MainStage_main_9enex_1"),
        "browser_type": defaults.get("browser_type", "chromium"),
        "headless": defaults.get("headless", False),
        "viewport_width": defaults.get("viewport_width", 1920),
        "viewport_height": defaults.get("viewport_height", 1080),
    }
