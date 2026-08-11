from __future__ import annotations

import ctypes
import os
import platform
import shutil
import subprocess
from typing import Any


def _ram_gb() -> float | None:
    try:
        if os.name == "nt":
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return round(status.ullTotalPhys / 1024**3, 1)
        if hasattr(os, "sysconf"):
            return round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024**3, 1)
    except Exception:
        pass
    return None


def _nvidia() -> dict[str, Any] | None:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        out = subprocess.check_output([exe, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"], text=True, timeout=4)
        rows = []
        for line in out.strip().splitlines():
            name, memory, driver = [x.strip() for x in line.split(",", 2)]
            rows.append({"name": name, "vram_gb": round(float(memory) / 1024, 1), "driver": driver})
        if rows:
            gpu = rows[0]
            gpu.update(vendor="NVIDIA", backend="CUDA", accelerator=True, gpus=rows)
            return gpu
    except Exception:
        pass
    return None


def _other_gpu() -> dict[str, Any] | None:
    system = platform.system()
    try:
        if system == "Windows":
            cmd = ["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"]
            out = subprocess.check_output(cmd, text=True, timeout=5)
            names = [x.strip() for x in out.splitlines() if x.strip()]
        elif system == "Linux" and shutil.which("lspci"):
            out = subprocess.check_output(["lspci"], text=True, timeout=3)
            names = [x.split(":", 2)[-1].strip() for x in out.splitlines() if "VGA compatible controller" in x or "3D controller" in x]
        else:
            names = []
        if names:
            name = names[0]
            vendor = "AMD" if "AMD" in name or "Radeon" in name else "Intel" if "Intel" in name or "Arc" in name else "Unknown"
            return {"name": name, "vendor": vendor, "backend": "OS", "accelerator": vendor in {"AMD", "Intel"}, "vram_gb": None, "driver": None, "gpus": [{"name": x, "vendor": vendor} for x in names]}
    except Exception:
        pass
    return None


def detect_hardware() -> dict[str, Any]:
    gpu = _nvidia() or _other_gpu()
    ram = _ram_gb()
    vram = gpu.get("vram_gb") if gpu else None
    if vram is not None:
        profile = "high" if vram >= 24 else "balanced" if vram >= 12 else "economy" if vram >= 6 else "cpu"
    else:
        profile = "economy" if gpu and ram and ram >= 16 else "cpu"
    return {
        "ok": True,
        "os": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "cpu": platform.processor() or platform.uname().processor,
        "cpu_cores": os.cpu_count(),
        "ram_gb": ram,
        "gpu": gpu,
        "profile": profile,
        "accelerator_available": bool(gpu and gpu.get("accelerator")),
    }
