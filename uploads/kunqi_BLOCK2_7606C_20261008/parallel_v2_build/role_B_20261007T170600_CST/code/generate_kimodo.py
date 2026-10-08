#!/usr/bin/env python3
"""Validated Kimodo generator for the frozen final grasp request contract."""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
import sys
import time

import numpy as np


CONTRACT = "kimodo_grasp_final_v1_20261007"
INTEGRATION = Path("/workspace/group2/kimodo-t6/g1-integration")
EXPECTED_PACKAGE = INTEGRATION / "kimodo-upload/kimodo"
COORDINATES = INTEGRATION / "coordinate-repair-20261007-v2"
CHECKPOINT = INTEGRATION / "checkpoints/Kimodo-G1-RP-v1"


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def frame_vectors(raw):
    keys = ["local_rot_mats", "root_positions", "posed_joints", "global_rot_mats", "smooth_root_pos"]
    return np.concatenate([np.asarray(raw[key]).reshape(len(raw[key]), -1) for key in keys], axis=1)


def validate_and_load(request_path, pose_path):
    request = json.loads(Path(request_path).read_text())
    required = {
        "contract_version", "task_id", "seed", "prompt", "requested_duration_sec",
        "source_fps", "reference_fps", "reference_frames", "body_joint_names",
        "hand_joint_names", "source_qpos_names", "pose_constraints_sha256",
    }
    require(required <= request.keys(), f"Missing request fields: {sorted(required - request.keys())}")
    require(request["contract_version"] == CONTRACT, "Unsupported contract_version")
    require(isinstance(request["prompt"], str) and request["prompt"].strip(), "Prompt must be nonempty")
    require(isinstance(request["seed"], int) and request["seed"] >= 0, "Seed must be a nonnegative integer")
    duration = float(request["requested_duration_sec"])
    fps = float(request["source_fps"])
    require(np.isfinite(duration) and duration > 0 and np.isfinite(fps) and fps > 0, "Invalid duration/fps")
    require(request["reference_fps"] == 50 and request["reference_frames"] == 810, "Final reference contract mismatch")
    require(len(request["body_joint_names"]) == len(set(request["body_joint_names"])) == 29, "Invalid body order")
    require(len(request["hand_joint_names"]) == len(set(request["hand_joint_names"])) == 14, "Invalid hand order")
    require(len(request["source_qpos_names"]) == len(set(request["source_qpos_names"])) == 36, "Invalid source qpos order")
    require(sha256(pose_path) == request["pose_constraints_sha256"], "pose_constraints SHA256 mismatch")
    frames = int(round(duration * fps)) + 1
    if "source_frames" in request:
        require(int(request["source_frames"]) == frames, "source_frames disagrees with duration/fps")

    sys.path.insert(0, str(COORDINATES))
    from kimodo.skeleton import G1Skeleton34
    from kimodo.exports.mujoco import MujocoQposConverter
    from kimodo_pose_constraint_codec import load_pose_constraints
    converter = MujocoQposConverter(G1Skeleton34())
    constraints, codec = load_pose_constraints(pose_path, converter)
    record = json.loads(Path(pose_path).read_text())
    constraint_frames = np.asarray(record["frame_indices"], dtype=np.int64)
    require(len(constraint_frames) > 0 and int(constraint_frames[-1]) < frames, "Constraint frame exceeds request")
    require(np.all(np.diff(constraint_frames) > 0), "Constraint timestamps are not strictly increasing")
    return request, frames, fps, constraints, codec, record


def api_report(model, resolved, kimodo_path):
    from kimodo import load_model
    from kimodo.motion_rep.conditioning import build_condition_dicts
    return {
        "audited_live_package": str(kimodo_path),
        "generation_entrypoint": f"{model.__class__.__module__}.{model.__class__.__name__}.__call__",
        "generation_signature": str(inspect.signature(model.__call__)),
        "load_model_signature": str(inspect.signature(load_model)),
        "condition_builder_signature": str(inspect.signature(build_condition_dicts)),
        "text_prompt_input": "prompts: str or list[str]",
        "fullbody_condition_api": "FullBodyConstraintSet through constraint_lst",
        "root_condition_api": "root components encoded by the matrix-preserving constraint codec",
        "pose_condition_api": "EndEffectorConstraintSet through constraint_lst",
        "duration_semantics": "No seconds argument; wrapper computes round(seconds * model.fps) + 1 frames.",
        "num_frames_semantics": "Inclusive sampled trajectory length passed directly to Kimodo.__call__.",
        "fps_semantics": f"model.fps={float(model.fps)} from checkpoint configuration",
        "seed_behavior": "numpy, torch, and torch.musa RNGs are seeded before inference",
        "device_behavior": "MUSA_VISIBLE_DEVICES selects physical S4000; model receives logical musa:0",
        "checkpoint": str(CHECKPOINT),
        "resolved_model": resolved,
        "input_schema": "generation_request.json + matrix-codec pose_constraints.json",
        "output_schema": "unaltered numpy arrays returned by Kimodo with shapes recorded in generation.json",
        "native_long_horizon": "A single native call is used and empirically validated at 487 frames / 16.2 s.",
        "segmentation": {"required": False, "supported_by_api": True, "api_parameter": "multi_prompt + num_transition_frames"},
        "known_limitations": [
            "The API exposes frames, not seconds; fps must match the loaded checkpoint.",
            "The raw model does not emit canonical hand14 references or SONIC CSV files.",
            "Conditioning error is not directly available in the returned motion dictionary.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--pose-constraints", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--physical-gpu", type=int, default=int(os.environ.get("KIMODO_PHYSICAL_GPU", "1")))
    parser.add_argument("--denoising-steps", type=int, default=100)
    parser.add_argument("--constraint-cfg", type=float, default=2.0)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    require(args.physical_gpu >= 0 and args.denoising_steps > 0, "Invalid GPU or denoising steps")
    require(np.isfinite(args.constraint_cfg) and args.constraint_cfg > 0, "Invalid constraint CFG")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)

    os.environ["MUSA_VISIBLE_DEVICES"] = str(args.physical_gpu)
    os.environ["CUDA_VISIBLE_DEVICES"] = str(args.physical_gpu)
    os.environ.update(TEXT_ENCODER_MODE="local", TEXT_ENCODER_DEVICE="cpu", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    request, frames, requested_fps, constraints, codec, record = validate_and_load(args.request, args.pose_constraints)
    if args.validate_only:
        write_json(output / "validation_only.json", {"valid": True, "frames": frames, "constraint_count": len(record["frame_indices"])})
        return 0

    import torch
    import torch_musa  # noqa: F401 - initializes MUSA integration
    import kimodo
    from kimodo import load_model
    from kimodo.motion_rep.conditioning import build_condition_dicts
    kimodo_path = Path(kimodo.__file__).resolve()
    require(EXPECTED_PACKAGE in kimodo_path.parents or kimodo_path.parent == EXPECTED_PACKAGE, f"Wrong Kimodo checkout: {kimodo_path}")
    require(torch.musa.is_available(), "MUSA is unavailable")
    indices, values = build_condition_dicts(constraints)
    for key, entries in indices.items():
        for value in entries:
            frame_index = value[:, 0] if value.ndim == 2 else value
            require(value.dtype == torch.long and bool(torch.all((frame_index >= 0) & (frame_index < frames))), f"Invalid {key} indices")
    for key, entries in values.items():
        for value in entries:
            require(bool(torch.isfinite(value).all()), f"Nonfinite {key} values")

    started = time.monotonic()
    print("Loading real Kimodo G1 checkpoint and local CPU text encoder", flush=True)
    model, resolved = load_model("g1", device="musa:0", return_resolved_name=True)
    model_load_seconds = time.monotonic() - started
    actual_fps = float(model.fps)
    require(abs(actual_fps - requested_fps) <= 1e-12, f"Request fps {requested_fps} != model fps {actual_fps}")
    for constraint in constraints:
        constraint.to(device="musa:0")
    torch.manual_seed(request["seed"])
    torch.musa.manual_seed_all(request["seed"])
    np.random.seed(request["seed"])
    print(f"Running one native Kimodo inference: {frames} frames at {actual_fps:g} Hz", flush=True)
    inference_started = time.monotonic()
    with torch.inference_mode():
        raw = model(
            request["prompt"], frames, num_denoising_steps=args.denoising_steps,
            constraint_lst=constraints, cfg_weight=[2.0, args.constraint_cfg],
            multi_prompt=False, post_processing=False, return_numpy=True,
        )
    inference_seconds = time.monotonic() - inference_started
    raw = {key: np.asarray(value) for key, value in raw.items()}
    require(raw, "Kimodo returned no fields")
    for key, value in raw.items():
        require(value.shape[0] == frames, f"Unexpected {key} shape: {value.shape}")
        require(np.isfinite(value).all(), f"Nonfinite values in {key}")
    raw_path = output / "raw_motion.npz"
    np.savez_compressed(raw_path, **raw)

    vectors = frame_vectors(raw)
    exact_adjacent_duplicate = np.all(vectors[1:] == vectors[:-1], axis=1)
    duplicate_count = int(exact_adjacent_duplicate.sum())
    duplicate_tail = bool(exact_adjacent_duplicate[-1])
    constant_tail = bool(np.max(np.abs(np.diff(vectors[-30:], axis=0))) <= 1e-12)
    actual_last = (frames - 1) / actual_fps
    raw_fields = {key: {"shape": list(value.shape), "dtype": str(value.dtype)} for key, value in raw.items()}
    generation = {
        "contract_version": CONTRACT,
        "real_model_run": True,
        "fixture_used": bool(request.get("fixture_only", False)),
        "final_grasp_run": not bool(request.get("fixture_only", False)),
        "prompt": request["prompt"],
        "seed": request["seed"],
        "requested_duration_sec": float(request["requested_duration_sec"]),
        "actual_fps": actual_fps,
        "actual_frames": frames,
        "actual_first_timestamp": 0.0,
        "actual_last_timestamp": actual_last,
        "actual_duration_sec": actual_last,
        "device": "musa:0",
        "physical_gpu": args.physical_gpu,
        "model": "Kimodo-G1-RP-v1",
        "resolved_model": resolved,
        "checkpoint": str(CHECKPOINT),
        "checkpoint_hashes": {name: sha256(CHECKPOINT / name) for name in ("config.yaml", "model.safetensors")},
        "python": sys.executable,
        "kimodo_package": str(kimodo_path),
        "model_load_seconds": model_load_seconds,
        "inference_seconds": inference_seconds,
        "total_wall_seconds": time.monotonic() - started,
        "num_denoising_steps": args.denoising_steps,
        "cfg_weight": [2.0, args.constraint_cfg],
        "post_processing": False,
        "segmentation_required": False,
        "segments": [{
            "segment_id": 0, "request_start_s": 0.0, "request_end_s": float(request["requested_duration_sec"]),
            "conditioning_start_frame": int(record["frame_indices"][0]),
            "conditioning_end_frame": int(record["frame_indices"][-1]),
            "actual_generated_frames": frames, "actual_fps": actual_fps,
            "actual_first_timestamp": 0.0, "actual_last_timestamp": actual_last,
            "overlap_size": 0, "overlap_handling_method": "not_applicable_single_native_generation",
        }],
        "raw_fields": raw_fields,
        "raw_motion_sha256": sha256(raw_path),
    }
    metrics = {
        "constraint_count": len(record["frame_indices"]),
        "constraint_timestamps": [frame / actual_fps for frame in record["frame_indices"]],
        "loaded_constraint_count": len(constraints),
        "finite": bool(all(np.isfinite(value).all() for value in raw.values())),
        "timestamp_monotonicity": True,
        "generated_duration": actual_last,
        "generated_frames": frames,
        "duplicate_frames": duplicate_count,
        "duplicate_tail": duplicate_tail,
        "constant_tail": constant_tail,
        "segment_boundary_jump": "not_applicable_single_native_generation",
        "first_frame_continuity": float(np.max(np.abs(vectors[1] - vectors[0]))),
        "last_frame_continuity": float(np.max(np.abs(vectors[-1] - vectors[-2]))),
        "conditioning_error": "not_computable_from_available_output",
        "coordinate_validation": codec,
    }
    write_json(output / "generation.json", generation)
    write_json(output / "conditioning_metrics.json", metrics)
    write_json(output / "runtime_api_report.json", api_report(model, resolved, kimodo_path))
    print(json.dumps({"real_model_run": True, "frames": frames, "duration": actual_last, "raw_motion": str(raw_path)}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
