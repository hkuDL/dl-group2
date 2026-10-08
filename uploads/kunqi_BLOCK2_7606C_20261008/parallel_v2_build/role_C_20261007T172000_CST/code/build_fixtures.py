#!/usr/bin/env python3
"""Create self-contained 810-frame reference fixtures; never label them as real Kimodo output."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import numpy as np


BASE = Path("/workspace/group2")
CANONICAL = BASE / "dl-group2"
SONIC = BASE / "GR00T-WholeBodyControl"
CONTRACT = "kimodo_grasp_final_v1_20261007"


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: build_fixtures.py FIXTURE_DIR")
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()):
        raise FileExistsError(f"Fixture directory is not empty: {output}")
    os.environ["SONIC_REPO"] = str(SONIC)
    sys.path.insert(0, str(CANONICAL / "scripts"))
    from expert_trajectory import orders
    body_names, hand_names, _ = orders()
    t = np.arange(810, dtype=np.float64) / 50.0
    body_q = np.zeros((810, 29), dtype=np.float64)
    envelope = np.sin(np.pi * t / t[-1]) ** 2
    body_q[:, body_names.index("right_shoulder_pitch_joint")] = 0.12 * envelope
    body_q[:, body_names.index("right_elbow_joint")] = 0.10 * envelope
    body_dq = np.gradient(body_q, t, axis=0, edge_order=2)
    root_pos = np.tile([0.0, 0.0, 0.7846157043688324], (810, 1)).astype(np.float64)
    root_quat = np.tile([1.0, 0.0, 0.0, 0.0], (810, 1)).astype(np.float64)
    hand_q = np.zeros((810, 14), dtype=np.float64)
    closure = np.clip((t - 8.0) / 2.0, 0.0, 1.0)
    closure = closure * closure * (3.0 - 2.0 * closure)
    for name, value in {
        "right_hand_index_0_joint": 0.5,
        "right_hand_middle_0_joint": 0.5,
        "right_hand_thumb_1_joint": -0.5,
    }.items():
        hand_q[:, hand_names.index(name)] = closure * value
    hand_dq = np.gradient(hand_q, t, axis=0, edge_order=2)
    np.savez_compressed(
        output / "body_reference_fixture.npz",
        contract_version=np.asarray(CONTRACT), fixture_only=np.asarray(True), timestamps=t,
        body_ref_q=body_q, body_ref_dq=body_dq, root_ref_pos=root_pos, root_ref_quat=root_quat,
        root_lin_vel=np.zeros((810, 3), dtype=np.float64),
        root_ang_vel=np.zeros((810, 3), dtype=np.float64),
        body_joint_names=np.asarray(body_names),
    )
    np.savez_compressed(
        output / "task_plan_fixture.npz",
        contract_version=np.asarray(CONTRACT), fixture_only=np.asarray(True), timestamps=t,
        hand_ref_q=hand_q, hand_ref_dq=hand_dq, hand_joint_names=np.asarray(hand_names),
    )
    (output / "README.md").write_text(
        "# Fixtures\n\nThese deterministic arrays exercise the final software contract only. "
        "They are not Kimodo output and are not evidence of grasp success.\n", encoding="utf-8"
    )
    print(json.dumps({"fixture_only": True, "frames": 810, "duration": 16.18}, indent=2))


if __name__ == "__main__":
    main()
