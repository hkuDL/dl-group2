#!/usr/bin/env python3
"""Build the Role-A canonical grasp task without model generation or replay."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation, Slerp


BASE = Path("/workspace/group2")
CANONICAL = BASE / "dl-group2"
SONIC = BASE / "GR00T-WholeBodyControl"
INTEGRATION = BASE / "kimodo-t6/g1-integration"
COORDINATES = INTEGRATION / "coordinate-repair-20261007-v2"
ROBOT = SONIC / "decoupled_wbc/control/robot_model/model_data/g1/g1_29dof_with_hand_rev_1_0_activatedfinger.xml"
SCENE = CANONICAL / "scenes/tabletop.xml"
CONTRACT_VERSION = "kimodo_parallel_20261007_v1"
SOURCE_FPS = 30.0
REFERENCE_FPS = 50.0
REFERENCE_FRAMES = 810
REQUESTED_DURATION = 16.2
PROMPT = (
    "A humanoid robot stands still, reaches toward the red cube at the center "
    "of the table with its right hand, aligns and grasps it, lifts it by at "
    "least 0.10 m, and holds it steadily. The left arm remains relaxed."
)
PHASES = [
    {"name": "initial_entering", "start_s": 0.0, "end_s": 1.5},
    {"name": "approach_alignment", "start_s": 1.5, "end_s": 8.0},
    {"name": "finger_closing", "start_s": 8.0, "end_s": 10.0},
    {"name": "lift", "start_s": 10.0, "end_s": 12.0},
    {"name": "hold", "start_s": 12.0, "end_s": 16.2},
]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    path = Path(path)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def smoothstep(value):
    u = np.clip(value, 0.0, 1.0)
    return u * u * (3.0 - 2.0 * u)


def blend(a, b, value):
    return np.asarray(a, dtype=float) + (
        np.asarray(b, dtype=float) - np.asarray(a, dtype=float)
    ) * smoothstep(value)


def rotation_error(actual, target):
    relative = np.asarray(target) @ np.asarray(actual).T
    return float(np.arccos(np.clip((np.trace(relative) - 1.0) / 2.0, -1.0, 1.0)))


def matrix_to_wxyz(matrix):
    xyzw = Rotation.from_matrix(matrix).as_quat()
    return xyzw[[3, 0, 1, 2]]


def phase_index(time_s):
    for index, phase in enumerate(PHASES[:-1]):
        if phase["start_s"] <= time_s < phase["end_s"]:
            return index
    return len(PHASES) - 1


def initialize(case_id):
    os.environ["SONIC_REPO"] = str(SONIC)
    sys.path[:0] = [str(CANONICAL / "scripts"), str(COORDINATES)]
    from cases import read_cases, reset_case
    from episode_schema import NEUTRAL_POSE, neutral_arms
    from scene import load_scene

    model, data = load_scene(supported=False, robot_path=ROBOT, scene_path=SCENE)
    case = next(item for item in read_cases()["cases"] if item["id"] == case_id)
    reset_case(model, data, case)
    for side in ("left", "right"):
        for part in ("hip_pitch", "knee", "ankle_pitch"):
            address = model.joint(f"{side}_{part}_joint").qposadr[0]
            data.qpos[address] = NEUTRAL_POSE[part]
    neutral_arms(model, data)
    mujoco.mj_forward(model, data)
    feet = [
        index
        for index in range(model.ngeom)
        if model.body(model.geom_bodyid[index]).name
        in ("left_ankle_roll_link", "right_ankle_roll_link")
        and model.geom_contype[index]
    ]
    require(feet, "No active foot collision geometries found")
    root = int(model.joint("floating_base_joint").qposadr[0])
    data.qpos[root + 2] -= min(
        data.geom_xpos[index, 2] - model.geom_size[index, 0] for index in feet
    ) + 0.0001
    mujoco.mj_forward(model, data)
    require(model.nq == 57 and model.nv == 55 and model.nu == 43, "Unexpected canonical dimensions")
    require(model.neq == 0, "Canonical model must not contain equality support")
    require(np.allclose(model.opt.gravity, [0, 0, -9.81]), "Unexpected gravity")
    return model, data, case, NEUTRAL_POSE


def desired_wrist(plan, time_s):
    start = plan.start
    final_rotation = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], dtype=float)
    grasp = plan.target.copy()
    above = grasp + np.array([0.0, 0.0, 0.13])
    clearance = np.array([0.06, start[1] - 0.03, above[2] + 0.04])
    lifted = grasp + np.array([0.0, 0.0, 0.18])
    if time_s < 1.5:
        return start.copy(), plan.start_rotation.copy()
    if time_s < 4.5:
        u = smoothstep((time_s - 1.5) / 3.0)
        rotation = Slerp(
            [0.0, 1.0], Rotation.from_matrix([plan.start_rotation, final_rotation])
        )([u]).as_matrix()[0]
        return blend(start, clearance, (time_s - 1.5) / 3.0), rotation
    if time_s < 6.5:
        return blend(clearance, above, (time_s - 4.5) / 2.0), final_rotation
    if time_s < 8.0:
        return blend(above, grasp, (time_s - 6.5) / 1.5), final_rotation
    if time_s < 10.0:
        return grasp.copy(), final_rotation
    if time_s < 12.0:
        return blend(grasp, lifted, (time_s - 10.0) / 2.0), final_rotation
    return lifted.copy(), final_rotation


def hand_plan(model, hand_names, timestamps):
    targets = {
        "right_hand_index_0_joint": 1.2,
        "right_hand_index_1_joint": 1.2,
        "right_hand_middle_0_joint": 1.2,
        "right_hand_middle_1_joint": 1.2,
        "right_hand_thumb_0_joint": 0.0,
        "right_hand_thumb_1_joint": -1.0,
        "right_hand_thumb_2_joint": -1.25,
    }
    values = np.zeros((len(timestamps), len(hand_names)), dtype=np.float64)
    for column, name in enumerate(hand_names):
        if name in targets:
            closure = smoothstep((timestamps - 8.0) / 2.0)
            values[:, column] = closure * targets[name]
    velocities = np.gradient(values, timestamps, axis=0, edge_order=2)
    violations = []
    for column, name in enumerate(hand_names):
        joint = model.joint(name)
        if model.jnt_limited[joint.id]:
            lower, upper = model.jnt_range[joint.id]
            bad = np.flatnonzero((values[:, column] < lower - 1e-9) | (values[:, column] > upper + 1e-9))
            if len(bad):
                violations.append({"joint": name, "frames": bad.tolist(), "range": [float(lower), float(upper)]})
    return values, velocities, violations


def per_phase(values, source_t):
    result = {}
    values = np.asarray(values, dtype=float)
    for index, phase in enumerate(PHASES):
        selection = np.asarray([phase_index(float(t)) == index for t in source_t])
        selected = values[selection]
        result[phase["name"]] = {
            "max": float(selected.max()),
            "mean": float(selected.mean()),
            "samples": int(len(selected)),
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", default="center")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--duration", type=float, default=REQUESTED_DURATION)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(args.case == "center", "Role-A v1 contract fixes case=center")
    require(args.seed == 0, "Role-A v1 contract fixes seed=0")
    require(abs(args.duration - REQUESTED_DURATION) < 1e-12, "Role-A v1 contract fixes duration=16.2")

    output = args.output.absolute()
    workdir = output.parent
    output.mkdir(parents=True, exist_ok=False)
    (workdir / "logs").mkdir(exist_ok=True)
    (workdir / "tests").mkdir(exist_ok=True)

    os.environ["SONIC_REPO"] = str(SONIC)
    sys.path[:0] = [str(CANONICAL / "scripts"), str(COORDINATES)]
    from expert_trajectory import orders
    from grasp_reference import GraspReference
    from kimodo.skeleton import G1Skeleton34
    from kimodo.exports.mujoco import MujocoQposConverter
    from kimodo_pose_constraint_codec import (
        load_pose_constraints,
        make_pose_constraint_record,
        save_pose_constraint_record,
    )
    import kimodo

    loaded_kimodo = Path(kimodo.__file__).resolve()
    require(INTEGRATION / "kimodo-upload" in loaded_kimodo.parents, f"Wrong Kimodo checkout: {loaded_kimodo}")

    protected = {
        "scene_xml": SCENE,
        "robot_xml": ROBOT,
        "grasp_cases": CANONICAL / "configs/grasp_cases.json",
        "neutral_standing": CANONICAL / "configs/neutral_standing.json",
        "scene_loader": CANONICAL / "scripts/scene.py",
        "case_reset": CANONICAL / "scripts/cases.py",
        "episode_schema": CANONICAL / "scripts/episode_schema.py",
        "expert_trajectory": CANONICAL / "scripts/expert_trajectory.py",
        "grasp_reference": CANONICAL / "scripts/grasp_reference.py",
        "coordinate_inverse": COORDINATES / "kimodo_condition_coordinates.py",
        "pose_codec": COORDINATES / "kimodo_pose_constraint_codec.py",
    }
    for path in protected.values():
        require(path.is_file(), f"Missing protected input: {path}")
    hashes_before = {name: {"path": str(path), "sha256": sha256(path)} for name, path in protected.items()}
    write_json(workdir / "logs/input_hashes_before.json", hashes_before)

    model, data, case, neutral_pose = initialize(args.case)
    body_names, hand_names, _ = orders()
    require(len(body_names) == len(set(body_names)) == 29, "Invalid canonical body order")
    require(len(hand_names) == len(set(hand_names)) == 14, "Invalid canonical hand order")

    converter = MujocoQposConverter(G1Skeleton34())
    converter_xml = Path(converter.xml_path).resolve(strict=True)
    source_names = [
        joint.get("name")
        for joint in ET.parse(converter_xml).findall(".//worldbody//joint")
        if joint.get("type") != "free"
    ]
    require(len(source_names) == len(set(source_names)) == 29, "Invalid Kimodo XML joint order")
    require(set(source_names) == set(body_names), "Kimodo/canonical body joint sets differ")
    source_addresses = np.asarray([model.joint(name).qposadr[0] for name in source_names], dtype=int)
    root_address = int(model.joint("floating_base_joint").qposadr[0])

    initial_qpos = data.qpos.copy()
    initial_qvel = data.qvel.copy()
    planner = GraspReference(model, data, lift_height=0.18)
    source_t = np.arange(int(round(args.duration * SOURCE_FPS)) + 1, dtype=np.float64) / SOURCE_FPS
    require(source_t[-1] >= args.duration, "Source timeline does not cover requested duration")
    reference_t = np.arange(REFERENCE_FRAMES, dtype=np.float64) / REFERENCE_FPS
    require(abs(reference_t[-1] - 16.18) < 1e-12, "Unexpected reference endpoint")

    source_qpos = []
    wrists_pos = []
    wrists_quat = []
    desired_pos = []
    desired_quat = []
    position_errors = []
    orientation_errors = []
    wrist_bodies = [model.body("left_wrist_yaw_link").id, model.body("right_wrist_yaw_link").id]
    for time_s in source_t:
        target_pos, target_rotation = desired_wrist(planner, float(time_s))
        planner.rotation = target_rotation
        planner.ik(target_pos)
        mujoco.mj_forward(model, planner.plan)
        source_qpos.append(
            np.r_[planner.plan.qpos[root_address : root_address + 7], planner.plan.qpos[source_addresses]]
        )
        wrists_pos.append(np.stack([planner.plan.xpos[body].copy() for body in wrist_bodies]))
        wrist_quats_now = np.stack([planner.plan.xquat[body].copy() for body in wrist_bodies])
        wrists_quat.append(wrist_quats_now)
        desired_pos.append(target_pos)
        desired_quat.append(matrix_to_wxyz(target_rotation))
        position_errors.append(float(np.linalg.norm(planner.plan.xpos[planner.wrist] - target_pos)))
        orientation_errors.append(rotation_error(planner.plan.xmat[planner.wrist].reshape(3, 3), target_rotation))

    source_qpos = np.asarray(source_qpos, dtype=np.float64)
    wrists_pos = np.asarray(wrists_pos, dtype=np.float64)
    wrists_quat = np.asarray(wrists_quat, dtype=np.float64)
    desired_pos = np.asarray(desired_pos, dtype=np.float64)
    desired_quat = np.asarray(desired_quat, dtype=np.float64)
    position_errors = np.asarray(position_errors, dtype=np.float64)
    orientation_errors = np.asarray(orientation_errors, dtype=np.float64)
    hand_q, hand_dq, hand_limit_violations = hand_plan(model, hand_names, reference_t)

    joint_limit_violations = []
    for column, name in enumerate(source_names):
        joint = model.joint(name)
        if model.jnt_limited[joint.id]:
            lower, upper = model.jnt_range[joint.id]
            bad = np.flatnonzero(
                (source_qpos[:, 7 + column] < lower - 1e-9)
                | (source_qpos[:, 7 + column] > upper + 1e-9)
            )
            if len(bad):
                joint_limit_violations.append(
                    {"joint": name, "frames": bad.tolist(), "range": [float(lower), float(upper)]}
                )

    phase_source_frames = sorted(
        set(np.arange(0, len(source_t), 6, dtype=int).tolist())
        | {int(round(phase["start_s"] * SOURCE_FPS)) for phase in PHASES}
        | {len(source_t) - 1}
    )
    phase_source_frames = np.asarray(phase_source_frames, dtype=np.int64)
    constraint_qpos = source_qpos[phase_source_frames]
    pose_record = make_pose_constraint_record(
        converter,
        constraint_qpos,
        phase_source_frames,
        SOURCE_FPS,
        fullbody_rows=(0,),
        purpose="canonical_center_right_grasp_lift_hold_role_a",
    )
    pose_path = output / "pose_constraints.json"
    save_pose_constraint_record(pose_path, pose_record)
    _, reload_metadata = load_pose_constraints(pose_path, converter)

    all_arrays = [
        source_t,
        source_qpos,
        wrists_pos,
        wrists_quat,
        desired_pos,
        desired_quat,
        reference_t,
        hand_q,
        hand_dq,
    ]
    finite_check = bool(all(np.isfinite(value).all() for value in all_arrays))
    initial_source_expected = np.r_[
        initial_qpos[root_address : root_address + 7], initial_qpos[source_addresses]
    ]
    root_initial_error = float(np.max(np.abs(source_qpos[0, :7] - initial_source_expected[:7])))
    body_initial_error = float(np.max(np.abs(source_qpos[0, 7:] - initial_source_expected[7:])))
    wrist_initial_position_error = float(position_errors[0])
    wrist_initial_orientation_error = float(orientation_errors[0])
    hand_initial_error = float(np.max(np.abs(hand_q[0])))
    nonzero = np.flatnonzero(np.max(np.abs(hand_q), axis=1) > 1e-8)
    first_hand_motion_s = float(reference_t[nonzero[0]]) if len(nonzero) else None
    hand_alignment = bool(
        first_hand_motion_s is not None
        and 8.0 <= first_hand_motion_s <= 8.04
        and np.allclose(hand_q[500:], hand_q[500], atol=1e-10, rtol=0)
    )
    grasp_lift = (source_t >= 8.0) & (source_t <= 12.0)

    ready = bool(
        finite_check
        and not joint_limit_violations
        and not hand_limit_violations
        and max(root_initial_error, body_initial_error, hand_initial_error) <= 1e-10
        and wrist_initial_position_error <= 1e-8
        and wrist_initial_orientation_error <= 1e-6
        and float(position_errors.max()) <= 0.02
        and reload_metadata["saved_matrix_roundtrip_max_error"] <= 1e-6
        and hand_alignment
    )

    cube_body = model.body("task_red_cube").id
    cube_geom = model.geom("task_cube_geom").id
    table_geom = model.geom("task_table_top").id
    task_id = "kimodo_center_right_seed0_role_a_20261007T163000_CST"
    task = {
        "task_id": task_id,
        "contract_version": CONTRACT_VERSION,
        "case": args.case,
        "seed": args.seed,
        "active_hand": "right",
        "prompt": PROMPT,
        "requested_duration_sec": args.duration,
        "duration_s": args.duration,
        "source_fps": SOURCE_FPS,
        "source_frames": int(len(source_t)),
        "source_min_frames": int(len(source_t)),
        "reference_fps": REFERENCE_FPS,
        "reference_frames": REFERENCE_FRAMES,
        "phases": PHASES,
        "initial_qpos57": initial_qpos.tolist(),
        "initial_qvel55": initial_qvel.tolist(),
        "body_joint_names": body_names,
        "body_joint_order": body_names,
        "hand_joint_names": hand_names,
        "hand_joint_order": hand_names,
        "source_qpos_names": [
            "root_x",
            "root_y",
            "root_z",
            "root_qw",
            "root_qx",
            "root_qy",
            "root_qz",
            *source_names,
        ],
        "wrist_order": ["left", "right"],
        "quaternion_order": "wxyz",
        "angle_unit": "radian",
        "position_unit": "metre",
        "robot_xml": str(ROBOT),
        "scene_xml": str(SCENE),
        "kimodo_converter_xml": str(converter_xml),
        "object": {
            "name": model.body(cube_body).name,
            "position": data.xpos[cube_body].tolist(),
            "quaternion_wxyz": data.xquat[cube_body].tolist(),
            "yaw": 0,
            "size": (2 * model.geom_size[cube_geom]).tolist(),
            "mass": float(model.body_mass[cube_body]),
            "friction": model.geom_friction[cube_geom].tolist(),
            "table_height": float(data.geom_xpos[table_geom, 2] + model.geom_size[table_geom, 2]),
        },
        "neutral_pose": neutral_pose,
        "constraint_policy": {
            "kind": "rule_based_canonical_IK_sparse_pose_constraints",
            "constraint_source_frames": phase_source_frames.tolist(),
            "fullbody_constraint_rows": [0],
            "direct_world_coordinate_copy": False,
        },
        "fixture_only": False,
        "real_generation_run": False,
        "physical_replay_run": False,
        "physical_success": None,
        "expert_valid": None,
        "input_hashes": hashes_before,
    }

    planning_metrics = {
        "status": "ready_for_integration" if ready else "partial",
        "max_position_error": float(position_errors.max()),
        "mean_position_error": float(position_errors.mean()),
        "max_orientation_error": float(orientation_errors.max()),
        "mean_orientation_error": float(orientation_errors.mean()),
        "per_phase_position_error": per_phase(position_errors, source_t),
        "per_phase_orientation_error": per_phase(orientation_errors, source_t),
        "grasp_and_lift_position_error_max_m": float(position_errors[grasp_lift].max()),
        "joint_limit_violations": joint_limit_violations,
        "joint_limits_pass": not joint_limit_violations,
        "finite_check": finite_check,
        "initial_state_error": {
            "root_max_abs": root_initial_error,
            "body_max_abs": body_initial_error,
            "wrist_position_m": wrist_initial_position_error,
            "wrist_orientation_rad": wrist_initial_orientation_error,
            "hand_max_abs": hand_initial_error,
        },
        "frame_zero_pass": max(root_initial_error, body_initial_error, hand_initial_error) <= 1e-10,
        "phase_boundary_times": PHASES,
        "coordinate_roundtrip_error": reload_metadata["saved_matrix_roundtrip_max_error"],
        "pose_constraint_reload_error": reload_metadata["saved_matrix_roundtrip_max_error"],
        "pose_constraint_codec_metadata": reload_metadata,
        "hand_joint_limit_violations": hand_limit_violations,
        "hand_timeline_alignment": hand_alignment,
        "first_hand_motion_s": first_hand_motion_s,
        "source_duration_sec": float(source_t[-1]),
        "reference_duration_sec": float(reference_t[-1]),
        "source_frames": int(len(source_t)),
        "reference_frames": int(len(reference_t)),
        "constraint_count": int(len(phase_source_frames)),
        "model_generation_run": False,
        "physics_replay_run": False,
    }

    np.savez_compressed(
        output / "task_plan.npz",
        source_timestamps=source_t,
        source_qpos=source_qpos,
        canonical_wrist_world_pos=wrists_pos,
        canonical_wrist_world_quat=wrists_quat,
        desired_right_wrist_world_pos=desired_pos,
        desired_right_wrist_world_quat=desired_quat,
        timestamps=reference_t,
        hand_ref_q=hand_q,
        hand_ref_dq=hand_dq,
        constraint_source_frames=phase_source_frames,
    )
    write_json(output / "task.json", task)
    write_json(output / "planning_metrics.json", planning_metrics)

    hashes_after = {name: {"path": str(path), "sha256": sha256(path)} for name, path in protected.items()}
    require(hashes_before == hashes_after, "Protected inputs changed during Role-A planning")
    write_json(workdir / "logs/input_hashes_after.json", hashes_after)
    write_json(
        workdir / "logs/prepare_summary.json",
        {
            "task_id": task_id,
            "status": planning_metrics["status"],
            "output": str(output),
            "source_frames": len(source_t),
            "reference_frames": len(reference_t),
            "constraint_count": len(phase_source_frames),
            "max_position_error_m": planning_metrics["max_position_error"],
            "max_orientation_error_rad": planning_metrics["max_orientation_error"],
        },
    )
    (workdir / "pending.md").write_text(
        "# Pending\n\n"
        "- Role B real Kimodo generation has not been run.\n"
        "- Role C canonical reference export has not been run.\n"
        "- SONIC/DDS and physical replay are intentionally not run by Role A.\n"
        "- physical_success and expert_valid remain null.\n"
        "- The formal comparison constraint/information budget still needs protocol freeze.\n",
        encoding="utf-8",
    )
    print(json.dumps({"status": planning_metrics["status"], "task_id": task_id, "output": str(output)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
