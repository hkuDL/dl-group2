from __future__ import annotations

import statistics
import time
from pathlib import Path
from typing import Any, Callable, Dict


def ensure_batch_one(batch_size: int) -> None:
    if batch_size != 1:
        raise ValueError(f"this deployment pipeline is fixed to batch=1, got {batch_size}")


def resolve_project_path(project_root: Path, configured: str) -> Path:
    path = Path(configured)
    if path.is_absolute():
        raise ValueError(f"runtime paths must be project-relative, got {configured}")
    resolved = (project_root / path).resolve()
    if project_root.resolve() not in resolved.parents and resolved != project_root.resolve():
        raise ValueError(f"runtime path escapes project root: {configured}")
    return resolved


def benchmark_cuda(call: Callable[[], Any], *, warmup: int = 3, repeats: int = 10, require_h100: bool = True) -> Dict[str, Any]:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; H100 benchmark not run")
    device_name = torch.cuda.get_device_name(0)
    if require_h100 and "H100" not in device_name.upper():
        raise RuntimeError(f"expected H100, found {device_name!r}; refusing to mislabel results")
    for _ in range(warmup):
        call()
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    timings = []
    for _ in range(repeats):
        start = time.perf_counter()
        call()
        torch.cuda.synchronize()
        timings.append((time.perf_counter() - start) * 1000.0)
    ordered = sorted(timings)
    p95 = ordered[min(len(ordered) - 1, max(0, int(round(0.95 * len(ordered))) - 1))]
    return {
        "device": device_name,
        "batch_size": 1,
        "warmup_runs": warmup,
        "measured_runs": repeats,
        "latency_ms_mean": statistics.fmean(timings),
        "latency_ms_p50": statistics.median(timings),
        "latency_ms_p95": p95,
        "peak_allocated_bytes": int(torch.cuda.max_memory_allocated()),
        "peak_reserved_bytes": int(torch.cuda.max_memory_reserved()),
    }

