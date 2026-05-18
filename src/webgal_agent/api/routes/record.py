"""浏览器录制 API 路由。

录制操作通过子进程调用 CLI 工具完成，Playwright 运行在独立进程中，
与 FastAPI/Uvicorn 的 event loop 完全隔离。

这个模块的重点不是浏览器细节，而是“子进程协议”：

1. 构造 `python -m webgal_agent.browser.demo record --json`
2. 读取 stderr 作为实时日志
3. 读取 stdout 最后一行 JSON 作为最终结果
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter
from pydantic import BaseModel
from webgal_agent.browser.paths import default_recording_output_path

router = APIRouter(prefix="/api/record", tags=["record"])

# ---- 配置读取 -------------------------------------------------------------

def _resolve_config_path() -> Path | None:
    candidates = [
        Path("src/configs/record.yaml"),
        Path(__file__).parent.parent.parent / "configs" / "record.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


_CONFIG_PATH = _resolve_config_path()


def _load_config() -> dict:
    if _CONFIG_PATH and _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def _record_defaults() -> dict:
    return _load_config()


class RecordConfigRequest(BaseModel):
    url: str
    output_path: str | None = None
    duration: float = 0
    fps: float = 30.0
    canvas_selector: str = "auto"
    scene_path: str = "index.txt"
    stop_condition: str | None = None
    browser_type: str = "msedge"
    headless: bool = False
    viewport_width: int = 1920
    viewport_height: int = 1080
    format: str = "jpeg"
    quality: int = 90
    record_audio: bool = False
    executable_path: str | None = None
    debug_sync: bool = False
    sync_debug_path: str | None = None
    game_config: dict[str, int] | None = None


class RecordResultResponse(BaseModel):
    success: bool
    message: str
    output_path: str | None = None
    total_frames: int = 0
    duration: float = 0.0
    source_fps: float = 0.0
    output_fps: float = 0.0
    file_size_mb: float = 0.0
    has_audio: bool = False


_recording_state: dict[str, Any] = {
    "recording": False,
    "proc": None,
    "progress": 0.0,
    "logs": [],
}


# ---- 子进程协调 -----------------------------------------------------------

def _read_stderr(proc: subprocess.Popen, logs: list[str]) -> None:
    """在后台线程中逐行读取子进程 stderr，追加到共享日志列表。"""
    for line in proc.stderr:
        logs.append(line.rstrip())


def _build_cli_args(req: RecordConfigRequest, output_path: str) -> list[str]:
    """构建 demo.py record 子进程命令行参数。"""
    args = [
        sys.executable, "-m", "webgal_agent.browser.demo", "record",
        "--url", req.url,
        "--output", output_path,
        "--fps", str(req.fps),
        "--width", str(req.viewport_width),
        "--height", str(req.viewport_height),
        "--selector", req.canvas_selector,
        "--scene", req.scene_path,
    ]
    if req.duration > 0:
        args.extend(["--duration", str(req.duration)])
    if req.stop_condition:
        args.extend(["--stop-on", req.stop_condition])
    args.extend([
        "--browser", req.browser_type,
        "--screencast-quality", str(req.quality),
        "--format", req.format,
        "--json",
    ])
    if req.headless:
        args.append("--headless")
    if req.record_audio:
        args.append("--record-audio")
    if req.executable_path:
        args.extend(["--executable", req.executable_path])
    if req.debug_sync:
        args.append("--debug-sync")
    if req.sync_debug_path:
        args.extend(["--sync-debug-path", req.sync_debug_path])
    if req.game_config:
        args.extend(["--game-config", json.dumps(req.game_config)])
    return args


@router.post("/start", response_model=RecordResultResponse)
async def start_record(req: RecordConfigRequest) -> RecordResultResponse:
    """开始录制（启动独立子进程）。"""
    if _recording_state["recording"]:
        return RecordResultResponse(
            success=False,
            message="已有录制任务正在进行中",
        )

    output_path = req.output_path
    if not output_path:
        output_path = str(default_recording_output_path())

    # 确保输出目录存在
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cli_args = _build_cli_args(req, str(output_path))

    try:
        proc = subprocess.Popen(
            cli_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception as e:
        return RecordResultResponse(
            success=False,
            message=f"启动录制进程失败: {e}",
        )

    _recording_state["recording"] = True
    _recording_state["proc"] = proc
    _recording_state["progress"] = 0.0
    _recording_state["logs"] = []

    # 后台线程：实时读取 stderr 日志
    t = threading.Thread(target=_read_stderr, args=(proc, _recording_state["logs"]), daemon=True)
    t.start()
    _recording_state["stderr_thread"] = t

    # 异步等待子进程完成
    asyncio.ensure_future(_wait_recording(proc))

    return RecordResultResponse(
        success=True,
        message="录制已启动",
        output_path=output_path,
    )


async def _wait_recording(proc: subprocess.Popen) -> None:
    """等待录制子进程完成，解析 JSON 结果。"""
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, proc.wait)

        # 等待 stderr 读取线程完成
        t = _recording_state.get("stderr_thread")
        if t:
            t.join(timeout=2)

        # 读取 stdout（未被线程消费）
        stdout = proc.stdout.read() if proc.stdout else ""

        if proc.returncode == 0:
            lines = stdout.strip().splitlines() if stdout else []
            if lines:
                result = json.loads(lines[-1])
                _recording_state["last_result"] = result
        else:
            # 优先从日志中提取错误信息
            logs = _recording_state.get("logs", [])
            error_msg = "\n".join(logs[-10:]) if logs else ""
            _recording_state["last_result"] = {
                "success": False,
                "message": error_msg or f"录制进程异常退出 (code={proc.returncode})",
            }
    except Exception as e:
        _recording_state["last_result"] = {
            "success": False,
            "message": f"录制异常: {e}",
        }
    finally:
        _recording_state["recording"] = False
        _recording_state["proc"] = None
        _recording_state["progress"] = 100.0


# ---- 路由 -----------------------------------------------------------------

@router.post("/stop")
async def stop_record() -> dict:
    """停止录制（终止子进程）。"""
    proc = _recording_state.get("proc")
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    _recording_state["recording"] = False
    return {"success": True, "message": "已停止录制"}


@router.get("/status")
async def get_record_status() -> dict:
    """获取录制状态和结果。"""
    logs = _recording_state.get("logs", [])
    proc = _recording_state.get("proc")
    if proc and proc.poll() is None:
        return {
            "recording": True,
            "progress": _recording_state.get("progress", 0),
            "message": "正在录制中...",
            "logs": logs,
        }
    last = _recording_state.get("last_result")
    if last:
        return {"recording": False, "progress": 100.0, "logs": logs, **last}
    return {"recording": False, "progress": 0, "logs": logs}


@router.get("/config")
async def get_record_config() -> dict:
    """获取录制配置默认值。"""
    defaults = _record_defaults()
    return {
        "url": defaults.get("url", ""),
        "format": defaults.get("format", "jpeg"),
        "quality": defaults.get("quality", 90),
        "fps": defaults.get("fps", 30),
        "duration": defaults.get("duration", 5.0),
        "canvas_selector": defaults.get("canvas_selector", "auto"),
        "scene_path": defaults.get("scene_path", "index.txt"),
        "stop_condition": defaults.get("stop_condition", ""),
        "browser_type": defaults.get("browser_type", "msedge"),
        "headless": defaults.get("headless", False),
        "viewport_width": defaults.get("viewport_width", 1920),
        "viewport_height": defaults.get("viewport_height", 1080),
        "record_audio": defaults.get("record_audio", False),
        "executable_path": defaults.get("executable_path", ""),
        "debug_sync": defaults.get("debug_sync", False),
        "sync_debug_path": defaults.get("sync_debug_path", ""),
        "game_config": defaults.get("game_config", {}),
    }
