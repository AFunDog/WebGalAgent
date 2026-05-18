"""FFmpeg 编码辅助。"""

from __future__ import annotations

import asyncio
import shutil
from pathlib import Path

from webgal_agent.browser.models import VideoConfig


def find_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("未找到 ffmpeg，请安装 ffmpeg 并确保其在 PATH 中。")
    return ffmpeg


def codec_from_ext(output_path: Path) -> tuple[str, str]:
    suffix = output_path.suffix.lower()
    if suffix == ".webm":
        return "webm", "libvpx-vp9"
    return "mp4", "libx264"


async def encode_from_dir(
    output_path: Path,
    video_config: VideoConfig,
    frames_dir: Path,
    ext: str,
    source_fps: float,
    output_fps: int,
    audio_path: Path | None = None,
) -> None:
    """从帧目录批量编码视频（录制完成后离线执行）。"""
    ffmpeg = find_ffmpeg()
    fmt, encoder = codec_from_ext(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    args = [
        ffmpeg,
        "-y",
        "-framerate",
        f"{source_fps:.6f}",
        "-i",
        str(frames_dir / f"frame_%08d.{ext}"),
    ]

    if audio_path and audio_path.exists():
        args.extend(["-i", str(audio_path), "-af", "aresample=async=1:first_pts=0"])

    args.extend(["-vf", f"tmix=2:weights='1 1',fps={output_fps}"])

    if audio_path and audio_path.exists():
        args.extend(["-map", "0:v:0", "-map", "1:a:0"])
        args.extend(["-c:v", encoder, "-crf", str(video_config.quality)])
        args.extend(["-c:a", "libopus" if fmt == "webm" else "aac"])
        args.append("-shortest")
    else:
        args.extend(["-c:v", encoder, "-crf", str(video_config.quality), "-an"])

    if fmt == "webm":
        args.extend(["-deadline", "good", "-cpu-used", "2", "-f", "webm"])
    else:
        args.extend(["-preset", "ultrafast", "-pix_fmt", "yuv420p", "-f", "mp4"])

    args.append(str(output_path))
    print(f"[ScreencastRecorder] ffmpeg {' '.join(args[1:])}")

    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg 编码失败:\n{stderr.decode()}")
