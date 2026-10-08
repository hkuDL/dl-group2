#!/usr/bin/env python3
"""Thin evidence hook around the existing canonical run_sonic_grasp replay path."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

import mujoco
import numpy as np


CONTRACT = "kimodo_grasp_final_v1_20261007"
BASE = Path("/workspace/group2")
CANONICAL = BASE / "dl-group2"
SONIC = BASE / "GR00T-WholeBodyControl"
ROBOT = SONIC / "decoupled_wbc/control/robot_model/model_data/g1/g1_29dof_with_hand_rev_1_0_activatedfinger.xml"
SCENE = CANONICAL / "scenes/tabletop.xml"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--run-name", default="kimodo_canonical_replay")
    parser.add_argument("--validate-input-only", action="store_true")
    args = parser.parse_args()
    reference = args.reference_dir.resolve(strict=True)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    os.environ["SONIC_REPO"] = str(SONIC)
    sys.path.insert(0, str(CANONICAL / "scripts"))
    from expert_trajectory import load_reference, orders
    arrays, metadata = load_reference(reference)
    if len(arrays["timestamps"]) != 810 or not np.allclose(arrays["timestamps"], np.arange(810) / 50.0, rtol=0, atol=1e-12):
        raise ValueError("Replay requires the exact 810-frame final reference")
    if args.validate_input_only:
        (output / "input_validation.json").write_text(json.dumps({
            "valid": True, "frames": 810, "duration": 16.18,
            "reference": str(reference), "reference_npz_sha256": sha256(reference / "reference.npz"),
        }, indent=2) + "\n")
        return 0

    episode = output / "staging_episode"
    candidate = episode / "candidates/kimodo"
    candidate.parent.mkdir(parents=True)
    shutil.copytree(reference, candidate)
    (episode / "metadata.json").write_text(json.dumps({
        "selected_candidate": "kimodo", "expert_valid": False, "validation_runs": {},
    }, indent=2) + "\n")
    (episode / "info.txt").write_text("Role-C isolated canonical replay staging episode\n")

    import run_sonic_grasp as runner
    body_order, hand_order, _ = orders()
    records = []
    runtime_holder = {}
    original_init = runner.TabletopDDS.__init__
    original_step = runner.TabletopDDS.step
    original_load_scene = runner.load_scene

    def load_frozen_scene(*scene_args, **scene_kwargs):
        """Use the robot XML frozen by this contract when baseline is requested.

        The canonical checkout may have an intentionally unpopulated SONIC
        submodule.  Supplying the already-frozen external XML here preserves the
        existing canonical scene composer without modifying controller code.
        """
        if scene_kwargs.get("robot_path") is None:
            scene_kwargs["robot_path"] = ROBOT
        return original_load_scene(*scene_args, **scene_kwargs)

    def hooked_init(self, *hook_args, **hook_kwargs):
        original_init(self, *hook_args, **hook_kwargs)
        runtime_holder["runtime"] = self
        runtime_holder["cube_reset_pos"] = self.data.xpos[self.model.body("task_red_cube").id].copy()

    def hooked_step(self, reference_time, sonic_control, playing):
        result = original_step(self, reference_time, sonic_control, playing)
        model, data = self.model, self.data
        cube_body = model.body("task_red_cube").id
        cube_geom = model.geom("task_cube_geom").id
        force = np.zeros(6, dtype=np.float64)
        digit_forces = {"thumb": 0.0, "index": 0.0, "middle": 0.0}
        table_contact = False
        for contact_index, contact in enumerate(data.contact):
            other_geom = contact.geom2 if contact.geom1 == cube_geom else contact.geom1 if contact.geom2 == cube_geom else -1
            if other_geom < 0:
                continue
            mujoco.mj_contactForce(model, data, contact_index, force)
            normal_force = float(abs(force[0]))
            name = model.body(model.geom_bodyid[other_geom]).name or ""
            if name == "task_table":
                table_contact = True
            for digit in digit_forces:
                if f"right_hand_{digit}" in name:
                    digit_forces[digit] = max(digit_forces[digit], normal_force)
        reset = runtime_holder["cube_reset_pos"]
        record = {
            "physics_step": len(records),
            "physics_time": float(data.time),
            "playing": bool(playing),
            "reference_index": int(round(reference_time * 50.0)) if playing else -1,
            "reference_time": float(reference_time) if playing else -1.0,
            "robot_qpos": data.qpos.copy(),
            "robot_qvel": data.qvel.copy(),
            "cube_pos": data.xpos[cube_body].copy(),
            "cube_quat": data.xquat[cube_body].copy(),
            "cube_reset_pos": reset.copy(),
            "cube_lift": float(data.xpos[cube_body, 2] - reset[2]),
            "thumb_cube_contact": digit_forces["thumb"] > 0.0,
            "index_cube_contact": digit_forces["index"] > 0.0,
            "middle_cube_contact": digit_forces["middle"] > 0.0,
            "thumb_contact_force": digit_forces["thumb"],
            "index_contact_force": digit_forces["index"],
            "middle_contact_force": digit_forces["middle"],
            "cube_table_contact": table_contact,
            "fall_detected": bool(data.xpos[model.body("pelvis").id, 2] < 0.2),
            "support_detected": bool(result[2]),
            "weld_detected": bool(model.neq > 0 or self.support_mode == "weld"),
            "finite": bool(np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all() and np.isfinite(data.xpos[cube_body]).all()),
        }
        records.append(record)
        return result

    runner.TabletopDDS.__init__ = hooked_init
    runner.TabletopDDS.step = hooked_step
    runner.load_scene = load_frozen_scene
    previous_argv = sys.argv
    sys.argv = [
        str(Path(runner.__file__)), "--episode", str(episode), "--candidate", "kimodo",
        "--band", "off", "--startup-support", "none", "--pelvis-support", "none",
        "--kp-scale", "1", "--kd-scale", "1", "--physics-hz", "200",
        "--startup-body", "freebase-wbc", "--run-name", args.run_name, "--no-images",
    ]
    runner_exit = 0
    try:
        runner.main()
    except SystemExit as exc:
        runner_exit = int(exc.code or 0)
    finally:
        sys.argv = previous_argv
        runner.TabletopDDS.__init__ = original_init
        runner.TabletopDDS.step = original_step
        runner.load_scene = original_load_scene

    if not records:
        raise RuntimeError("Canonical replay produced no physics-step evidence")
    keys = records[0].keys()
    evidence = {key: np.asarray([row[key] for row in records]) for key in keys}
    np.savez_compressed(output / "replay_evidence.npz", **evidence)
    runtime = runtime_holder["runtime"]
    unique_reference = np.unique(evidence["reference_index"][evidence["playing"]])
    process_completed = bool(np.array_equal(unique_reference, np.arange(810)))
    integrity = {
        "contract_version": CONTRACT,
        "controller": "canonical_run_sonic_grasp",
        "canonical_runner": str(Path(runner.__file__).resolve()),
        "canonical_runner_sha256": sha256(Path(runner.__file__)),
        "runner_exit_code": runner_exit,
        "process_completed": process_completed,
        "unassisted": True,
        "robot_xml": str(ROBOT), "robot_xml_sha256": sha256(ROBOT),
        "scene": str(SCENE), "scene_sha256": sha256(SCENE),
        "nq": runtime.model.nq, "nv": runtime.model.nv, "nu": runtime.model.nu, "neq": runtime.model.neq,
        "reference_frames": 810, "reference_fps": 50,
        "reference_npz_sha256": sha256(reference / "reference.npz"),
        "body_joint_order": body_order, "hand_joint_order": hand_order,
        "sonic_kp_scale": 1.0, "sonic_kd_scale": 1.0,
        "hand_pd": {"kp": 12.0, "kd": 0.3},
        "physics_dt": float(runtime.model.opt.timestep),
        "gravity": runtime.model.opt.gravity.tolist(),
        "initialization_support": "none", "final_support": "none", "pelvis_weld": False,
        "evidence_rows": len(records),
        "playing_start_step": int(np.flatnonzero(evidence["playing"])[0]) if evidence["playing"].any() else None,
        "playing_end_step": int(np.flatnonzero(evidence["playing"])[-1]) if evidence["playing"].any() else None,
        "actual_playing_duration": float(evidence["playing"].sum() * runtime.model.opt.timestep),
        "simulation_time_start": float(evidence["physics_time"][0]),
        "simulation_time_end": float(evidence["physics_time"][-1]),
        "wall_clock_is_not_reference_clock": True,
    }
    (output / "integrity.json").write_text(json.dumps(integrity, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({"output": str(output), "evidence_rows": len(records), "process_completed": process_completed, "runner_exit_code": runner_exit}, indent=2))
    return 0 if process_completed else 2


if __name__ == "__main__":
    raise SystemExit(main())
