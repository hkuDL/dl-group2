"""Kimodo batch-one CUDA inference without MuJoCo or training data."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import numpy as np

from adapters.motion import qpos_to_canonical_arrays
from inference.common import ensure_batch_one, resolve_project_path
from inference.io import write_motion_reference


def prepare(config: Mapping[str, Any], project_root: Path):
    import os
    import torch
    from kimodo import load_model
    from kimodo.constraints import load_constraints_lst
    from kimodo.exports.mujoco import MujocoQposConverter
    from kimodo.skeleton import G1Skeleton34

    ensure_batch_one(int(config.get("batch_size", 1)))
    if not torch.cuda.is_available():
        raise RuntimeError("Kimodo CUDA inference requires one visible NVIDIA GPU")
    checkpoint_root = resolve_project_path(project_root, config["checkpoints_dir"])
    os.environ["CHECKPOINT_DIR"] = str(checkpoint_root)
    os.environ["TEXT_ENCODER_MODE"] = str(config.get("text_encoder_mode", "local"))
    model, _ = load_model("g1", device="cuda:0", return_resolved_name=True)
    frames = int(round(float(config["duration_s"]) * float(model.fps)))
    constraint_list = []
    if config.get("constraints_file"):
        constraint_path = resolve_project_path(project_root, config["constraints_file"])
        constraint_list = load_constraints_lst(str(constraint_path), model.skeleton, device="cuda:0")
    converter = MujocoQposConverter(G1Skeleton34())

    def infer():
        with torch.inference_mode():
            raw = model(
                str(config["prompt"]),
                frames,
                num_denoising_steps=int(config["diffusion_steps"]),
                constraint_lst=constraint_list,
                cfg_weight=list(config.get("cfg_weight", [2.0, 2.0])),
                multi_prompt=False,
                post_processing=False,
                return_numpy=True,
            )
        qpos = converter.to_qpos(
            torch.as_tensor(raw["local_rot_mats"])[None],
            torch.as_tensor(raw["root_positions"])[None],
            root_quat_w_first=True,
            mujoco_rest_zero=False,
        ).detach().cpu().numpy()[0]
        hand = np.zeros((len(qpos), 14), dtype=np.float64)
        return qpos_to_canonical_arrays(qpos, hand, source_hz=float(model.fps), target_hz=50)

    return infer


def run(config: Mapping[str, Any], project_root: Path, output_dir: Path) -> None:
    write_motion_reference(output_dir, prepare(config, project_root)(), "kimodo")

