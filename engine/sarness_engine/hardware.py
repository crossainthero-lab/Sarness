"""Hardware and runtime introspection. Never imports torch (that would allocate VRAM)."""

from __future__ import annotations

import logging
import os
import platform
import shutil
import socket
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import psutil

log = logging.getLogger("sarness.hardware")

try:
    import pynvml  # provided by nvidia-ml-py

    pynvml.nvmlInit()
    _NVML = True
except Exception:  # pragma: no cover - machines without NVIDIA driver
    pynvml = None
    _NVML = False


def _s(v: Any) -> str:
    return v.decode() if isinstance(v, bytes) else str(v)


@lru_cache(maxsize=1)
def cpu_name() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "Unknown CPU"


def gpus() -> list[dict[str, Any]]:
    if not _NVML:
        return []
    out = []
    try:
        driver = _s(pynvml.nvmlSystemGetDriverVersion())
        try:
            cuda_drv = pynvml.nvmlSystemGetCudaDriverVersion_v2()
            cuda_driver = f"{cuda_drv // 1000}.{(cuda_drv % 1000) // 10}"
        except Exception:
            cuda_driver = None
        for i in range(pynvml.nvmlDeviceGetCount()):
            h = pynvml.nvmlDeviceGetHandleByIndex(i)
            mem = pynvml.nvmlDeviceGetMemoryInfo(h)
            util = pynvml.nvmlDeviceGetUtilizationRates(h)
            try:
                temp = pynvml.nvmlDeviceGetTemperature(h, pynvml.NVML_TEMPERATURE_GPU)
            except Exception:
                temp = None
            try:
                power = pynvml.nvmlDeviceGetPowerUsage(h) / 1000.0
                power_limit = pynvml.nvmlDeviceGetEnforcedPowerLimit(h) / 1000.0
            except Exception:
                power = power_limit = None
            procs = []
            try:
                for p in pynvml.nvmlDeviceGetComputeRunningProcesses(h):
                    procs.append({"pid": p.pid, "used_mb": (p.usedGpuMemory or 0) // (1024 * 1024)})
            except Exception:
                pass
            out.append({
                "index": i,
                "name": _s(pynvml.nvmlDeviceGetName(h)),
                "vram_total_mb": mem.total // (1024 * 1024),
                "vram_used_mb": mem.used // (1024 * 1024),
                "vram_free_mb": mem.free // (1024 * 1024),
                "utilization_pct": util.gpu,
                "temperature_c": temp,
                "power_w": power,
                "power_limit_w": power_limit,
                "driver_version": driver,
                "cuda_driver_version": cuda_driver,
                "compute_processes": procs,
            })
    except Exception as exc:  # pragma: no cover
        log.warning("NVML query failed: %s", exc)
    return out


def vram_free_mb(index: int = 0) -> int | None:
    g = gpus()
    return g[index]["vram_free_mb"] if len(g) > index else None


def vram_total_mb(index: int = 0) -> int | None:
    g = gpus()
    return g[index]["vram_total_mb"] if len(g) > index else None


def system_snapshot(data_dir: Path) -> dict[str, Any]:
    vm = psutil.virtual_memory()
    du = shutil.disk_usage(data_dir)
    load = os.getloadavg() if hasattr(os, "getloadavg") else (0, 0, 0)
    return {
        "hostname": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "distro": _distro(),
        "python": platform.python_version(),
        "cpu": {
            "name": cpu_name(),
            "cores_physical": psutil.cpu_count(logical=False),
            "cores_logical": psutil.cpu_count(logical=True),
            "utilization_pct": psutil.cpu_percent(interval=None),
            "load_avg": list(load),
        },
        "memory": {
            "total_mb": vm.total // (1024 * 1024),
            "used_mb": (vm.total - vm.available) // (1024 * 1024),
            "available_mb": vm.available // (1024 * 1024),
        },
        "storage": {
            "path": str(data_dir),
            "total_gb": round(du.total / 1e9, 1),
            "used_gb": round(du.used / 1e9, 1),
            "free_gb": round(du.free / 1e9, 1),
        },
        "gpus": gpus(),
        "uptime_s": time.time() - psutil.boot_time(),
    }


@lru_cache(maxsize=1)
def _distro() -> str:
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if line.startswith("PRETTY_NAME="):
                return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return platform.platform()


def disk_free_bytes(path: Path) -> int:
    path = Path(path)
    while not path.exists():
        path = path.parent
    return shutil.disk_usage(path).free
