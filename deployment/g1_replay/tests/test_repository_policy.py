from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_gitignore_blocks_runtime_and_sensitive_artifacts() -> None:
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    required = [
        "*.pt",
        "*.pth",
        "*.safetensors",
        "*.onnx",
        "*.npz",
        "datasets/",
        "videos/",
        "outputs/",
        "logs/",
        ".env",
        "*.pem",
        "*.key",
        "__pycache__/",
        ".pytest_cache/",
    ]
    for pattern in required:
        assert pattern in text, f"missing protective ignore rule: {pattern}"
    assert "!test_reference/golden_ardy/reference.npz" in text


def test_no_forbidden_or_oversized_repository_files() -> None:
    forbidden = {".pt", ".pth", ".safetensors", ".onnx", ".mp4", ".avi", ".zip", ".tar", ".so"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        assert path.suffix.lower() not in forbidden, f"forbidden artifact in repository: {path}"
        assert path.stat().st_size <= 10 * 1024 * 1024, f"file exceeds 10 MiB: {path}"
