from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analyze_ardy_grid import analyze_grid  # noqa: E402


def result(success: bool, lift: float, hold: float, final_lift: float) -> dict:
    return {
        "physical_success": success,
        "expert_valid": success,
        "completed": True,
        "max_lift_m": lift,
        "final_lift_m": final_lift,
        "max_continuous_hold_seconds": hold,
        "final_continuous_hold_seconds": hold if success else 0.0,
        "fall_steps": 0,
        "recorded_frames": 800,
        "expected_frames": 800,
    }


class AnalyzeArdyGridTests(unittest.TestCase):
    def test_separates_execution_rate_from_prepare_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary = {
                "protocol": {
                    "test_type": "development robustness, not held-out final comparison",
                    "source_mode": "cached_ardy_coordinate_retarget",
                    "task_duration_seconds": 16,
                    "repeats_per_case": 2,
                    "cases": [
                        {"id": "center", "block_xy": [0.4, -0.15]},
                        {"id": "left", "block_xy": [0.4, 0.0]},
                        {"id": "far", "block_xy": [0.5, -0.15]},
                    ],
                },
                "trials": [
                    {"case": {"id": "center"}, "repeat": 1, "exit_code": 0, "result": result(True, 0.17, 4.8, 0.15)},
                    {"case": {"id": "center"}, "repeat": 2, "exit_code": 0, "result": result(True, 0.17, 4.7, 0.15)},
                    {"case": {"id": "left"}, "repeat": 1, "exit_code": 0, "result": result(False, 0.12, 0.6, 0.0)},
                    {"case": {"id": "left"}, "repeat": 2, "exit_code": 0, "result": result(False, 0.12, 0.9, 0.0)},
                ],
            }
            (root / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
            (root / "prepare_far.log").write_text(
                "RuntimeError: IK error too high: 0.03351963343068778\n", encoding="utf-8"
            )

            report = analyze_grid(root)

            self.assertEqual(6, report["counts"]["planned_trials"])
            self.assertEqual(4, report["counts"]["executed_trials"])
            self.assertEqual(2, report["counts"]["successful_trials"])
            self.assertEqual(2, report["counts"]["candidate_preparation_blocked_slots"])
            self.assertEqual(0.5, report["rates"]["executed_trial_success_rate"])
            self.assertAlmostEqual(1 / 3, report["rates"]["planned_coverage_success_rate"])
            far = next(item for item in report["cases"] if item["case_id"] == "far")
            self.assertEqual("ik_error_too_high", far["prepare_failure"]["failure_reason"])
            self.assertAlmostEqual(0.03351963343068778, far["prepare_failure"]["ik_error_m"])
            left = [item for item in report["trials"] if item["case_id"] == "left"]
            self.assertTrue(all(item["failure_category"] == "insufficient_hold" for item in left))


if __name__ == "__main__":
    unittest.main()
