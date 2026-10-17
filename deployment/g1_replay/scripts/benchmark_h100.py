from __future__ import annotations

import argparse
import importlib
import json
import time
from pathlib import Path

import yaml

from inference.common import benchmark_cuda
from scripts.run_inference import PIPELINES


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark one prepared batch-one pipeline on an actual H100")
    parser.add_argument("model", choices=PIPELINES)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--warmup", type=int, default=2)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args()
    if args.config.is_absolute() or args.report.is_absolute():
        parser.error("paths must be project-relative")
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / args.config).read_text(encoding="utf-8"))
    module = importlib.import_module(PIPELINES[args.model])

    import torch
    load_started = time.perf_counter()
    runner = module.prepare(config, root)
    torch.cuda.synchronize()
    model_load_seconds = time.perf_counter() - load_started
    report = benchmark_cuda(runner, warmup=args.warmup, repeats=args.repeats, require_h100=True)
    report.update(
        {
            "model": args.model,
            "model_load_seconds": model_load_seconds,
            "measurement_scope": "prepared model inference plus Sonic-reference adapter",
            "simulator_used": False,
            "training_data_used": False,
        }
    )
    destination = root / args.report
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
