"""Video request normalization for AI Creator Studio.

The adapter deliberately keeps WanGP's native parameter names. The Studio
only supplies a small set of user-facing options and lets the model schema
provide the remaining defaults.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def choose_video_model(models: list[dict[str, Any]]) -> str | None:
    """Pick an available WanGP video model without hard-coding one model name."""
    candidates: list[tuple[int, str]] = []
    for model in models:
        model_type = str(model.get("model_type") or "").strip()
        if not model_type or (model.get("availability") or {}).get("available") is False:
            continue
        text = str(model).lower()
        score = 0
        if any(token in text for token in ("text-to-video", "text to video", "t2v")):
            score += 100
        if any(token in text for token in ("video", "wan", "ltx")):
            score += 20
        if score:
            candidates.append((score, model_type))
    candidates.sort(reverse=True)
    return candidates[0][1] if candidates else None


def build_video_settings(
    schema: dict[str, Any],
    prompt: str,
    user_settings: dict[str, Any],
    runtime_settings: dict[str, Any],
) -> dict[str, Any]:
    """Build a native WanGP video settings object from schema defaults."""
    settings = dict(schema.get("default_settings") or {})
    settings.update({k: v for k, v in user_settings.items() if k != "model_type"})
    settings.update(runtime_settings)
    settings["prompt"] = prompt
    return settings


def register_video_result(project_store, timeline_store, project_id: str | None, generated_files: list[Any], prompt: str, model_type: str, runtime: dict[str, Any]) -> None:
    if not project_id:
        return
    for path in generated_files:
        path_str = str(path)
        asset = project_store.add_asset(project_id, "video", prompt, path_str, {"model_type": model_type, "runtime": runtime})
        timeline = timeline_store.get(project_id)
        timeline_store.add(project_id, {
            "kind": "video",
            "track": "video",
            "path": path_str,
            "asset_id": asset["id"],
            "name": Path(path_str).name,
            "start": timeline.get("duration", 0),
            "duration": 5,
            "volume": 1,
        })
