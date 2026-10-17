from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from adapters.motion import qpos_to_canonical_arrays
from inference.common import ensure_batch_one, resolve_project_path


def test_qpos_adapter_produces_canonical_motion() -> None:
    qpos = np.zeros((4, 36), dtype=np.float32)
    qpos[:, 3] = 1.0
    hand = np.zeros((4, 14), dtype=np.float32)
    arrays = qpos_to_canonical_arrays(qpos, hand, source_hz=25, target_hz=50)
    assert arrays["body_ref_q"].shape == (7, 29)
    assert arrays["body_ref_dq"].shape == (7, 29)
    assert arrays["root_ref_quat"].shape == (7, 4)
    assert np.allclose(np.diff(arrays["time_s"]), 0.02)


def test_batch_must_be_one() -> None:
    ensure_batch_one(1)
    with pytest.raises(ValueError, match="batch=1"):
        ensure_batch_one(2)


def test_runtime_paths_are_relative_to_project(tmp_path: Path) -> None:
    assert resolve_project_path(tmp_path, "models/x") == tmp_path / "models/x"
    with pytest.raises(ValueError, match="relative"):
        resolve_project_path(tmp_path, "/home/group2/model")
