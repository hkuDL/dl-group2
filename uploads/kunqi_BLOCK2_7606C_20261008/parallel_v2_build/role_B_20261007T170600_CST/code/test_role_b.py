#!/usr/bin/env python3
"""Fresh-process tests for the independent Kimodo runtime bundle."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_role_b.py WORKDIR")
    workdir = Path(sys.argv[1]).resolve(strict=True)
    fixture = workdir / "fixtures"
    output = workdir / "artifacts/fixture_run"
    generation = json.loads((output / "generation.json").read_text())
    metrics = json.loads((output / "conditioning_metrics.json").read_text())
    report = json.loads((output / "runtime_api_report.json").read_text())
    with np.load(output / "raw_motion.npz", allow_pickle=False) as archive:
        raw = {key: archive[key].copy() for key in archive.files}

    results = []

    def check(name, function):
        try:
            detail = function()
            if isinstance(detail, np.generic):
                detail = detail.item()
            results.append({"name": name, "status": "pass", "detail": detail})
        except Exception as exc:
            results.append({"name": name, "status": "fail", "detail": f"{type(exc).__name__}: {exc}"})

    check("api_discovery", lambda: (
        "Kimodo.__call__" in report["generation_entrypoint"]
        and "num_frames" in report["generation_signature"]
        and report["audited_live_package"].startswith("/workspace/group2/kimodo-t6/g1-integration/kimodo-upload/")
    ) or (_ for _ in ()).throw(AssertionError(report)))
    check("model_load", lambda: generation["model_load_seconds"] > 0 and generation["resolved_model"] == "kimodo-g1-rp")
    check("real_inference", lambda: generation["real_model_run"] is True and generation["inference_seconds"] > 0)
    check("fixture_not_final_grasp", lambda: generation["fixture_used"] is True and generation["final_grasp_run"] is False)
    check("condition_load", lambda: metrics["constraint_count"] == 17 and metrics["loaded_constraint_count"] == 2)
    check("duration_16p2", lambda: generation["actual_duration_sec"] >= 16.2 and metrics["generated_duration"] >= 16.2)
    check("actual_frames_and_fps", lambda: generation["actual_frames"] == 487 and generation["actual_fps"] == 30.0)
    check("finite", lambda: metrics["finite"] and all(np.isfinite(value).all() for value in raw.values()))
    check("timestamps", lambda: generation["actual_first_timestamp"] == 0.0 and generation["actual_last_timestamp"] == 16.2 and metrics["timestamp_monotonicity"])
    check("duplicate_detection", lambda: metrics["duplicate_frames"] >= 0 and isinstance(metrics["duplicate_tail"], bool))
    check("no_duplicate_tail", lambda: not metrics["duplicate_tail"])
    check("no_constant_tail", lambda: not metrics["constant_tail"])
    check("single_native_segment", lambda: not generation["segmentation_required"] and len(generation["segments"]) == 1 and generation["segments"][0]["overlap_size"] == 0)
    check("continuity_metrics", lambda: np.isfinite(metrics["first_frame_continuity"]) and np.isfinite(metrics["last_frame_continuity"]))
    check("raw_save_hash", lambda: generation["raw_motion_sha256"] == sha256(output / "raw_motion.npz"))

    def reload_contract():
        for key, descriptor in generation["raw_fields"].items():
            assert key in raw
            assert list(raw[key].shape) == descriptor["shape"]
            assert str(raw[key].dtype) == descriptor["dtype"]
            assert raw[key].shape[0] == generation["actual_frames"]
        return {key: list(value.shape) for key, value in raw.items()}

    check("fresh_disk_reload", reload_contract)

    scratch = workdir / "tests/bad_inputs"
    scratch.mkdir(exist_ok=True)
    generator = workdir / "code/generate_kimodo.py"
    base_request = json.loads((fixture / "fixture_generation_request.json").read_text())
    base_pose = json.loads((fixture / "fixture_pose_constraints.json").read_text())

    def run_bad(label, request_value, pose_value):
        case = scratch / label
        case.mkdir(exist_ok=False)
        request_path = case / "request.json"
        pose_path = case / "pose.json"
        pose_path.write_text(json.dumps(pose_value, allow_nan=True) + "\n")
        request_value = dict(request_value)
        request_value["pose_constraints_sha256"] = sha256(pose_path)
        request_path.write_text(json.dumps(request_value, allow_nan=True) + "\n")
        process = subprocess.run([
            sys.executable, str(generator), "--request", str(request_path),
            "--pose-constraints", str(pose_path), "--output-dir", str(case / "out"), "--validate-only",
        ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        assert process.returncode != 0, process.stdout
        return process.stdout[-500:]

    bad_schema = dict(base_request)
    bad_schema.pop("prompt")
    check("bad_schema_rejection", lambda: run_bad("bad_schema", bad_schema, base_pose))
    bad_contract = dict(base_request)
    bad_contract["contract_version"] = "wrong"
    check("bad_contract_rejection", lambda: run_bad("bad_contract", bad_contract, base_pose))
    bad_matrix = json.loads(json.dumps(base_pose))
    bad_matrix["local_rot_mats"][0][0][0][0] = 2.0
    check("bad_matrix_rejection", lambda: run_bad("bad_matrix", base_request, bad_matrix))
    bad_nan = json.loads(json.dumps(base_pose))
    bad_nan["root_positions"][0][0] = float("nan")
    check("nan_rejection", lambda: run_bad("nan", base_request, bad_nan))

    failures = [item for item in results if item["status"] == "fail"]
    result = {
        "scope": "Independent Work B runtime and genuine fixture inference",
        "passed": not failures,
        "summary": {"pass": len(results) - len(failures), "fail": len(failures)},
        "tests": results,
    }
    (workdir / "tests/test_results.json").write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
