from __future__ import annotations

import hashlib
import json
from pathlib import Path

from contracts.reference import ReferenceBundle, validate_reference


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "test_reference" / "golden_ardy"


def test_golden_reference_checksum_and_contract() -> None:
    digest = hashlib.sha256((GOLDEN / "reference.npz").read_bytes()).hexdigest()
    assert digest == "e16dc4b3125a0a611e15a0b555b9164ec268e71d63d44c70aba96d3b7608e053"
    bundle = ReferenceBundle.load(GOLDEN)
    assert bundle.arrays["time_s"].shape == (810,)
    assert validate_reference(bundle, mode="dry-run").overall == "PASS"


def test_golden_evidence_keeps_contact_limitation() -> None:
    source = json.loads((GOLDEN / "reference_validation.json").read_text())
    task = json.loads((GOLDEN / "task_validation.json").read_text())
    assert source["status"] == "ACCEPT_REFERENCE"
    assert source["physical_success"] is True
    assert task["strict_no_table_expert_valid"] is False
    assert task["robot_table_contact_steps"] == 26
    assert task["robot_table_contact_duration_s"] == 0.13
    assert task["classification"] == "development_tuned_ARDY_pipeline; not raw-model zero-shot score"
