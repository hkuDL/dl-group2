#!/usr/bin/env bash
set -uo pipefail

WORKDIR=/workspace/group2/handoffs/kimodo_parallel_v2/role_C_20261007T172000_CST
PYTHON=/workspace/group2/workspace/amy/kimodo-work/.venv/bin/python
INCLUDE=/workspace/group2/GR00T-WholeBodyControl/gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/include

export GIT_CONFIG_COUNT=2
export GIT_CONFIG_KEY_0=safe.directory
export GIT_CONFIG_VALUE_0=/workspace/group2/dl-group2
export GIT_CONFIG_KEY_1=safe.directory
export GIT_CONFIG_VALUE_1=/workspace/group2/GR00T-WholeBodyControl
export SONIC_REPO=/workspace/group2/GR00T-WholeBodyControl
source /workspace/group2/workspace/amy/kimodo-work/.venv/bin/activate
cd "$WORKDIR"

"$PYTHON" -B code/build_fixtures.py "$WORKDIR/fixtures" 2>&1 | tee logs/build_fixtures.log
status=${PIPESTATUS[0]}
if [ "$status" -ne 0 ]; then exit "$status"; fi

"$PYTHON" -B code/assemble_sonic_reference.py \
  --body-reference "$WORKDIR/fixtures/body_reference_fixture.npz" \
  --task-plan "$WORKDIR/fixtures/task_plan_fixture.npz" \
  --output-dir "$WORKDIR/artifacts/fixture_reference" \
  2>&1 | tee logs/assemble.log
status=${PIPESTATUS[0]}
if [ "$status" -ne 0 ]; then exit "$status"; fi

g++ -std=c++17 -O2 code/sonic_loader_probe.cpp -I"$INCLUDE" -I/usr/include/eigen3 \
  -o tests/sonic_loader_probe 2>&1 | tee logs/compile_loader_probe.log
status=${PIPESTATUS[0]}
if [ "$status" -ne 0 ]; then exit "$status"; fi

"$PYTHON" -B code/test_role_c.py "$WORKDIR" 2>&1 | tee logs/tests.log
test_status=${PIPESTATUS[0]}

"$PYTHON" -B code/finalize_role_c.py "$WORKDIR" 2>&1 | tee logs/finalize.log
finalize_status=${PIPESTATUS[0]}

if [ "$test_status" -ne 0 ]; then exit "$test_status"; fi
exit "$finalize_status"
