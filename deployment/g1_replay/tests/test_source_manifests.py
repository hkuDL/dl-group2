from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    return json.loads((ROOT / "manifests" / name).read_text(encoding="utf-8"))


def test_source_commits_are_pinned() -> None:
    data = _load("SOURCE_COMMITS.json")
    assert data["ardy"]["commit"] == "693f74d13b3d04a0a22ce127ee79c929dd89756b"
    assert data["ardy"]["origin"] == "https://github.com/nv-tlabs/ardy.git"
    assert data["sonic"]["commit"] == "39ea4bc6feffc72a752dff3766e38edd910524f1"
    assert data["sonic"]["base_commit"] == "b042411fae38ee4d1af9aac82a37a1f8d14d6dd0"
    assert data["sonic"]["result_tree"] == "606f1101ff1aa03b5b498842f520499b225d475b"
    assert data["sonic"]["remote_contains_commit"] is False


def test_every_source_record_has_audit_fields() -> None:
    records = _load("SOURCE_FILES.json")
    assert records
    for record in records:
        assert set(record) >= {"component", "source_path", "sha256", "disposition", "license"}
        assert len(record["sha256"]) == 64
        assert record["disposition"] in {"rewritten", "interface_evidence", "manifest_only", "fixture"}


def test_model_weights_are_manifest_only() -> None:
    data = json.loads((ROOT / "models" / "model_requirements.json").read_text(encoding="utf-8"))
    assert {entry["model"] for entry in data["weights"]} == {"kimodo", "ardy_denoiser", "ardy_tokenizer", "va_v4_1"}
    assert all(entry["git_policy"] == "never_commit" for entry in data["weights"])
    assert all(not entry["install_path"].startswith("/") for entry in data["weights"])
