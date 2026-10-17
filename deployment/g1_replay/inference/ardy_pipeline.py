"""ARDY batch-one CUDA inference without simulator or training-data imports."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import numpy as np

from adapters.motion import qpos_to_canonical_arrays
from inference.common import ensure_batch_one, resolve_project_path
from inference.io import write_motion_reference


def prepare(config: Mapping[str, Any], project_root: Path):
    import torch
    from ardy.model import load_model
    from ardy.constraints import load_constraints_lst
    from ardy.motion_rep.tools import length_to_mask
    from ardy.exports.mujoco import MujocoQposConverter
    from ardy.tools import to_numpy

    ensure_batch_one(int(config.get("batch_size", 1)))
    if not torch.cuda.is_available():
        raise RuntimeError("ARDY CUDA inference requires one visible NVIDIA GPU")
    checkpoint_root = resolve_project_path(project_root, config["checkpoints_dir"])
    model = load_model(config["model"], device="cuda:0", checkpoints_dir=str(checkpoint_root))
    fps = float(model.motion_rep.fps)
    frames = int(round(float(config["duration_s"]) * fps))
    lengths = torch.tensor([frames], device="cuda:0")
    constraint_list = []
    if config.get("constraints_file"):
        constraint_path = resolve_project_path(project_root, config["constraints_file"])
        constraint_list = load_constraints_lst(str(constraint_path), model.skeleton)
    observed_motion, motion_mask = None, None
    if constraint_list:
        observed_motion, motion_mask = model.motion_rep.create_conditions_from_constraints_batched(
            constraint_list, lengths, to_normalize=True, device="cuda:0"
        )
    converter = MujocoQposConverter(model.skeleton)

    def infer():
        with torch.inference_mode():
            motion = model(
                [str(config["prompt"])],
                frames,
                num_denoising_steps=int(config["diffusion_steps"]),
                pad_mask=length_to_mask(lengths),
                first_heading_angle=torch.zeros(1, device="cuda:0"),
                motion_mask=motion_mask,
                observed_motion=observed_motion,
                cfg_weight=tuple(config.get("cfg_weight", [2.0, 2.0])),
                crop_history_length=config.get("history_frames"),
            )
            raw = to_numpy(model.motion_rep.inverse(motion, is_normalized=True))
        qpos = converter.dict_to_qpos(raw, device="cuda:0")
        if qpos.ndim == 3:
            qpos = qpos[0]
        hand = np.zeros((len(qpos), 14), dtype=np.float64)
        return qpos_to_canonical_arrays(qpos, hand, source_hz=fps, target_hz=50)

    return infer


def run(config: Mapping[str, Any], project_root: Path, output_dir: Path) -> None:
    write_motion_reference(output_dir, prepare(config, project_root)(), "ardy")

