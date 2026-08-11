"""Local backend bridge between AI Creator Studio and WanGP's public session API."""

from __future__ import annotations

import json
import os
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HOST = "127.0.0.1"
PORT = int(os.environ.get("AI_CREATOR_PORT", "18765"))

_session = None
_session_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def get_session():
    global _session
    with _session_lock:
        if _session is None:
            from shared.api import WanGPSession
            _session = WanGPSession()
        return _session


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if hasattr(value, "model_dump"):
        return jsonable(value.model_dump())
    if hasattr(value, "__dict__"):
        return jsonable(value.__dict__)
    return str(value)


def model_info() -> dict[str, Any]:
    session = get_session()
    try:
        models = session.list_model_defs()
    except Exception as exc:
        return {"ok": False, "error": str(exc), "models": []}
    return {"ok": True, "models": jsonable(models)}


def choose_image_model(models: Any) -> str | None:
    """Pick only from discovered WanGP metadata; never invent a model id."""
    if isinstance(models, dict):
        items = models.items()
    elif isinstance(models, list):
        items = []
        for item in models:
            if isinstance(item, dict):
                mid = item.get("id") or item.get("model_id") or item.get("name")
                if mid:
                    items.append((mid, item))
    else:
        return None

    candidates: list[tuple[str, Any]] = []
    for mid, meta in items:
        text = json.dumps(jsonable(meta), ensure_ascii=False).lower()
        if any(token in text for token in ("image", "img", "text-to-image", "t2i")):
            candidates.append((str(mid), meta))
    if not candidates and isinstance(models, dict):
        candidates = [(str(k), v) for k, v in models.items()]
    return candidates[0][0] if candidates else None


def run_image(job_id: str, prompt: str, settings: dict[str, Any]) -> None:
    job = _jobs[job_id]
    try:
        session = get_session()
        job.update(status="preparing", progress=0.02)
        model_id = settings.get("model_id")
        if not model_id:
            model_id = choose_image_model(session.list_model_defs())
        if not model_id:
            raise RuntimeError("WanGP не сообщил доступную модель для генерации изображения")

        job.update(status="running", progress=0.05, model_id=model_id)
        task = session.submit_task(
            model_id=model_id,
            settings={**settings, "prompt": prompt},
        )
        result = session.run_task(task)
        payload = jsonable(result)
        job.update(status="completed", progress=1.0, result=payload)
    except Exception as exc:
        job.update(status="failed", progress=0.0, error=str(exc))


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self) -> None:
        try:
            if self.path == "/health":
                self.send_json(200, {"ok": True, "engine": "WanGP", "stage": "session"})
            elif self.path == "/models":
                self.send_json(200, model_info())
            elif self.path.startswith("/jobs/"):
                job_id = self.path.rsplit("/", 1)[-1]
                job = _jobs.get(job_id)
                self.send_json(200 if job else 404, job or {"error": "Задача не найдена"})
            else:
                self.send_json(404, {"ok": False, "error": "Не найдено"})
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})

    def do_POST(self) -> None:
        try:
            if self.path != "/generate/image":
                self.send_json(404, {"ok": False, "error": "Не найдено"})
                return
            body = self.read_json()
            prompt = str(body.get("prompt", "")).strip()
            if not prompt:
                self.send_json(400, {"ok": False, "error": "Введите описание изображения"})
                return
            job_id = uuid.uuid4().hex
            _jobs[job_id] = {"id": job_id, "status": "queued", "progress": 0.0}
            thread = threading.Thread(target=run_image, args=(job_id, prompt, body.get("settings") or {}), daemon=True)
            thread.start()
            self.send_json(202, {"ok": True, "job_id": job_id})
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})

    def log_message(self, *_args) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
