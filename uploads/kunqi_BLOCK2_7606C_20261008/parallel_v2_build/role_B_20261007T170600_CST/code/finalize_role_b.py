#!/usr/bin/env python3
"""Finalize the Independent Work B handoff after inference and tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def main():
    workdir = Path(sys.argv[1]).resolve(strict=True)
    run = workdir / "artifacts/fixture_run"
    artifacts = workdir / "artifacts"
    copies = {
        "raw_motion.npz": "fixture_raw_motion.npz",
        "generation.json": "fixture_generation.json",
        "runtime_api_report.json": "runtime_api_report.json",
        "conditioning_metrics.json": "conditioning_metrics.json",
    }
    for source, target in copies.items():
        shutil.copy2(run / source, artifacts / target)
    generation = json.loads((artifacts / "fixture_generation.json").read_text())
    metrics = json.loads((artifacts / "conditioning_metrics.json").read_text())
    tests = json.loads((workdir / "tests/test_results.json").read_text())
    status = "ready_for_final_integration" if tests["passed"] and generation["real_model_run"] else "failed"
    generator = workdir / "code/generate_kimodo.py"
    command = (
        f"source /workspace/group2/kimodo-t6/g1-integration/activate-g1.sh && "
        f"KIMODO_PHYSICAL_GPU=<FREE_GPU_ID> {sys.executable} {generator} "
        "--request generation_request.json --pose-constraints pose_constraints.json --output-dir OUTPUT"
    )
    readme = f"""# Independent Work B — Kimodo runtime and long-horizon generator

Status: `{status}`  
Contract: `kimodo_grasp_final_v1_20261007`

This bundle inspected the live Kimodo package and completed a genuine model inference on S4000 using an independent fixture. The fixture is not the final grasp (`real_model_run=true`, `final_grasp_run=false`).

## Final inputs

Provide exactly a frozen `generation_request.json` and its matching matrix-codec `pose_constraints.json`. The request hash for the constraint file is verified before model loading.

## Exact command template

```bash
{command}
```

Python: `{sys.executable}`. Select a genuinely free physical S4000 with `KIMODO_PHYSICAL_GPU`; inside the process it is exposed as logical `musa:0`.

## Duration and fps

The checkpoint reports 30 Hz. The wrapper converts seconds to `round(duration * fps) + 1` frames, so 16.2 s becomes 487 frames with timestamps 0.0 through 16.2. A single native generation call was empirically successful; segmentation is not required and no padding, frame repetition, extrapolation, tail copy, or smoothing is performed.

## Output

`OUTPUT/raw_motion.npz` contains only the arrays returned by Kimodo, converted to NumPy without motion modification. `generation.json` records model/checkpoint/device/timing/field shapes. `conditioning_metrics.json` records constraint loading, duration, exact duplicate/tail checks, and continuity. `runtime_api_report.json` records the inspected live signatures and limitations.

The proof run is copied to `artifacts/fixture_raw_motion.npz` and related JSON files. It uses `fixtures/fixture_generation_request.json` and is explicitly fixture-only.

## Proving 16.2 seconds is real

Require all of: actual frames = 487, checkpoint fps = 30, first timestamp = 0, last timestamp = 16.2, all raw arrays have 487 leading frames, finite values, and a fresh-process reload with matching SHA256. The tests also reject an exact duplicate last frame and a constant 30-frame tail.

## API facts

See `artifacts/runtime_api_report.json`. Kimodo accepts `prompts`, `num_frames`, `num_denoising_steps`, `constraint_lst`, CFG settings, and returns motion arrays. The generator loads the constraints through the matrix-preserving `load_pose_constraints()` path; the legacy axis-angle JSON path is not used.
"""
    (workdir / "README.md").write_text(readme, encoding="utf-8")

    protected = [
        Path("/workspace/group2/kimodo-t6/g1-integration/kimodo-upload/kimodo/model/kimodo_model.py"),
        Path("/workspace/group2/kimodo-t6/g1-integration/kimodo-upload/kimodo/model/load_model.py"),
        Path("/workspace/group2/kimodo-t6/g1-integration/coordinate-repair-20261007-v2/kimodo_pose_constraint_codec.py"),
        Path("/workspace/group2/kimodo-t6/g1-integration/checkpoints/Kimodo-G1-RP-v1/config.yaml"),
        Path("/workspace/group2/kimodo-t6/g1-integration/checkpoints/Kimodo-G1-RP-v1/model.safetensors"),
    ]
    anticipated = {"README.md", "change_audit.json", "handoff.json", "checksums.sha256"}
    audit = {
        "created_files": sorted({str(path.relative_to(workdir)) for path in workdir.rglob("*") if path.is_file()} | anticipated),
        "modified_files": [],
        "read_only_inputs": {str(path): sha256(path) for path in protected},
        "scope_note": "Work was confined to this new handoff directory; the listed live runtime inputs were inspected read-only.",
    }
    write_json(workdir / "change_audit.json", audit)
    handoff = {
        "role": "B",
        "contract_version": "kimodo_grasp_final_v1_20261007",
        "status": status,
        "generator_path": str(generator),
        "generator_sha256": sha256(generator),
        "real_model_run": generation["real_model_run"],
        "final_grasp_run": False,
        "tested_duration_sec": generation["actual_duration_sec"],
        "actual_fps": generation["actual_fps"],
        "actual_frames": generation["actual_frames"],
        "segmentation_required": generation["segmentation_required"],
        "duplicate_tail": metrics["duplicate_tail"],
        "runtime_api_report": str(artifacts / "runtime_api_report.json"),
        "runtime_api_report_sha256": sha256(artifacts / "runtime_api_report.json"),
        "raw_motion": str(artifacts / "fixture_raw_motion.npz"),
        "raw_motion_sha256": sha256(artifacts / "fixture_raw_motion.npz"),
        "conditioning_metrics": str(artifacts / "conditioning_metrics.json"),
        "conditioning_metrics_sha256": sha256(artifacts / "conditioning_metrics.json"),
        "tests_pass": tests["passed"],
        "exact_final_command_template": command,
    }
    write_json(workdir / "handoff.json", handoff)
    files = sorted(
        path for path in workdir.rglob("*")
        if path.is_file() and path.name != "checksums.sha256" and "logs" not in path.relative_to(workdir).parts
    )
    (workdir / "checksums.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(workdir).as_posix()}\n" for path in files), encoding="utf-8"
    )
    print(json.dumps(handoff, indent=2, ensure_ascii=False))
    return 0 if status == "ready_for_final_integration" else 2


if __name__ == "__main__":
    raise SystemExit(main())
