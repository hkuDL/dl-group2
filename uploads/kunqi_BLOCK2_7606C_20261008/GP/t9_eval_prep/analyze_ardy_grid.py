#!/usr/bin/env python3
"""Summarize an ARDY canonical development grid without changing its artifacts.

The input is the directory containing ``summary.json``, case run directories,
and optional ``prepare_<case>.log`` files.  The report deliberately separates
executed-trial success from planned end-to-end coverage so a candidate
preparation failure is not silently dropped from the denominator.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


DEFAULT_MINIMUM_LIFT_M = 0.10
DEFAULT_MINIMUM_HOLD_S = 2.0
IK_ERROR_RE = re.compile(r"IK error too high:\s*([0-9.eE+-]+)")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def _number(value: Any) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _classify_result(result: dict[str, Any]) -> tuple[str, str | None, list[str]]:
    """Return status, primary failure category, and non-normative observations."""

    observations: list[str] = []
    if result.get("physical_success") is True and result.get("expert_valid") is True:
        return "success", None, observations

    if (_number(result.get("fall_steps")) or 0.0) > 0:
        return "safety_failure", "robot_fall", observations

    max_lift = _number(result.get("max_lift_m"))
    max_hold = _number(result.get("max_continuous_hold_seconds"))
    final_lift = _number(result.get("final_lift_m"))

    if max_lift is None or max_hold is None:
        return "invalid_result", "missing_physical_metrics", observations
    if max_lift < DEFAULT_MINIMUM_LIFT_M:
        return "task_failure", "insufficient_lift", observations
    if max_hold < DEFAULT_MINIMUM_HOLD_S:
        if final_lift is not None and final_lift < 0.01:
            observations.append("lift_threshold_reached_then_object_returned_to_table")
        return "task_failure", "insufficient_hold", observations
    return "task_failure", "physical_criterion_mismatch", observations


def _prepare_failure(grid_root: Path, case_id: str) -> dict[str, Any] | None:
    path = grid_root / f"prepare_{case_id}.log"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    match = IK_ERROR_RE.search(text)
    if match:
        return {
            "status": "candidate_preparation_failure",
            "failure_phase": "adapter",
            "runtime_failure_category": "adapter_error",
            "failure_reason": "ik_error_too_high",
            "ik_error_m": float(match.group(1)),
            "log_path": str(path),
        }
    if "Traceback" in text:
        return {
            "status": "candidate_preparation_failure",
            "failure_phase": "adapter",
            "runtime_failure_category": "adapter_error",
            "failure_reason": "unclassified_prepare_traceback",
            "ik_error_m": None,
            "log_path": str(path),
        }
    return None


def analyze_grid(grid_root: Path) -> dict[str, Any]:
    summary_path = grid_root / "summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"missing {summary_path}")
    source = _read_json(summary_path)
    protocol = source.get("protocol")
    if not isinstance(protocol, dict):
        raise ValueError(f"{summary_path}: protocol must be an object")

    case_specs = protocol.get("cases")
    if not isinstance(case_specs, list) or not case_specs:
        raise ValueError(f"{summary_path}: protocol.cases must be a non-empty array")
    repeats = protocol.get("repeats_per_case")
    if not isinstance(repeats, int) or isinstance(repeats, bool) or repeats < 1:
        raise ValueError(f"{summary_path}: repeats_per_case must be a positive integer")

    expected_cases: list[dict[str, Any]] = []
    for item in case_specs:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError(f"{summary_path}: every case must contain a string id")
        expected_cases.append(item)

    source_trials = source.get("trials")
    if not isinstance(source_trials, list):
        raise ValueError(f"{summary_path}: trials must be an array")

    trials: list[dict[str, Any]] = []
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in source_trials:
        if not isinstance(item, dict):
            continue
        case = item.get("case") if isinstance(item.get("case"), dict) else {}
        case_id = case.get("id")
        result = item.get("result") if isinstance(item.get("result"), dict) else {}
        status, failure_category, observations = _classify_result(result)
        record = {
            "case_id": case_id,
            "repeat": item.get("repeat"),
            "exit_code": item.get("exit_code"),
            "status": status,
            "failure_category": failure_category,
            "observations": observations,
            "physical_success": result.get("physical_success"),
            "expert_valid": result.get("expert_valid"),
            "completed": result.get("completed"),
            "max_lift_m": result.get("max_lift_m"),
            "final_lift_m": result.get("final_lift_m"),
            "max_hold_s": result.get("max_continuous_hold_seconds"),
            "final_hold_s": result.get("final_continuous_hold_seconds"),
            "fall_steps": result.get("fall_steps"),
            "recorded_frames": result.get("recorded_frames"),
            "expected_frames": result.get("expected_frames"),
            "body_tracking_rmse_rad": result.get("body_tracking_rmse_rad"),
            "execution_wall_seconds": item.get("total_replay_process_wall_seconds"),
            "candidate_preparation_seconds": item.get("candidate_preparation_seconds"),
            "source_generation_seconds": item.get("source_generation_wall_seconds"),
            "run_path": item.get("run"),
        }
        trials.append(record)
        if isinstance(case_id, str):
            by_case[case_id].append(record)

    case_reports: list[dict[str, Any]] = []
    blocked_slots = 0
    missing_slots = 0
    for spec in expected_cases:
        case_id = spec["id"]
        executed = by_case.get(case_id, [])
        success_count = sum(item["status"] == "success" for item in executed)
        outstanding = max(0, repeats - len(executed))
        prepare_failure = _prepare_failure(grid_root, case_id) if outstanding else None
        blocked = outstanding if prepare_failure else 0
        missing = outstanding - blocked
        blocked_slots += blocked
        missing_slots += missing
        case_reports.append(
            {
                "case_id": case_id,
                "block_xy": spec.get("block_xy"),
                "planned_trials": repeats,
                "executed_trials": len(executed),
                "successful_trials": success_count,
                "candidate_preparation_blocked_slots": blocked,
                "missing_slots": missing,
                "prepare_failure": prepare_failure,
            }
        )

    planned = len(expected_cases) * repeats
    executed_count = len(trials)
    successes = sum(item["status"] == "success" for item in trials)
    failures = executed_count - successes
    warnings = [
        "This report describes a development robustness grid, not a held-out formal comparison.",
        "Executed-trial and planned-coverage rates use different denominators and must remain separate.",
    ]
    if protocol.get("source_mode") == "cached_ardy_coordinate_retarget":
        warnings.append(
            "Candidates were cached ARDY motions with coordinate retargeting; this is not end-to-end generation timing."
        )
    if blocked_slots:
        warnings.append(
            "Candidate-preparation failures blocked planned execution slots; they are visible in coverage but are not fabricated as executed trials."
        )

    return {
        "summary_schema_version": "t9_ardy_dev_grid_summary_v0.1",
        "source_summary_path": str(summary_path),
        "test_type": protocol.get("test_type"),
        "source_mode": protocol.get("source_mode"),
        "task_duration_seconds": protocol.get("task_duration_seconds"),
        "repeats_per_case": repeats,
        "counts": {
            "planned_trials": planned,
            "executed_trials": executed_count,
            "successful_trials": successes,
            "failed_executed_trials": failures,
            "candidate_preparation_blocked_slots": blocked_slots,
            "unexplained_missing_slots": missing_slots,
        },
        "rates": {
            "executed_trial_success_rate": successes / executed_count if executed_count else None,
            "planned_coverage_success_rate": successes / planned if planned else None,
            "execution_coverage_rate": executed_count / planned if planned else None,
        },
        "cases": case_reports,
        "trials": trials,
        "warnings": warnings,
    }


def _write_csv(path: Path, report: dict[str, Any]) -> None:
    rows = report["trials"]
    fields = [
        "case_id",
        "repeat",
        "status",
        "failure_category",
        "physical_success",
        "expert_valid",
        "max_lift_m",
        "final_lift_m",
        "max_hold_s",
        "final_hold_s",
        "fall_steps",
        "recorded_frames",
        "expected_frames",
        "body_tracking_rmse_rad",
        "execution_wall_seconds",
        "candidate_preparation_seconds",
        "source_generation_seconds",
        "run_path",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _markdown(report: dict[str, Any]) -> str:
    counts = report["counts"]
    rates = report["rates"]
    lines = [
        "# ARDY development grid summary",
        "",
        f"- Test type: `{report['test_type']}`",
        f"- Source mode: `{report['source_mode']}`",
        f"- Executed success: {counts['successful_trials']}/{counts['executed_trials']} "
        f"({rates['executed_trial_success_rate']:.1%})",
        f"- Planned coverage success: {counts['successful_trials']}/{counts['planned_trials']} "
        f"({rates['planned_coverage_success_rate']:.1%})",
        f"- Candidate-preparation blocked slots: {counts['candidate_preparation_blocked_slots']}",
        "",
        "| Case | Executed | Success | Preparation blocked | Missing |",
        "|---|---:|---:|---:|---:|",
    ]
    for case in report["cases"]:
        lines.append(
            f"| {case['case_id']} | {case['executed_trials']} | {case['successful_trials']} | "
            f"{case['candidate_preparation_blocked_slots']} | {case['missing_slots']} |"
        )
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {warning}" for warning in report["warnings"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("grid_root", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)

    try:
        report = analyze_grid(args.grid_root.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.output_dir is None:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "ardy_grid_summary.json"
    csv_path = args.output_dir / "ardy_grid_trials.csv"
    markdown_path = args.output_dir / "ardy_grid_summary.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_csv(csv_path, report)
    markdown_path.write_text(_markdown(report), encoding="utf-8")
    print(f"WROTE: {json_path}")
    print(f"WROTE: {csv_path}")
    print(f"WROTE: {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
