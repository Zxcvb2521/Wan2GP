"""Persistent lightweight timeline for AI Creator Studio projects."""
from __future__ import annotations
import json, threading, uuid
from datetime import datetime, timezone
from pathlib import Path

class TimelineStore:
    def __init__(self, root: Path):
        self.root = root; self.root.mkdir(parents=True, exist_ok=True); self.path = self.root / "timelines.json"; self.lock = threading.Lock()
        if not self.path.exists(): self.path.write_text("{}", encoding="utf-8")
    def _read(self):
        try: return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception: return {}
    def _write(self, data):
        tmp=self.path.with_suffix(".tmp"); tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8"); tmp.replace(self.path)
    def get(self, project_id):
        with self.lock:
            data=self._read(); return data.get(project_id,{"project_id":project_id,"fps":30,"duration":0,"items":[]})
    def save(self, project_id, timeline):
        now=datetime.now(timezone.utc).isoformat(); timeline=dict(timeline); timeline["project_id"]=project_id; timeline["updated_at"]=now; timeline.setdefault("fps",30); timeline.setdefault("duration",0); timeline.setdefault("items",[])
        with self.lock: data=self._read(); data[project_id]=timeline; self._write(data)
        return timeline
    def add(self, project_id, item):
        timeline=self.get(project_id); item=dict(item); item.setdefault("id",uuid.uuid4().hex); item.setdefault("start",timeline.get("duration",0)); item.setdefault("duration",5); item.setdefault("track", "video"); timeline["items"].append(item); timeline["duration"]=max((float(x.get("start",0))+float(x.get("duration",0)) for x in timeline["items"]),default=0); return self.save(project_id,timeline)
