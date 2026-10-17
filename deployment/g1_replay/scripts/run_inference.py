from __future__ import annotations

import argparse
import importlib
from pathlib import Path

import yaml


PIPELINES = {
    "kimodo": "inference.kimodo_pipeline",
    "ardy": "inference.ardy_pipeline",
    "va": "inference.va_pipeline",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one simulator-free batch-one inference pipeline")
    parser.add_argument("model", choices=PIPELINES)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parents[1]
    if args.config.is_absolute() or args.output.is_absolute():
        parser.error("--config and --output must be project-relative paths")
    config = yaml.safe_load((project_root / args.config).read_text(encoding="utf-8"))
    importlib.import_module(PIPELINES[args.model]).run(config, project_root, project_root / args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

