"""VA batch-one CUDA inference from explicit portable input arrays."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import numpy as np

from inference.common import ensure_batch_one, resolve_project_path
from inference.io import write_token_reference


def prepare(config: Mapping[str, Any], project_root: Path):
    import torch
    from PIL import Image
    from inference.va_model import VAPolicy

    ensure_batch_one(int(config.get("batch_size", 1)))
    if not torch.cuda.is_available():
        raise RuntimeError("VA CUDA inference requires one visible NVIDIA GPU")
    checkpoint = resolve_project_path(project_root, config["checkpoint"])
    input_path = resolve_project_path(project_root, config["input_npz"])
    with np.load(input_path, allow_pickle=False) as archive:
        rgb, body, hand = archive["rgb"], archive["body"], archive["hand"]
    if rgb.ndim != 3 or rgb.shape[2] != 3 or body.shape != (68,) or hand.shape != (28,):
        raise ValueError("VA input must contain rgb [H,W,3], body [68], hand [28]")
    image = np.asarray(Image.fromarray(rgb.astype(np.uint8)).resize((128, 128), Image.Resampling.BILINEAR))
    image = image.transpose(2, 0, 1).astype(np.float32) / 255.0
    model = VAPolicy(v41=bool(config.get("v41", True))).to("cuda:0").eval()
    payload = torch.load(checkpoint, map_location="cuda:0", weights_only=True)
    state = payload.get("model", payload.get("state_dict", payload)) if isinstance(payload, dict) else payload
    model.load_state_dict(state, strict=True)
    tensors = [torch.from_numpy(value).to("cuda:0")[None] for value in (image, body.astype(np.float32), hand.astype(np.float32))]
    def infer():
        with torch.inference_mode():
            return {name: value[0].cpu().numpy() for name, value in model(*tensors).items()}

    return infer


def run(config: Mapping[str, Any], project_root: Path, output_dir: Path) -> None:
    write_token_reference(output_dir, prepare(config, project_root)())

