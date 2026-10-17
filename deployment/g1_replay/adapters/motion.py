"""Simulator-free conversion from G1 kinematic qpos to the canonical reference."""

from __future__ import annotations

from typing import Dict

import numpy as np


def _interp(time_in: np.ndarray, values: np.ndarray, time_out: np.ndarray) -> np.ndarray:
    flat = values.reshape(values.shape[0], -1)
    out = np.stack([np.interp(time_out, time_in, flat[:, column]) for column in range(flat.shape[1])], axis=1)
    return out.reshape((len(time_out),) + values.shape[1:])


def qpos_to_canonical_arrays(
    qpos: np.ndarray,
    hand_ref_q: np.ndarray | None = None,
    *,
    source_hz: float,
    target_hz: float = 50.0,
) -> Dict[str, np.ndarray]:
    qpos = np.asarray(qpos, dtype=np.float64)
    if qpos.ndim != 2 or qpos.shape[1] != 36 or len(qpos) < 2:
        raise ValueError("qpos must have shape [T,36] with at least two frames")
    if not np.isfinite(qpos).all() or source_hz <= 0 or target_hz <= 0:
        raise ValueError("qpos and frequencies must be finite and positive")
    if hand_ref_q is None:
        hand_ref_q = np.zeros((len(qpos), 14), dtype=np.float64)
    hand_ref_q = np.asarray(hand_ref_q, dtype=np.float64)
    if hand_ref_q.shape != (len(qpos), 14) or not np.isfinite(hand_ref_q).all():
        raise ValueError("hand_ref_q must have shape [T,14]")

    time_in = np.arange(len(qpos), dtype=np.float64) / source_hz
    count = int(round(time_in[-1] * target_hz)) + 1
    time_out = np.arange(count, dtype=np.float64) / target_hz
    root_pos = _interp(time_in, qpos[:, :3], time_out)
    root_quat = _interp(time_in, qpos[:, 3:7], time_out)
    root_quat /= np.clip(np.linalg.norm(root_quat, axis=1, keepdims=True), 1e-12, None)
    body_q = _interp(time_in, qpos[:, 7:36], time_out)
    hand_q = _interp(time_in, hand_ref_q, time_out)
    return {
        "time_s": time_out,
        "body_ref_q": body_q,
        "body_ref_dq": np.gradient(body_q, time_out, axis=0, edge_order=1),
        "root_ref_pos": root_pos,
        "root_ref_quat": root_quat,
        "hand_ref_q": hand_q,
        "hand_ref_dq": np.gradient(hand_q, time_out, axis=0, edge_order=1),
    }

