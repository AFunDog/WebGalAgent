"""CDP Screencast 录制器：从 Chromium compositor 直接拉帧，绕过 MediaRecorder 帧率限制。

录制流程：
1. Page.startScreencast → 帧保存到临时目录（磁盘 I/O，无编码压力）
2. 可选：WebAudio 捕获（masterGain + MediaStreamTrackProcessor）→ PCM → WAV
3. 录制结束后 ffmpeg 批量编码（不受实时帧率限制），如有音频则合流
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import shutil
import time
import uuid
from pathlib import Path

from webgal_agent.browser.audio_capture import (
    pull_audio_chunks,
    start_audio_recording,
    stop_audio_recording,
)
from webgal_agent.browser.ffmpeg_encoder import encode_from_dir
from webgal_agent.browser.models import RecordingResult, VideoConfig
from webgal_agent.browser.script_loader import load_browser_script

SYNC_MARKER_JS = load_browser_script("sync_marker.js")
NS_PER_SECOND = 1_000_000_000


# ---- 同步调试辅助 ---------------------------------------------------------

def _monotonic_seconds_from_ns(value_ns: int) -> float:
    """将 monotonic_ns 结果转换为秒。"""
    return value_ns / NS_PER_SECOND

def _default_sync_debug_path(output_path: Path) -> Path:
    """为同步调试输出构造默认 JSON 路径。"""
    return Path(f"{output_path}.sync_debug.json")


def _print_sync_debug_event(name: str, ts_ns: int) -> None:
    """打印同步调试关键时间点。"""
    print(f"[ScreencastRecorder][sync-debug] {name}: {_monotonic_seconds_from_ns(ts_ns):.6f}")


def _build_sync_debug_payload(
    *,
    output_path: Path,
    audio_enabled: bool,
    timings_ns: dict[str, int],
    sync_marker: dict[str, object] | None,
    total_frames: int,
    source_fps: float,
    output_fps: float,
    audio_meta: dict[str, int],
    audio_path: Path | None,
) -> dict[str, object]:
    """构造同步调试 JSON 内容。"""
    base_time_ns = timings_ns.get("screencast_start_completed") or timings_ns.get("recording_start")
    relative_timings_ms = {
        key: round((value_ns - base_time_ns) / 1_000_000, 3)
        for key, value_ns in timings_ns.items()
        if base_time_ns is not None
    }

    audio_data_bytes = 0
    audio_duration_estimate_sec = 0.0
    sample_rate = audio_meta.get("sampleRate", 0)
    channels = audio_meta.get("channels", 0)
    if audio_path and audio_path.exists():
        audio_data_bytes = max(audio_path.stat().st_size - 44, 0)
        if sample_rate > 0 and channels > 0:
            audio_duration_estimate_sec = audio_data_bytes / (sample_rate * channels * 4)

    systematic_offset_ms: dict[str, float] = {}
    if "audio_start_completed" in timings_ns and "screencast_start_completed" in timings_ns:
        systematic_offset_ms["audio_started_before_screencast_ms"] = round(
            (timings_ns["screencast_start_completed"] - timings_ns["audio_start_completed"]) / 1_000_000,
            3,
        )
    if "audio_stop_completed" in timings_ns and "screencast_stop_completed" in timings_ns:
        systematic_offset_ms["audio_stopped_after_screencast_ms"] = round(
            (timings_ns["audio_stop_completed"] - timings_ns["screencast_stop_completed"]) / 1_000_000,
            3,
        )

    return {
        "debug_sync": True,
        "output_path": str(output_path),
        "audio_enabled": audio_enabled,
        "timings_monotonic_ns": timings_ns,
        "timings_monotonic": {
            key: round(_monotonic_seconds_from_ns(value_ns), 6)
            for key, value_ns in timings_ns.items()
        },
        "relative_timings_ms": relative_timings_ms,
        "sync_marker": sync_marker or {},
        "frame_stats": {
            "total_frames": total_frames,
            "source_fps": round(source_fps, 6),
            "output_fps": round(output_fps, 6),
        },
        "audio_stats": {
            "sample_rate": sample_rate,
            "channels": channels,
            "audio_data_bytes": audio_data_bytes,
            "estimated_duration_sec": round(audio_duration_estimate_sec, 6),
            "audio_path": str(audio_path) if audio_path else None,
        },
        "systematic_offset_ms": systematic_offset_ms,
    }


def _write_sync_debug_file(path: Path, payload: dict[str, object]) -> None:
    """将同步调试信息写入 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class ScreencastRecorder:
    """CDP Screencast 录制器。

    通过 Chrome DevTools Protocol 的 Page.startScreencast 从 Chromium
    compositor 直接拉取帧，保存到磁盘后再用 ffmpeg 批量编码为视频。

    支持 WebAudio + HTMLAudio 全局捕获：通过 masterGain 汇聚点 +
    MediaStreamTrackProcessor 提取 PCM，最终以 WAV 形式与视频合流。

    与 VideoRecorder（基于 HeadlessExperimental.beginFrame）的区别：
    - 无需 chrome-headless-shell，普通 Chromium/Edge 即可
    - 帧率由 compositor 决定，可随显示器刷新率
    - 非确定性（真实时间流逝），但帧率上限远高于 MediaRecorder

    用法::

        async with BrowserClient(config) as client:
            await client.new_context()
            await client.prepare_webaudio_capture()
            await client.navigate("https://example.com")

            recorder = ScreencastRecorder(client, video_cfg, record_audio=True)
            result = await recorder.start(duration=5.0, format="jpeg")
    """

    def __init__(
        self,
        client,
        video_config: VideoConfig,
        screencast_quality: int = 90,
        record_audio: bool = False,
    ) -> None:
        self._client = client
        self._video_config = video_config
        self._output_path = Path(video_config.output_path)
        self._quality = screencast_quality
        self._record_audio = record_audio
        self._audio_buffer = bytearray()
        self._audio_meta: dict[str, int] = {}

    # ---- 主录制流程 -------------------------------------------------------

    async def start(
        self,
        duration: float = 0,
        context_id: str = "default",
        format: str = "jpeg",
        save_frames_dir: str | Path | None = None,
        stop_condition: str | None = None,
        debug_sync: bool = False,
        sync_debug_path: str | Path | None = None,
    ) -> RecordingResult:
        """开始录制，阻塞 duration 秒后停止并编码输出。

        Args:
            duration: 录制最大时长（秒），传 0 且设置了 stop_condition 时无限等待。
            context_id: 浏览器上下文 ID。
            format: 截图格式，"jpeg" 或 "png"。
            save_frames_dir: 如果设置，保留帧目录（默认录制完成后清理）。
            stop_condition: 可选 JS 表达式，满足时触发停止。
            debug_sync: 是否启用音视频同步调试模式。
            sync_debug_path: 调试 JSON 输出路径，默认写到输出视频同目录。
        """
        if format not in ("jpeg", "png"):
            raise ValueError(f"不支持的格式: {format}，支持 jpeg 和 png")
        if duration <= 0 and not stop_condition:
            raise ValueError("必须指定 duration > 0 或 stop_condition，否则录制无法退出")

        # ---- 初始化：页面、CDP、临时帧目录 --------------------------------
        page = await self._client.get_page(context_id)
        cdp = await self._client.create_cdp_session(context_id)

        viewport = page.viewport_size
        if not viewport:
            raise RuntimeError("无法获取页面 viewport 尺寸")

        ext = "png" if format == "png" else "jpg"
        frames_dir = Path("data/temp") / f"webgal_screencast_{uuid.uuid4().hex[:8]}"
        frames_dir.mkdir(parents=True, exist_ok=True)
        frame_index = 0
        start_time_ns = time.monotonic_ns()
        timings_ns: dict[str, int] = {"recording_start": start_time_ns}
        sync_marker: dict[str, object] | None = None
        frame_queue: asyncio.Queue[tuple[int, bytes] | None] = asyncio.Queue(maxsize=128)
        frame_writer_error: RuntimeError | None = None
        accept_frames = True
        sync_debug_file = (
            Path(sync_debug_path) if sync_debug_path else _default_sync_debug_path(self._output_path)
        )

        def mark_timing(name: str) -> int:
            ts_ns = time.monotonic_ns()
            timings_ns[name] = ts_ns
            if debug_sync:
                _print_sync_debug_event(name, ts_ns)
            return ts_ns

        async def _ack_frame(session_id: int) -> None:
            try:
                await cdp.send("Page.screencastFrameAck", {"sessionId": session_id})
            except Exception:
                pass

        async def _frame_writer() -> None:
            nonlocal frame_writer_error
            while True:
                item = await frame_queue.get()
                try:
                    if item is None:
                        return
                    if frame_writer_error is not None:
                        continue
                    queued_index, queued_data = item
                    frame_path = frames_dir / f"frame_{queued_index:08d}.{ext}"
                    await asyncio.to_thread(frame_path.write_bytes, queued_data)
                except Exception as exc:
                    if frame_writer_error is None:
                        frame_writer_error = RuntimeError(f"帧写盘失败: {exc}")
                finally:
                    frame_queue.task_done()

        writer_task = asyncio.create_task(_frame_writer())

        # CDP 事件回调里只做最小工作：解码、入队、ack。
        # 真正写盘放到后台 writer，避免事件回调被同步磁盘 I/O 阻塞。
        def on_frame(params: dict) -> None:
            nonlocal frame_index, frame_writer_error
            frame_ts_ns = time.monotonic_ns()
            if "first_video_frame" not in timings_ns:
                timings_ns["first_video_frame"] = frame_ts_ns
                if debug_sync:
                    _print_sync_debug_event("first_video_frame", frame_ts_ns)
            timings_ns["last_video_frame"] = frame_ts_ns
            if not accept_frames or frame_writer_error is not None:
                asyncio.ensure_future(_ack_frame(params["sessionId"]))
                return
            try:
                data = base64.b64decode(params["data"])
                frame_queue.put_nowait((frame_index, data))
                frame_index += 1
            except asyncio.QueueFull:
                if frame_writer_error is None:
                    frame_writer_error = RuntimeError("帧写入队列已满，后台 writer 吞吐不足")
            except Exception as exc:
                if frame_writer_error is None:
                    frame_writer_error = RuntimeError(f"帧处理失败: {exc}")
            asyncio.ensure_future(_ack_frame(params["sessionId"]))

        cdp.on("Page.screencastFrame", on_frame)

        screencast_opts: dict = {
            "format": format,
            "maxWidth": viewport["width"],
            "maxHeight": viewport["height"],
            "everyNthFrame": 1,
        }
        if format == "jpeg":
            screencast_opts["quality"] = self._quality

        # ---- 录制启动：先音频，再 screencast，尽量缩小音画起始偏差 --------
        audio_path: Path | None = None
        has_audio = False
        if self._record_audio:
            mark_timing("audio_start_requested")
            has_audio = await self._start_audio_recording(page)
            mark_timing("audio_start_completed")
            if has_audio:
                print("[ScreencastRecorder] WebAudio 捕获已启动 (TrackProcessor + PCM)")

        mark_timing("screencast_start_requested")
        await cdp.send("Page.startScreencast", screencast_opts)
        mark_timing("screencast_start_completed")
        if debug_sync:
            mark_timing("sync_marker_requested")
            try:
                # marker 只用于人工校对音画起始偏移；正常录制不注入任何额外元素/音频。
                sync_marker = await page.evaluate(SYNC_MARKER_JS)
            except Exception as exc:
                sync_marker = {"error": str(exc)}
            mark_timing("sync_marker_completed")
            print(
                "[ScreencastRecorder][sync-debug] marker:",
                json.dumps(sync_marker, ensure_ascii=False),
            )

        # ---- 主循环：停止条件轮询 + 音频增量拉取 ---------------------------
        deadline_ns = start_time_ns + int(duration * NS_PER_SECOND) if duration > 0 else None
        last_pull_ns = time.monotonic_ns()
        pull_task: asyncio.Task | None = None
        try:
            while True:
                now_ns = time.monotonic_ns()
                if frame_writer_error is not None:
                    print(f"[ScreencastRecorder] {frame_writer_error}")
                    break
                # 超时检查
                if deadline_ns is not None and now_ns >= deadline_ns:
                    break
                # 音频增量拉取：启动异步 task（fire-and-forget），不阻塞停止条件检查
                if has_audio and now_ns - last_pull_ns >= NS_PER_SECOND and pull_task is None:
                    pull_task = asyncio.create_task(
                        pull_audio_chunks(cdp, self._audio_buffer, self._audio_meta)
                    )
                    last_pull_ns = now_ns
                # 检查上次拉取是否完成
                if pull_task is not None and pull_task.done():
                    with contextlib.suppress(Exception):
                        await pull_task
                    pull_task = None
                # 停止条件检查（走 CDP Runtime.evaluate，绕过已失活的 page 对象）
                if stop_condition:
                    try:
                        resp = await cdp.send("Runtime.evaluate", {
                            "expression": f"!!({stop_condition})",
                            "returnByValue": True,
                        })
                        if resp.get("result", {}).get("value"):
                            break
                    except Exception as e:
                        print(f"[ScreencastRecorder] 录制过程异常: {e}")
                        break
                # 迭代间隔
                if not stop_condition:
                    if deadline_ns is None:
                        break
                    remaining_ns = deadline_ns - time.monotonic_ns()
                    if remaining_ns <= 0:
                        break
                    await asyncio.sleep(min(0.5, _monotonic_seconds_from_ns(remaining_ns)))
                else:
                    await asyncio.sleep(0.5)
        except Exception as e:
            print(f"[ScreencastRecorder] 录制过程异常: {e}")
        # ---- 录制收尾：停止 screencast / 音频 / 编码 ------------------------

        # 等待未完成的拉取任务
        if pull_task is not None:
            with contextlib.suppress(Exception):
                await pull_task

        # 安全停止 screencast（页面可能已导航，忽略 target closed 错误）
        mark_timing("stop_requested")
        try:
            mark_timing("screencast_stop_requested")
            await cdp.send("Page.stopScreencast")
            mark_timing("screencast_stop_completed")
        except Exception:
            pass
        accept_frames = False
        await asyncio.sleep(0.1)
        await frame_queue.join()
        await frame_queue.put(None)
        with contextlib.suppress(Exception):
            await writer_task

        # 停止音频轮询并完成录制
        if has_audio:
            mark_timing("audio_stop_requested")
            audio_path = await stop_audio_recording(cdp, self._audio_buffer, self._audio_meta)
            mark_timing("audio_stop_completed")
            if audio_path:
                print(f"[ScreencastRecorder] 音频已保存: {audio_path}")
            else:
                has_audio = False

        if frame_writer_error is not None:
            shutil.rmtree(frames_dir, ignore_errors=True)
            if audio_path and audio_path.exists():
                print(f"[ScreencastRecorder] 音频文件保留: {audio_path}")
            raise frame_writer_error

        total_frames = frame_index
        actual_duration = _monotonic_seconds_from_ns(time.monotonic_ns() - start_time_ns)
        source_fps = total_frames / actual_duration if actual_duration > 0 else 0

        print(f"[ScreencastRecorder] 捕获帧数: {total_frames}")
        print(f"[ScreencastRecorder] 截图格式: {format.upper()}")
        print(f"[ScreencastRecorder] 实际录制时长: {actual_duration:.2f}s")
        print(f"[ScreencastRecorder] 源帧率: {source_fps:.2f} FPS")

        if total_frames == 0:
            shutil.rmtree(frames_dir, ignore_errors=True)
            if audio_path and audio_path.exists():
                print(f"[ScreencastRecorder] 音频文件保留: {audio_path}")
            if stop_condition:
                return RecordingResult(
                    output_path=self._output_path,
                    total_frames=0,
                    duration=0,
                    actual_fps=0,
                    file_size_mb=0,
                    source_fps=0,
                    output_fps=self._video_config.fps,
                    has_audio=False,
                )
            raise RuntimeError("Screencast 未捕获到任何帧")

        output_fps = int(self._video_config.fps)
        print(f"[ScreencastRecorder] 源帧率: {source_fps:.2f} FPS → 输出帧率: {output_fps} FPS")
        print("[ScreencastRecorder] 开始 FFmpeg 编码 (tmix 时间混合 + fps 输出)...")
        encode_start_ns = time.monotonic_ns()

        try:
            await encode_from_dir(
                self._output_path,
                self._video_config,
                frames_dir,
                ext,
                source_fps,
                output_fps,
                audio_path,
            )
        except Exception as e:
            print(f"[ScreencastRecorder] FFmpeg 编码失败: {e}")

        encode_elapsed = _monotonic_seconds_from_ns(time.monotonic_ns() - encode_start_ns)
        print(f"[ScreencastRecorder] FFmpeg 编码完成，耗时 {encode_elapsed:.1f}s")

        # ---- 清理 ----------------------------------------------------------
        if save_frames_dir:
            keep_dir = Path(save_frames_dir)
            if keep_dir.exists():
                shutil.rmtree(keep_dir, ignore_errors=True)
            shutil.move(str(frames_dir), str(keep_dir))
            print(f"[ScreencastRecorder] 已保留帧目录: {keep_dir}")
        else:
            shutil.rmtree(frames_dir, ignore_errors=True)
        if audio_path and audio_path.exists():
            print(f"[ScreencastRecorder] 音频文件保留: {audio_path} "
                  f"({audio_path.stat().st_size / 1024:.1f}KB)")

        output_exists = self._output_path.exists()
        file_size = self._output_path.stat().st_size / (1024 * 1024) if output_exists else 0
        if debug_sync:
            payload = _build_sync_debug_payload(
                output_path=self._output_path,
                audio_enabled=has_audio,
                timings_ns=timings_ns,
                sync_marker=sync_marker,
                total_frames=total_frames,
                source_fps=source_fps,
                output_fps=output_fps,
                audio_meta=self._audio_meta,
                audio_path=audio_path,
            )
            _write_sync_debug_file(sync_debug_file, payload)
            print(f"[ScreencastRecorder][sync-debug] JSON已保存: {sync_debug_file}")

        return RecordingResult(
            output_path=self._output_path,
            total_frames=total_frames,
            duration=actual_duration,
            actual_fps=source_fps,
            file_size_mb=file_size,
            source_fps=source_fps,
            output_fps=output_fps,
            has_audio=has_audio,
            sync_debug_path=sync_debug_file if debug_sync else None,
        )

    # ── 音频录制辅助 ──────────────────────────────────────────────

    async def _start_audio_recording(self, page) -> bool:
        return await start_audio_recording(page)
