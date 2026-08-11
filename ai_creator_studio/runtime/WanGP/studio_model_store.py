from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


class ModelStoreError(RuntimeError):
    pass


class ModelStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.models_dir = self.root / "models"
        self.registry_path = self.root / "installed_models.json"
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def _read_registry(self) -> dict[str, Any]:
        if not self.registry_path.exists():
            return {"version": 1, "models": {}}
        try:
            return json.loads(self.registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ModelStoreError(f"Не удалось прочитать реестр моделей: {exc}") from exc

    def _write_registry(self, registry: dict[str, Any]) -> None:
        tmp = self.registry_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.registry_path)

    def list_installed(self) -> list[dict[str, Any]]:
        return list(self._read_registry().get("models", {}).values())

    def get_path(self, model_id: str) -> Path | None:
        record = self._read_registry().get("models", {}).get(model_id)
        if not record:
            return None
        path = Path(record["path"])
        return path if path.exists() else None

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def install_file(self, model_id: str, url: str, filename: str, sha256: str | None = None) -> dict[str, Any]:
        if not url.startswith(("https://", "http://")):
            raise ModelStoreError("Источник модели должен использовать HTTP(S).")
        destination_dir = self.models_dir / model_id
        destination_dir.mkdir(parents=True, exist_ok=True)
        destination = destination_dir / filename

        with tempfile.NamedTemporaryFile(prefix="model-", suffix=".download", delete=False, dir=destination_dir) as tmp:
            temp_path = Path(tmp.name)

        try:
            request = Request(url, headers={"User-Agent": "AI-Creator-Studio/0.1"})
            with urlopen(request, timeout=60) as response, temp_path.open("wb") as output:
                shutil.copyfileobj(response, output, length=1024 * 1024)

            actual_hash = self._sha256(temp_path)
            if sha256 and actual_hash.lower() != sha256.lower():
                raise ModelStoreError("Проверка SHA-256 не пройдена.")

            temp_path.replace(destination)
            registry = self._read_registry()
            registry["models"][model_id] = {
                "model_id": model_id,
                "path": str(destination),
                "filename": filename,
                "sha256": actual_hash,
                "verified": True,
            }
            self._write_registry(registry)
            return registry["models"][model_id]
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)

    def remove(self, model_id: str) -> None:
        registry = self._read_registry()
        record = registry.get("models", {}).pop(model_id, None)
        if record:
            path = Path(record.get("path", ""))
            shutil.rmtree(path.parent, ignore_errors=True)
            self._write_registry(registry)
