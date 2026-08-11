"""FFmpeg renderer for AI Creator Studio timelines."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi"}


def ffmpeg_path() -> str:
    path = os.environ.get("FFMPEG_PATH") or shutil.which("ffmpeg")
    if not path:
        raise RuntimeError("FFmpeg не найден. Укажите FFMPEG_PATH или добавьте ffmpeg.exe в runtime приложения.")
    return path


def _number(value, default):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_path(value, root: Path) -> Path:
    path = Path(str(value)).expanduser()
    if not path.is_absolute():
        path = (root / path).resolve()
    else:
        path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def render_timeline(timeline: dict, output: Path, root: Path) -> Path:
    items = [item for item in timeline.get("items", []) if item.get("path")]
    if not items:
        raise ValueError("Timeline не содержит материалов для рендера")

    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    fps = max(1, int(_number(timeline.get("fps"), 30)))
    width = max(2, int(_number(timeline.get("width"), 1280)))
    height = max(2, int(_number(timeline.get("height"), 720)))
    duration = _number(timeline.get("duration"), 0)

    prepared = []
    for item in items:
        path = _safe_path(item["path"], root)
        start = max(0.0, _number(item.get("start"), 0.0))
        clip_duration = max(0.05, _number(item.get("duration"), 5.0))
        volume = max(0.0, min(2.0, _number(item.get("volume"), 1.0)))
        prepared.append((item, path, start, clip_duration, volume))
        duration = max(duration, start + clip_duration)

    if duration <= 0:
        raise ValueError("Длительность Timeline должна быть больше нуля")

    ffmpeg = ffmpeg_path()
    args = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
    video_inputs = []
    audio_inputs = []

    for item, path, start, clip_duration, volume in prepared:
        track = str(item.get("track", "video")).lower()
        kind = str(item.get("kind", track)).lower()
        suffix = path.suffix.lower()
        is_image = suffix in IMAGE_EXTENSIONS or kind == "image"
        is_video = kind == "video" or suffix in VIDEO_EXTENSIONS
        is_audio = track in {"voice", "music", "audio"} or kind in {"voice", "music", "audio"} or suffix in AUDIO_EXTENSIONS

        input_index = len(video_inputs) + len(audio_inputs)
        if is_audio and not is_image and not is_video:
            args += ["-i", str(path)]
            audio_inputs.append((input_index, start, clip_duration, volume))
        elif track == "video" or is_image or is_video:
            if is_image:
                args += ["-loop", "1", "-t", str(clip_duration), "-i", str(path)]
            else:
                args += ["-i", str(path)]
            video_inputs.append((input_index, start, clip_duration, is_image))
        else:
            args += ["-i", str(path)]
            audio_inputs.append((input_index, start, clip_duration, volume))

    filters: list[str] = [f"color=c=black:s={width}x{height}:r={fps}:d={duration}[canvas0]"]
    current = "canvas0"
    for n, (input_index, start, clip_duration, _is_image) in enumerate(video_inputs):
        clip_label = f"clipv{n}"
        next_canvas = f"canvas{n + 1}"
        filters.append(
            f"[{input_index}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,fps={fps},"
            f"setpts=PTS-STARTPTS[{clip_label}]"
        )
        end = min(duration, start + clip_duration)
        filters.append(
            f"[{current}][{clip_label}]overlay=shortest=0:"
            f"enable='between(t,{start:.6f},{end:.6f})'[{next_canvas}]"
        )
        current = next_canvas
    filters.append(f"[{current}]format=yuv420p[vout]")

    audio_labels = []
    for n, (input_index, start, clip_duration, volume) in enumerate(audio_inputs):
        label = f"clipa{n}"
        delay = int(start * 1000)
        filters.append(
            f"[{input_index}:a]atrim=duration={clip_duration:.6f},asetpts=PTS-STARTPTS,"
            f"volume={volume:.4f},adelay={delay}|{delay}[{label}]"
        )
        audio_labels.append(f"[{label}]")

    if audio_labels:
        filters.append(
            "".join(audio_labels)
            + f"amix=inputs={len(audio_labels)}:duration=longest:dropout_transition=0:normalize=0,"
            f"atrim=duration={duration:.6f},asetpts=PTS-STARTPTS[aout]"
        )

    args += ["-filter_complex", ";".join(filters), "-map", "[vout]", "-r", str(fps), "-c:v", "libx264", "-preset", "medium", "-crf", "18"]
    if audio_labels:
        args += ["-map", "[aout]", "-c:a", "aac", "-b:a", "192k"]
    args += ["-t", f"{duration:.6f}", "-movflags", "+faststart", str(output)]

    completed = subprocess.run(args, check=False, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "Неизвестная ошибка FFmpeg").strip()
        raise RuntimeError(f"FFmpeg завершился с ошибкой:\n{detail}")
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("FFmpeg завершился без создания MP4-файла")
    return output
