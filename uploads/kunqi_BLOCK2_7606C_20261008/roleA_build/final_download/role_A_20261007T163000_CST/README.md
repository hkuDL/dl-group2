# Kimodo Role A handoff

Status: `ready_for_integration`  
Contract: `kimodo_parallel_20261007_v1`

This bundle is real canonical CPU task/IK/hand planning. It is not a fixture. It does not claim Kimodo generation, SONIC replay, physical success, or expert validity.

## Exact runtime

Python: `/workspace/group2/workspace/amy/kimodo-work/.venv/bin/python`

Activation: `/workspace/group2/kimodo-t6/g1-integration/activate-g1.sh`

Exact one-shot command:

```bash
bash /workspace/group2/handoffs/kimodo_parallel/role_A_20261007T163000_CST/run_role_a.sh
```

The command is single-use because artifact creation refuses to overwrite an existing directory.

## Inputs

- Canonical project: `/workspace/group2/dl-group2`
- Robot XML: `/workspace/group2/GR00T-WholeBodyControl/decoupled_wbc/control/robot_model/model_data/g1/g1_29dof_with_hand_rev_1_0_activatedfinger.xml`
- Scene XML: `/workspace/group2/dl-group2/scenes/tabletop.xml`
- Existing matrix coordinate repair: `/workspace/group2/kimodo-t6/g1-integration/coordinate-repair-20261007-v2`
- Case/seed/hand: `center / 0 / right`

No old ARDY trajectory, old hand plan, old object trajectory, or old frame schedule is consumed.

## Outputs and shapes

- `artifacts/task.json`: task contract, paths, orders, hashes, phases.
- `artifacts/task_plan.npz`:
  - `source_timestamps`: `(487,)` at 30 Hz, covering 16.2 s.
  - `source_qpos`: `(487, 36)` root7 + Kimodo-XML body29.
  - `canonical_wrist_world_pos`: `(487, 2, 3)`, wrist order left/right.
  - `canonical_wrist_world_quat`: `(487, 2, 4)`, wxyz.
  - `timestamps`: `(810,)` at 50 Hz, 0.00 through 16.18 s.
  - `hand_ref_q`, `hand_ref_dq`: `(810, 14)` in canonical hand order.
- `artifacts/pose_constraints.json`: matrix-preserving Kimodo constraint record, saved and freshly reloaded.
- `artifacts/planning_metrics.json`: measured IK, limits, initial-state and codec errors.

## Verification

Fresh-process verification:

```bash
source /workspace/group2/kimodo-t6/g1-integration/activate-g1.sh
cd /workspace/group2/handoffs/kimodo_parallel/role_A_20261007T163000_CST
python code/verify_role_a.py --workdir /workspace/group2/handoffs/kimodo_parallel/role_A_20261007T163000_CST
```

Results: `/workspace/group2/handoffs/kimodo_parallel/role_A_20261007T163000_CST/tests/test_results.json`

## Downstream contract

Role B consumes `task.json`, `task_plan.npz`, and `pose_constraints.json`. It must use `load_pose_constraints()` from the v2 matrix codec and record real Kimodo generation separately.

Role C consumes `task.json`, `task_plan.npz`, and Role B's generated Kimodo NPZ. It must preserve the canonical body/hand orders and 50 Hz timeline; Role A's `source_qpos` is task conditioning, not generated output.

## Real versus unresolved

Real: canonical scene reset, neutral initial state, 16.2 s phase planner, right-wrist IK, newly generated hand14 plan, matrix codec save/reload and SHA checks.

Unresolved: real Kimodo generation, canonical generated-reference export, SONIC replay and physical success. See `pending.md`.
