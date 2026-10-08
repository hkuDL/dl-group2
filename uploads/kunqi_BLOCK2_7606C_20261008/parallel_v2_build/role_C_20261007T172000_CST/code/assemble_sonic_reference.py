#!/usr/bin/env python3
"""Assemble a strict 810-frame canonical SONIC reference from Phase1 body/root and task hand data."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

import numpy as np


BASE = Path("/workspace/group2")
CANONICAL = BASE / "dl-group2"
SONIC = BASE / "GR00T-WholeBodyControl"
PHASE1 = BASE / "kimodo-t6/g1-integration/kimodo_to_t7_reference.py"
CONTRACT = "kimodo_grasp_final_v1_20261007"
EXPECTED_T = np.arange(810, dtype=np.float64) / 50.0


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_npz(path, required):
    with np.load(path, allow_pickle=False) as archive:
        require(set(required) <= set(archive.files), f"Missing {sorted(set(required) - set(archive.files))} in {path}")
        return {name: archive[name].copy() for name in archive.files}


def names(array):
    value = np.asarray(array)
    require(value.ndim == 1 and value.dtype.kind in "US", "Joint names must be a one-dimensional string array")
    return value.astype(str).tolist()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-reference", type=Path, required=True)
    parser.add_argument("--task-plan", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    os.environ["SONIC_REPO"] = str(SONIC)
    sys.path.insert(0, str(CANONICAL / "scripts"))
    from expert_trajectory import orders
    from reference_io import export_reference

    body = load_npz(args.body_reference, {
        "timestamps", "body_ref_q", "body_ref_dq", "root_ref_pos", "root_ref_quat",
        "root_lin_vel", "root_ang_vel",
    })
    task = load_npz(args.task_plan, {"timestamps", "hand_ref_q", "hand_ref_dq"})
    body_order, hand_order, _ = orders()
    if "contract_version" in body:
        require(str(np.asarray(body["contract_version"]).item()) == CONTRACT, "Body reference contract mismatch")
    if "contract_version" in task:
        require(str(np.asarray(task["contract_version"]).item()) == CONTRACT, "Task plan contract mismatch")
    if "body_joint_names" in body:
        require(names(body["body_joint_names"]) == body_order, "Body joint order disagrees with canonical orders()")
    if "hand_joint_names" in task:
        require(names(task["hand_joint_names"]) == hand_order, "Hand joint order disagrees with canonical orders()")
    body_order_source = "explicit_input_names_verified" if "body_joint_names" in body else "frozen_canonical_contract_order"
    hand_order_source = "explicit_input_names_verified" if "hand_joint_names" in task else "frozen_canonical_contract_order"
    body_t = np.asarray(body["timestamps"], dtype=np.float64)
    require(body_t.shape in ((810,), (811,)), f"Body reference must contain 810 frozen frames or the 811-frame Phase1 inclusive endpoint, got {body_t.shape}")
    np.testing.assert_allclose(body_t, np.arange(len(body_t)) / 50.0, rtol=0, atol=1e-12)
    np.testing.assert_allclose(body_t[:810], EXPECTED_T, rtol=0, atol=1e-12)
    np.testing.assert_allclose(task["timestamps"], EXPECTED_T, rtol=0, atol=1e-12)
    body_frames = len(body_t)
    required_shapes = {
        "body_ref_q": (810, 29), "body_ref_dq": (810, 29), "root_ref_pos": (810, 3),
        "root_ref_quat": (810, 4), "root_lin_vel": (810, 3), "root_ang_vel": (810, 3),
    }
    for key, shape in required_shapes.items():
        input_shape = (body_frames, shape[1])
        require(body[key].shape == input_shape and np.isfinite(body[key]).all(), f"Invalid {key}: {body[key].shape}")
    for key in ("hand_ref_q", "hand_ref_dq"):
        require(task[key].shape == (810, 14) and np.isfinite(task[key]).all(), f"Invalid {key}: {task[key].shape}")
    norms = np.linalg.norm(body["root_ref_quat"], axis=1)
    require(np.allclose(norms, 1.0, rtol=0, atol=1e-6), "Root quaternions are not unit wxyz")
    arrays = {
        "timestamps": EXPECTED_T,
        "body_ref_q": body["body_ref_q"][:810], "body_ref_dq": body["body_ref_dq"][:810],
        "hand_ref_q": task["hand_ref_q"], "hand_ref_dq": task["hand_ref_dq"],
        "root_ref_pos": body["root_ref_pos"][:810], "root_ref_quat": body["root_ref_quat"][:810],
        "root_lin_vel": body["root_lin_vel"][:810], "root_ang_vel": body["root_ang_vel"][:810],
    }
    require(all(np.isfinite(value).all() for value in arrays.values()), "Nonfinite assembled reference")
    metadata = {
        "contract_version": CONTRACT,
        "candidate_type": "kimodo_phase1_body_plus_task_hand",
        "fixture_only": bool(np.asarray(body.get("fixture_only", False)).item()) or bool(np.asarray(task.get("fixture_only", False)).item()),
        "body_joint_order": body_order,
        "hand_joint_order": hand_order,
        "body_joint_order_source": body_order_source,
        "hand_joint_order_source": hand_order_source,
        "quaternion_order": "wxyz",
        "root_velocities_frame": "world",
        "reference_fps": 50,
        "reference_frames": 810,
        "reference_duration_seconds": 16.18,
        "phase1_converter": str(PHASE1),
        "phase1_converter_sha256": sha256(PHASE1),
        "body_reference_path": str(args.body_reference.resolve()),
        "body_reference_sha256": sha256(args.body_reference),
        "task_plan_path": str(args.task_plan.resolve()),
        "task_plan_sha256": sha256(args.task_plan),
        "no_padding": True,
        "no_tail_repeat": True,
        "no_extrapolation": True,
        "body_input_frames": body_frames,
        "discarded_surplus_frame_count": body_frames - 810,
        "surplus_policy": "If Phase1 provides its inclusive 16.20 s endpoint (811th frame), discard that one out-of-contract terminal sample; never pad or extrapolate.",
        "source_success": False,
        "case": {"id": "center", "block_xy": [0.40, -0.15], "block_yaw_deg": 0.0},
        "pelvis_supported_during_source_generation": False,
        "source_trajectory": "Kimodo Phase1 body/root intermediate",
        "initial_pose": {"name": "canonical_input_reference"},
        "sonic_config": {"encoder_mode": 0},
        "root_velocities": (arrays["root_lin_vel"], arrays["root_ang_vel"]),
    }
    export_reference(output, arrays, body_order, hand_order, metadata)
    np.savez_compressed(output / "reference.npz", **arrays)
    assembler_metadata = {
        "contract_version": CONTRACT,
        "shapes": {key: list(value.shape) for key, value in arrays.items()},
        "timestamp_start": 0.0,
        "timestamp_end": 16.18,
        "body_input_frames": body_frames,
        "discarded_surplus_frame_count": body_frames - 810,
        "body_joint_order": body_order,
        "hand_joint_order": hand_order,
        "body_joint_order_source": body_order_source,
        "hand_joint_order_source": hand_order_source,
        "sonic_csv_files": [
            "joint_pos.csv", "joint_vel.csv", "body_pos.csv", "body_quat.csv",
            "body_lin_vel.csv", "body_ang_vel.csv",
        ],
        "fresh_loader_test_pending": True,
    }
    (output / "assembler_metadata.json").write_text(json.dumps(assembler_metadata, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"output": str(output), "frames": 810, "csv_files": assembler_metadata["sonic_csv_files"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
