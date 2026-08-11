"""Small SQLite project/history store for AI Creator Studio."""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path


class ProjectStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "projects.db"
        self.lock = threading.Lock()
        self._init()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init(self):
        with self._connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS assets (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                prompt TEXT,
                path TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
            );
            """)

    def create_project(self, name: str) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        project = {"id": uuid.uuid4().hex, "name": name.strip() or "Новый проект", "created_at": now, "updated_at": now}
        with self.lock, self._connect() as db:
            db.execute("INSERT INTO projects VALUES (?, ?, ?, ?)", tuple(project.values()))
        return project

    def list_projects(self) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("SELECT id,name,created_at,updated_at FROM projects ORDER BY updated_at DESC").fetchall()
        return [dict(zip(("id", "name", "created_at", "updated_at"), row)) for row in rows]

    def add_asset(self, project_id: str, kind: str, prompt: str, path: str, metadata: dict | None = None) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        asset = {"id": uuid.uuid4().hex, "project_id": project_id, "kind": kind, "prompt": prompt, "path": path, "metadata": json.dumps(metadata or {}, ensure_ascii=False), "created_at": now}
        with self.lock, self._connect() as db:
            db.execute("INSERT INTO assets VALUES (?, ?, ?, ?, ?, ?, ?)", tuple(asset.values()))
            db.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
        return asset

    def list_assets(self, project_id: str) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("SELECT id,project_id,kind,prompt,path,metadata,created_at FROM assets WHERE project_id=? ORDER BY created_at DESC", (project_id,)).fetchall()
        keys = ("id", "project_id", "kind", "prompt", "path", "metadata", "created_at")
        result = []
        for row in rows:
            item = dict(zip(keys, row))
            try: item["metadata"] = json.loads(item["metadata"] or "{}")
            except json.JSONDecodeError: item["metadata"] = {}
            result.append(item)
        return result
