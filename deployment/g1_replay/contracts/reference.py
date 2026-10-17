"""Canonical replay reference contract used by Kimodo and ARDY outputs.

This module validates data only. A schema PASS is deliberately not named or
treated as approval for robot motion.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import numpy as np


REQUIRED_SHAPES = {
    "time_s": (None,),
    "body_ref_q": (None, 29),
    "body_ref_dq": (None, 29),
    "hand_ref_q": (None, 14),
    "root_ref_pos": (None, 3),
    "root_ref_quat": (None, 4),
}
EXPECTED_UNITS = {
    "time_s": "s",
    "body_ref_q": "rad",
    "body_ref_dq": "rad/s",
    "root_ref_pos": "m",
    "root_ref_quat": "unitless",
    "hand_ref_q": "rad",
}
PRODUCERS = {"kimodo", "ardy"}


@dataclass(frozen=True)
class ReferenceBundle:
    arrays: Mapping[str, np.ndarray]
    metadata: Mapping[str, Any]
    root: Path

    @classmethod
    def load(cls, root: Path | str) -> "ReferenceBundle":
        root = Path(root)
        with np.load(root / "reference.npz", allow_pickle=False) as archive:
            arrays = {name: np.array(archive[name], copy=True) for name in archive.files}
        metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
        return cls(arrays=arrays, metadata=metadata, root=root)


@dataclass(frozen=True)
class ValidationReport:
    overall: str
    checks: Mapping[str, str]
    details: Mapping[str, str]

    def as_dict(self) -> Dict[str, Any]:
        return {"overall": self.overall, "checks": dict(self.checks), "details": dict(self.details)}


def _shape_ok(arrays: Mapping[str, np.ndarray]) -> bool:
    if not set(REQUIRED_SHAPES).issubset(arrays):
        return False
    frames = arrays["time_s"].shape[0] if arrays["time_s"].ndim == 1 else -1
    return frames > 0 and all(
        arrays[name].shape == tuple(frames if dim is None else dim for dim in expected)
        for name, expected in REQUIRED_SHAPES.items()
    )


def validate_reference(
    bundle: ReferenceBundle,
    *,
    mode: str = "dry-run",
    safety_config: Optional[Mapping[str, Any]] = None,
    current_pose: Optional[np.ndarray] = None,
) -> ValidationReport:
    if mode not in {"dry-run", "real"}:
        raise ValueError("mode must be 'dry-run' or 'real'")

    arrays, meta = bundle.arrays, bundle.metadata
    checks: Dict[str, str] = {}
    details: Dict[str, str] = {}

    shape_ok = _shape_ok(arrays)
    checks["shape"] = "PASS" if shape_ok else "FAIL"
    details["shape"] = "required [T], [T,29], [T,14], [T,3], [T,4] arrays"

    finite_ok = bool(arrays) and all(np.issubdtype(value.dtype, np.number) and np.isfinite(value).all() for value in arrays.values())
    checks["finite"] = "PASS" if finite_ok else "FAIL"

    time_ok = False
    if shape_ok:
        time_s = arrays["time_s"]
        delta = np.diff(time_s)
        time_ok = bool(np.isclose(time_s[0], 0.0, atol=1e-9) and np.all(delta > 0) and np.allclose(delta, 0.02, atol=1e-6, rtol=0))
    checks["clock_50hz"] = "PASS" if time_ok else "FAIL"

    quat_ok = False
    if shape_ok and finite_ok:
        quat_ok = bool(np.allclose(np.linalg.norm(arrays["root_ref_quat"], axis=1), 1.0, atol=1e-3))
    checks["quaternion_norm"] = "PASS" if quat_ok else "FAIL"

    metadata_ok = (
        meta.get("producer_type") in PRODUCERS
        and meta.get("reference_hz") == 50
        and meta.get("quaternion_convention") == "wxyz"
        and meta.get("root_pose_frame") == "world"
        and meta.get("units") == EXPECTED_UNITS
        and len(meta.get("body_joint_names", [])) == 29
        and len(meta.get("hand_joint_names", [])) == 14
        and len(set(meta.get("body_joint_names", []))) == 29
        and len(set(meta.get("hand_joint_names", []))) == 14
    )
    checks["metadata"] = "PASS" if metadata_ok else "FAIL"

    if mode == "dry-run":
        checks["robot_safety"] = "NOT_EVALUATED"
        details["robot_safety"] = "dry-run validates the artifact only; it is not approval for robot motion"
    else:
        required_site_keys = {"body_step_limit_rad", "hand_step_limit_rad", "approved_joint_order", "operator_acknowledged"}
        configured = safety_config is not None and required_site_keys.issubset(safety_config)
        pose_ok = current_pose is not None and np.asarray(current_pose).shape == (29,)
        checks["robot_safety"] = "PASS" if configured and pose_ok and bool(safety_config["operator_acknowledged"]) else "FAIL"
        details["robot_safety"] = "real mode requires site limits, approved joint order, operator acknowledgement and current [29] pose"

    overall = "FAIL" if "FAIL" in checks.values() else "PASS"
    return ValidationReport(overall=overall, checks=checks, details=details)

