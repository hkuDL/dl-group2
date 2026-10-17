from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from contracts.reference import ReferenceBundle, validate_reference


BODY = [f"body_{i}" for i in range(29)]
HAND = [f"hand_{i}" for i in range(14)]


def _fixture(tmp_path: Path, *, frames: int = 5) -> Path:
    time_s = np.arange(frames, dtype=np.float64) / 50.0
    np.savez(
        tmp_path / "reference.npz",
        time_s=time_s,
        body_ref_q=np.zeros((frames, 29)),
        body_ref_dq=np.zeros((frames, 29)),
        hand_ref_q=np.zeros((frames, 14)),
        root_ref_pos=np.zeros((frames, 3)),
        root_ref_quat=np.tile([1.0, 0.0, 0.0, 0.0], (frames, 1)),
    )
    (tmp_path / "metadata.json").write_text(
        json.dumps(
            {
                "producer_type": "ardy",
                "reference_hz": 50,
                "quaternion_convention": "wxyz",
                "root_pose_frame": "world",
                "units": {
                    "time_s": "s",
                    "body_ref_q": "rad",
                    "body_ref_dq": "rad/s",
                    "root_ref_pos": "m",
                    "root_ref_quat": "unitless",
                    "hand_ref_q": "rad",
                },
                "body_joint_names": BODY,
                "hand_joint_names": HAND,
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_valid_dry_run_contract(tmp_path: Path) -> None:
    bundle = ReferenceBundle.load(_fixture(tmp_path))
    report = validate_reference(bundle, mode="dry-run")
    assert report.overall == "PASS"
    assert report.checks["robot_safety"] == "NOT_EVALUATED"


def test_rejects_wrong_shape_and_nonfinite(tmp_path: Path) -> None:
    path = _fixture(tmp_path)
    with np.load(path / "reference.npz") as z:
        arrays = {k: z[k] for k in z.files}
    arrays["body_ref_q"] = np.zeros((5, 28))
    arrays["hand_ref_q"][0, 0] = np.nan
    np.savez(path / "reference.npz", **arrays)
    report = validate_reference(ReferenceBundle.load(path), mode="dry-run")
    assert report.overall == "FAIL"
    assert report.checks["shape"] == "FAIL"
    assert report.checks["finite"] == "FAIL"


def test_real_mode_fails_closed_without_site_values(tmp_path: Path) -> None:
    report = validate_reference(ReferenceBundle.load(_fixture(tmp_path)), mode="real")
    assert report.overall == "FAIL"
    assert report.checks["robot_safety"] == "FAIL"

