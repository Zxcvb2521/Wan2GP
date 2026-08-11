from __future__ import annotations

from typing import Any


def _hardware_profile(hardware: dict[str, Any]) -> tuple[float, float, str, bool]:
    gpu = hardware.get("gpu") or {}
    return (
        float(gpu.get("vram_gb") or 0),
        float(hardware.get("ram_gb") or 0),
        str(gpu.get("vendor") or "unknown").lower(),
        bool(gpu.get("accelerator") or hardware.get("accelerator_available")),
    )


def check_model(hardware: dict[str, Any], requirements: dict[str, Any] | None = None) -> dict[str, Any]:
    req = requirements or {}
    vram, ram, vendor, accelerator = _hardware_profile(hardware)
    min_vram = float(req.get("min_vram_gb") or 0)
    recommended_vram = float(req.get("recommended_vram_gb") or 0)
    min_ram = float(req.get("min_ram_gb") or 0)
    vendors = [str(x).lower() for x in (req.get("vendors") or [])]
    cpu_supported = bool(req.get("cpu_supported", False))
    reasons: list[str] = []

    if min_ram and ram < min_ram:
        reasons.append(f"Нужно минимум {min_ram:g} ГБ ОЗУ, доступно {ram:g} ГБ.")
    if vendors and accelerator and vendor not in vendors:
        reasons.append("Видеоускоритель этого производителя не указан среди поддерживаемых.")
    if min_vram and vram < min_vram and not cpu_supported:
        reasons.append(f"Нужно минимум {min_vram:g} ГБ VRAM, доступно {vram:g} ГБ.")
    if not accelerator and not cpu_supported and min_vram:
        reasons.append("Аппаратный GPU-ускоритель не обнаружен.")

    if reasons:
        return {"compatible": False, "level": "unsupported", "reasons": reasons}
    if not accelerator and cpu_supported:
        return {"compatible": True, "level": "possible", "reasons": ["Будет использован CPU-режим; генерация может быть медленной."]}
    if recommended_vram and vram < recommended_vram:
        return {"compatible": True, "level": "possible", "reasons": [f"Запуск возможен, но рекомендуется {recommended_vram:g} ГБ VRAM."]}
    return {"compatible": True, "level": "recommended", "reasons": []}


def annotate_models(models: list[dict[str, Any]], hardware: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for model in models:
        item = dict(model)
        requirements = item.get("requirements") or {}
        item["compatibility"] = check_model(hardware, requirements)
        result.append(item)
    return result
