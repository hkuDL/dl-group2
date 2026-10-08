#!/usr/bin/env python3
"""Independent assembler, actual-loader, capture-interface, and T01-T16 validator tests."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np


BASE = Path("/workspace/group2")
CANONICAL = BASE / "dl-group2"
SONIC = BASE / "GR00T-WholeBodyControl"
ROBOT = SONIC / "decoupled_wbc/control/robot_model/model_data/g1/g1_29dof_with_hand_rev_1_0_activatedfinger.xml"
SCENE = CANONICAL / "scenes/tabletop.xml"
CONTRACT = "kimodo_grasp_final_v1_20261007"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def copy_evidence(value):
    return {key: np.asarray(item).copy() for key, item in value.items()}


def main():
    workdir = Path(sys.argv[1]).resolve(strict=True)
    reference = workdir / "artifacts/fixture_reference"
    os.environ["SONIC_REPO"] = str(SONIC)
    sys.path.insert(0, str(CANONICAL / "scripts"))
    sys.path.insert(0, str(workdir / "code"))
    from expert_trajectory import load_reference, orders
    from validate_kimodo_replay import validate
    body_order, hand_order, _ = orders()
    results = []

    def check(name, function):
        try:
            detail = function()
            if isinstance(detail, np.generic):
                detail = detail.item()
            results.append({"name": name, "status": "pass", "detail": detail})
        except Exception as exc:
            results.append({"name": name, "status": "fail", "detail": f"{type(exc).__name__}: {exc}"})

    def canonical_loader():
        arrays, metadata = load_reference(reference)
        assert len(arrays["timestamps"]) == 810
        assert metadata["body_joint_order"] == body_order and metadata["hand_joint_order"] == hand_order
        return {key: list(value.shape) for key, value in arrays.items()}

    check("canonical_python_loader_fresh_process", canonical_loader)

    def six_csv():
        expected = {
            "joint_pos.csv": 29, "joint_vel.csv": 29, "body_pos.csv": 3,
            "body_quat.csv": 4, "body_lin_vel.csv": 3, "body_ang_vel.csv": 3,
        }
        result = {}
        for name, width in expected.items():
            path = reference / name
            lines = path.read_text().splitlines()
            assert len(lines) == 811 and len(lines[0].split(",")) == width
            values = np.loadtxt(path, delimiter=",", skiprows=1, ndmin=2)
            assert values.shape == (810, width) and np.isfinite(values).all()
            result[name] = list(values.shape)
        return result

    check("six_sonic_csv_files", six_csv)

    def actual_cpp_loader():
        parent = workdir / "tests/loader_parent"
        parent.mkdir(exist_ok=False)
        (parent / "fixture_motion").symlink_to(reference, target_is_directory=True)
        process = subprocess.run([str(workdir / "tests/sonic_loader_probe"), str(parent)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        assert process.returncode == 0 and "ACTUAL_SONIC_LOADER_PASS" in process.stdout, process.stdout
        return process.stdout.strip()

    check("actual_sonic_cpp_loader_fresh_process", actual_cpp_loader)

    def capture_input_validation():
        target = workdir / "tests/capture_input_validation"
        process = subprocess.run([
            sys.executable, str(workdir / "code/capture_sonic_replay.py"),
            "--reference-dir", str(reference), "--output-dir", str(target), "--validate-input-only",
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        assert process.returncode == 0, process.stdout
        return json.loads((target / "input_validation.json").read_text())

    check("capture_wrapper_input_contract", capture_input_validation)

    def bad_assembler(label, body_file, task_file):
        target = workdir / f"tests/{label}_out"
        process = subprocess.run([
            sys.executable, str(workdir / "code/assemble_sonic_reference.py"),
            "--body-reference", str(body_file), "--task-plan", str(task_file), "--output-dir", str(target),
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        assert process.returncode != 0, process.stdout
        return process.stdout[-400:]

    fixture = workdir / "fixtures"
    with np.load(fixture / "body_reference_fixture.npz", allow_pickle=False) as z:
        body = {key: z[key].copy() for key in z.files}
    bad_short = workdir / "tests/body_short.npz"
    np.savez_compressed(bad_short, **{key: value[:-1] if value.ndim and len(value) == 810 else value for key, value in body.items()})
    check("assembler_rejects_short_input", lambda: bad_assembler("short", bad_short, fixture / "task_plan_fixture.npz"))
    bad_time_data = dict(body)
    bad_time_data["timestamps"] = body["timestamps"].copy()
    bad_time_data["timestamps"][400] += 0.001
    bad_time = workdir / "tests/body_bad_time.npz"
    np.savez_compressed(bad_time, **bad_time_data)
    check("assembler_rejects_timestamp_mismatch", lambda: bad_assembler("bad_time", bad_time, fixture / "task_plan_fixture.npz"))

    def minimal_frozen_contract():
        minimal_body = workdir / "tests/body_minimal_contract.npz"
        np.savez_compressed(minimal_body, **{key: value for key, value in body.items() if key not in {"body_joint_names", "contract_version", "fixture_only"}})
        with np.load(fixture / "task_plan_fixture.npz", allow_pickle=False) as z:
            task_values = {key: z[key].copy() for key in z.files if key not in {"hand_joint_names", "contract_version", "fixture_only"}}
        minimal_task = workdir / "tests/task_minimal_contract.npz"
        np.savez_compressed(minimal_task, **task_values)
        target = workdir / "tests/minimal_contract_reference"
        process = subprocess.run([
            sys.executable, str(workdir / "code/assemble_sonic_reference.py"),
            "--body-reference", str(minimal_body), "--task-plan", str(minimal_task), "--output-dir", str(target),
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        assert process.returncode == 0, process.stdout
        arrays, metadata = load_reference(target)
        assert len(arrays["timestamps"]) == 810
        assert metadata["body_joint_order_source"] == "frozen_canonical_contract_order"
        assert metadata["hand_joint_order_source"] == "frozen_canonical_contract_order"
        return "minimal frozen NPZ keys accepted with canonical implicit order"

    check("minimal_frozen_input_contract", minimal_frozen_contract)

    def phase1_inclusive_endpoint_contract():
        extended = {}
        for key, value in body.items():
            if key == "timestamps":
                extended[key] = np.arange(811, dtype=np.float64) / 50.0
            elif value.ndim and len(value) == 810:
                last = value[-1:].copy()
                if key == "body_ref_q":
                    last[:, 0] += 1e-5
                extended[key] = np.concatenate([value, last], axis=0)
            else:
                extended[key] = value
        body_811 = workdir / "tests/body_phase1_811.npz"
        np.savez_compressed(body_811, **extended)
        target = workdir / "tests/phase1_811_reference"
        process = subprocess.run([
            sys.executable, str(workdir / "code/assemble_sonic_reference.py"),
            "--body-reference", str(body_811), "--task-plan", str(fixture / "task_plan_fixture.npz"), "--output-dir", str(target),
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        assert process.returncode == 0, process.stdout
        metadata = json.loads((target / "assembler_metadata.json").read_text())
        assert metadata["body_input_frames"] == 811 and metadata["discarded_surplus_frame_count"] == 1
        with np.load(target / "reference.npz", allow_pickle=False) as z:
            assert z["timestamps"].shape == (810,) and z["timestamps"][-1] == 16.18
        return "Phase1 inclusive 16.20 s endpoint is explicitly dropped to the frozen 16.18 s contract"

    check("phase1_811_endpoint_compatibility", phase1_inclusive_endpoint_contract)

    dt = 0.005
    n = 3240
    step = np.arange(n, dtype=np.int64)
    ref = np.floor_divide(step, 4).clip(max=809)
    reset = np.array([0.4, -0.15, 0.785], dtype=np.float64)
    base = {
        "physics_step": step,
        "physics_time": step.astype(np.float64) * dt,
        "playing": np.ones(n, dtype=bool),
        "reference_index": ref,
        "reference_time": ref.astype(np.float64) / 50.0,
        "robot_qpos": np.zeros((n, 57), dtype=np.float64),
        "robot_qvel": np.zeros((n, 55), dtype=np.float64),
        "cube_pos": np.tile(reset, (n, 1)),
        "cube_quat": np.tile([1.0, 0.0, 0.0, 0.0], (n, 1)),
        "cube_reset_pos": np.tile(reset, (n, 1)),
        "cube_lift": np.zeros(n, dtype=np.float64),
        "thumb_cube_contact": np.zeros(n, dtype=bool),
        "index_cube_contact": np.zeros(n, dtype=bool),
        "middle_cube_contact": np.zeros(n, dtype=bool),
        "thumb_contact_force": np.zeros(n, dtype=np.float64),
        "index_contact_force": np.zeros(n, dtype=np.float64),
        "middle_contact_force": np.zeros(n, dtype=np.float64),
        "cube_table_contact": np.zeros(n, dtype=bool),
        "fall_detected": np.zeros(n, dtype=bool),
        "support_detected": np.zeros(n, dtype=bool),
        "weld_detected": np.zeros(n, dtype=bool),
        "finite": np.ones(n, dtype=bool),
    }

    def qualify(evidence, selection):
        evidence["cube_lift"][selection] = 0.11
        evidence["cube_pos"][selection, 2] = reset[2] + 0.11
        evidence["thumb_cube_contact"][selection] = True
        evidence["index_cube_contact"][selection] = True
        evidence["thumb_contact_force"][selection] = 0.01
        evidence["index_contact_force"][selection] = 0.02

    integrity = {
        "contract_version": CONTRACT, "process_completed": True, "unassisted": True,
        "robot_xml_sha256": sha256(ROBOT), "scene_sha256": sha256(SCENE),
        "nq": 57, "nv": 55, "nu": 43, "neq": 0,
        "reference_frames": 810, "reference_fps": 50,
        "body_joint_order": body_order, "hand_joint_order": hand_order,
        "controller": "canonical_run_sonic_grasp", "sonic_kp_scale": 1.0, "sonic_kd_scale": 1.0,
        "hand_pd": {"kp": 12.0, "kd": 0.3}, "physics_dt": dt, "gravity": [0.0, 0.0, -9.81],
    }

    cases = {}
    e = copy_evidence(base); qualify(e, slice(n - 440, n)); cases["T01_full_success"] = (e, True, True)
    e = copy_evidence(base); qualify(e, slice(n - 440, n)); e["cube_lift"][-440:] = 0.099; e["cube_pos"][-440:, 2] = reset[2] + 0.099; cases["T02_lift_0p099"] = (e, False, False)
    e = copy_evidence(base); qualify(e, slice(n - 440, n)); e["thumb_cube_contact"][-440:] = False; cases["T03_no_thumb"] = (e, False, False)
    e = copy_evidence(base); qualify(e, slice(n - 440, n)); e["index_cube_contact"][-440:] = False; cases["T04_no_index_or_middle"] = (e, False, False)
    e = copy_evidence(base); qualify(e, slice(n - 440, n)); e["thumb_contact_force"][-440:] = 1e-4; cases["T05_force_at_threshold"] = (e, False, False)
    e = copy_evidence(base); qualify(e, slice(n - 440, n)); e["cube_table_contact"][-440:] = True; cases["T06_cube_table_contact"] = (e, False, False)
    e = copy_evidence(base); qualify(e, slice(n - 398, n)); cases["T07_hold_1p99"] = (e, False, False)
    e = copy_evidence(base); qualify(e, slice(n - 900, n)); e["thumb_cube_contact"][n - 500:n - 490] = False; cases["T08_interrupted_restarted"] = (e, True, True)
    e = copy_evidence(base); qualify(e, slice(1000, 1420)); qualify(e, slice(n - 100, n)); cases["T09_longest_success_terminal_short"] = (e, True, True)
    e = copy_evidence(base); qualify(e, slice(n - 440, n)); e["fall_detected"][100] = True; cases["T10_fall"] = (e, True, False)
    e = copy_evidence(base); qualify(e, slice(n - 440, n)); e["support_detected"][100] = True; cases["T11_support"] = (e, True, False)
    e = copy_evidence(base); qualify(e, slice(n - 440, n)); e["weld_detected"][100] = True; cases["T12_weld"] = (e, True, False)
    e = copy_evidence(base); qualify(e, slice(n - 440, n)); e["robot_qpos"][0, 0] = np.nan; e["finite"][0] = False; cases["T13_nan"] = (e, True, False)
    e = {key: value[:3200].copy() for key, value in copy_evidence(base).items()}; qualify(e, slice(2760, 3200)); cases["T14_incomplete_replay"] = (e, True, False)
    e = copy_evidence(base); qualify(e, slice(n - 440, n)); e["physics_time"][1600:] += dt; cases["T15_timestamp_gap"] = (e, True, False)
    e = copy_evidence(base); qualify(e, slice(n - 440, n)); e["reference_time"][1600] += 0.01; cases["T16_unsynchronized_reference"] = (e, True, False)

    synthetic_root = workdir / "tests/synthetic"
    synthetic_root.mkdir(exist_ok=False)
    synthetic_summary = {}
    for label, (evidence, expected_physical, expected_expert) in cases.items():
        case = synthetic_root / label
        case.mkdir()
        evidence_path = case / "replay_evidence.npz"
        integrity_path = case / "integrity.json"
        np.savez_compressed(evidence_path, **evidence)
        integrity_path.write_text(json.dumps(integrity, indent=2) + "\n")
        result = validate(evidence_path, integrity_path)
        passed = result["physical_success"] is expected_physical and result["expert_valid"] is expected_expert
        synthetic_summary[label] = {
            "expected_physical_success": expected_physical,
            "actual_physical_success": result["physical_success"],
            "expected_expert_valid": expected_expert,
            "actual_expert_valid": result["expert_valid"],
            "passed": passed,
            "longest_hold": result["longest_qualifying_hold_sec"],
            "terminal_hold": result["terminal_qualifying_hold_sec"],
        }
        check(f"synthetic_{label}", lambda passed=passed, summary=synthetic_summary[label]: summary if passed else (_ for _ in ()).throw(AssertionError(summary)))
    (workdir / "tests/synthetic_summary.json").write_text(json.dumps(synthetic_summary, indent=2) + "\n")

    failures = [item for item in results if item["status"] == "fail"]
    result = {
        "scope": "Independent Work C reference/replay-evidence/validator toolchain",
        "passed": not failures,
        "fresh_loader_test_pass": next(item for item in results if item["name"] == "actual_sonic_cpp_loader_fresh_process")["status"] == "pass",
        "synthetic_validator_tests_pass": all(item["passed"] for item in synthetic_summary.values()),
        "number_of_synthetic_cases": len(synthetic_summary),
        "summary": {"pass": len(results) - len(failures), "fail": len(failures)},
        "tests": results,
    }
    (workdir / "tests/test_results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
