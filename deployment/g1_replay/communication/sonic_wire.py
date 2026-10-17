"""Byte-compatible subset of SONIC's packed ZMQ pose protocol."""

from __future__ import annotations

import json
from typing import Mapping

import numpy as np


HEADER_SIZE = 1280
_DTYPES = {
    np.dtype("float32"): "f32",
    np.dtype("float64"): "f64",
    np.dtype("int32"): "i32",
    np.dtype("int64"): "i64",
    np.dtype("bool"): "bool",
}


def _validate_protocol(data: Mapping[str, np.ndarray], version: int) -> None:
    keys = set(data)
    hand = {"left_hand_joints", "right_hand_joints"}
    if version == 1:
        required = {"joint_pos", "joint_vel", "body_quat", "frame_index"}
        if not required.issubset(keys) or not keys.issubset(required | hand):
            raise ValueError("protocol v1 requires motion fields and optional hand fields")
        count = data["joint_pos"].shape[0] if data["joint_pos"].ndim == 2 else -1
        expected = {
            "joint_pos": (count, 29),
            "joint_vel": (count, 29),
            "body_quat": (count, 4),
            "frame_index": (count,),
        }
        for name, shape in expected.items():
            if data[name].shape != shape:
                raise ValueError(f"{name}: expected {shape}, got {data[name].shape}")
    elif version == 4:
        required = {"token_state", "frame_index"}
        if not required.issubset(keys) or not keys.issubset(required | hand):
            raise ValueError("protocol v4 requires token fields and optional hand fields; mixed protocol fields are forbidden")
        if data["token_state"].shape != (1, 64) or data["frame_index"].shape != (1,):
            raise ValueError("protocol v4 expects token_state [1,64] and frame_index [1]")
    else:
        raise ValueError("only SONIC protocol v1 motion and v4 token messages are supported")
    for name in hand & keys:
        if data[name].shape != (1, 7):
            raise ValueError(f"{name}: expected [1,7]")


def pack_pose_message(pose_data: Mapping[str, np.ndarray], topic: str = "pose", version: int = 1) -> bytes:
    data = {name: np.asarray(value) for name, value in pose_data.items()}
    _validate_protocol(data, version)
    fields = []
    payload = []
    for name, value in data.items():
        if value.dtype not in _DTYPES:
            raise ValueError(f"{name}: unsupported dtype {value.dtype}")
        if not np.isfinite(value).all():
            raise ValueError(f"{name}: non-finite value")
        value = np.ascontiguousarray(value)
        if value.dtype.byteorder == ">":
            value = value.astype(value.dtype.newbyteorder("<"))
        fields.append({"name": name, "dtype": _DTYPES[value.dtype], "shape": list(value.shape)})
        payload.append(value.tobytes())
    header = json.dumps(
        {"v": version, "endian": "le", "count": 1, "fields": fields},
        separators=(",", ":"),
    ).encode("utf-8")
    if len(header) > HEADER_SIZE:
        raise ValueError(f"header too large: {len(header)} > {HEADER_SIZE}")
    return topic.encode("utf-8") + header.ljust(HEADER_SIZE, b"\x00") + b"".join(payload)

