#!/usr/bin/env bash
set -uo pipefail

WORKDIR=/workspace/group2/handoffs/kimodo_parallel/role_A_20261007T162500_CST
PYTHON=/workspace/group2/workspace/amy/kimodo-work/.venv/bin/python

source /workspace/group2/kimodo-t6/g1-integration/activate-g1.sh
cd "$WORKDIR"
mkdir -p logs tests

"$PYTHON" -B code/prepare_grasp_task.py \
  --case center \
  --seed 0 \
  --duration 16.2 \
  --output "$WORKDIR/artifacts" \
  2>&1 | tee logs/prepare.log
prepare_status=${PIPESTATUS[0]}
if [ "$prepare_status" -ne 0 ]; then
  exit "$prepare_status"
fi

"$PYTHON" -B code/verify_role_a.py --workdir "$WORKDIR" 2>&1 | tee logs/verify.log
verify_status=${PIPESTATUS[0]}

"$PYTHON" -B code/finalize_handoff.py --workdir "$WORKDIR" 2>&1 | tee logs/finalize.log
finalize_status=${PIPESTATUS[0]}

if [ "$verify_status" -ne 0 ]; then
  exit "$verify_status"
fi
exit "$finalize_status"
