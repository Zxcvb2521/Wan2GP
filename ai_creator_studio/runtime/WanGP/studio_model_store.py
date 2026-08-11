from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable
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
            return {"version": 2, "models": {}}
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
    def _sha256(path: Path, chunk_size: int = 4 * 1024 * 1024) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(chunk_size), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def install_bundle(
        self,
        model_id: str,
        files: list[dict[str, Any]],
        progress: Callable[[dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        if not model_id or not files:
            raise ModelStoreError("Пакет модели не содержит файлов.")
        destination = self.models_dir / model_id
        staging_root = Path(tempfile.mkdtemp(prefix=f"{model_id}-", dir=self.models_dir))
        records: list[dict[str, Any]] = []
        total = sum(max(0, int(item.get("size_bytes", 0))) for item in files)
        completed = 0

        def report(phase: str, current: str = "") -> None:
            if progress:
                progress({"phase": phase, "file": current, "bytes": completed, "total_bytes": total})

        try:
            for item in files:
                filename = str(item.get("filename", "")).replace("\\", "/").lstrip("/")
                url = str(item.get("url", ""))
                expected = str(item.get("sha256", "")).strip().lower()
                if not filename or Path(filename).is_absolute() or ".." in Path(filename).parts:
                    raise ModelStoreError(f"Некорректное имя файла: {filename}")
                if not url.startswith(("https://", "http://")):
                    raise ModelStoreError(f"Некорректный источник для {filename}")

                target = staging_root / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                report("downloading", filename)
                request = Request(url, headers={"User-Agent": "AI-Creator-Studio/0.1"})
                with urlopen(request, timeout=60) as response, target.open("wb") as output:
                    while True:
                        chunk = response.read(4 * 1024 * 1024)
                        if not chunk:
                            break
                        output.write(chunk)
                        completed += len(chunk)
                        if progress:
                            progress({"phase": "downloading", "file": filename, "bytes": completed, "total_bytes": total})

                report("verifying", filename)
                actual = self._sha256(target)
                if expected and actual != expected:
                    raise ModelStoreError(f"SHA-256 не совпадает: {filename}")
                records.append({"filename": filename, "path": str(destination / filename), "sha256": actual, "size_bytes": target.stat().st_size})

            report("installing")
            if destination.exists():
                shutil.rmtree(destination)
            staging_root.replace(destination)
            registry = self._read_registry()
            registry["version"] = 2
            registry["models"][model_id] = {
                "model_id": model_id,
                "path": str(destination),
                "files": records,
                "verified": True,
            }
            self._write_registry(registry)
            report("completed")
            return registry["models"][model_id]
        except Exception:
            shutil.rmtree(staging_root, ignore_errors=True)
            raise

    def install_file(self, model_id: str, url: str, filename: str, sha256: str | None = None) -> dict[str, Any]:
        return self.install_bundle(model_id, [{"url": url, "filename": filename, "sha256": sha256 or ""}])

    def remove(self, model_id: str) -> None:
        registry = self._read_registry()
        record = registry.get("models", {}).pop(model_id, None)
        if record:
            path = Path(record.get("path", ""))
            shutil.rmtree(path, ignore_errors=True)
            self._write_registry(registry)
