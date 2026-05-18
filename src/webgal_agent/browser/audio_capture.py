"""Screencast 录制使用的音频抓取与 WAV 落盘辅助。"""

from __future__ import annotations

import base64
import struct
import uuid
from pathlib import Path


def write_wav_header(f, data_size: int, sample_rate: int, channels: int) -> None:
    """写入 WAV header (IEEE float32)。"""
    byte_rate = sample_rate * channels * 4
    block_align = channels * 4
    f.write(b"RIFF")
    f.write(struct.pack("<I", 36 + data_size))
    f.write(b"WAVE")
    f.write(b"fmt ")
    f.write(struct.pack("<I", 16))
    f.write(struct.pack("<H", 3))
    f.write(struct.pack("<H", channels))
    f.write(struct.pack("<I", sample_rate))
    f.write(struct.pack("<I", byte_rate))
    f.write(struct.pack("<H", block_align))
    f.write(struct.pack("<H", 32))
    f.write(b"data")
    f.write(struct.pack("<I", data_size))


async def start_audio_recording(page) -> bool:
    """启动 MediaStreamTrackProcessor PCM 提取。"""
    try:
        result = await page.evaluate(
            """
            () => {
                if (!window.__startTrackProcessor) return false;
                return window.__startTrackProcessor();
            }
            """
        )
        return bool(result)
    except Exception as exc:
        print(f"[ScreencastRecorder] 音频捕获启动失败: {exc}")
        return False


async def pull_audio_chunks(cdp, audio_buffer: bytearray, audio_meta: dict[str, int]) -> None:
    """通过 CDP 拉取累积的 PCM 数据。"""
    try:
        resp = await cdp.send(
            "Runtime.evaluate",
            {
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
            },
        )
        result = resp.get("result", {}).get("value")
        if result and result.get("pcm_b64"):
            pcm_bytes = base64.b64decode(result["pcm_b64"])
            audio_buffer.extend(pcm_bytes)

            meta = result.get("meta", {})
            if meta and not audio_meta:
                audio_meta.update(
                    {
                        "sampleRate": meta.get("sampleRate", 48000),
                        "channels": meta.get("channels", 2),
                    }
                )

            kb = len(pcm_bytes) / 1024
            total_kb = len(audio_buffer) / 1024
            print(f"[ScreencastRecorder] PCM拉取: +{kb:.1f}KB, buffer {total_kb:.1f}KB")
    except Exception as exc:
        print(f"[ScreencastRecorder] PCM拉取失败: {exc}")


async def diagnose_audio_signal(cdp, pcm_bytes: bytes) -> None:
    """打印音频信号诊断信息。"""
    sample_count = min(len(pcm_bytes) // 4, 4000)
    max_abs = 0.0
    sum_abs = 0.0
    for i in range(0, sample_count * 4, 4):
        val = abs(struct.unpack_from("<f", pcm_bytes, i)[0])
        sum_abs += val
        if val > max_abs:
            max_abs = val
    mean_abs = sum_abs / sample_count if sample_count > 0 else 0.0
    print(
        f"[ScreencastRecorder] 信号诊断 (本地PCM, 前{sample_count}采样): "
        f"max={max_abs:.6f}, mean={mean_abs:.6f}, "
        f"{'有信号' if max_abs > 1e-4 else '静音'}"
    )

    try:
        resp = await cdp.send(
            "Runtime.evaluate",
            {
                "expression": "window.__checkAudioSignal ? window.__checkAudioSignal() : null",
                "returnByValue": True,
            },
        )
        diag = resp.get("result", {}).get("value")
        if diag:
            print(
                f"[ScreencastRecorder] 信号诊断 (页面): "
                f"status={diag.get('status')}, "
                f"max={diag.get('maxAmplitude', 0):.6f}, "
                f"mean={diag.get('meanAmplitude', 0):.6f}, "
                f"samples={diag.get('sampleCount', 0)}, "
                f"ctxStates={diag.get('audioContextStates', [])}, "
                f"audioElements={diag.get('routedAudioElements', 0)}"
            )
    except Exception as exc:
        print(f"[ScreencastRecorder] 页面诊断失败: {exc}")


async def stop_audio_recording(
    cdp,
    audio_buffer: bytearray,
    audio_meta: dict[str, int],
) -> Path | None:
    """拉取残留 PCM，写入 WAV 文件并返回路径。"""
    try:
        resp = await cdp.send(
            "Runtime.evaluate",
            {
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
            },
        )
        result = resp.get("result", {}).get("value")
        if result and result.get("pcm_b64"):
            pcm_bytes = base64.b64decode(result["pcm_b64"])
            audio_buffer.extend(pcm_bytes)

            meta = result.get("meta", {})
            if meta and not audio_meta:
                audio_meta.update(
                    {
                        "sampleRate": meta.get("sampleRate", 48000),
                        "channels": meta.get("channels", 2),
                    }
                )
    except Exception as exc:
        print(f"[ScreencastRecorder] PCM残留拉取失败: {exc}")

    if len(audio_buffer) == 0:
        audio_buffer.clear()
        return None

    pcm_bytes = bytes(audio_buffer)
    audio_buffer.clear()
    await diagnose_audio_signal(cdp, pcm_bytes)

    sr = audio_meta.get("sampleRate", 48000)
    ch = audio_meta.get("channels", 2)

    audio_path = Path("data/temp") / f"webgal_audio_{uuid.uuid4().hex[:8]}.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    with open(audio_path, "wb") as f:
        write_wav_header(f, len(pcm_bytes), sr, ch)
        f.write(pcm_bytes)
    print(
        f"[ScreencastRecorder] WAV已保存: {audio_path} "
        f"({len(pcm_bytes) / 1024:.1f}KB, sr={sr}, ch={ch})"
    )
    return audio_path
