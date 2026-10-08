from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from summarize_profile import check_manifest, summarize, validate_event  # noqa: E402


SCHEMA = json.loads((ROOT / "profiling_schema.json").read_text(encoding="utf-8"))


def event(duration_ms: float = 10.0) -> dict:
    start = 1_000_000_000
    return {
        "schema_version": "t9_profile_event_v0.3",
        "event_id": "ardy-center-smoke-0:policy_infer:0",
        "experiment_id": "synthetic-exp-v0.3",
        "config_id": "synthetic-config-v0.3",
        "run_id": "ardy-center-smoke-0",
        "method": "ardy",
        "run_type": "not_final_smoke",
        "case_id": "center",
        "trial_index": 0,
        "scope": "control_step",
        "stage": "policy_infer",
        "clock": "perf_counter_ns",
        "start_ns": start,
        "end_ns": start + int(duration_ms * 1_000_000),
        "duration_ms": duration_ms,
        "deadline_ms": 20.0,
        "frame_index": 0,
        "process_id": 123,
        "thread_id": 1,
        "device": "cpu",
        "hardware_id": "worker00038",
        "synchronized": False,
        "profile_overhead_included": False,
        "accelerator": None,
        "transport": None,
        "tags": {"synthetic": True},
    }


def manifest_for(value: dict, *, expected_count: int = 1) -> dict:
    return {
        "schema_version": "t9_profile_manifest_v0.3",
        "runs": [{
            "run_id": value["run_id"],
            "experiment_id": value["experiment_id"],
            "config_id": value["config_id"],
            "method": value["method"],
            "run_type": value["run_type"],
            "case_id": value["case_id"],
            "trial_index": value["trial_index"],
            "status": "completed",
            "failure_reason": None,
            "requirements": [{
                "scope": value["scope"],
                "stage": value["stage"],
                "clock": value["clock"],
                "expected_count": expected_count,
                "frame_start": 0,
                "frame_stride": 1,
            }],
        }],
    }


class SummarizeProfileTests(unittest.TestCase):
    def test_valid_cpu_events_and_deadline_summary(self) -> None:
        first = event(10.0)
        second = event(25.0)
        second["event_id"] = "ardy-center-smoke-0:policy_infer:1"
        second["frame_index"] = 1
        self.assertEqual([], validate_event(first, SCHEMA))
        report = summarize([first, second])
        group = report["groups"][0]
        self.assertEqual(2, group["event_count"])
        self.assertEqual(1, group["deadline_misses"])
        self.assertEqual(0.5, group["deadline_miss_rate"])
        self.assertEqual(25.0, group["p95_ms"])

    def test_gpu_event_requires_synchronization(self) -> None:
        value = event(2.0)
        value.update({
            "clock": "musa_event",
            "start_ns": None,
            "end_ns": None,
            "synchronized": False,
            "accelerator": {
                "model": "MTT-S4000",
                "device_ids": ["4"],
                "device_count": 1,
                "backend": "MUSA",
                "execution_provider": "MUSAExecutionProvider",
                "dtype": "fp32",
                "warmup_runs": 1,
                "shared_device": False,
                "peak_memory_mb": None,
                "utilization_percent": None,
            },
        })
        errors = validate_event(value, SCHEMA)
        self.assertTrue(any("synchronized" in error for error in errors), errors)

    def test_rejects_duration_mismatch(self) -> None:
        value = event(10.0)
        value["duration_ms"] = 1.0
        errors = validate_event(value, SCHEMA)
        self.assertTrue(any("inconsistent" in error for error in errors), errors)

    def test_unknown_cpu_wall_accelerator_identity_is_allowed(self) -> None:
        value = event(10.0)
        value["scope"] = "generation"
        value["stage"] = "generation_total"
        value["frame_index"] = None
        value["accelerator"] = {
            "model": "MTT-S4000",
            "device_ids": [],
            "device_count": None,
            "backend": "MUSA",
            "execution_provider": None,
            "dtype": None,
            "warmup_runs": None,
            "shared_device": None,
            "peak_memory_mb": None,
            "utilization_percent": None,
        }
        self.assertEqual([], validate_event(value, SCHEMA))

    def test_hardware_conditions_are_kept_separate(self) -> None:
        first = event(10.0)
        second = copy.deepcopy(first)
        second.update({
            "event_id": "kimodo-center-smoke-0:policy_infer:0",
            "method": "kimodo",
            "run_id": "kimodo-center-smoke-0",
            "hardware_id": "worker00039",
        })
        report = summarize([first, second])
        self.assertEqual(2, len(report["groups"]))
        self.assertEqual(2, len(report["condition_groups"]))

    def test_transport_counters_and_mutual_exclusion(self) -> None:
        value = event(0.04)
        value.update({
            "stage": "dds_command_read",
            "transport": {
                "kind": "dds",
                "topic": "rt/lowcmd",
                "direction": "read",
                "command_received": True,
                "new_command": False,
                "reused_previous_command": True,
                "missing_command": False,
                "stale_command": False,
                "command_age_ms": 4.6,
                "command_interval_ms": None,
                "stale_threshold_ms": 20.0,
            },
        })
        self.assertEqual([], validate_event(value, SCHEMA))
        group = summarize([value])["groups"][0]
        self.assertEqual(1, group["reused_previous_command_true_samples"])
        invalid = copy.deepcopy(value)
        invalid["transport"].update(new_command=False, reused_previous_command=False, missing_command=False)
        errors = validate_event(invalid, SCHEMA)
        self.assertTrue(any("exactly one" in error for error in errors), errors)

    def test_v02_requires_real_migration(self) -> None:
        value = event(1.0)
        value["schema_version"] = "t9_profile_event_v0.2"
        errors = validate_event(value, SCHEMA)
        self.assertTrue(any("t9_profile_event_v0.3" in error for error in errors), errors)

    def test_unknown_strings_use_null_not_empty_text(self) -> None:
        value = event(1.0)
        value["device"] = ""
        errors = validate_event(value, SCHEMA)
        self.assertTrue(any("$.device: too short" in error for error in errors), errors)

    def test_manifest_coverage_pass_and_fail(self) -> None:
        value = event(1.0)
        coverage = check_manifest([value], manifest_for(value))
        self.assertTrue(coverage[0]["coverage_ok"])
        failed = check_manifest([value], manifest_for(value, expected_count=2))
        self.assertFalse(failed[0]["coverage_ok"])
        self.assertTrue(any("expected 2" in p for p in failed[0]["problems"]))

    def test_completed_manifest_rejects_failure_reason(self) -> None:
        value = event(1.0)
        manifest = manifest_for(value)
        manifest["runs"][0]["failure_reason"] = "should not be present"
        with self.assertRaisesRegex(ValueError, "failure_reason=null"):
            check_manifest([value], manifest)

    def test_duplicate_coverage_requirement_is_rejected(self) -> None:
        value = event(1.0)
        manifest = manifest_for(value)
        manifest["runs"][0]["requirements"].append(
            copy.deepcopy(manifest["runs"][0]["requirements"][0])
        )
        with self.assertRaisesRegex(ValueError, "Duplicate coverage requirement"):
            check_manifest([value], manifest)


if __name__ == "__main__":
    unittest.main()
