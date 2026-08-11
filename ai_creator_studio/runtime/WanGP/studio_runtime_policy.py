from __future__ import annotations

from typing import Any


def choose_runtime_mode(hardware: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
    """Choose a conservative execution mode without exposing backend knobs to the UI."""
    gpu = hardware.get("gpu") or {}
    vram = gpu.get("vram_gb")
    ram = hardware.get("ram_gb")
    requirements = model.get("requirements") or {}
    min_vram = float(requirements.get("min_vram_gb") or 0)
    recommended_vram = float(requirements.get("recommended_vram_gb") or min_vram)
    min_ram = float(requirements.get("min_ram_gb") or 0)
    vendor = str(gpu.get("vendor") or "").upper()

    if vendor == "NVIDIA" and vram is not None:
        if vram >= recommended_vram:
            return {"mode": "gpu", "label": "Полная производительность", "reason": "Достаточно видеопамяти.", "overrides": {}}
        if vram >= min_vram:
            return {"mode": "gpu_offload", "label": "Экономия VRAM", "reason": "Модель подходит, но будет использовать выгрузку в оперативную память.", "overrides": {"offload": True}}
        if ram is not None and ram >= max(min_ram, min_vram * 1.5):
            return {"mode": "cpu_offload", "label": "Максимальная экономия VRAM", "reason": "VRAM недостаточно для обычного режима; используется RAM offload.", "overrides": {"offload": True, "cpu_offload": True}}
        return {"mode": "unsupported", "label": "Недостаточно памяти", "reason": f"Нужно минимум {min_vram:g} ГБ VRAM.", "overrides": {}}

    if ram is not None and ram >= max(min_ram, min_vram * 1.5):
        return {"mode": "cpu", "label": "CPU-режим", "reason": "Аппаратный GPU backend не определён; используется CPU.", "overrides": {"cpu": True}}
    return {"mode": "unsupported", "label": "Недостаточно ресурсов", "reason": "Недостаточно VRAM/RAM для этой модели.", "overrides": {}}
