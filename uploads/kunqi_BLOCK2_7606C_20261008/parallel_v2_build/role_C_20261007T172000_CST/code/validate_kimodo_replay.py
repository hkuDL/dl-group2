#!/usr/bin/env python3
"""Independently recompute physical_success and expert_valid from replay evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

import numpy as np


CONTRACT = "kimodo_grasp_final_v1_20261007"
BASE = Path("/workspace/group2")
CANONICAL = BASE / "dl-group2"
SONIC = BASE / "GR00T-WholeBodyControl"
ROBOT = SONIC / "decoupled_wbc/control/robot_model/model_data/g1/g1_29dof_with_hand_rev_1_0_activatedfinger.xml"
SCENE = CANONICAL / "scenes/tabletop.xml"
REQUIRED = {
    "physics_step", "physics_time", "playing", "reference_index", "reference_time",
    "robot_qpos", "robot_qvel", "cube_pos", "cube_quat", "cube_reset_pos", "cube_lift",
    "thumb_cube_contact", "index_cube_contact", "middle_cube_contact",
    "thumb_contact_force", "index_contact_force", "middle_contact_force",
    "cube_table_contact", "fall_detected", "support_detected", "weld_detected", "finite",
}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def longest_run(mask):
    best_start = best_end = 0
    current_start = None
    for index, value in enumerate(np.asarray(mask, dtype=bool)):
        if value and current_start is None:
            current_start = index
        if current_start is not None and (not value or index == len(mask) - 1):
            end = index + 1 if value and index == len(mask) - 1 else index
            if end - current_start > best_end - best_start:
                best_start, best_end = current_start, end
            current_start = None
    return best_start, best_end


def validate(evidence_path, integrity_path):
    with np.load(evidence_path, allow_pickle=False) as archive:
        missing = REQUIRED - set(archive.files)
        if missing:
            raise ValueError(f"Missing evidence keys: {sorted(missing)}")
        evidence = {key: archive[key].copy() for key in archive.files}
    integrity = json.loads(Path(integrity_path).read_text())
    count = len(evidence["physics_step"])
    if count == 0:
        raise ValueError("Evidence is empty")
    for key, value in evidence.items():
        if value.ndim == 0 or len(value) != count:
            raise ValueError(f"Evidence length mismatch for {key}: {value.shape}")

    numeric_finite = all(np.isfinite(value).all() for value in evidence.values())
    finite = bool(numeric_finite and np.asarray(evidence["finite"], dtype=bool).all())
    playing = np.asarray(evidence["playing"], dtype=bool)
    ref = np.asarray(evidence["reference_index"], dtype=np.int64)
    physics_t = np.asarray(evidence["physics_time"], dtype=np.float64)
    dt = float(integrity.get("physics_dt", 0.005))
    steps_contiguous = bool(np.array_equal(np.diff(evidence["physics_step"]), np.ones(count - 1, dtype=np.int64)))
    time_contiguous = bool(count >= 2 and np.allclose(np.diff(physics_t), dt, rtol=0, atol=1e-9))
    played_ref = ref[playing]
    coverage = bool(len(played_ref) and np.array_equal(np.unique(played_ref), np.arange(810)))
    reference_monotonic = bool(len(played_ref) and np.all(np.diff(played_ref) >= 0) and np.all(np.diff(played_ref) <= 1))
    reference_time_match = bool(len(played_ref) and np.allclose(
        evidence["reference_time"][playing], played_ref / 50.0, rtol=0, atol=1e-9
    ))
    synchronized = bool(coverage and reference_monotonic and reference_time_match)
    playing_duration = float(playing.sum() * dt)
    complete = bool(
        integrity.get("process_completed", False) and coverage and playing_duration >= 16.0
        and steps_contiguous and time_contiguous
    )
    computed_lift = evidence["cube_pos"][:, 2] - evidence["cube_reset_pos"][:, 2]
    lift_consistent = bool(np.allclose(evidence["cube_lift"], computed_lift, rtol=0, atol=1e-9, equal_nan=True))

    finger_force = np.maximum(
        np.where(evidence["index_cube_contact"], evidence["index_contact_force"], -np.inf),
        np.where(evidence["middle_cube_contact"], evidence["middle_contact_force"], -np.inf),
    )
    qualifying = (
        playing
        & (computed_lift >= 0.10)
        & np.asarray(evidence["thumb_cube_contact"], dtype=bool)
        & (np.asarray(evidence["index_cube_contact"], dtype=bool) | np.asarray(evidence["middle_cube_contact"], dtype=bool))
        & (evidence["thumb_contact_force"] > 1e-4)
        & (finger_force > 1e-4)
        & ~np.asarray(evidence["cube_table_contact"], dtype=bool)
    )
    start, end = longest_run(qualifying)
    longest_hold = float((end - start) * dt)
    played_indices = np.flatnonzero(playing)
    terminal_steps = 0
    if len(played_indices):
        cursor = int(played_indices[-1])
        while cursor >= 0 and qualifying[cursor]:
            terminal_steps += 1
            cursor -= 1
    terminal_hold = float(terminal_steps * dt)
    physical_success = bool(longest_hold >= 2.0)
    if end > start:
        required_force = np.minimum(evidence["thumb_contact_force"][start:end], finger_force[start:end])
        minimum_force = float(np.min(required_force))
        table_during = bool(np.asarray(evidence["cube_table_contact"][start:end], dtype=bool).any())
    else:
        minimum_force = None
        table_during = False

    os.environ["SONIC_REPO"] = str(SONIC)
    sys.path.insert(0, str(CANONICAL / "scripts"))
    from expert_trajectory import orders
    body_order, hand_order, _ = orders()
    checks = {
        "contract_version": integrity.get("contract_version") == CONTRACT,
        "robot_xml_hash": integrity.get("robot_xml_sha256") == sha256(ROBOT),
        "scene_hash": integrity.get("scene_sha256") == sha256(SCENE),
        "canonical_dimensions": [integrity.get(name) for name in ("nq", "nv", "nu", "neq")] == [57, 55, 43, 0],
        "reference_dimensions": integrity.get("reference_frames") == 810 and integrity.get("reference_fps") == 50,
        "body_order": integrity.get("body_joint_order") == body_order,
        "hand_order": integrity.get("hand_joint_order") == hand_order,
        "controller_config": integrity.get("controller") == "canonical_run_sonic_grasp" and integrity.get("sonic_kp_scale") == 1.0 and integrity.get("sonic_kd_scale") == 1.0,
        "hand_pd": integrity.get("hand_pd") == {"kp": 12.0, "kd": 0.3},
        "physics_dt": abs(dt - 0.005) <= 1e-12,
        "gravity": integrity.get("gravity") == [0.0, 0.0, -9.81],
        "finite": finite,
        "cube_lift_consistency": lift_consistent,
        "complete_playing_interval": complete,
        "missing_log_steps": steps_contiguous and time_contiguous,
        "synchronized_reference": synchronized,
        "unassisted": integrity.get("unassisted", False) and not evidence["support_detected"].any() and not evidence["weld_detected"].any(),
        "no_fall": not evidence["fall_detected"].any(),
        "no_support": not evidence["support_detected"].any(),
        "no_weld": not evidence["weld_detected"].any(),
    }
    integrity_pass = bool(all(checks.values()))
    expert_valid = bool(physical_success and complete and finite and synchronized and integrity_pass)
    return {
        "contract_version": CONTRACT,
        "physical_success": physical_success,
        "expert_valid": expert_valid,
        "max_cube_lift": float(np.nanmax(computed_lift)) if np.isfinite(computed_lift).any() else None,
        "longest_qualifying_hold_sec": longest_hold,
        "terminal_qualifying_hold_sec": terminal_hold,
        "minimum_required_contact_force_during_qualifying_interval": minimum_force,
        "cube_table_contact_during_qualifying_interval": table_during,
        "actual_playing_duration": playing_duration,
        "complete_replay": complete,
        "finite": finite,
        "synchronized": synchronized,
        "integrity_checks_pass": integrity_pass,
        "integrity_checks": checks,
        "qualifying_interval_steps": [start, end],
        "evidence_sha256": sha256(evidence_path),
        "integrity_sha256": sha256(integrity_path),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--integrity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate(args.evidence, args.integrity)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
