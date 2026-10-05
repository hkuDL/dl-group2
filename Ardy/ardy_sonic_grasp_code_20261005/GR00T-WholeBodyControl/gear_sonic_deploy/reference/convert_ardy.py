#!/usr/bin/env python3
"""Convert an ARDY G1 NPZ into SONIC's 50 Hz reference-motion CSV directory.

Run from the GR00T-WholeBodyControl repository root:
    python gear_sonic_deploy/reference/convert_ardy.py \
        ../ardy/outputs/baseline_g1.npz \
        --output-dir gear_sonic_deploy/reference/ardy/walk_circle

The matching ARDY MuJoCo qpos CSV is reused when present. Otherwise ARDY's
official MujocoQposConverter runs on CPU. No model weights or GPU are needed.
"""

import argparse
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
from scipy.spatial.transform import Rotation, Slerp

from convert_motions import convert_single_motion


TARGET_FPS = 50
# Same IsaacLab body indexes and order as SONIC's released reference examples.
BODY_INDEXES = np.array([0, 4, 10, 18, 5, 11, 19, 9, 16, 22, 28, 17, 23, 29])


def load_ardy_qpos(npz_path, ardy_repo, qpos_csv):
    with np.load(npz_path, allow_pickle=False) as data:
        fps = float(data["fps"])
        local_rotations = data["local_rot_mats"]
        root_positions = data["root_positions"]
        prompt = str(data["text"]) if "text" in data else ""
    if local_rotations.shape[1:] != (34, 3, 3):
        raise ValueError("Only ARDY G1 (34-node skeleton) motions are supported")

    csv_path = qpos_csv if qpos_csv is not None else npz_path.with_suffix(".csv")
    if csv_path.is_file():
        qpos = np.loadtxt(csv_path, delimiter=",", ndmin=2)
        source = str(csv_path)
    else:
        if qpos_csv is not None:
            raise FileNotFoundError(csv_path)
        sys.path.insert(0, str(ardy_repo))
        from ardy.exports.mujoco import MujocoQposConverter
        from ardy.skeleton import G1Skeleton34

        converter = MujocoQposConverter(G1Skeleton34())
        qpos = converter.dict_to_qpos(
            {"local_rot_mats": local_rotations[None], "root_positions": root_positions[None]},
            device="cpu",
        )[0]
        source = "ARDY MujocoQposConverter (CPU)"
    if qpos.shape != (len(root_positions), 36) or len(qpos) < 2:
        raise ValueError("Expected matching qpos data with shape (frames >= 2, 36)")
    if not np.isfinite(qpos).all() or not np.isfinite(fps) or fps <= 0:
        raise ValueError("Motion values must be finite and fps must be positive")
    return qpos, fps, prompt, source


def resample_qpos(qpos, source_fps):
    source_times = np.arange(len(qpos)) / source_fps
    frame_count = int(round(len(qpos) / source_fps * TARGET_FPS))
    if frame_count < 2:
        raise ValueError("Motion is too short to resample at 50 Hz")
    # Keep N/fps playback duration; hold the final pose for the last sub-frame.
    target_times = np.minimum(np.arange(frame_count) / TARGET_FPS, source_times[-1])
    result = np.empty((frame_count, 36))
    for column in list(range(3)) + list(range(7, 36)):
        result[:, column] = np.interp(target_times, source_times, qpos[:, column])
    rotations = Rotation.from_quat(qpos[:, [4, 5, 6, 3]])
    result[:, 3:7] = Slerp(source_times, rotations)(target_times).as_quat()[:, [3, 0, 1, 2]]
    return result


def sonic_kinematics(qpos, ardy_repo, deploy_dir):
    # The ARDY CSV follows its XML's hinge-joint order. Match these joints by name
    # to SONIC's model instead of assuming MuJoCo body IDs or joint IDs coincide.
    ardy_xml = ardy_repo / "ardy/assets/skeletons/g1skel34/xml/g1.xml"
    joint_names = [
        joint.attrib["name"]
        for joint in ET.parse(ardy_xml).findall(".//worldbody//joint")
        if joint.get("type") != "free"
    ]
    parameters = deploy_dir / "src/g1/g1_deploy_onnx_ref/include/policy_parameters.hpp"
    mapping_text = re.search(
        r"mujoco_to_isaaclab\s*=\s*\{([^}]+)\}", parameters.read_text()
    ).group(1)
    isaac_to_source = np.array([int(value) for value in re.findall(r"\d+", mapping_text)])
    if len(joint_names) != 29 or sorted(isaac_to_source.tolist()) != list(range(29)):
        raise ValueError("Expected 29 G1 joints and a valid SONIC joint permutation")

    model = mujoco.MjModel.from_xml_path(str(deploy_dir / "g1/g1_29dof.xml"))
    data = mujoco.MjData(model)
    joint_ids = np.array([model.joint(name).id for name in joint_names])
    joint_addresses = model.jnt_qposadr[joint_ids]
    root_address = model.joint("floating_base_joint").qposadr[0]
    body_ids = [model.body("pelvis").id] + [
        int(model.jnt_bodyid[joint_ids[isaac_to_source[index - 1]]])
        for index in BODY_INDEXES[1:]
    ]
    positions = np.empty((len(qpos), len(body_ids), 3))
    quaternions = np.empty((len(qpos), len(body_ids), 4))
    for frame, pose in enumerate(qpos):
        data.qpos[root_address : root_address + 7] = pose[:7]
        data.qpos[joint_addresses] = pose[7:]
        mujoco.mj_kinematics(model, data)
        positions[frame] = data.xpos[body_ids]
        quaternions[frame] = data.xquat[body_ids]  # MuJoCo wxyz.
    return qpos[:, 7:][:, isaac_to_source], positions, quaternions


def world_angular_velocity(quaternions):
    count, bodies = quaternions.shape[:2]
    rotations = Rotation.from_quat(quaternions[:, :, [1, 2, 3, 0]].reshape(-1, 4))
    rotations_next = rotations[bodies:]
    rotations_prev = rotations[:-bodies]
    differences = (rotations_next * rotations_prev.inv()).as_rotvec().reshape(count - 1, bodies, 3)
    differences *= TARGET_FPS
    velocity = np.empty((count, bodies, 3))
    velocity[0], velocity[-1] = differences[0], differences[-1]
    velocity[1:-1] = (differences[:-1] + differences[1:]) / 2
    return velocity


def main():
    deploy_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path, help="ARDY G1 .npz from generate.py")
    parser.add_argument("--output-dir", required=True, type=Path, help="One motion folder, e.g. reference/ardy/walk_circle")
    parser.add_argument("--ardy-repo", type=Path, default=deploy_dir.parent.parent / "ardy")
    parser.add_argument("--qpos-csv", type=Path, help="Override the matching ARDY qpos CSV")
    args = parser.parse_args()

    source_qpos, source_fps, prompt, source = load_ardy_qpos(args.input, args.ardy_repo, args.qpos_csv)
    qpos = resample_qpos(source_qpos, source_fps)
    joint_positions, body_positions, body_quaternions = sonic_kinematics(qpos, args.ardy_repo, deploy_dir)
    motion = {
        "joint_pos": joint_positions,
        "joint_vel": np.gradient(joint_positions, 1 / TARGET_FPS, axis=0),
        "body_pos_w": body_positions,
        "body_quat_w": body_quaternions,
        "body_lin_vel_w": np.gradient(body_positions, 1 / TARGET_FPS, axis=0),
        "body_ang_vel_w": world_angular_velocity(body_quaternions),
        "_body_indexes": BODY_INDEXES,
        "time_step_total": len(qpos),
        "fps": TARGET_FPS,
        "source_fps": source_fps,
        "source_npz": str(args.input.resolve()),
        "qpos_source": source,
        "prompt": prompt,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if not convert_single_motion(args.output_dir.name, motion, str(args.output_dir)):
        raise SystemExit(1)
    print(f"Source: {source}")
    print(f"Frames: {len(source_qpos)} @ {source_fps:g} FPS -> {len(qpos)} @ {TARGET_FPS} FPS")
    print(f"Playback duration: {len(qpos) / TARGET_FPS:g} s")
    print(f"SONIC reference parent directory: {args.output_dir.resolve().parent}")


if __name__ == "__main__":
    main()
