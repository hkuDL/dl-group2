#!/usr/bin/env python3
"""Build an independent final-contract fixture for the Kimodo runtime wrapper."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import mujoco
import numpy as np


BASE = Path("/workspace/group2")
CANONICAL = BASE / "dl-group2"
SONIC = BASE / "GR00T-WholeBodyControl"
INTEGRATION = BASE / "kimodo-t6/g1-integration"
COORDINATES = INTEGRATION / "coordinate-repair-20261007-v2"
ROBOT = SONIC / "decoupled_wbc/control/robot_model/model_data/g1/g1_29dof_with_hand_rev_1_0_activatedfinger.xml"
SCENE = CANONICAL / "scenes/tabletop.xml"
CONTRACT = "kimodo_grasp_final_v1_20261007"
FPS = 30.0
FRAMES = 487


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: build_fixture.py OUTPUT_DIR")
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise FileExistsError(f"Fixture directory is not empty: {output}")
    os.environ["SONIC_REPO"] = str(SONIC)
    sys.path[:0] = [str(CANONICAL / "scripts"), str(COORDINATES)]
    from cases import read_cases, reset_case
    from episode_schema import NEUTRAL_POSE, neutral_arms
    from expert_trajectory import orders
    from scene import load_scene
    from kimodo.skeleton import G1Skeleton34
    from kimodo.exports.mujoco import MujocoQposConverter
    from kimodo_pose_constraint_codec import make_pose_constraint_record, save_pose_constraint_record

    model, data = load_scene(supported=False, robot_path=ROBOT, scene_path=SCENE)
    case = next(item for item in read_cases()["cases"] if item["id"] == "center")
    reset_case(model, data, case)
    for side in ("left", "right"):
        for part in ("hip_pitch", "knee", "ankle_pitch"):
            data.qpos[model.joint(f"{side}_{part}_joint").qposadr[0]] = NEUTRAL_POSE[part]
    neutral_arms(model, data)
    mujoco.mj_forward(model, data)
    feet = [
        index for index in range(model.ngeom)
        if model.body(model.geom_bodyid[index]).name in ("left_ankle_roll_link", "right_ankle_roll_link")
        and model.geom_contype[index]
    ]
    root = int(model.joint("floating_base_joint").qposadr[0])
    data.qpos[root + 2] -= min(data.geom_xpos[index, 2] - model.geom_size[index, 0] for index in feet) + 0.0001
    mujoco.mj_forward(model, data)

    body_names, hand_names, _ = orders()
    converter = MujocoQposConverter(G1Skeleton34())
    source_names = [
        joint.get("name") for joint in ET.parse(converter.xml_path).findall(".//worldbody//joint")
        if joint.get("type") != "free"
    ]
    if len(source_names) != 29 or set(source_names) != set(body_names):
        raise ValueError("Fixture joint order does not match canonical order")
    addresses = np.asarray([model.joint(name).qposadr[0] for name in source_names], dtype=int)
    neutral = np.r_[data.qpos[root:root + 7], data.qpos[addresses]].astype(np.float64)

    frames = np.linspace(0, FRAMES - 1, 17, dtype=np.int64)
    qpos = np.repeat(neutral[None], len(frames), axis=0)
    shoulder = 7 + source_names.index("right_shoulder_pitch_joint")
    elbow = 7 + source_names.index("right_elbow_joint")
    phase = np.sin(np.linspace(0, np.pi, len(frames)))
    qpos[:, shoulder] += 0.15 * phase
    qpos[:, elbow] += 0.12 * phase
    record = make_pose_constraint_record(
        converter, qpos, frames, FPS, fullbody_rows=(0,), purpose="role_b_runtime_fixture_not_final_grasp"
    )
    pose_path = output / "fixture_pose_constraints.json"
    save_pose_constraint_record(pose_path, record)

    timestamps = np.arange(810, dtype=np.float64) / 50.0
    np.savez_compressed(
        output / "fixture_task_plan.npz",
        timestamps=timestamps,
        hand_ref_q=np.zeros((810, 14), dtype=np.float64),
        hand_ref_dq=np.zeros((810, 14), dtype=np.float64),
    )
    request = {
        "contract_version": CONTRACT,
        "task_id": "role_b_independent_runtime_fixture_20261007",
        "case": "fixture_neutral_right_arm",
        "seed": 0,
        "active_hand": "right",
        "prompt": "A humanoid stands in place and slowly raises and lowers the right forearm while keeping balance.",
        "requested_duration_sec": 16.2,
        "source_fps": FPS,
        "source_frames": FRAMES,
        "reference_fps": 50,
        "reference_frames": 810,
        "phases": [{"name": "fixture_motion", "start_s": 0.0, "end_s": 16.2}],
        "initial_qpos57": data.qpos.tolist(),
        "initial_qvel55": data.qvel.tolist(),
        "body_joint_names": body_names,
        "hand_joint_names": hand_names,
        "source_qpos_names": ["root_x", "root_y", "root_z", "root_qw", "root_qx", "root_qy", "root_qz", *source_names],
        "robot_xml": str(ROBOT),
        "scene_xml": str(SCENE),
        "object": {"fixture_only": True},
        "pose_constraints_sha256": sha256(pose_path),
        "task_plan_sha256": sha256(output / "fixture_task_plan.npz"),
        "fixture_only": True,
        "final_grasp_run": False,
    }
    write_json(output / "fixture_generation_request.json", request)
    write_json(output / "fixture_manifest.json", {
        "fixture_only": True,
        "final_grasp_run": False,
        "purpose": "Exercise the frozen generator contract without consuming Role-A output.",
        "files": {path.name: sha256(path) for path in sorted(output.iterdir()) if path.is_file()},
    })
    print(json.dumps({"output": str(output), "frames": FRAMES, "constraints": len(frames)}, indent=2))


if __name__ == "__main__":
    main()
