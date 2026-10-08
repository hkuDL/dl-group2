#!/usr/bin/env python3
"""Build a development-only SONIC reference that isolates startup alignment.

The adapter applies one constant vertical translation to the entire root
trajectory so that the lowest activated-foot contact sphere starts with a
small, explicit ground penetration.  It also selects the canonical runner's
current-COM startup initialization.  Body joints, hand joints, quaternions,
velocities, timing, and all within-trajectory discontinuities are preserved.

This output is diagnostic evidence only.  It must never replace the frozen
formal reference or be reported as a formal comparison trial.
"""
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
ROBOT = (
    SONIC
    / "decoupled_wbc/control/robot_model/model_data/g1/"
      "g1_29dof_with_hand_rev_1_0_activatedfinger.xml"
)
SCENE = CANONICAL / "scenes/tabletop.xml"
TARGET_FOOT_BOTTOM_M = -1.0e-4


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    )


def initial_foot_bottom(arrays: dict[str, np.ndarray]) -> tuple[float, list[dict]]:
    os.environ["SONIC_REPO"] = str(SONIC)
    sys.path.insert(0, str(CANONICAL / "scripts"))
    from expert_trajectory import JointMap, orders
    from run_sonic_grasp import load_scene

    model, data = load_scene(False, robot_path=ROBOT, scene_path=SCENE)
    body_names, hand_names, _ = orders()
    body = JointMap(model, body_names, 29)
    hand = JointMap(model, hand_names, 14)
    data.qpos[body.qa] = arrays["body_ref_q"][0]
    data.qpos[hand.qa] = arrays["hand_ref_q"][0]
    root_id = model.joint("floating_base_joint").id
    root_qpos = model.jnt_qposadr[root_id]
    data.qpos[root_qpos : root_qpos + 3] = arrays["root_ref_pos"][0]
    data.qpos[root_qpos + 3 : root_qpos + 7] = arrays["root_ref_quat"][0]
    mujoco.mj_forward(model, data)

    contact_spheres = []
    for geom_id in range(model.ngeom):
        body_name = model.body(model.geom_bodyid[geom_id]).name or ""
        if body_name not in {"left_ankle_roll_link", "right_ankle_roll_link"}:
            continue
        if model.geom_type[geom_id] != mujoco.mjtGeom.mjGEOM_SPHERE:
            continue
        radius = float(model.geom_size[geom_id, 0])
        bottom = float(data.geom_xpos[geom_id, 2] - radius)
        contact_spheres.append(
            {
                "geom_id": int(geom_id),
                "body": body_name,
                "center_z_m": float(data.geom_xpos[geom_id, 2]),
                "radius_m": radius,
                "bottom_z_m": bottom,
            }
        )
    if len(contact_spheres) != 8:
        raise RuntimeError(
            f"Expected 8 activated-foot contact spheres, found {len(contact_spheres)}"
        )
    return min(row["bottom_z_m"] for row in contact_spheres), contact_spheres


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-reference", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    source = args.input_reference.resolve(strict=True)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)

    source_npz = source / "reference.npz"
    with np.load(source_npz, allow_pickle=False) as loaded:
        arrays = {key: loaded[key].copy() for key in loaded.files}
    metadata = json.loads((source / "metadata.json").read_text())

    required = {
        "timestamps",
        "body_ref_q",
        "body_ref_dq",
        "hand_ref_q",
        "hand_ref_dq",
        "root_ref_pos",
        "root_ref_quat",
        "root_lin_vel",
        "root_ang_vel",
    }
    if set(arrays) != required:
        raise ValueError(f"Unexpected reference keys: {sorted(arrays)}")
    if arrays["root_ref_pos"].shape != (810, 3):
        raise ValueError(f"Expected 810x3 root positions, got {arrays['root_ref_pos'].shape}")

    source_bottom, foot_spheres = initial_foot_bottom(arrays)
    shift_m = TARGET_FOOT_BOTTOM_M - source_bottom
    arrays["root_ref_pos"][:, 2] += shift_m
    aligned_bottom, aligned_spheres = initial_foot_bottom(arrays)
    if not np.isclose(aligned_bottom, TARGET_FOOT_BOTTOM_M, atol=1e-10, rtol=0):
        raise RuntimeError(
            f"Ground alignment failed: got {aligned_bottom}, expected {TARGET_FOOT_BOTTOM_M}"
        )

    original_initial_pose = metadata.get("initial_pose")
    metadata.update(
        {
            "candidate_type": "development_start_aligned_kimodo",
            "development_only": True,
            "formal_eligible": False,
            "diagnostic_question": (
                "Does constant root-Z ground alignment plus current-COM startup "
                "allow canonical SONIC playback to begin?"
            ),
            "diagnostic_adapter": "constant_root_z_and_current_com_startup_v1",
            "source_reference_dir": str(source),
            "source_reference_npz_sha256": sha256(source_npz),
            "source_initial_pose_metadata": original_initial_pose,
            "initial_pose": {
                "name": "neutral_standing_v1",
                "development_override": True,
                "generated_frame0_is_exact_neutral": False,
                "reason": "Select current-pose COM target during startup WBC only.",
            },
            "constant_root_z_shift_m": float(shift_m),
            "source_min_foot_bottom_m": float(source_bottom),
            "aligned_min_foot_bottom_m": float(aligned_bottom),
            "target_min_foot_bottom_m": TARGET_FOOT_BOTTOM_M,
            "body_joint_trajectory_modified": False,
            "hand_joint_trajectory_modified": False,
            "root_orientation_modified": False,
            "root_velocity_modified": False,
            "known_joint_wrap_preserved": True,
        }
    )

    sys.path.insert(0, str(CANONICAL / "scripts"))
    from reference_io import export_reference

    export_metadata = dict(metadata)
    export_metadata["root_velocities"] = (
        arrays["root_lin_vel"],
        arrays["root_ang_vel"],
    )
    export_reference(
        output,
        arrays,
        metadata["body_joint_order"],
        metadata["hand_joint_order"],
        export_metadata,
    )
    np.savez_compressed(output / "reference.npz", **arrays)

    manifest = {
        "development_only": True,
        "formal_eligible": False,
        "source_reference_dir": str(source),
        "output_reference_dir": str(output),
        "source_reference_npz_sha256": sha256(source_npz),
        "output_reference_npz_sha256": sha256(output / "reference.npz"),
        "constant_root_z_shift_m": float(shift_m),
        "source_min_foot_bottom_m": float(source_bottom),
        "aligned_min_foot_bottom_m": float(aligned_bottom),
        "source_foot_spheres": foot_spheres,
        "aligned_foot_spheres": aligned_spheres,
        "preserved": [
            "timestamps",
            "body_ref_q",
            "body_ref_dq",
            "hand_ref_q",
            "hand_ref_dq",
            "root_ref_quat",
            "root_lin_vel",
            "root_ang_vel",
            "known_joint_wrap",
        ],
    }
    write_json(output / "development_adapter_manifest.json", manifest)
    print(json.dumps(manifest, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
