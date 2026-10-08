#!/usr/bin/env bash
set -uo pipefail

WORKDIR=/workspace/group2/handoffs/kimodo_parallel_v2/role_B_20261007T170600_CST
PYTHON=/workspace/group2/workspace/amy/kimodo-work/.venv/bin/python

export GIT_CONFIG_COUNT=2
export GIT_CONFIG_KEY_0=safe.directory
export GIT_CONFIG_VALUE_0=/workspace/group2/dl-group2
export GIT_CONFIG_KEY_1=safe.directory
export GIT_CONFIG_VALUE_1=/workspace/group2/GR00T-WholeBodyControl
source /workspace/group2/kimodo-t6/g1-integration/activate-g1.sh
cd "$WORKDIR"

"$PYTHON" -B code/build_fixture.py "$WORKDIR/fixtures" 2>&1 | tee logs/build_fixture.log
status=${PIPESTATUS[0]}
if [ "$status" -ne 0 ]; then exit "$status"; fi

KIMODO_PHYSICAL_GPU=1 "$PYTHON" -B code/generate_kimodo.py \
  --request "$WORKDIR/fixtures/fixture_generation_request.json" \
  --pose-constraints "$WORKDIR/fixtures/fixture_pose_constraints.json" \
  --output-dir "$WORKDIR/artifacts/fixture_run" \
  2>&1 | tee logs/generation.log
status=${PIPESTATUS[0]}
if [ "$status" -ne 0 ]; then exit "$status"; fi

"$PYTHON" -B code/test_role_b.py "$WORKDIR" 2>&1 | tee logs/tests.log
test_status=${PIPESTATUS[0]}

"$PYTHON" -B code/finalize_role_b.py "$WORKDIR" 2>&1 | tee logs/finalize.log
finalize_status=${PIPESTATUS[0]}

if [ "$test_status" -ne 0 ]; then exit "$test_status"; fi
exit "$finalize_status"
