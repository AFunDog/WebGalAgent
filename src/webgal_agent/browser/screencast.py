"""CDP Screencast 录制器：从 Chromium compositor 直接拉帧，绕过 MediaRecorder 帧率限制。

录制流程：
1. Page.startScreencast → 帧保存到临时目录（磁盘 I/O，无编码压力）
2. 可选：WebAudio 捕获（Hook AudioNode.prototype.connect）→ MediaRecorder → 音频 webm
3. 录制结束后 ffmpeg 批量编码（不受实时帧率限制），如有音频则合流
"""

from __future__ import annotations

import asyncio
import base64
import shutil
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


class ScreencastRecorder:
    """CDP Screencast 录制器。

    通过 Chrome DevTools Protocol 的 Page.startScreencast 从 Chromium
    compositor 直接拉取帧，保存到磁盘后再用 ffmpeg 批量编码为视频。

    支持 WebAudio 全局捕获：通过 Hook AudioNode.prototype.connect，
    将所有输出到 AudioContext.destination 的音频同步复制到
    MediaStreamDestination，再用 MediaRecorder 录制，最终与视频合流。

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
                print("[ScreencastRecorder] WebAudio 捕获已启动 (MediaRecorder + 增量轮询)")

        await cdp.send("Page.startScreencast", screencast_opts)

        # 录制等待：手动交替轮询停止条件 + 音频拉取
        deadline = time.monotonic() + duration if duration > 0 else float("inf")
        last_pull = time.monotonic()
        try:
            while True:
                now = time.monotonic()
                # 超时检查
                if now >= deadline:
                    break
                # 音频增量拉取（每秒一次）
                if has_audio and now - last_pull >= 1.0:
                    await self._pull_audio_chunks(page)
                    last_pull = now
                # 停止条件检查（参数化传值，避免注入风险）
                if stop_condition:
                    try:
                        result = await page.evaluate(
                            "(expr) => !!eval(expr)", stop_condition
                        )
                        if result:
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

        # 安全停止 screencast（页面可能已导航，忽略 target closed 错误）
        try:
            await cdp.send("Page.stopScreencast")
        except Exception:
            pass
        await asyncio.sleep(0.1)

        # 停止音频轮询并完成录制
        if has_audio:
            audio_path = await self._stop_audio_recording(page)
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
            if audio_path:
                audio_path.unlink(missing_ok=True)
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
        if audio_path:
            audio_path.unlink(missing_ok=True)

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
        """启动 WebAudio 捕获的 MediaRecorder，返回是否有音频轨道可录制。

        MediaRecorder 将 chunk 写入 page 内存（window.__audioChunks），
        由后台轮询任务 _poll_audio_chunks 定期拉取到本地 buffer，
        避免页面崩溃时丢失全部数据。
        """
        try:
            result = await page.evaluate("""
            () => {
                const stream = window.__getCapturedStream();
                if (!stream || stream.getAudioTracks().length === 0) {
                    return false;
                }

                let mimeType = 'audio/webm;codecs=opus';
                if (!MediaRecorder.isTypeSupported(mimeType)) {
                    mimeType = 'audio/webm';
                }

                const chunks = [];
                const recorder = new MediaRecorder(stream, { mimeType });

                recorder.ondataavailable = e => {
                    if (e.data.size > 0) chunks.push(e.data);
                };

                window.__audioRecorder = recorder;
                window.__audioChunks = chunks;

                recorder.start(100);
                return true;
            }
            """)
            return bool(result)
        except Exception as e:
            print(f"[ScreencastRecorder] 音频录制启动失败: {e}")
            return False

    async def _pull_audio_chunks(self, page) -> None:
        """从页面拉取一次 audio chunk 到本地 buffer。

        由录制主循环每秒调用一次，单次拉取，不包含循环逻辑。
        """
        try:
            new_bytes = await page.evaluate("""
            async () => {
                const chunks = window.__audioChunks;
                if (!chunks || chunks.length === 0) return [];
                window.__audioChunks = [];

                const allBytes = [];
                for (const blob of chunks) {
                    const ab = await blob.arrayBuffer();
                    const view = new Uint8Array(ab);
                    for (let i = 0; i < view.length; i++) {
                        allBytes.push(view[i]);
                    }
                }
                return allBytes;
            }
            """)
            if new_bytes:
                self._audio_buffer.extend(new_bytes)
                kb = len(new_bytes) / 1024
                total_kb = len(self._audio_buffer) / 1024
                print(f"[ScreencastRecorder] 音频拉取: +{kb:.1f}KB, buffer 累计 {total_kb:.1f}KB")
        except Exception as e:
            print(f"[ScreencastRecorder] 音频拉取失败: {e}")

    async def _stop_audio_recording(self, page) -> Path | None:
        """停止 MediaRecorder，合并本地 buffer 与页面残留数据，写入 webm 文件。

        优先从页面拉取最后一波数据（如果页面还活着），再合并本地 buffer，
        最后写入完整的 webm 文件。
        """
        # 尝试从页面拉取残留数据（页面可能已关闭）
        try:
            result = await page.evaluate("""
            async () => {
                const recorder = window.__audioRecorder;
                if (!recorder || recorder.state === 'inactive') {
                    // recorder 已停止，只返回残留 chunk
                    const chunks = window.__audioChunks || [];
                    window.__audioChunks = null;
                    window.__audioRecorder = null;
                    if (chunks.length === 0) return [];

                    const allBytes = [];
                    for (const blob of chunks) {
                        const ab = await blob.arrayBuffer();
                        const view = new Uint8Array(ab);
                        for (let i = 0; i < view.length; i++) {
                            allBytes.push(view[i]);
                        }
                    }
                    return allBytes;
                }

                return new Promise(resolve => {
                    recorder.onstop = async () => {
                        const chunks = window.__audioChunks || [];
                        window.__audioChunks = null;
                        window.__audioRecorder = null;

                        const allBytes = [];
                        for (const blob of chunks) {
                            const ab = await blob.arrayBuffer();
                            const view = new Uint8Array(ab);
                            for (let i = 0; i < view.length; i++) {
                                allBytes.push(view[i]);
                            }
                        }
                        resolve(allBytes);
                    };
                    recorder.stop();
                });
            }
            """)
            if result:
                self._audio_buffer.extend(result)
        except Exception as e:
            print(f"[ScreencastRecorder] 音频残留数据拉取失败（页面可能已关闭）: {e}")

        if len(self._audio_buffer) == 0:
            self._audio_buffer = bytearray()
            return None

        audio_bytes = bytes(self._audio_buffer)
        self._audio_buffer = bytearray()

        audio_path = Path("data/temp") / f"webgal_audio_{uuid.uuid4().hex[:8]}.webm"
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(audio_bytes)
        return audio_path

    # ── FFmpeg 编码 ────────────────────────────────────────────────

    async def _encode_from_dir(
        self,
        frames_dir: Path,
        ext: str,
        source_fps: float,
        output_fps: int,
        audio_path: Path | None = None,
    ) -> None:
        """从帧目录批量编码视频（录制完成后离线执行），可选融合音频。"""
        ffmpeg = _find_ffmpeg()
        fmt, encoder = _codec_from_ext(self._output_path)

        self._output_path.parent.mkdir(parents=True, exist_ok=True)

        args = [
            ffmpeg, "-y",
            "-framerate", f"{source_fps:.6f}",
            "-i", str(frames_dir / f"frame_%08d.{ext}"),
        ]

        if audio_path and audio_path.exists():
            args.extend(["-i", str(audio_path)])

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
