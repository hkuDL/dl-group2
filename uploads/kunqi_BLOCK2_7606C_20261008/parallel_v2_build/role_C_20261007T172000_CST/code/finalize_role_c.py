#!/usr/bin/env python3
"""Write loader/evidence contracts and finalize Independent Work C."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


BASE = Path("/workspace/group2")
CANONICAL = BASE / "dl-group2"
SONIC = BASE / "GR00T-WholeBodyControl"
LOADER = SONIC / "gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/include/motion_data_reader.hpp"
WRITER = CANONICAL / "scripts/reference_io.py"
RUNNER = CANONICAL / "scripts/run_sonic_grasp.py"
PHASE1 = BASE / "kimodo-t6/g1-integration/kimodo_to_t7_reference.py"


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
    artifacts = workdir / "artifacts"
    tests = json.loads((workdir / "tests/test_results.json").read_text())
    loader_contract = {
        "contract_version": "kimodo_grasp_final_v1_20261007",
        "actual_loader": str(LOADER),
        "actual_loader_sha256": sha256(LOADER),
        "canonical_writer": str(WRITER),
        "canonical_writer_sha256": sha256(WRITER),
        "loader_behavior": "MotionDataReader::ReadFromCSV discovers one subdirectory per motion, skips each CSV first line as header, parses remaining comma-separated doubles, and validates frame-count/body-count consistency.",
        "body_part_indexes": [0],
        "metadata_txt": "Body part indexes followed by [0], and Total timesteps: 810",
        "sample_rate_hz": 50,
        "timestamps": "not stored in the six native CSV files; frame index / 50 is the frozen reference clock",
        "files": [
            {"name": "joint_pos.csv", "shape": [810, 29], "order": "canonical expert_trajectory.orders() body order", "unit": "radian", "header": "joint_<canonical_joint_name>"},
            {"name": "joint_vel.csv", "shape": [810, 29], "order": "same canonical body order", "unit": "radian/second", "header": "joint_vel_<canonical_joint_name>"},
            {"name": "body_pos.csv", "shape": [810, 3], "order": ["root_x", "root_y", "root_z"], "unit": "metre", "header": ["body_0_x", "body_0_y", "body_0_z"]},
            {"name": "body_quat.csv", "shape": [810, 4], "order": ["w", "x", "y", "z"], "unit": "unit quaternion", "header": ["body_0_w", "body_0_x", "body_0_y", "body_0_z"]},
            {"name": "body_lin_vel.csv", "shape": [810, 3], "order": ["world_vx", "world_vy", "world_vz"], "unit": "metre/second", "header": ["body_0_vel_x", "body_0_vel_y", "body_0_vel_z"]},
            {"name": "body_ang_vel.csv", "shape": [810, 3], "order": ["world_wx", "world_wy", "world_wz"], "unit": "radian/second", "header": ["body_0_angvel_x", "body_0_angvel_y", "body_0_angvel_z"]},
        ],
        "header_note": "The actual C++ loader ignores header text after skipping row 1; the exporter preserves the canonical descriptive headers used by the current project.",
        "fresh_process_probe": str(workdir / "tests/sonic_loader_probe"),
        "fresh_process_test_pass": tests["fresh_loader_test_pass"],
    }
    evidence_schema = {
        "format": "npz",
        "file": "replay_evidence.npz",
        "row_semantics": "one row per MuJoCo physics step, including initialization and playing",
        "required_fields": {
            "physics_step": "int64[N]", "physics_time": "float64[N]", "playing": "bool[N]",
            "reference_index": "int64[N] (-1 outside playing)", "reference_time": "float64[N]",
            "robot_qpos": "float64[N,nq]", "robot_qvel": "float64[N,nv]",
            "cube_pos": "float64[N,3]", "cube_quat": "float64[N,4]", "cube_reset_pos": "float64[N,3]", "cube_lift": "float64[N]",
            "thumb_cube_contact": "bool[N]", "index_cube_contact": "bool[N]", "middle_cube_contact": "bool[N]",
            "thumb_contact_force": "float64[N]", "index_contact_force": "float64[N]", "middle_contact_force": "float64[N]",
            "cube_table_contact": "bool[N]", "fall_detected": "bool[N]", "support_detected": "bool[N]", "weld_detected": "bool[N]", "finite": "bool[N]",
        },
        "force_semantics": "absolute MuJoCo contact normal force; digit forces are the maximum matching cube contact force per physics step",
        "contact_grouping": "current canonical body-name substring grouping; no extra contact-normal-angle threshold",
    }
    validation_schema = {
        "physical_success": "same continuous interval: lift >=0.10m, thumb force >1e-4N, index OR middle force >1e-4N, no cube-table contact, duration >=2.0s",
        "hold_reset": "any failed condition resets the interval",
        "expert_valid": "physical_success AND complete finite synchronized unassisted canonical replay AND no fall/support/weld AND all integrity checks pass",
        "reported_metrics": [
            "max_cube_lift", "longest_qualifying_hold_sec", "terminal_qualifying_hold_sec",
            "minimum_required_contact_force_during_qualifying_interval", "cube_table_contact_during_qualifying_interval",
        ],
        "synthetic_cases": 16,
    }
    write_json(artifacts / "sonic_loader_contract.json", loader_contract)
    write_json(artifacts / "replay_evidence_schema.json", evidence_schema)
    write_json(artifacts / "validation_schema.json", validation_schema)
    status = "ready_for_final_integration" if tests["passed"] else "failed"
    assembler = workdir / "code/assemble_sonic_reference.py"
    capture = workdir / "code/capture_sonic_replay.py"
    validator = workdir / "code/validate_kimodo_replay.py"
    assemble_command = f"{sys.executable} {assembler} --body-reference body_reference.npz --task-plan task_plan.npz --output-dir OUTPUT_REFERENCE"
    replay_command = f"{sys.executable} {capture} --reference-dir OUTPUT_REFERENCE --output-dir OUTPUT_REPLAY"
    validate_command = f"{sys.executable} {validator} --evidence OUTPUT_REPLAY/replay_evidence.npz --integrity OUTPUT_REPLAY/integrity.json --output OUTPUT_REPLAY/validation.json"
    readme = f"""# Independent Work C — SONIC reference, evidence and validation

Status: `{status}`  
Contract: `kimodo_grasp_final_v1_20261007`

This bundle is independent of the current Role-A/Role-B outputs. It uses deterministic fixtures to prove that the final CLI contracts work. It does not claim a new Kimodo physical replay.

## Assemble

```bash
{assemble_command}
```

`body_reference.npz` must contain the existing Phase1 converter's body/root fields. It may contain the frozen 810 frames through 16.18 s, or Phase1's 811-frame inclusive endpoint through 16.20 s; in the latter case the assembler explicitly drops only the out-of-contract 16.20 s sample. `task_plan.npz` supplies exactly 810 hand14 frames through 16.18 s. Explicit name arrays are verified when present; the documented minimal NPZ contract uses the frozen canonical order. Short, shifted, padded, repeated-tail, or extrapolated inputs fail.

The assembler calls the current canonical exporter. It writes `reference.npz`, NPY files used by the Python replay path, the six native SONIC CSV files, hand files, timestamps, and metadata. The actual C++ `MotionDataReader` successfully loaded the fixture in a fresh process; see `artifacts/sonic_loader_contract.json`.

## Replay evidence

```bash
{replay_command}
```

The capture tool monkey-patches only a per-step evidence hook around the existing `{RUNNER}` entrypoint. It does not implement or modify the controller. Replay flags are frozen to band off, no startup support, no weld, Kp/Kd scales 1, hand PD 12/0.3, physics dt 0.005, and no replay-time IK. It records every MuJoCo physics step to `replay_evidence.npz` plus integrity hashes/configuration.

## Independent validation

```bash
{validate_command}
```

The validator reads only evidence and integrity metadata; it never trusts the canonical runner's summary success. It recomputes cube lift from positions, verifies the logged lift, applies the exact contact/force/table/continuous-hold rule, and separately gates `expert_valid` on completeness, synchronization, finite state and integrity. T01-T16 all pass in `tests/synthetic_summary.json`.

## Phase1

The body/root converter remains `{PHASE1}` (SHA256 `{sha256(PHASE1)}`). This work does not create a competing Kimodo-to-body converter.
"""
    (workdir / "README.md").write_text(readme, encoding="utf-8")
    handoff = {
        "role": "C", "contract_version": "kimodo_grasp_final_v1_20261007", "status": status,
        "assembler": str(assembler), "assembler_sha256": sha256(assembler),
        "replay_capture": str(capture), "replay_capture_sha256": sha256(capture),
        "validator": str(validator), "validator_sha256": sha256(validator),
        "sonic_loader_contract": str(artifacts / "sonic_loader_contract.json"),
        "sonic_loader_contract_sha256": sha256(artifacts / "sonic_loader_contract.json"),
        "synthetic_tests_pass": tests["synthetic_validator_tests_pass"],
        "fresh_loader_test_pass": tests["fresh_loader_test_pass"],
        "number_of_test_cases": tests["number_of_synthetic_cases"],
        "tests_pass": tests["passed"], "physical_success": None, "expert_valid": None,
        "exact_assemble_command": assemble_command, "exact_replay_command": replay_command, "exact_validate_command": validate_command,
    }
    write_json(workdir / "handoff.json", handoff)
    protected = [LOADER, WRITER, RUNNER, PHASE1]
    anticipated = {"README.md", "change_audit.json", "handoff.json", "checksums.sha256"}
    write_json(workdir / "change_audit.json", {
        "created_files": sorted({str(path.relative_to(workdir)) for path in workdir.rglob("*") if path.is_file()} | anticipated),
        "modified_files": [], "read_only_inputs": {str(path): sha256(path) for path in protected},
        "scope_note": "All implementation and test outputs are confined to this new role directory.",
    })
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
