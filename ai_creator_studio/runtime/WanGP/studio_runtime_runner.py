"""Translate the Studio runtime policy into safe WanGP settings.

The adapter deliberately applies only options exposed by a model schema. This
keeps the desktop application independent from WanGP's changing backend knobs.
"""
from __future__ import annotations

from typing import Any

from studio_hardware import detect_hardware
from studio_runtime_policy import choose_runtime_mode


def prepare_runtime(
    model: dict[str, Any],
    schema: dict[str, Any],
    requested: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return generation settings plus a user-facing runtime report."""
    requested = dict(requested or {})
    settings = dict(schema.get("default_settings") or {})
    hardware = detect_hardware()
    policy = choose_runtime_mode(hardware, model)

    if policy["mode"] == "unsupported":
        raise RuntimeError(policy.get("reason") or "Модель несовместима с этим компьютером")

    applied: dict[str, Any] = {}
    for key, value in (policy.get("overrides") or {}).items():
        if key in settings:
            settings[key] = value
            applied[key] = value

    # Explicit user settings are applied last. Advanced settings are therefore
    # still available, while the automatic policy remains the default path.
    for key, value in requested.items():
        if key != "model_type":
            settings[key] = value

    report = {
        "mode": policy.get("mode"),
        "label": policy.get("label"),
        "reason": policy.get("reason"),
        "hardware": hardware,
        "applied_overrides": applied,
    }
    return settings, report
