"""Minimal local backend contract for AI Creator Studio.

This is intentionally a thin bootstrap layer. The next integration step will
replace the placeholder health endpoint with the real WanGPSession lifecycle
and generation calls from the parent WanGP runtime.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os

HOST = "127.0.0.1"
PORT = int(os.environ.get("AI_CREATOR_PORT", "18765"))


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send(200, {"ok": True, "engine": "WanGP", "stage": "bootstrap"})
            return
        self._send(404, {"ok": False, "error": "Не найдено"})

    def log_message(self, *_args) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
