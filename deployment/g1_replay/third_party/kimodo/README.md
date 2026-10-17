# Kimodo inference runtime snapshot

This is the minimum Apache-2.0 Python runtime imported from the audited S4000 snapshot `kimodo-t6/g1-integration/kimodo-upload`. Demo, visualization, metrics, conversion CLIs, meshes, example motions, MotionCorrection, training outputs and checkpoints are excluded.

`kimodo/exports/__init__.py` is intentionally narrowed to the G1 kinematic converter so importing it does not pull visualization/AMASS dependencies. The model checkpoint remains external under its own NVIDIA model terms.

