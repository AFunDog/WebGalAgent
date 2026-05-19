"""FFmpeg 编码辅助。"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
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


def _count_frame_files(frames_dir: Path, ext: str) -> int:
    return len(list(frames_dir.glob(f"frame_*.{ext}")))


def _build_time_segments(
    frame_pts: list[float] | None,
    total_frames: int,
    actual_duration: float,
    segment_seconds: float = 1.0,
) -> list[tuple[int, int, float]]:
    """将序列帧按时间切成近似 1 秒段，返回 (start_index, count, duration)。"""
    if total_frames <= 0:
        return []

    if not frame_pts or len(frame_pts) != total_frames or actual_duration <= 0:
        return [(0, total_frames, max(actual_duration, 1e-6))]

    segments: list[tuple[int, int, float]] = []
    segment_index = 0
    segment_start_index = 0
    segment_start_time = 0.0

    for index, pts in enumerate(frame_pts):
        current_segment = int(pts // segment_seconds)
        if current_segment != segment_index:
            count = index - segment_start_index
            duration = min(current_segment * segment_seconds, actual_duration) - segment_start_time
            if count > 0 and duration > 0:
                segments.append((segment_start_index, count, duration))
            segment_index = current_segment
            segment_start_index = index
            segment_start_time = current_segment * segment_seconds

    final_count = total_frames - segment_start_index
    final_duration = actual_duration - segment_start_time
    if final_count > 0:
        segments.append((segment_start_index, final_count, max(final_duration, 1e-6)))

    return segments


async def _run_ffmpeg(args: list[str]) -> None:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg 编码失败:\n{stderr.decode()}")


async def _mux_audio(
    ffmpeg: str,
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    fmt: str,
) -> None:
    args = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-af",
        "aresample=async=1:first_pts=0",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "libopus" if fmt == "webm" else "aac",
        "-shortest",
    ]
    if fmt == "webm":
        args.extend(["-f", "webm"])
    else:
        args.extend(["-f", "mp4"])
    args.append(str(output_path))
    print(f"[ScreencastRecorder] ffmpeg {' '.join(args[1:])}")
    await _run_ffmpeg(args)


async def encode_from_dir(
    output_path: Path,
    video_config: VideoConfig,
    frames_dir: Path,
    ext: str,
    source_fps: float,
    output_fps: int,
    audio_path: Path | None = None,
    frame_pts: list[float] | None = None,
    actual_duration: float | None = None,
) -> None:
    """从帧目录批量编码视频（录制完成后离线执行）。"""
    ffmpeg = find_ffmpeg()
    fmt, encoder = codec_from_ext(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_frames = len(frame_pts) if frame_pts else _count_frame_files(frames_dir, ext)
    clip_duration = actual_duration
    if clip_duration is None:
        clip_duration = total_frames / source_fps if source_fps > 0 else 0.0
    segments = _build_time_segments(frame_pts, total_frames, clip_duration)

    temp_dir = Path(tempfile.mkdtemp(prefix="webgal_segments_", dir=frames_dir))
    concat_manifest = temp_dir / "segments.ffconcat"
    merged_video = temp_dir / f"merged_video{output_path.suffix}"

    try:
        segment_paths: list[Path] = []
        for segment_no, (start_index, count, duration) in enumerate(segments):
            segment_path = temp_dir / f"segment_{segment_no:04d}{output_path.suffix}"
            segment_fps = max(count / max(duration, 1e-6), 1e-3)
            args = [
                ffmpeg,
                "-y",
                "-framerate",
                f"{segment_fps:.6f}",
                "-start_number",
                str(start_index),
                "-i",
                str(frames_dir / f"frame_%08d.{ext}"),
                "-frames:v",
                str(count),
                "-vf",
                f"tmix=2:weights='1 1',fps={output_fps},trim=duration={duration:.6f}",
                "-an",
                "-c:v",
                encoder,
                "-crf",
                str(video_config.quality),
            ]
            if fmt == "webm":
                args.extend(["-deadline", "good", "-cpu-used", "2", "-f", "webm"])
            else:
                args.extend(["-preset", "ultrafast", "-pix_fmt", "yuv420p", "-f", "mp4"])
            args.append(str(segment_path))
            print(f"[ScreencastRecorder] ffmpeg {' '.join(args[1:])}")
            await _run_ffmpeg(args)
            segment_paths.append(segment_path)

        with open(concat_manifest, "w", encoding="utf-8") as handle:
            handle.write("ffconcat version 1.0\n")
            for segment_path in segment_paths:
                handle.write(f"file '{segment_path.resolve().as_posix()}'\n")

        concat_args = [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_manifest),
            "-c",
            "copy",
        ]
        if fmt == "webm":
            concat_args.extend(["-f", "webm"])
        else:
            concat_args.extend(["-f", "mp4"])
        concat_args.append(str(merged_video))
        print(f"[ScreencastRecorder] ffmpeg {' '.join(concat_args[1:])}")
        await _run_ffmpeg(concat_args)

        if audio_path and audio_path.exists():
            await _mux_audio(ffmpeg, merged_video, audio_path, output_path, fmt)
        else:
            shutil.move(str(merged_video), str(output_path))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
