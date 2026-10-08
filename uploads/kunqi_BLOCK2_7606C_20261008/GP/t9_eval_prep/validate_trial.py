#!/usr/bin/env python3
"""Validate Task 9 ARDY/Kimodo TrialLog records.

The validator intentionally uses only the Python standard library. It checks
record structure, provenance, and internal consistency. It does not rerun the
physics evaluator and therefore cannot independently certify task success.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


SCHEMA_PATH = Path(__file__).with_name("trial_schema.json")
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
TOP_LEVEL_REQUIRED = tuple(SCHEMA["required"])
TOP_LEVEL_ALLOWED = frozenset(SCHEMA["properties"])

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
METHODS = {"ardy", "kimodo"}
RUN_TYPES = {"not_final_smoke", "pilot", "formal"}
ARMS = {"left", "right", "unspecified"}
CONDITIONING = {
    "text_only",
    "text_and_object_pose",
    "expert_sparse",
    "expert_dense",
    "other",
}
RUNTIME_FAILURES = {
    "reset_error",
    "generation_timeout",
    "generation_error",
    "invalid_reference",
    "adapter_error",
    "sonic_startup_error",
    "sonic_runtime_error",
    "hand_control_error",
    "execution_timeout",
    "logging_error",
    "unknown",
}
TASK_FAILURES = {
    "missed_object",
    "object_slip",
    "insufficient_lift",
    "insufficient_hold",
}
SAFETY_FAILURES = {"robot_fall", "unsafe_collision", "joint_limit_violation"}
FAILURE_PHASES = {"reset", "generate", "adapter", "reach", "grasp", "lift", "hold"}


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant is forbidden: {value}")


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _mapping(value: Any, path: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{path}: expected object")
        return {}
    return value


def _required(obj: dict[str, Any], keys: Iterable[str], path: str, errors: list[str]) -> None:
    for key in keys:
        if key not in obj:
            errors.append(f"{path}.{key}: missing required field")


def _check_sha256(value: Any, path: str, errors: list[str], *, allow_null: bool = True) -> None:
    if value is None and allow_null:
        return
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        errors.append(f"{path}: expected lowercase 64-character SHA-256 or null")


def _check_git_sha(value: Any, path: str, errors: list[str], *, allow_null: bool = True) -> None:
    if value is None and allow_null:
        return
    if not isinstance(value, str) or not GIT_SHA_RE.fullmatch(value):
        errors.append(f"{path}: expected lowercase full 40-character Git SHA or null")


def _check_vector(value: Any, size: int, path: str, errors: list[str]) -> None:
    if not isinstance(value, list) or len(value) != size:
        errors.append(f"{path}: expected {size}-element numeric array")
        return
    for index, item in enumerate(value):
        if not _is_number(item):
            errors.append(f"{path}[{index}]: expected finite number")


def _check_nonnegative_number(value: Any, path: str, errors: list[str], *, allow_null: bool = True) -> None:
    if value is None and allow_null:
        return
    if not _is_number(value) or float(value) < 0:
        errors.append(f"{path}: expected non-negative finite number")


def _check_nonnegative_int(value: Any, path: str, errors: list[str], *, allow_null: bool = True) -> None:
    if value is None and allow_null:
        return
    if not _is_int(value) or value < 0:
        errors.append(f"{path}: expected non-negative integer")


def _check_utc(value: Any, path: str, errors: list[str], *, allow_null: bool = True) -> None:
    if value is None and allow_null:
        return
    if not isinstance(value, str) or not value.endswith("Z"):
        errors.append(f"{path}: expected RFC3339 UTC timestamp ending in Z")
        return
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        errors.append(f"{path}: invalid RFC3339 UTC timestamp")
        return
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        errors.append(f"{path}: timestamp must be UTC")


def _check_environment(value: Any, path: str, errors: list[str], *, formal: bool) -> None:
    env = _mapping(value, path, errors)
    keys = ("host", "host_class", "accelerator_model", "container_digest", "runtime_versions")
    _required(env, keys, path, errors)
    if formal:
        if not _is_nonempty_string(env.get("host_class")):
            errors.append(f"{path}.host_class: required for formal trial")
        if not _is_nonempty_string(env.get("container_digest")):
            errors.append(f"{path}.container_digest: required for formal trial")
        versions = env.get("runtime_versions")
        if not isinstance(versions, dict) or not versions:
            errors.append(f"{path}.runtime_versions: non-empty object required for formal trial")
    elif "runtime_versions" in env and not isinstance(env.get("runtime_versions"), dict):
        errors.append(f"{path}.runtime_versions: expected object")


def validate_trial(record: Any, *, require_formal: bool = False) -> list[str]:
    """Return human-readable validation errors for one TrialLog record."""

    errors: list[str] = []
    if not isinstance(record, dict):
        return ["$: expected JSON object"]

    _required(record, TOP_LEVEL_REQUIRED, "$", errors)
    for key in sorted(set(record) - TOP_LEVEL_ALLOWED):
        errors.append(f"$.{key}: unknown top-level field")

    if record.get("schema_version") != "t9_trial_v0.1":
        errors.append("$.schema_version: expected t9_trial_v0.1")
    if record.get("protocol_version") != "t9_eval_v0.2":
        errors.append("$.protocol_version: expected t9_eval_v0.2")
    if not _is_nonempty_string(record.get("run_id")):
        errors.append("$.run_id: expected non-empty string")

    run_type = record.get("run_type")
    if run_type not in RUN_TYPES:
        errors.append(f"$.run_type: expected one of {sorted(RUN_TYPES)}")
    formal = run_type == "formal"
    if require_formal and not formal:
        errors.append("$.run_type: --require-formal accepts only formal records")

    formal_score = record.get("formal_score")
    if not isinstance(formal_score, bool):
        errors.append("$.formal_score: expected boolean")
    elif formal_score != formal:
        errors.append("$.formal_score: must be true exactly when run_type=formal")

    if record.get("method") not in METHODS:
        errors.append(f"$.method: expected one of {sorted(METHODS)}")
    if record.get("task") != "grasp_and_lift":
        errors.append("$.task: expected grasp_and_lift")

    if record.get("batch_id") is not None and not _is_nonempty_string(record.get("batch_id")):
        errors.append("$.batch_id: expected non-empty string or null")
    _check_nonnegative_int(record.get("trial_index"), "$.trial_index", errors)
    _check_sha256(record.get("manifest_sha256"), "$.manifest_sha256", errors)
    _check_sha256(record.get("run_plan_sha256"), "$.run_plan_sha256", errors)
    _check_nonnegative_int(record.get("run_plan_index"), "$.run_plan_index", errors)

    case = _mapping(record.get("case"), "$.case", errors)
    _required(case, ("case_id", "object_pose", "grasp_arm"), "$.case", errors)
    if not _is_nonempty_string(case.get("case_id")):
        errors.append("$.case.case_id: expected non-empty string")
    if case.get("grasp_arm") not in ARMS:
        errors.append(f"$.case.grasp_arm: expected one of {sorted(ARMS)}")
    pose = _mapping(case.get("object_pose"), "$.case.object_pose", errors)
    _required(pose, ("position_xyz_m", "quaternion_wxyz"), "$.case.object_pose", errors)
    _check_vector(pose.get("position_xyz_m"), 3, "$.case.object_pose.position_xyz_m", errors)
    quat = pose.get("quaternion_wxyz")
    if quat is None:
        if formal:
            errors.append("$.case.object_pose.quaternion_wxyz: required for formal trial")
    else:
        _check_vector(quat, 4, "$.case.object_pose.quaternion_wxyz", errors)
        if isinstance(quat, list) and len(quat) == 4 and all(_is_number(x) for x in quat):
            norm = math.sqrt(sum(float(x) ** 2 for x in quat))
            if not math.isclose(norm, 1.0, rel_tol=0.0, abs_tol=1e-3):
                errors.append("$.case.object_pose.quaternion_wxyz: quaternion norm must be approximately 1")

    inp = _mapping(record.get("input"), "$.input", errors)
    input_keys = (
        "instruction_phases",
        "seed",
        "conditioning_regime",
        "input_spec_hash",
        "uses_expert_constraints",
        "constraint_source",
        "constraint_mode",
        "constraint_bundle_sha256",
        "hand_reference_source",
        "generation_timeout_seconds",
        "execution_timeout_seconds",
    )
    _required(inp, input_keys, "$.input", errors)
    phases = inp.get("instruction_phases")
    if not isinstance(phases, list) or not phases or not all(_is_nonempty_string(x) for x in phases):
        errors.append("$.input.instruction_phases: expected non-empty array of non-empty strings")
    if inp.get("seed") is not None and not _is_int(inp.get("seed")):
        errors.append("$.input.seed: expected integer or null")
    regime = inp.get("conditioning_regime")
    if regime not in CONDITIONING:
        errors.append(f"$.input.conditioning_regime: expected one of {sorted(CONDITIONING)}")
    _check_sha256(inp.get("input_spec_hash"), "$.input.input_spec_hash", errors)
    _check_sha256(inp.get("constraint_bundle_sha256"), "$.input.constraint_bundle_sha256", errors)
    expert = inp.get("uses_expert_constraints")
    if not isinstance(expert, bool):
        errors.append("$.input.uses_expert_constraints: expected boolean")
    elif expert:
        if regime not in {"expert_sparse", "expert_dense"}:
            errors.append("$.input.conditioning_regime: expert constraints require expert_sparse or expert_dense")
        if inp.get("constraint_bundle_sha256") is None:
            errors.append("$.input.constraint_bundle_sha256: required when expert constraints are used")
        if not _is_nonempty_string(inp.get("constraint_source")):
            errors.append("$.input.constraint_source: required when expert constraints are used")
        if not _is_nonempty_string(inp.get("constraint_mode")):
            errors.append("$.input.constraint_mode: required when expert constraints are used")
    elif regime in {"expert_sparse", "expert_dense"}:
        errors.append("$.input.uses_expert_constraints: must be true for expert conditioning")
    _check_nonnegative_number(inp.get("generation_timeout_seconds"), "$.input.generation_timeout_seconds", errors)
    _check_nonnegative_number(inp.get("execution_timeout_seconds"), "$.input.execution_timeout_seconds", errors)

    candidates = _mapping(record.get("candidates"), "$.candidates", errors)
    candidate_keys = (
        "samples_requested",
        "samples_generated",
        "selected_sample_index",
        "selection_policy",
        "retry_policy",
        "attempted_sample_indices",
        "retry_count",
    )
    _required(candidates, candidate_keys, "$.candidates", errors)
    requested = candidates.get("samples_requested")
    generated = candidates.get("samples_generated")
    if not _is_int(requested) or requested < 1:
        errors.append("$.candidates.samples_requested: expected integer >= 1")
    if not _is_int(generated) or generated < 0:
        errors.append("$.candidates.samples_generated: expected non-negative integer")
    if _is_int(requested) and _is_int(generated) and generated > requested:
        errors.append("$.candidates.samples_generated: cannot exceed samples_requested")
    selected = candidates.get("selected_sample_index")
    if selected is not None:
        if not _is_int(selected) or selected < 0:
            errors.append("$.candidates.selected_sample_index: expected non-negative integer or null")
        elif _is_int(generated) and selected >= generated:
            errors.append("$.candidates.selected_sample_index: index is outside generated candidates")
    attempted = candidates.get("attempted_sample_indices")
    if not isinstance(attempted, list) or not all(_is_int(x) and x >= 0 for x in attempted):
        errors.append("$.candidates.attempted_sample_indices: expected non-negative integer array")
        attempted = []
    elif len(attempted) != len(set(attempted)):
        errors.append("$.candidates.attempted_sample_indices: duplicate indices are forbidden")
    if _is_int(generated):
        for index in attempted:
            if index >= generated:
                errors.append(f"$.candidates.attempted_sample_indices: index {index} is outside generated candidates")
    _check_nonnegative_int(candidates.get("retry_count"), "$.candidates.retry_count", errors)
    for name in ("selection_policy", "retry_policy"):
        value = candidates.get(name)
        if value is not None and not _is_nonempty_string(value):
            errors.append(f"$.candidates.{name}: expected non-empty string or null")

    versions = _mapping(record.get("versions"), "$.versions", errors)
    version_keys = (
        "source_commit",
        "source_dirty",
        "source_dirty_diff_sha256",
        "generator_revision",
        "integration_revision",
        "integration_dirty",
        "integration_dirty_diff_sha256",
        "checkpoint_sha256",
        "scene_sha256",
        "controller_sha256",
        "evaluator_sha256",
    )
    _required(versions, version_keys, "$.versions", errors)
    _check_git_sha(versions.get("source_commit"), "$.versions.source_commit", errors)
    for name in (
        "source_dirty_diff_sha256",
        "integration_dirty_diff_sha256",
        "checkpoint_sha256",
        "scene_sha256",
        "controller_sha256",
        "evaluator_sha256",
    ):
        _check_sha256(versions.get(name), f"$.versions.{name}", errors)
    for dirty_name, diff_name in (
        ("source_dirty", "source_dirty_diff_sha256"),
        ("integration_dirty", "integration_dirty_diff_sha256"),
    ):
        dirty = versions.get(dirty_name)
        diff_hash = versions.get(diff_name)
        if dirty is not None and not isinstance(dirty, bool):
            errors.append(f"$.versions.{dirty_name}: expected boolean or null")
        elif dirty is True and diff_hash is None:
            errors.append(f"$.versions.{diff_name}: required when {dirty_name}=true")
        elif dirty is False and diff_hash is not None:
            errors.append(f"$.versions.{diff_name}: must be null when {dirty_name}=false")

    envs = _mapping(record.get("environments"), "$.environments", errors)
    _required(envs, ("generation", "execution"), "$.environments", errors)
    _check_environment(envs.get("generation"), "$.environments.generation", errors, formal=formal)
    _check_environment(envs.get("execution"), "$.environments.execution", errors, formal=formal)

    artifacts = record.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("$.artifacts: expected non-empty array")
    else:
        for index, item in enumerate(artifacts):
            artifact = _mapping(item, f"$.artifacts[{index}]", errors)
            _required(artifact, ("name", "path", "sha256"), f"$.artifacts[{index}]", errors)
            if not _is_nonempty_string(artifact.get("name")):
                errors.append(f"$.artifacts[{index}].name: expected non-empty string")
            if artifact.get("path") is not None and not _is_nonempty_string(artifact.get("path")):
                errors.append(f"$.artifacts[{index}].path: expected non-empty string or null")
            _check_sha256(artifact.get("sha256"), f"$.artifacts[{index}].sha256", errors, allow_null=False)

    execution = _mapping(record.get("execution"), "$.execution", errors)
    execution_keys = (
        "controller",
        "completed",
        "expected_frames",
        "recorded_frames",
        "frame_coverage_complete",
        "physics_hz",
        "physical_duration_seconds",
        "state_finite",
        "hand_synchronized",
        "fall",
        "cube_attached",
        "cube_teleported_during_rollout",
    )
    _required(execution, execution_keys, "$.execution", errors)
    completed = execution.get("completed")
    if not isinstance(completed, bool):
        errors.append("$.execution.completed: expected boolean")
    expected_frames = execution.get("expected_frames")
    recorded_frames = execution.get("recorded_frames")
    _check_nonnegative_int(expected_frames, "$.execution.expected_frames", errors)
    _check_nonnegative_int(recorded_frames, "$.execution.recorded_frames", errors)
    if _is_int(expected_frames) and _is_int(recorded_frames) and recorded_frames > expected_frames:
        errors.append("$.execution.recorded_frames: cannot exceed expected_frames")
    if completed is True:
        if not _is_int(expected_frames) or expected_frames <= 0 or recorded_frames != expected_frames:
            errors.append("$.execution: completed trial requires positive expected_frames == recorded_frames")
        if selected is None:
            errors.append("$.candidates.selected_sample_index: completed trial requires selected candidate")
        elif selected not in attempted:
            errors.append("$.candidates.attempted_sample_indices: completed selected candidate must be listed")
    _check_nonnegative_number(execution.get("physics_hz"), "$.execution.physics_hz", errors)
    _check_nonnegative_number(execution.get("physical_duration_seconds"), "$.execution.physical_duration_seconds", errors)
    for name in (
        "frame_coverage_complete",
        "state_finite",
        "hand_synchronized",
        "fall",
        "cube_attached",
        "cube_teleported_during_rollout",
    ):
        if execution.get(name) is not None and not isinstance(execution.get(name), bool):
            errors.append(f"$.execution.{name}: expected boolean or null")

    criteria = _mapping(record.get("criteria"), "$.criteria", errors)
    criteria_keys = (
        "minimum_lift_m",
        "minimum_continuous_hold_s",
        "requires_opposing_contacts",
        "requires_no_cube_table_contact_during_hold",
        "requires_complete_synchronized_rollout",
        "requires_no_fall",
        "forbids_attachment",
        "forbids_teleport",
        "robot_table_contact_policy",
    )
    _required(criteria, criteria_keys, "$.criteria", errors)
    _check_nonnegative_number(criteria.get("minimum_lift_m"), "$.criteria.minimum_lift_m", errors, allow_null=False)
    _check_nonnegative_number(
        criteria.get("minimum_continuous_hold_s"),
        "$.criteria.minimum_continuous_hold_s",
        errors,
        allow_null=False,
    )
    for name in (
        "requires_opposing_contacts",
        "requires_no_cube_table_contact_during_hold",
        "requires_complete_synchronized_rollout",
        "requires_no_fall",
        "forbids_attachment",
        "forbids_teleport",
    ):
        if not isinstance(criteria.get(name), bool):
            errors.append(f"$.criteria.{name}: expected boolean")
    if criteria.get("robot_table_contact_policy") is not None and not _is_nonempty_string(
        criteria.get("robot_table_contact_policy")
    ):
        errors.append("$.criteria.robot_table_contact_policy: expected non-empty string or null")

    metrics = _mapping(record.get("metrics"), "$.metrics", errors)
    metric_keys = (
        "max_lift_m",
        "final_lift_m",
        "max_continuous_hold_seconds",
        "final_continuous_hold_seconds",
        "place_error_m",
    )
    _required(metrics, metric_keys, "$.metrics", errors)
    for name in ("max_lift_m", "final_lift_m"):
        value = metrics.get(name)
        if value is not None and not _is_number(value):
            errors.append(f"$.metrics.{name}: expected finite number or null")
    for name in ("max_continuous_hold_seconds", "final_continuous_hold_seconds"):
        _check_nonnegative_number(metrics.get(name), f"$.metrics.{name}", errors)
    if metrics.get("place_error_m") is not None:
        errors.append("$.metrics.place_error_m: must be null for grasp_and_lift")
    max_lift = metrics.get("max_lift_m")
    final_lift = metrics.get("final_lift_m")
    if _is_number(max_lift) and _is_number(final_lift) and final_lift > max_lift + 1e-9:
        errors.append("$.metrics.final_lift_m: cannot exceed max_lift_m")

    contacts = _mapping(record.get("contacts"), "$.contacts", errors)
    contact_keys = (
        "cube_table_contact_steps",
        "cube_table_contact_during_hold",
        "robot_table_contact_steps",
        "robot_table_contact_bodies",
        "robot_self_contact_steps",
        "robot_self_contact_pairs",
        "active_arm_environment_contact_steps",
        "inactive_arm_environment_contact_steps",
        "final_cube_contacts",
    )
    _required(contacts, contact_keys, "$.contacts", errors)
    for name in (
        "cube_table_contact_steps",
        "robot_table_contact_steps",
        "robot_self_contact_steps",
        "active_arm_environment_contact_steps",
        "inactive_arm_environment_contact_steps",
    ):
        _check_nonnegative_int(contacts.get(name), f"$.contacts.{name}", errors)
    if contacts.get("cube_table_contact_during_hold") is not None and not isinstance(
        contacts.get("cube_table_contact_during_hold"), bool
    ):
        errors.append("$.contacts.cube_table_contact_during_hold: expected boolean or null")
    for name in ("robot_table_contact_bodies", "robot_self_contact_pairs"):
        value = contacts.get(name)
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            errors.append(f"$.contacts.{name}: expected string array")
    final_contacts = contacts.get("final_cube_contacts")
    if not isinstance(final_contacts, list):
        errors.append("$.contacts.final_cube_contacts: expected array")
    else:
        for index, item in enumerate(final_contacts):
            if not isinstance(item, dict):
                errors.append(f"$.contacts.final_cube_contacts[{index}]: expected object")
                continue
            if not _is_nonempty_string(item.get("body")):
                errors.append(f"$.contacts.final_cube_contacts[{index}].body: expected non-empty string")
            _check_nonnegative_number(
                item.get("normal_force_n"),
                f"$.contacts.final_cube_contacts[{index}].normal_force_n",
                errors,
                allow_null=False,
            )

    outcome = _mapping(record.get("outcome"), "$.outcome", errors)
    outcome_keys = (
        "runtime_valid",
        "task_success",
        "collision_observed",
        "unsafe_collision",
        "safety_success",
        "overall_success",
        "formal_eligible",
        "source_physical_success",
        "physical_execution_success",
    )
    _required(outcome, outcome_keys, "$.outcome", errors)
    runtime_valid = outcome.get("runtime_valid")
    task_success = outcome.get("task_success")
    collision_observed = outcome.get("collision_observed")
    unsafe_collision = outcome.get("unsafe_collision")
    safety_success = outcome.get("safety_success")
    overall_success = outcome.get("overall_success")
    formal_eligible = outcome.get("formal_eligible")
    for name in ("runtime_valid", "collision_observed", "formal_eligible"):
        if not isinstance(outcome.get(name), bool):
            errors.append(f"$.outcome.{name}: expected boolean")
    for name in ("task_success", "unsafe_collision", "safety_success", "overall_success"):
        if outcome.get(name) is not None and not isinstance(outcome.get(name), bool):
            errors.append(f"$.outcome.{name}: expected boolean or null")
    for name in ("source_physical_success", "physical_execution_success"):
        if outcome.get(name) is not None and not isinstance(outcome.get(name), bool):
            errors.append(f"$.outcome.{name}: expected boolean or null")
    if formal_eligible != formal:
        errors.append("$.outcome.formal_eligible: must be true exactly for formal TrialLog records")
    if runtime_valid is True:
        if completed is not True:
            errors.append("$.outcome.runtime_valid: requires execution.completed=true")
        for name in ("frame_coverage_complete", "state_finite", "hand_synchronized"):
            if execution.get(name) is not True:
                errors.append(f"$.execution.{name}: must be true when runtime_valid=true")
        if execution.get("cube_attached") is not False:
            errors.append("$.execution.cube_attached: must be false when runtime_valid=true")
        if execution.get("cube_teleported_during_rollout") is not False:
            errors.append("$.execution.cube_teleported_during_rollout: must be false when runtime_valid=true")
    if task_success is True:
        if runtime_valid is not True:
            errors.append("$.outcome.task_success: requires runtime_valid=true")
        lift_threshold = criteria.get("minimum_lift_m")
        hold_threshold = criteria.get("minimum_continuous_hold_s")
        max_hold = metrics.get("max_continuous_hold_seconds")
        if not _is_number(max_lift) or not _is_number(lift_threshold) or max_lift < lift_threshold:
            errors.append("$.metrics.max_lift_m: task_success requires lift threshold to be met")
        if not _is_number(max_hold) or not _is_number(hold_threshold) or max_hold < hold_threshold:
            errors.append("$.metrics.max_continuous_hold_seconds: task_success requires hold threshold to be met")
        if criteria.get("requires_no_cube_table_contact_during_hold") is True and contacts.get(
            "cube_table_contact_during_hold"
        ) is not False:
            errors.append("$.contacts.cube_table_contact_during_hold: must be false for successful task")
    if safety_success is None:
        if overall_success is not None:
            errors.append("$.outcome.overall_success: must be null while safety_success is unknown")
    elif isinstance(task_success, bool):
        expected_overall = task_success and safety_success
        if overall_success is not expected_overall:
            errors.append("$.outcome.overall_success: must equal task_success && safety_success")
    else:
        errors.append("$.outcome.task_success: must be known when safety_success is known")

    failures = _mapping(record.get("failures"), "$.failures", errors)
    failure_keys = (
        "runtime_failure_category",
        "task_failure_category",
        "safety_failure_categories",
        "failure_phase",
        "failure_reason",
    )
    _required(failures, failure_keys, "$.failures", errors)
    runtime_failure = failures.get("runtime_failure_category")
    task_failure = failures.get("task_failure_category")
    safety_failures = failures.get("safety_failure_categories")
    if runtime_failure is not None and runtime_failure not in RUNTIME_FAILURES:
        errors.append(f"$.failures.runtime_failure_category: unknown category {runtime_failure!r}")
    if task_failure is not None and task_failure not in TASK_FAILURES:
        errors.append(f"$.failures.task_failure_category: unknown category {task_failure!r}")
    if not isinstance(safety_failures, list) or any(x not in SAFETY_FAILURES for x in safety_failures):
        errors.append("$.failures.safety_failure_categories: contains unknown category")
        safety_failures = []
    if failures.get("failure_phase") is not None and failures.get("failure_phase") not in FAILURE_PHASES:
        errors.append("$.failures.failure_phase: invalid phase; place is not part of protocol v0.2")
    if runtime_valid is False and runtime_failure is None:
        errors.append("$.failures.runtime_failure_category: required when runtime_valid=false")
    if runtime_valid is False and task_success is not False:
        errors.append("$.outcome.task_success: must be false when runtime_valid=false")
    if runtime_valid is False and task_failure is not None:
        errors.append("$.failures.task_failure_category: must be null when runtime_valid=false")
    if runtime_valid is True and runtime_failure is not None:
        errors.append("$.failures.runtime_failure_category: must be null when runtime_valid=true")
    if runtime_valid is True and task_success is False and task_failure is None:
        errors.append("$.failures.task_failure_category: required for a valid runtime task failure")
    if task_success is True and task_failure is not None:
        errors.append("$.failures.task_failure_category: must be null when task_success=true")
    if safety_success is True and safety_failures:
        errors.append("$.failures.safety_failure_categories: must be empty when safety_success=true")
    if safety_success is False and not safety_failures:
        errors.append("$.failures.safety_failure_categories: required when safety_success=false")

    positive_contact = any(
        _is_int(contacts.get(name)) and contacts.get(name) > 0
        for name in ("cube_table_contact_steps", "robot_table_contact_steps", "robot_self_contact_steps")
    )
    if positive_contact and collision_observed is not True:
        errors.append("$.outcome.collision_observed: contact steps > 0 require true")
    if unsafe_collision is True:
        if collision_observed is not True:
            errors.append("$.outcome.unsafe_collision: requires collision_observed=true")
        if safety_success is not False:
            errors.append("$.outcome.unsafe_collision: requires safety_success=false")
        if "unsafe_collision" not in safety_failures:
            errors.append("$.failures.safety_failure_categories: must include unsafe_collision")
    if execution.get("fall") is True:
        if safety_success is True:
            errors.append("$.outcome.safety_success: cannot be true when fall=true")
        if safety_success is False and "robot_fall" not in safety_failures:
            errors.append("$.failures.safety_failure_categories: must include robot_fall when fall=true")

    timing = _mapping(record.get("timing"), "$.timing", errors)
    timing_keys = (
        "generation_time_scope",
        "generation_total_seconds",
        "execution_wall_seconds",
        "started_at_utc",
    )
    _required(timing, timing_keys, "$.timing", errors)
    _check_nonnegative_number(timing.get("generation_total_seconds"), "$.timing.generation_total_seconds", errors)
    _check_nonnegative_number(timing.get("execution_wall_seconds"), "$.timing.execution_wall_seconds", errors)
    _check_utc(timing.get("started_at_utc"), "$.timing.started_at_utc", errors)
    if timing.get("generation_time_scope") is not None and not _is_nonempty_string(
        timing.get("generation_time_scope")
    ):
        errors.append("$.timing.generation_time_scope: expected non-empty string or null")
    if _is_number(metrics.get("max_continuous_hold_seconds")) and _is_number(
        execution.get("physical_duration_seconds")
    ):
        if metrics.get("max_continuous_hold_seconds") > execution.get("physical_duration_seconds") + 1e-9:
            errors.append("$.metrics.max_continuous_hold_seconds: cannot exceed physical duration")

    if formal:
        for path, value in (
            ("$.batch_id", record.get("batch_id")),
            ("$.manifest_sha256", record.get("manifest_sha256")),
            ("$.run_plan_sha256", record.get("run_plan_sha256")),
            ("$.trial_index", record.get("trial_index")),
            ("$.run_plan_index", record.get("run_plan_index")),
            ("$.input.seed", inp.get("seed")),
            ("$.input.input_spec_hash", inp.get("input_spec_hash")),
            ("$.input.generation_timeout_seconds", inp.get("generation_timeout_seconds")),
            ("$.input.execution_timeout_seconds", inp.get("execution_timeout_seconds")),
            ("$.candidates.selection_policy", candidates.get("selection_policy")),
            ("$.candidates.retry_policy", candidates.get("retry_policy")),
            ("$.candidates.retry_count", candidates.get("retry_count")),
            ("$.versions.source_commit", versions.get("source_commit")),
            ("$.versions.generator_revision", versions.get("generator_revision")),
            ("$.versions.integration_revision", versions.get("integration_revision")),
            ("$.versions.checkpoint_sha256", versions.get("checkpoint_sha256")),
            ("$.versions.scene_sha256", versions.get("scene_sha256")),
            ("$.versions.controller_sha256", versions.get("controller_sha256")),
            ("$.versions.evaluator_sha256", versions.get("evaluator_sha256")),
            ("$.criteria.robot_table_contact_policy", criteria.get("robot_table_contact_policy")),
            ("$.outcome.safety_success", safety_success),
            ("$.outcome.overall_success", overall_success),
            ("$.timing.started_at_utc", timing.get("started_at_utc")),
        ):
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"{path}: required for formal trial")
        if versions.get("source_dirty") is None:
            errors.append("$.versions.source_dirty: required for formal trial")
        if versions.get("integration_dirty") is None:
            errors.append("$.versions.integration_dirty: required for formal trial")

    return errors


def validate_records(
    labeled_records: list[tuple[str, dict[str, Any]]],
    *,
    require_formal: bool = False,
    check_pairs: bool = False,
) -> list[tuple[str, str]]:
    """Validate records plus batch-level uniqueness and optional ARDY/Kimodo pairing."""

    issues: list[tuple[str, str]] = []
    seen_run_ids: dict[str, str] = {}
    seen_trials: dict[tuple[Any, Any, Any], str] = {}

    for label, record in labeled_records:
        for error in validate_trial(record, require_formal=require_formal):
            issues.append((label, error))
        run_id = record.get("run_id")
        if isinstance(run_id, str):
            if run_id in seen_run_ids:
                issues.append((label, f"$.run_id: duplicate of {seen_run_ids[run_id]}"))
            else:
                seen_run_ids[run_id] = label
        case = record.get("case") if isinstance(record.get("case"), dict) else {}
        key = (record.get("method"), case.get("case_id"), record.get("trial_index"))
        if None not in key:
            if key in seen_trials:
                issues.append((label, f"$: duplicate method/case/trial of {seen_trials[key]}"))
            else:
                seen_trials[key] = label

    if check_pairs:
        groups: dict[tuple[Any, Any, Any], list[tuple[str, dict[str, Any]]]] = defaultdict(list)
        for label, record in labeled_records:
            case = record.get("case") if isinstance(record.get("case"), dict) else {}
            groups[(record.get("batch_id"), case.get("case_id"), record.get("trial_index"))].append(
                (label, record)
            )
        for key, group in groups.items():
            methods = {record.get("method") for _, record in group}
            if methods != METHODS or len(group) != 2:
                for label, _ in group:
                    issues.append((label, f"$: pair {key} must contain exactly one ARDY and one Kimodo record"))
                continue
            first_label, first = group[0]
            second_label, second = group[1]
            comparisons = {
                "protocol_version": (first.get("protocol_version"), second.get("protocol_version")),
                "case": (first.get("case"), second.get("case")),
                "instruction_phases": (
                    (first.get("input") or {}).get("instruction_phases"),
                    (second.get("input") or {}).get("instruction_phases"),
                ),
                "seed": ((first.get("input") or {}).get("seed"), (second.get("input") or {}).get("seed")),
                "input_spec_hash": (
                    (first.get("input") or {}).get("input_spec_hash"),
                    (second.get("input") or {}).get("input_spec_hash"),
                ),
                "conditioning_regime": (
                    (first.get("input") or {}).get("conditioning_regime"),
                    (second.get("input") or {}).get("conditioning_regime"),
                ),
                "samples_requested": (
                    (first.get("candidates") or {}).get("samples_requested"),
                    (second.get("candidates") or {}).get("samples_requested"),
                ),
                "selection_policy": (
                    (first.get("candidates") or {}).get("selection_policy"),
                    (second.get("candidates") or {}).get("selection_policy"),
                ),
                "retry_policy": (
                    (first.get("candidates") or {}).get("retry_policy"),
                    (second.get("candidates") or {}).get("retry_policy"),
                ),
                "scene_sha256": (
                    (first.get("versions") or {}).get("scene_sha256"),
                    (second.get("versions") or {}).get("scene_sha256"),
                ),
                "controller_sha256": (
                    (first.get("versions") or {}).get("controller_sha256"),
                    (second.get("versions") or {}).get("controller_sha256"),
                ),
                "evaluator_sha256": (
                    (first.get("versions") or {}).get("evaluator_sha256"),
                    (second.get("versions") or {}).get("evaluator_sha256"),
                ),
                "execution_environment": (
                    (first.get("environments") or {}).get("execution"),
                    (second.get("environments") or {}).get("execution"),
                ),
            }
            for name, (left, right) in comparisons.items():
                if left != right:
                    issues.append((second_label, f"$: pair mismatch for {name} versus {first_label}"))

    return issues


def _load_records(path: Path, force_jsonl: bool) -> tuple[list[tuple[str, dict[str, Any]]], list[str]]:
    records: list[tuple[str, dict[str, Any]]] = []
    parse_errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [], [f"{path}: cannot read file: {exc}"]

    if force_jsonl or path.suffix.lower() == ".jsonl":
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            label = f"{path}:{line_number}"
            try:
                value = json.loads(line, parse_constant=_reject_constant)
            except (json.JSONDecodeError, ValueError) as exc:
                parse_errors.append(f"{label}: invalid JSON: {exc}")
                continue
            if not isinstance(value, dict):
                parse_errors.append(f"{label}: expected one JSON object per line")
                continue
            records.append((label, value))
        return records, parse_errors

    try:
        value = json.loads(text, parse_constant=_reject_constant)
    except (json.JSONDecodeError, ValueError) as exc:
        return [], [f"{path}: invalid JSON: {exc}"]
    if isinstance(value, dict):
        records.append((str(path), value))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            label = f"{path}[{index}]"
            if isinstance(item, dict):
                records.append((label, item))
            else:
                parse_errors.append(f"{label}: expected JSON object")
    else:
        parse_errors.append(f"{path}: expected JSON object or array of objects")
    return records, parse_errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="JSON or JSONL TrialLog files")
    parser.add_argument("--jsonl", action="store_true", help="parse every input as JSONL")
    parser.add_argument("--require-formal", action="store_true", help="reject smoke and pilot records")
    parser.add_argument("--check-pairs", action="store_true", help="check matched ARDY/Kimodo batch pairs")
    parser.add_argument("--quiet", action="store_true", help="print only errors")
    args = parser.parse_args(argv)

    labeled_records: list[tuple[str, dict[str, Any]]] = []
    parse_errors: list[str] = []
    for path in args.paths:
        loaded, errors = _load_records(path, args.jsonl)
        labeled_records.extend(loaded)
        parse_errors.extend(errors)

    if not labeled_records and not parse_errors:
        parse_errors.append("no TrialLog records found")

    issues = validate_records(
        labeled_records,
        require_formal=args.require_formal,
        check_pairs=args.check_pairs,
    )
    for error in parse_errors:
        print(f"[ERROR] {error}")
    for label, error in issues:
        print(f"[ERROR] {label} {error}")

    if parse_errors or issues:
        print(f"FAILED: {len(parse_errors) + len(issues)} issue(s) across {len(labeled_records)} parsed record(s)")
        return 1
    if not args.quiet:
        print(f"OK: {len(labeled_records)} TrialLog record(s) validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
