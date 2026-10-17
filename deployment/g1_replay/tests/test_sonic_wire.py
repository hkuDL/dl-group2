from __future__ import annotations

import json
import hashlib

import numpy as np
import pytest

from communication.sonic_wire import HEADER_SIZE, pack_pose_message


def _header(message: bytes, topic: bytes = b"pose") -> dict:
    raw = message[len(topic) : len(topic) + HEADER_SIZE].rstrip(b"\x00")
    return json.loads(raw)


def test_v1_motion_layout() -> None:
    data = {
        "joint_pos": np.zeros((1, 29), dtype=np.float32),
        "joint_vel": np.ones((1, 29), dtype=np.float32),
        "body_quat": np.array([[1, 0, 0, 0]], dtype=np.float32),
        "frame_index": np.array([3], dtype=np.int64),
        "left_hand_joints": np.zeros((1, 7), dtype=np.float32),
        "right_hand_joints": np.zeros((1, 7), dtype=np.float32),
    }
    message = pack_pose_message(data, version=1)
    assert message.startswith(b"pose")
    header = _header(message)
    assert header["v"] == 1 and header["endian"] == "le" and header["count"] == 1
    assert [field["name"] for field in header["fields"]] == list(data)
    assert len(message) == 4 + HEADER_SIZE + sum(value.nbytes for value in data.values())


def test_v4_token_layout_and_mixed_fields_rejected() -> None:
    message = pack_pose_message(
        {"token_state": np.zeros((1, 64), np.float32), "frame_index": np.array([0], np.int64)},
        version=4,
    )
    assert _header(message)["fields"][0]["shape"] == [1, 64]
    with pytest.raises(ValueError, match="protocol"):
        pack_pose_message(
            {
                "token_state": np.zeros((1, 64), np.float32),
                "joint_pos": np.zeros((1, 29), np.float32),
                "frame_index": np.array([0], np.int64),
            },
            version=4,
        )


def test_wrong_shapes_are_rejected() -> None:
    with pytest.raises(ValueError, match="joint_pos"):
        pack_pose_message(
            {
                "joint_pos": np.zeros((29,), np.float32),
                "joint_vel": np.zeros((1, 29), np.float32),
                "body_quat": np.zeros((1, 4), np.float32),
                "frame_index": np.array([0], np.int64),
            },
            version=1,
        )


def test_vectors_match_pinned_s4000_upstream() -> None:
    motion = {
        "joint_pos": np.arange(58, dtype=np.float32).reshape(2, 29) / 10,
        "joint_vel": np.zeros((2, 29), np.float32),
        "body_quat": np.tile(np.array([[1, 0, 0, 0]], np.float32), (2, 1)),
        "frame_index": np.array([7, 8], np.int64),
        "left_hand_joints": np.arange(7, dtype=np.float32).reshape(1, 7),
        "right_hand_joints": np.arange(7, 14, dtype=np.float32).reshape(1, 7),
    }
    token = {
        "token_state": np.arange(64, dtype=np.float32).reshape(1, 64) / 16,
        "frame_index": np.array([9], np.int64),
    }
    assert hashlib.sha256(pack_pose_message(motion, version=1)).hexdigest() == "029ef45f4c8f17f94d646c85904e7736f4705f7952c3bdc3612bf5e8bde59af3"
    assert hashlib.sha256(pack_pose_message(token, version=4)).hexdigest() == "e15f54a574e28255bb7763c2d406df852ecfd0f4b7b5cdea9ce6b0fe467cd94a"

