#!/usr/bin/env python3
"""Fresh-process validation of a Role-A artifact bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

import mujoco
import numpy as np


BASE = Path("/workspace/group2")
CANONICAL = BASE / "dl-group2"
SONIC = BASE / "GR00T-WholeBodyControl"
INTEGRATION = BASE / "kimodo-t6/g1-integration"
COORDINATES = INTEGRATION / "coordinate-repair-20261007-v2"
ROBOT = SONIC / "decoupled_wbc/control/robot_model/model_data/g1/g1_29dof_with_hand_rev_1_0_activatedfinger.xml"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", type=Path, required=True)
    args = parser.parse_args()
    workdir = args.workdir.resolve(strict=True)
    artifacts = workdir / "artifacts"
    result_path = workdir / "tests/test_results.json"
    result_path.parent.mkdir(exist_ok=True)

    tests = []

    def check(name, function):
        try:
            detail = function()
            tests.append({"name": name, "status": "pass", "detail": detail})
        except Exception as exc:
            tests.append({"name": name, "status": "fail", "detail": f"{type(exc).__name__}: {exc}"})

    task = json.loads((artifacts / "generation_request.json").read_text())
    metrics = json.loads((artifacts / "planning_metrics.json").read_text())
    with np.load(artifacts / "task_plan.npz", allow_pickle=False) as archive:
        plan = {name: archive[name].copy() for name in archive.files}

    check(
        "task_schema",
        lambda: (
            task["contract_version"] == "kimodo_grasp_final_v1_20261007"
            and task["case"] == "center"
            and task["seed"] == 0
            and task["active_hand"] == "right"
            and task["reference_frames"] == 810
        )
        or (_ for _ in ()).throw(AssertionError("fixed task contract mismatch")),
    )

    def shapes():
        expected = {
            "source_timestamps": (task["source_frames"],),
            "source_qpos": (task["source_frames"], 36),
            "canonical_wrist_world_pos": (task["source_frames"], 2, 3),
            "canonical_wrist_world_quat": (task["source_frames"], 2, 4),
            "timestamps": (810,),
            "hand_ref_q": (810, 14),
            "hand_ref_dq": (810, 14),
            "phase_id": (810,),
            "grasp_phase_mask": (810,),
            "lift_phase_mask": (810,),
            "hold_phase_mask": (810,),
        }
        for name, shape in expected.items():
            assert plan[name].shape == shape, (name, plan[name].shape, shape)
        return expected

    check("array_shapes", shapes)
    check(
        "finite_arrays",
        lambda: all(np.isfinite(value).all() for value in plan.values())
        or (_ for _ in ()).throw(AssertionError("non-finite array")),
    )

    def timestamps():
        np.testing.assert_allclose(plan["timestamps"], np.arange(810) / 50.0, rtol=0, atol=1e-12)
        np.testing.assert_allclose(
            plan["source_timestamps"], np.arange(task["source_frames"]) / 30.0, rtol=0, atol=1e-12
        )
        assert plan["source_timestamps"][-1] >= task["requested_duration_sec"] - 1e-12
        assert plan["timestamps"][-1] == 16.18
        return {"source_end": float(plan["source_timestamps"][-1]), "reference_end": 16.18}

    check("timestamp_monotonicity_and_exact_grid", timestamps)

    def phase_timing():
        expected = np.select(
            [plan["timestamps"] < 1.5, plan["timestamps"] < 8.0,
             plan["timestamps"] < 10.0, plan["timestamps"] < 12.0],
            [0, 1, 2, 3], default=4,
        )
        np.testing.assert_array_equal(plan["phase_id"], expected)
        np.testing.assert_array_equal(plan["grasp_phase_mask"], (plan["timestamps"] >= 8.0) & (plan["timestamps"] < 10.0))
        np.testing.assert_array_equal(plan["lift_phase_mask"], (plan["timestamps"] >= 10.0) & (plan["timestamps"] < 12.0))
        np.testing.assert_array_equal(plan["hold_phase_mask"], plan["timestamps"] >= 12.0)
        return "phase ids and masks follow the frozen absolute timeline"

    check("phase_timing", phase_timing)
    check(
        "joint_names_and_order",
        lambda: (
            len(task["body_joint_names"]) == len(set(task["body_joint_names"])) == 29
            and len(task["hand_joint_names"]) == len(set(task["hand_joint_names"])) == 14
            and len(task["source_qpos_names"]) == 36
        )
        or (_ for _ in ()).throw(AssertionError("joint names/order invalid")),
    )

    os.environ["SONIC_REPO"] = str(SONIC)
    sys.path[:0] = [str(CANONICAL / "scripts"), str(COORDINATES)]
    from scene import load_scene
    from kimodo.skeleton import G1Skeleton34
    from kimodo.exports.mujoco import MujocoQposConverter
    from kimodo_pose_constraint_codec import load_pose_constraints

    model, _ = load_scene(supported=False, robot_path=ROBOT)

    def limits():
        violations = []
        for column, name in enumerate(task["source_qpos_names"][7:]):
            joint = model.joint(name)
            if model.jnt_limited[joint.id]:
                lo, hi = model.jnt_range[joint.id]
                value = plan["source_qpos"][:, 7 + column]
                if np.any((value < lo - 1e-9) | (value > hi + 1e-9)):
                    violations.append(name)
        for column, name in enumerate(task["hand_joint_names"]):
            joint = model.joint(name)
            if model.jnt_limited[joint.id]:
                lo, hi = model.jnt_range[joint.id]
                value = plan["hand_ref_q"][:, column]
                if np.any((value < lo - 1e-9) | (value > hi + 1e-9)):
                    violations.append(name)
        assert not violations, violations
        return "body29 and hand14 within canonical XML limits"

    check("joint_limits", limits)

    def initial_state():
        initial = np.asarray(task["initial_qpos57"])
        root = int(model.joint("floating_base_joint").qposadr[0])
        addresses = [model.joint(name).qposadr[0] for name in task["source_qpos_names"][7:]]
        expected = np.r_[initial[root : root + 7], initial[addresses]]
        np.testing.assert_allclose(plan["source_qpos"][0], expected, rtol=0, atol=1e-10)
        np.testing.assert_allclose(plan["hand_ref_q"][0], 0, rtol=0, atol=1e-10)
        return "root/body/hand frame zero matches canonical initial state"

    check("initial_state", initial_state)
    check(
        "ik_errors",
        lambda: (
            metrics["max_position_error"] <= 0.02
            and np.isfinite(metrics["max_orientation_error"])
            and all(item["samples"] > 0 for item in metrics["per_phase_position_error"].values())
        )
        or (_ for _ in ()).throw(AssertionError(metrics)),
    )

    def fk_and_continuity():
        assert metrics["fk_validation"]["passed"], metrics["fk_validation"]
        measured = float(np.max(np.abs(np.diff(plan["source_qpos"][:, 7:], axis=0))))
        assert abs(measured - metrics["trajectory_max_joint_step"]) <= 1e-12
        assert metrics["trajectory_continuity_pass"] and measured <= 0.20
        assert metrics["grasp_geometry_valid"], metrics["grasp_geometry"]
        assert metrics["grasp_geometry"]["planned_lift_delta_m"] >= 0.17
        return {"trajectory_max_joint_step": measured, "grasp_geometry": metrics["grasp_geometry"]}

    check("fk_trajectory_continuity_and_grasp_geometry", fk_and_continuity)

    def hand_timeline():
        names = task["hand_joint_names"]
        left = [names.index(name) for name in names if name.startswith("left_hand_")]
        np.testing.assert_allclose(plan["hand_ref_q"][:, left], 0, rtol=0, atol=1e-10)
        nonzero = np.flatnonzero(np.max(np.abs(plan["hand_ref_q"]), axis=1) > 1e-8)
        assert len(nonzero) and 8.0 <= plan["timestamps"][nonzero[0]] <= 8.04
        held = np.broadcast_to(plan["hand_ref_q"][500], plan["hand_ref_q"][500:].shape)
        np.testing.assert_allclose(plan["hand_ref_q"][500:], held, rtol=0, atol=1e-10)
        np.testing.assert_allclose(
            plan["hand_ref_dq"], np.gradient(plan["hand_ref_q"], plan["timestamps"], axis=0, edge_order=2),
            rtol=0,
            atol=1e-10,
        )
        return {"first_motion_s": float(plan["timestamps"][nonzero[0]])}

    check("hand_timeline_alignment", hand_timeline)

    def pose_reload():
        converter = MujocoQposConverter(G1Skeleton34())
        loaded, metadata = load_pose_constraints(artifacts / "pose_constraints.json", converter)
        assert len(loaded) == 2
        assert metadata["saved_matrix_roundtrip_max_error"] <= 1e-6
        record = json.loads((artifacts / "pose_constraints.json").read_text())
        frames = np.asarray(record["frame_indices"], dtype=int)
        np.testing.assert_allclose(
            np.asarray(record["canonical_qpos"]), plan["source_qpos"][frames], rtol=0, atol=1e-6
        )
        assert frames[-1] < len(plan["source_qpos"])
        return metadata

    check("pose_codec_fresh_process_save_reload", pose_reload)

    def portable_hash_links():
        assert task["task_plan_sha256"] == sha256(artifacts / "task_plan.npz")
        assert task["pose_constraints_sha256"] == sha256(artifacts / "pose_constraints.json")
        assert "role_B" not in json.dumps(task)
        return "request hashes both portable inputs and contains no Role-B path"

    check("generation_request_artifact_hashes", portable_hash_links)

    def hashes():
        mismatches = []
        for name, item in task["input_hashes"].items():
            actual = sha256(item["path"])
            if actual != item["sha256"]:
                mismatches.append({"name": name, "expected": item["sha256"], "actual": actual})
        assert not mismatches, mismatches
        return f"verified {len(task['input_hashes'])} protected inputs"

    check("sha_verification", hashes)
    check(
        "planning_metrics_contract",
        lambda: (
            metrics["finite_check"]
            and metrics["joint_limits_pass"]
            and metrics["frame_zero_pass"]
            and metrics["hand_timeline_alignment"]
            and metrics["trajectory_continuity_pass"]
            and metrics["grasp_geometry_valid"]
            and not metrics["model_generation_run"]
            and not metrics["physics_replay_run"]
        )
        or (_ for _ in ()).throw(AssertionError(metrics)),
    )
    failures = [item for item in tests if item["status"] == "fail"]
    result = {
        "scope": "Role A task/IK/hand planning; fresh Python process",
        "passed": not failures,
        "summary": {
            "pass": sum(item["status"] == "pass" for item in tests),
            "fail": len(failures),
        },
        "tests": tests,
    }
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
