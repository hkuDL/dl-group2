from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

import numpy as np

from contracts.joints import BODY_JOINT_NAMES, HAND_JOINT_NAMES


def write_motion_reference(output_dir: Path, arrays: Mapping[str, np.ndarray], producer: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(output_dir / "reference.npz", **arrays)
    metadata = {
        "producer_type": producer,
        "reference_complete": True,
        "reference_hz": 50,
        "quaternion_convention": "wxyz",
        "root_pose_frame": "world",
        "units": {
            "time_s": "s", "body_ref_q": "rad", "body_ref_dq": "rad/s",
            "root_ref_pos": "m", "root_ref_quat": "unitless", "hand_ref_q": "rad",
        },
        "body_joint_names": BODY_JOINT_NAMES,
        "hand_joint_names": HAND_JOINT_NAMES,
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def write_token_reference(output_dir: Path, arrays: Mapping[str, np.ndarray], producer: str = "va") -> None:
    output_dir.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(output_dir / "reference.npz", **arrays)
    metadata = {
        "producer_type": producer,
        "variant": "sonic_token_v4",
        "token_shape": [10, 64],
        "hand_shape": [50, 14],
        "batch_size": 1,
        "sonic_protocol": 4,
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

