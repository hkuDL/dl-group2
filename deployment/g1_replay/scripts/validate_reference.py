from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import yaml

from contracts.reference import ReferenceBundle, validate_reference


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a canonical G1 reference without sending it")
    parser.add_argument("reference_dir", type=Path)
    parser.add_argument("--mode", choices=("dry-run", "real"), default="dry-run")
    parser.add_argument("--safety-config", type=Path)
    parser.add_argument("--current-pose", type=Path)
    args = parser.parse_args()

    safety = yaml.safe_load(args.safety_config.read_text()) if args.safety_config else None
    current_pose = None
    if args.current_pose:
        with np.load(args.current_pose, allow_pickle=False) as archive:
            current_pose = archive["body_q"]
    report = validate_reference(
        ReferenceBundle.load(args.reference_dir),
        mode=args.mode,
        safety_config=safety,
        current_pose=current_pose,
    )
    print(json.dumps(report.as_dict(), indent=2, ensure_ascii=False))
    return 0 if report.overall == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

