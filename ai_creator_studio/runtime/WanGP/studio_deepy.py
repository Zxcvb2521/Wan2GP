"""Deepy integration boundary for AI Creator Studio.

Deepy remains WanGP's native media agent. The Studio deliberately does not
reimplement Deepy's tool orchestration. This adapter only discovers the native
Deepy capability and exposes the command/requirements to the desktop layer.
Actual media generation continues through the existing WanGP session adapter.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DeepyStatus:
    available: bool
    enabled_by_runtime: bool
    command: list[str]
    prompt_enhancer_modes: tuple[str, ...]
    note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "enabled_by_runtime": self.enabled_by_runtime,
            "command": self.command,
            "prompt_enhancer_modes": list(self.prompt_enhancer_modes),
            "note": self.note,
        }


class DeepyAdapter:
    SUPPORTED_MODES = (
        "Qwen3.5VL Abliterated 4B",
        "Qwen3.5VL Abliterated 9B",
    )

    def __init__(self, wan_root: str | Path):
        self.wan_root = Path(wan_root).resolve()
        self.wgp = self.wan_root / "wgp.py"

    def status(self) -> DeepyStatus:
        available = self.wgp.is_file()
        command = [sys.executable, str(self.wgp), "--ask-deepy"] if available else []
        return DeepyStatus(
            available=available,
            enabled_by_runtime=False,
            command=command,
            prompt_enhancer_modes=self.SUPPORTED_MODES,
            note=(
                "Deepy доступен через встроенный WanGP CLI. "
                "Для работы Deepy требуется включённый Prompt Enhancer "
                "Qwen3.5VL Abliterated 4B или 9B."
                if available
                else "WanGP runtime не найден: Deepy недоступен."
            ),
        )

    def launch_cli(self) -> subprocess.Popen[str]:
        status = self.status()
        if not status.available:
            raise RuntimeError("WanGP wgp.py не найден; невозможно запустить Deepy.")
        return subprocess.Popen(
            status.command,
            cwd=self.wan_root,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )


def detect_deepy(wan_root: str | Path) -> dict[str, Any]:
    return DeepyAdapter(wan_root).status().to_dict()
