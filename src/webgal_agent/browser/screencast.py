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
import shutil
import struct
import time
import uuid
from pathlib import Path

from webgal_agent.browser.models import RecordingResult, VideoConfig


def _find_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("未找到 ffmpeg，请安装 ffmpeg 并确保其在 PATH 中。")
    return ffmpeg


def _codec_from_ext(output_path: Path) -> tuple[str, str]:
    suffix = output_path.suffix.lower()
    if suffix == ".webm":
        return "webm", "libvpx-vp9"
    return "mp4", "libx264"


def _write_wav_header(f, data_size: int, sample_rate: int, channels: int) -> None:
    """写入 WAV header (IEEE float32)，为 PCM 数据提供完整时间轴。"""
    byte_rate = sample_rate * channels * 4
    block_align = channels * 4
    f.write(b"RIFF")
    f.write(struct.pack("<I", 36 + data_size))
    f.write(b"WAVE")
    f.write(b"fmt ")
    f.write(struct.pack("<I", 16))          # chunk size
    f.write(struct.pack("<H", 3))           # WAVE_FORMAT_IEEE_FLOAT
    f.write(struct.pack("<H", channels))
    f.write(struct.pack("<I", sample_rate))
    f.write(struct.pack("<I", byte_rate))
    f.write(struct.pack("<H", block_align))
    f.write(struct.pack("<H", 32))          # bits per sample
    f.write(b"data")
    f.write(struct.pack("<I", data_size))


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

    async def start(
        self,
        duration: float = 0,
        context_id: str = "default",
        format: str = "jpeg",
        save_frames_dir: str | Path | None = None,
        stop_condition: str | None = None,
    ) -> RecordingResult:
        """开始录制，阻塞 duration 秒后停止并编码输出。

        Args:
            duration: 录制最大时长（秒），传 0 且设置了 stop_condition 时无限等待。
            context_id: 浏览器上下文 ID。
            format: 截图格式，"jpeg" 或 "png"。
            save_frames_dir: 如果设置，保留帧目录（默认录制完成后清理）。
            stop_condition: 可选 JS 表达式，满足时触发停止。
        """
        if format not in ("jpeg", "png"):
            raise ValueError(f"不支持的格式: {format}，支持 jpeg 和 png")
        if duration <= 0 and not stop_condition:
            raise ValueError("必须指定 duration > 0 或 stop_condition，否则录制无法退出")

        page = await self._client.get_page(context_id)
        cdp = await self._client.create_cdp_session(context_id)

        viewport = page.viewport_size
        if not viewport:
            raise RuntimeError("无法获取页面 viewport 尺寸")

        ext = "png" if format == "png" else "jpg"
        frames_dir = Path("data/temp") / f"webgal_screencast_{uuid.uuid4().hex[:8]}"
        frames_dir.mkdir(parents=True, exist_ok=True)
        frame_index = 0
        start_time = time.monotonic()

        async def _ack_frame(session_id: int) -> None:
            try:
                await cdp.send("Page.screencastFrameAck", {"sessionId": session_id})
            except Exception:
                pass

        def on_frame(params: dict) -> None:
            nonlocal frame_index
            data = base64.b64decode(params["data"])
            frame_path = frames_dir / f"frame_{frame_index:08d}.{ext}"
            frame_path.write_bytes(data)
            frame_index += 1
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

        # 启动音频录制（在 screencast 之前，尽量接近同步）
        audio_path: Path | None = None
        has_audio = False
        if self._record_audio:
            has_audio = await self._start_audio_recording(page)
            if has_audio:
                print("[ScreencastRecorder] WebAudio 捕获已启动 (TrackProcessor + PCM)")

        await cdp.send("Page.startScreencast", screencast_opts)

        # 录制等待：停止条件检查（主循环）+ 音频拉取（异步 task，不阻塞主循环）
        deadline = time.monotonic() + duration if duration > 0 else float("inf")
        last_pull = time.monotonic()
        pull_task: asyncio.Task | None = None
        try:
            while True:
                now = time.monotonic()
                # 超时检查
                if now >= deadline:
                    break
                # 音频增量拉取：启动异步 task（fire-and-forget），不阻塞停止条件检查
                if has_audio and now - last_pull >= 1.0 and pull_task is None:
                    pull_task = asyncio.create_task(self._pull_audio_chunks(cdp))
                    last_pull = now
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
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        break
                    await asyncio.sleep(min(0.5, remaining))
                else:
                    await asyncio.sleep(0.5)
        except Exception as e:
            print(f"[ScreencastRecorder] 录制过程异常: {e}")
        # 等待未完成的拉取任务
        if pull_task is not None:
            with contextlib.suppress(Exception):
                await pull_task

        # 安全停止 screencast（页面可能已导航，忽略 target closed 错误）
        try:
            await cdp.send("Page.stopScreencast")
        except Exception:
            pass
        await asyncio.sleep(0.1)

        # 停止音频轮询并完成录制
        if has_audio:
            audio_path = await self._stop_audio_recording(cdp)
            if audio_path:
                print(f"[ScreencastRecorder] 音频已保存: {audio_path}")
            else:
                has_audio = False

        total_frames = frame_index
        actual_duration = time.monotonic() - start_time
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
        encode_start = time.monotonic()

        encode_error: str | None = None
        try:
            await self._encode_from_dir(frames_dir, ext, source_fps, output_fps, audio_path)
        except Exception as e:
            encode_error = str(e)
            print(f"[ScreencastRecorder] FFmpeg 编码失败: {e}")

        encode_elapsed = time.monotonic() - encode_start
        print(f"[ScreencastRecorder] FFmpeg 编码完成，耗时 {encode_elapsed:.1f}s")

        # 清理临时文件
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

        return RecordingResult(
            output_path=self._output_path,
            total_frames=total_frames,
            duration=actual_duration,
            actual_fps=source_fps,
            file_size_mb=file_size,
            source_fps=source_fps,
            output_fps=output_fps,
            has_audio=has_audio,
        )

    # ── 音频录制辅助 ──────────────────────────────────────────────

    async def _start_audio_recording(self, page) -> bool:
        """启动 MediaStreamTrackProcessor PCM 提取。

        调用注入脚本中的 __startTrackProcessor()，创建 TrackProcessor
        reader loop，持续从 MediaStreamTrack 读取 AudioData → PCM。
        """
        try:
            result = await page.evaluate("""
            () => {
                if (!window.__startTrackProcessor) return false;
                return window.__startTrackProcessor();
            }
            """)
            return bool(result)
        except Exception as e:
            print(f"[ScreencastRecorder] 音频捕获启动失败: {e}")
            return False

    async def _pull_audio_chunks(self, cdp) -> None:
        """通过 CDP 拉取累积的 PCM 数据（base64 编码的 Float32 原始字节）。"""
        try:
            resp = await cdp.send("Runtime.evaluate", {
                "expression": """
                (() => {
                    const chunks = window.__audioPcmChunks;
                    if (!chunks || chunks.length === 0) return null;
                    window.__audioPcmChunks = [];

                    // 拼接所有 Float32Array
                    let totalLen = 0;
                    for (const c of chunks) totalLen += c.length;
                    const combined = new Float32Array(totalLen);
                    let offset = 0;
                    for (const c of chunks) {
                        combined.set(c, offset);
                        offset += c.length;
                    }

                    // Float32 → Uint8 → base64
                    const bytes = new Uint8Array(combined.buffer);
                    const chunkSize = 0x8000;
                    const parts = [];
                    for (let i = 0; i < bytes.length; i += chunkSize) {
                        parts.push(String.fromCharCode.apply(
                            null, bytes.subarray(i, i + chunkSize)
                        ));
                    }
                    return {
                        pcm_b64: btoa(parts.join('')),
                        meta: window.__audioPcmMeta || {}
                    };
                })()
                """,
                "returnByValue": True,
            })
            result = resp.get("result", {}).get("value")
            if result and result.get("pcm_b64"):
                pcm_bytes = base64.b64decode(result["pcm_b64"])
                self._audio_buffer.extend(pcm_bytes)

                meta = result.get("meta", {})
                if meta and not self._audio_meta:
                    self._audio_meta = {
                        "sampleRate": meta.get("sampleRate", 48000),
                        "channels": meta.get("channels", 2),
                    }

                kb = len(pcm_bytes) / 1024
                total_kb = len(self._audio_buffer) / 1024
                print(f"[ScreencastRecorder] PCM拉取: +{kb:.1f}KB, buffer {total_kb:.1f}KB")
        except Exception as e:
            print(f"[ScreencastRecorder] PCM拉取失败: {e}")

    async def _stop_audio_recording(self, cdp) -> Path | None:
        """拉取残留 PCM，写入 raw f32le 文件供 ffmpeg 编码。"""
        try:
            resp = await cdp.send("Runtime.evaluate", {
                "expression": """
                (() => {
                    const chunks = window.__audioPcmChunks;
                    if (!chunks || chunks.length === 0) return null;
                    window.__audioPcmChunks = [];

                    let totalLen = 0;
                    for (const c of chunks) totalLen += c.length;
                    const combined = new Float32Array(totalLen);
                    let offset = 0;
                    for (const c of chunks) {
                        combined.set(c, offset);
                        offset += c.length;
                    }

                    const bytes = new Uint8Array(combined.buffer);
                    const chunkSize = 0x8000;
                    const parts = [];
                    for (let i = 0; i < bytes.length; i += chunkSize) {
                        parts.push(String.fromCharCode.apply(
                            null, bytes.subarray(i, i + chunkSize)
                        ));
                    }
                    return {
                        pcm_b64: btoa(parts.join('')),
                        meta: window.__audioPcmMeta || {}
                    };
                })()
                """,
                "returnByValue": True,
            })
            result = resp.get("result", {}).get("value")
            if result and result.get("pcm_b64"):
                pcm_bytes = base64.b64decode(result["pcm_b64"])
                self._audio_buffer.extend(pcm_bytes)

                meta = result.get("meta", {})
                if meta and not self._audio_meta:
                    self._audio_meta = {
                        "sampleRate": meta.get("sampleRate", 48000),
                        "channels": meta.get("channels", 2),
                    }
        except Exception as e:
            print(f"[ScreencastRecorder] PCM残留拉取失败: {e}")

        if len(self._audio_buffer) == 0:
            self._audio_buffer = bytearray()
            return None

        pcm_bytes = bytes(self._audio_buffer)
        self._audio_buffer = bytearray()

        # 诊断：检查 PCM 信号是否真的有振幅
        await self._diagnose_audio_signal(cdp, pcm_bytes)

        sr = self._audio_meta.get("sampleRate", 48000)
        ch = self._audio_meta.get("channels", 2)

        audio_path = Path("data/temp") / f"webgal_audio_{uuid.uuid4().hex[:8]}.wav"
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        with open(audio_path, "wb") as f:
            _write_wav_header(f, len(pcm_bytes), sr, ch)
            f.write(pcm_bytes)
        print(f"[ScreencastRecorder] WAV已保存: {audio_path} "
              f"({len(pcm_bytes) / 1024:.1f}KB, sr={sr}, ch={ch})")
        return audio_path

    async def _diagnose_audio_signal(self, cdp, pcm_bytes: bytes) -> None:
        """打印音频信号诊断信息：振幅统计 + AudioContext 状态 + audio 元素数。"""
        # 本地 PCM 振幅检查（采样前 4000 个 float 避免全量扫描）
        sample_count = min(len(pcm_bytes) // 4, 4000)
        max_abs = 0.0
        sum_abs = 0.0
        for i in range(0, sample_count * 4, 4):
            val = abs(struct.unpack_from("<f", pcm_bytes, i)[0])
            sum_abs += val
            if val > max_abs:
                max_abs = val
        mean_abs = sum_abs / sample_count if sample_count > 0 else 0.0
        print(f"[ScreencastRecorder] 信号诊断 (本地PCM, 前{sample_count}采样): "
              f"max={max_abs:.6f}, mean={mean_abs:.6f}, "
              f"{'有信号' if max_abs > 1e-4 else '静音'}")

        # 页面端诊断
        try:
            resp = await cdp.send("Runtime.evaluate", {
                "expression": "window.__checkAudioSignal ? window.__checkAudioSignal() : null",
                "returnByValue": True,
            })
            diag = resp.get("result", {}).get("value")
            if diag:
                print(f"[ScreencastRecorder] 信号诊断 (页面): "
                      f"status={diag.get('status')}, "
                      f"max={diag.get('maxAmplitude', 0):.6f}, "
                      f"mean={diag.get('meanAmplitude', 0):.6f}, "
                      f"samples={diag.get('sampleCount', 0)}, "
                      f"ctxStates={diag.get('audioContextStates', [])}, "
                      f"audioElements={diag.get('routedAudioElements', 0)}")
        except Exception as e:
            print(f"[ScreencastRecorder] 页面诊断失败: {e}")

    # ── FFmpeg 编码 ────────────────────────────────────────────────

    async def _encode_from_dir(
        self,
        frames_dir: Path,
        ext: str,
        source_fps: float,
        output_fps: int,
        audio_path: Path | None = None,
    ) -> None:
        """从帧目录批量编码视频（录制完成后离线执行），可选融合 PCM 音频。"""
        ffmpeg = _find_ffmpeg()
        fmt, encoder = _codec_from_ext(self._output_path)

        self._output_path.parent.mkdir(parents=True, exist_ok=True)

        args = [
            ffmpeg, "-y",
            "-framerate", f"{source_fps:.6f}",
            "-i", str(frames_dir / f"frame_%08d.{ext}"),
        ]

        if audio_path and audio_path.exists():
            args.extend([
                "-i", str(audio_path),
                "-af", "aresample=async=1:first_pts=0",
            ])

        args.extend([
            "-vf", f"tmix=2:weights='1 1',fps={output_fps}",
        ])

        if audio_path and audio_path.exists():
            args.extend(["-map", "0:v:0", "-map", "1:a:0"])
            args.extend(["-c:v", encoder, "-crf", str(self._video_config.quality)])
            if fmt == "webm":
                args.extend(["-c:a", "libopus"])
            else:
                args.extend(["-c:a", "aac"])
            args.append("-shortest")
        else:
            args.extend(["-c:v", encoder, "-crf", str(self._video_config.quality), "-an"])

        if fmt == "webm":
            args.extend(["-deadline", "good", "-cpu-used", "2", "-f", "webm"])
        else:
            args.extend(["-preset", "ultrafast", "-pix_fmt", "yuv420p", "-f", "mp4"])

        args.append(str(self._output_path))

        print(f"[ScreencastRecorder] ffmpeg {' '.join(args[1:])}")

        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg 编码失败:\n{stderr.decode()}")
