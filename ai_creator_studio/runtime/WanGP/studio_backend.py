"""Local AI Creator Studio bridge for the real WanGP in-process API."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import traceback
from urllib.parse import urlparse

from shared.api import init

HOST = "127.0.0.1"
PORT = int(os.environ.get("AI_CREATOR_PORT", "18765"))
ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "studio_outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_session = None
_session_lock = threading.RLock()


def get_session():
    global _session
    with _session_lock:
        if _session is None:
            _session = init(
                root=ROOT,
                output_dir=OUTPUT_DIR,
                console_output=False,
            )
        return _session


def json_safe(value):
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def find_image_model(session):
    records = session.list_model_metadata()
    candidates = []
    for record in records:
        blob = json.dumps(record, ensure_ascii=False).lower()
        model_type = str(record.get("model_type", ""))
        if "image" in blob and "video" not in blob:
            candidates.append(model_type)
    if not candidates:
        # The API is still useful without guessing: callers can use /models
        # and submit an explicit model_type later.
        return None
    return candidates[0]


def generate_image(prompt: str, model_type: str | None = None):
    session = get_session()
    selected_model = model_type or find_image_model(session)
    if not selected_model:
        raise RuntimeError("Не удалось автоматически выбрать модель изображений. Используйте /models для выбора модели.")

    settings = session.get_default_settings(selected_model)
    settings["model_type"] = selected_model
    settings["prompt"] = prompt
    settings["_api"] = {"return_media": True}

    result = session.run_task(settings)
    return {
        "success": result.success,
        "files": result.generated_files,
        "errors": [str(error) for error in result.errors],
        "model_type": selected_model,
        "artifacts": [
            {
                "path": artifact.path,
                "media_type": artifact.media_type,
                "fps": artifact.fps,
            }
            for artifact in result.artifacts
        ],
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:
        self._send(204, {})

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/health":
                self._send(200, {"ok": True, "engine": "WanGP", "stage": "ready"})
                return
            if path == "/models":
                session = get_session()
                self._send(200, {"ok": True, "models": json_safe(session.list_model_metadata())})
                return
            self._send(404, {"ok": False, "error": "Не найдено"})
        except Exception as exc:
            self._send(500, {"ok": False, "error": str(exc), "traceback": traceback.format_exc()})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            if path == "/generate/image":
                prompt = str(payload.get("prompt", "")).strip()
                if not prompt:
                    self._send(400, {"ok": False, "error": "Введите описание изображения."})
                    return
                result = generate_image(prompt, payload.get("model_type"))
                self._send(200, result)
                return
            self._send(404, {"ok": False, "error": "Не найдено"})
        except Exception as exc:
            self._send(500, {"ok": False, "error": str(exc), "traceback": traceback.format_exc()})

    def log_message(self, *_args) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
