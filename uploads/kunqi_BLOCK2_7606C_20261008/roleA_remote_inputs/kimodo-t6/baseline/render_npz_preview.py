#!/usr/bin/env python3
"""Render Kimodo's posed_joints output as a compact SOMA 77-joint MP4 preview."""
import argparse
from pathlib import Path

import cv2
import numpy as np
from kimodo.skeleton import SOMASkeleton77


def render(source: Path, output: Path, fps: int = 30) -> None:
    data = np.load(source)
    pts = np.asarray(data["posed_joints"], dtype=np.float32)
    if pts.ndim != 3 or pts.shape[1:] != (77, 3):
        raise ValueError(f"Expected posed_joints shaped [T, 77, 3], got {pts.shape}")
    pairs = SOMASkeleton77.bone_order_names_with_parents
    names = [name for name, _ in pairs]
    index = {name: i for i, name in enumerate(names)}
    edges = [(index[child], index[parent], child) for child, parent in pairs if parent is not None]
    height, width = 540, 960
    output.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError("OpenCV MP4 writer failed to initialize")
    theta = np.deg2rad(28.0)
    co, si = np.cos(theta), np.sin(theta)
    xx = pts[:, :, 0] * co - pts[:, :, 2] * si
    depth = pts[:, :, 0] * si + pts[:, :, 2] * co
    span_x = float(xx.max() - xx.min())
    span_y = float(pts[:, :, 1].max() - pts[:, :, 1].min())
    scale = min(175.0, 660.0 / (span_x + 0.5), 355.0 / max(span_y, 1.0))
    center_x = float((xx.max() + xx.min()) * 0.5)
    center_depth = float((depth.max() + depth.min()) * 0.5)
    base_y = float(np.percentile(pts[:, :, 1], 3))
    duration = len(pts) / fps
    for frame_index, pose in enumerate(pts):
        frame = np.full((height, width, 3), (250, 251, 253), dtype=np.uint8)
        cv2.rectangle(frame, (0, 456), (width, height), (244, 247, 250), -1)
        for y in range(466, height, 22):
            cv2.line(frame, (0, y), (width, y), (231, 235, 240), 1, cv2.LINE_AA)
        cv2.line(frame, (0, 455), (width, 455), (206, 214, 224), 2, cv2.LINE_AA)
        projected = np.empty((77, 2), dtype=np.int32)
        projected[:, 0] = np.round(width * 0.52 + (xx[frame_index] - center_x) * scale).astype(np.int32)
        projected[:, 1] = np.round(455 - (pose[:, 1] - base_y) * scale + (depth[frame_index] - center_depth) * scale * 0.035).astype(np.int32)
        root = projected[index.get("Hips", 0)]
        cv2.ellipse(frame, (int(root[0]), 458), (46, 9), 0, 0, 360, (222, 228, 236), -1, cv2.LINE_AA)
        for child_index, parent_index, child_name in edges:
            if child_name.startswith("Left"):
                color = (194, 108, 57)
            elif child_name.startswith("Right"):
                color = (66, 139, 206)
            else:
                color = (115, 105, 82)
            thickness = 4 if child_name in ("Spine1", "Spine2", "Chest", "Hips") else 3
            cv2.line(frame, tuple(projected[parent_index]), tuple(projected[child_index]), color, thickness, cv2.LINE_AA)
        for joint_index, point in enumerate(projected):
            cv2.circle(frame, tuple(point), 4 if joint_index < 30 else 2, (57, 68, 83), -1, cv2.LINE_AA)
        cv2.putText(frame, "KIMODO  /  TEST WALK", (36, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (42, 51, 63), 2, cv2.LINE_AA)
        cv2.putText(frame, "SOMA 77-joint motion preview", (38, 76), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (108, 119, 133), 1, cv2.LINE_AA)
        cv2.putText(frame, "A person walks forward.", (36, height - 28), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (60, 71, 86), 1, cv2.LINE_AA)
        stamp = f"{frame_index / fps:04.1f}s / {duration:.1f}s"
        cv2.putText(frame, stamp, (width - 170, height - 28), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (96, 106, 120), 1, cv2.LINE_AA)
        writer.write(frame)
    writer.release()
    check = cv2.VideoCapture(str(output))
    print(f"Wrote {output}: {int(check.get(cv2.CAP_PROP_FRAME_COUNT))} frames at {check.get(cv2.CAP_PROP_FPS):g} FPS")
    check.release()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_npz", type=Path)
    parser.add_argument("output_mp4", type=Path)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()
    render(args.input_npz, args.output_mp4, args.fps)
