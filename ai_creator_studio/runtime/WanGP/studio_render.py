"""Small FFmpeg renderer for AI Creator Studio timelines.

The renderer intentionally starts with a conservative feature set: video/image clips,
voice/audio clips, sequential placement, and mixed audio. More advanced transitions
can be added without changing the Timeline data model.
"""
from __future__ import annotations
import os, shutil, subprocess, tempfile
from pathlib import Path


def ffmpeg_path() -> str:
    path = os.environ.get("FFMPEG_PATH") or shutil.which("ffmpeg")
    if not path:
        raise RuntimeError("FFmpeg не найден. Укажите FFMPEG_PATH или добавьте ffmpeg.exe в runtime приложения.")
    return path


def render_timeline(timeline: dict, output: Path, root: Path) -> Path:
    items = [x for x in timeline.get("items", []) if x.get("path")]
    if not items:
        raise ValueError("Timeline не содержит материалов для рендера")
    output.parent.mkdir(parents=True, exist_ok=True)
    fps = int(timeline.get("fps") or 30)
    duration = float(timeline.get("duration") or max(float(x.get("start", 0)) + float(x.get("duration", 5)) for x in items))
    ff = ffmpeg_path()
    with tempfile.TemporaryDirectory(prefix="ai_creator_render_") as td:
        args=[ff,"-y"]
        video=[]; audio=[]
        for i,item in enumerate(items):
            p=Path(str(item["path"])).expanduser()
            if not p.is_absolute(): p=(root/p).resolve()
            if not p.exists(): raise FileNotFoundError(p)
            start=float(item.get("start",0)); dur=max(.05,float(item.get("duration",5))); track=str(item.get("track","video"))
            kind=str(item.get("kind",track))
            if track=="video" or kind in {"image","video"}:
                args += ["-loop","1","-t",str(dur),"-i",str(p)] if p.suffix.lower() in {".png",".jpg",".jpeg",".webp"} else ["-i",str(p)]
                video.append((i,start,dur,p.suffix.lower() in {".png",".jpg",".jpeg",".webp"}))
            else:
                args += ["-i",str(p)]; audio.append((i,start,dur))
        filters=[]; vlabels=[]
        for n,(idx,start,dur,is_image) in enumerate(video):
            label=f"v{n}"; filters.append(f"[{idx}:v]scale=trunc(iw/2)*2:trunc(ih/2)*2,fps={fps},setpts=PTS-STARTPTS+{start}/TB,trim=duration={dur}[{label}]");vlabels.append(f"[{label}]")
        if vlabels:
            filters.append("".join(vlabels)+f"concat=n={len(vlabels)}:v=1:a=0,setpts=PTS-STARTPTS[vout]")
        alabels=[]
        for n,(idx,start,dur) in enumerate(audio):
            label=f"a{n}";filters.append(f"[{idx}:a]atrim=duration={dur},asetpts=PTS-STARTPTS,adelay={int(start*1000)}|{int(start*1000)}[{label}]");alabels.append(f"[{label}]")
        if alabels: filters.append("".join(alabels)+f"amix=inputs={len(alabels)}:duration=longest:dropout_transition=0[aout]")
        args += ["-filter_complex",";".join(filters)]
        if vlabels: args += ["-map","[vout]","-r",str(fps),"-c:v","libx264","-pix_fmt","yuv420p"]
        else: args += ["-f","lavfi","-i",f"color=c=black:s=1280x720:r={fps}:d={duration}","-c:v","libx264","-pix_fmt","yuv420p"]
        if alabels: args += ["-map","[aout]","-c:a","aac","-shortest"]
        args += ["-t",str(duration),str(output)]
        subprocess.run(args,check=True,capture_output=True,text=True)
    return output
