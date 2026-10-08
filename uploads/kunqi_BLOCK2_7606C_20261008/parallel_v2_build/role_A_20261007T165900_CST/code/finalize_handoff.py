#!/usr/bin/env python3
"""Create the Role-A audit, README, handoff manifest and checksums."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", type=Path, required=True)
    args = parser.parse_args()
    workdir = args.workdir.resolve(strict=True)
    artifacts = workdir / "artifacts"
    task = json.loads((artifacts / "generation_request.json").read_text())
    metrics = json.loads((artifacts / "planning_metrics.json").read_text())
    tests = json.loads((workdir / "tests/test_results.json").read_text())
    before = json.loads((workdir / "logs/input_hashes_before.json").read_text())
    after = json.loads((workdir / "logs/input_hashes_after.json").read_text())
    status = "ready_for_final_integration" if tests["passed"] and metrics["status"] == "ready_for_final_integration" else "failed"

    pending = [
        line[2:].strip()
        for line in (workdir / "pending.md").read_text().splitlines()
        if line.startswith("- ")
    ]
    run_command = f"bash {workdir}/run_role_a.sh"
    readme = f"""# Kimodo Role A handoff

Status: `{status}`  
Contract: `{task['contract_version']}`

This bundle is real canonical CPU task/IK/hand planning. It is not a fixture. It does not claim Kimodo generation, SONIC replay, physical success, or expert validity.

## Exact runtime

Python: `/workspace/group2/workspace/amy/kimodo-work/.venv/bin/python`

Activation: `/workspace/group2/kimodo-t6/g1-integration/activate-g1.sh`

Exact one-shot command:

```bash
{run_command}
```

The command is single-use because artifact creation refuses to overwrite an existing directory.

## Inputs

- Canonical project: `/workspace/group2/dl-group2`
- Robot XML: `{task['robot_xml']}`
- Scene XML: `{task['scene_xml']}`
- Existing matrix coordinate repair: `/workspace/group2/kimodo-t6/g1-integration/coordinate-repair-20261007-v2`
- Case/seed/hand: `center / 0 / right`

No old ARDY trajectory, old hand plan, old object trajectory, or old frame schedule is consumed.

## Outputs and shapes

- `artifacts/generation_request.json`: portable frozen generator request, including task-plan and pose-constraint hashes.
- `artifacts/task_plan.npz`:
  - `source_timestamps`: `({task['source_frames']},)` at 30 Hz, covering 16.2 s.
  - `source_qpos`: `({task['source_frames']}, 36)` root7 + Kimodo-XML body29.
  - `canonical_wrist_world_pos`: `({task['source_frames']}, 2, 3)`, wrist order left/right.
  - `canonical_wrist_world_quat`: `({task['source_frames']}, 2, 4)`, wxyz.
  - `timestamps`: `(810,)` at 50 Hz, 0.00 through 16.18 s.
  - `hand_ref_q`, `hand_ref_dq`: `(810, 14)` in canonical hand order.
- `artifacts/pose_constraints.json`: matrix-preserving Kimodo constraint record, saved and freshly reloaded.
- `artifacts/planning_metrics.json`: measured IK, limits, initial-state and codec errors.

## Verification

Fresh-process verification:

```bash
source /workspace/group2/kimodo-t6/g1-integration/activate-g1.sh
cd {workdir}
python code/verify_role_a.py --workdir {workdir}
```

Results: `{workdir}/tests/test_results.json`

## Downstream contract

The final generator consumes `generation_request.json` and `pose_constraints.json`; `task_plan.npz` is the synchronized planning/hand artifact. The matrix codec must be used without the legacy axis-angle serializer.

The final reference assembler consumes `task_plan.npz` together with a body reference produced from the generator output. It must preserve canonical body/hand order and the exact 50 Hz timeline; Role A's `source_qpos` is task conditioning, not generated output.

## Real versus unresolved

Real: canonical scene reset, neutral initial state, 16.2 s phase planner, right-wrist IK, newly generated hand14 plan, matrix codec save/reload and SHA checks.

Unresolved: real Kimodo generation, canonical generated-reference export, SONIC replay and physical success. See `pending.md`.
"""
    (workdir / "README.md").write_text(readme, encoding="utf-8")

    anticipated = ["README.md", "change_audit.json", "handoff.json", "checksums.sha256"]
    created = sorted(
        {str(path.relative_to(workdir)) for path in workdir.rglob("*") if path.is_file()} | set(anticipated)
    )
    audit = {
        "created_files": created,
        "modified_files": [],
        "read_only_inputs": [item["path"] for item in before.values()],
        "protected_files_checked": [item["path"] for item in before.values()],
        "before_hashes": {item["path"]: item["sha256"] for item in before.values()},
        "after_hashes": {item["path"]: item["sha256"] for item in after.values()},
        "protected_files_unchanged": before == after,
        "scope_note": "Only the listed protected inputs were hashed; no broader unchanged claim is made.",
    }
    write_json(workdir / "change_audit.json", audit)

    artifact_paths = {
        name: str(artifacts / name)
        for name in ["generation_request.json", "task_plan.npz", "pose_constraints.json", "planning_metrics.json"]
    }
    artifact_hashes = {name: sha256(path) for name, path in artifact_paths.items()}
    handoff = {
        "role": "A",
        "owner": "kunqi + Codex",
        "run_id": workdir.name,
        "task_id": task["task_id"],
        "contract_version": task["contract_version"],
        "status": status,
        "generation_request": {"path": artifact_paths["generation_request.json"], "sha256": artifact_hashes["generation_request.json"]},
        "task_plan": {"path": artifact_paths["task_plan.npz"], "sha256": artifact_hashes["task_plan.npz"]},
        "pose_constraints": {"path": artifact_paths["pose_constraints.json"], "sha256": artifact_hashes["pose_constraints.json"]},
        "planning_metrics": {"path": artifact_paths["planning_metrics.json"], "sha256": artifact_hashes["planning_metrics.json"]},
        "input_paths": {name: item["path"] for name, item in before.items()},
        "input_hashes": {name: item["sha256"] for name, item in before.items()},
        "entrypoints": {"prepare_grasp_task": str(workdir / "code/prepare_grasp_task.py")},
        "executed_commands": [run_command],
        "test_results_path": str(workdir / "tests/test_results.json"),
        "tests_pass": tests["passed"],
        "fixture_only": False,
        "real_generation_run": False,
        "physical_replay_run": False,
        "physical_success": None,
        "expert_valid": None,
        "resource_requirements": {"gpu": False, "dds": False},
        "pending": pending,
    }
    write_json(workdir / "handoff.json", handoff)

    checksum_files = sorted(
        path
        for path in workdir.rglob("*")
        if path.is_file() and path.name != "checksums.sha256" and "logs" not in path.relative_to(workdir).parts
    )
    (workdir / "checksums.sha256").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(workdir).as_posix()}\n" for path in checksum_files),
        encoding="utf-8",
    )
    print(json.dumps({"status": status, "handoff": str(workdir / "handoff.json")}, indent=2))
    return 0 if status == "ready_for_final_integration" else 2


if __name__ == "__main__":
    raise SystemExit(main())
