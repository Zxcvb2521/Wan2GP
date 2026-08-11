"""Local backend bridge between AI Creator Studio and WanGP's headless session API."""

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
OUTPUT_DIR = ROOT / "ai_creator_studio" / "projects" / "generated"

_session = None
_session_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def get_session():
    global _session
    with _session_lock:
        if _session is None:
            from shared.api import init
            _session = init(root=ROOT, output_dir=OUTPUT_DIR, console_output=False)
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
        models = session.list_model_metadata(include_availability=True)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "models": []}
    return {"ok": True, "models": jsonable(models)}


def choose_image_model(models: list[dict[str, Any]]) -> str | None:
    """Select a real model_type from WanGP metadata; never invent an id."""
    candidates: list[dict[str, Any]] = []
    for model in models:
        model_type = str(model.get("model_type") or "").strip()
        if not model_type:
            continue
        text = json.dumps(model, ensure_ascii=False).lower()
        availability = model.get("availability") or {}
        if availability.get("available") is False:
            continue
        if any(token in text for token in ("text-to-image", "text to image", "image generation", "image", "t2i")):
            candidates.append(model)
    return str(candidates[0]["model_type"]) if candidates else None


def run_image(job_id: str, prompt: str, overrides: dict[str, Any]) -> None:
    job = _jobs[job_id]
    try:
        session = get_session()
        job.update(status="preparing", progress=0.02)
        models = session.list_model_metadata(include_availability=True)
        model_type = str(overrides.get("model_type") or choose_image_model(models) or "").strip()
        if not model_type:
            raise RuntimeError("WanGP не сообщил доступную модель для генерации изображения")

        schema = session.get_model_schema(model_type)
        if not schema:
            raise RuntimeError(f"Не удалось получить схему модели: {model_type}")
        settings = dict(schema.get("default_settings") or {})
        settings.update({k: v for k, v in overrides.items() if k != "model_type"})
        settings["model_type"] = model_type
        settings["prompt"] = prompt
        settings.setdefault("repeat_generation", 1)
        settings.setdefault("batch_size", 1)

        job.update(status="running", progress=0.05, model_type=model_type, model_name=schema.get("name"))
        session_job = session.submit_task(settings)
        result = session_job.result()
        payload = jsonable(result)
        job.update(
            status="completed" if getattr(result, "success", False) else "failed",
            progress=1.0 if getattr(result, "success", False) else 0.0,
            result=payload,
        )
        if not getattr(result, "success", False):
            errors = getattr(result, "errors", ())
            job["error"] = "; ".join(str(error) for error in errors) or "WanGP не смог выполнить генерацию"
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
            elif self.path.startswith("/models/") and self.path.endswith("/schema"):
                model_type = self.path[len("/models/"):-len("/schema")]
                self.send_json(200, jsonable(get_session().get_model_schema(model_type)))
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
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
