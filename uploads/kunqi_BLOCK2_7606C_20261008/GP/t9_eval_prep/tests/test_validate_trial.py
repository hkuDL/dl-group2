from __future__ import annotations

import contextlib
import copy
import io
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from validate_trial import main, validate_records, validate_trial  # noqa: E402


EXAMPLE_PATH = ROOT / "examples" / "kimodo_not_final_trial.json"


def make_smoke() -> dict:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def make_formal(method: str = "kimodo") -> dict:
    trial = make_smoke()
    sha_a = "a" * 64
    sha_b = "b" * 64
    trial.update(
        {
            "run_id": f"{method}-common-center-trial-0",
            "run_type": "formal",
            "formal_score": True,
            "method": method,
            "batch_id": "formal-batch-001",
            "trial_index": 0,
            "manifest_sha256": sha_a,
            "run_plan_sha256": sha_b,
            "run_plan_index": 0 if method == "ardy" else 1,
        }
    )
    trial["case"]["case_id"] = "common_center"
    trial["case"]["object_pose"]["quaternion_wxyz"] = [1.0, 0.0, 0.0, 0.0]
    trial["input"].update(
        {
            "input_spec_hash": sha_a,
            "generation_timeout_seconds": 300.0,
            "execution_timeout_seconds": 60.0,
        }
    )
    trial["candidates"].update(
        {
            "samples_requested": 1,
            "samples_generated": 1,
            "selected_sample_index": 0,
            "selection_policy": "single_sample",
            "retry_policy": "no_retry",
            "attempted_sample_indices": [0],
            "retry_count": 0,
        }
    )
    trial["versions"].update(
        {
            "source_commit": "c" * 40,
            "source_dirty": False,
            "source_dirty_diff_sha256": None,
            "generator_revision": "d" * 40,
            "integration_revision": "e" * 40,
            "integration_dirty": False,
            "integration_dirty_diff_sha256": None,
            "checkpoint_sha256": sha_a,
            "scene_sha256": sha_b,
            "controller_sha256": "c" * 64,
            "evaluator_sha256": "d" * 64,
        }
    )
    for environment in trial["environments"].values():
        environment.update(
            {
                "host": "shared-host",
                "host_class": "shared-execution" if environment is trial["environments"]["execution"] else "generation",
                "accelerator_model": "recorded-model",
                "container_digest": "sha256:" + "f" * 64,
                "runtime_versions": {"python": "3.x", "mujoco": "recorded"},
            }
        )
    trial["criteria"]["robot_table_contact_policy"] = "record_only"
    trial["outcome"].update(
        {
            "unsafe_collision": False,
            "safety_success": True,
            "overall_success": True,
            "formal_eligible": True,
        }
    )
    trial["timing"]["started_at_utc"] = "2026-10-06T12:00:00Z"
    return trial


class TrialValidatorTests(unittest.TestCase):
    def assert_has(self, errors: list[str], text: str) -> None:
        self.assertTrue(any(text in error for error in errors), errors)

    def test_valid_not_final_collision_with_unknown_safety(self) -> None:
        trial = make_smoke()
        self.assertTrue(trial["outcome"]["task_success"])
        self.assertTrue(trial["outcome"]["collision_observed"])
        self.assertIsNone(trial["outcome"]["safety_success"])
        self.assertEqual([], validate_trial(trial))

    def test_valid_formal_success(self) -> None:
        self.assertEqual([], validate_trial(make_formal(), require_formal=True))

    def test_run_type_and_formal_gate(self) -> None:
        trial = make_smoke()
        trial["formal_score"] = True
        self.assert_has(validate_trial(trial), "formal_score")
        self.assert_has(validate_trial(make_smoke(), require_formal=True), "--require-formal")

    def test_required_unknown_and_nonfinite(self) -> None:
        trial = make_smoke()
        del trial["case"]
        trial["unexpected"] = 1
        errors = validate_trial(trial)
        self.assert_has(errors, "$.case: missing")
        self.assert_has(errors, "unknown top-level")

        trial = make_smoke()
        trial["metrics"]["max_lift_m"] = math.inf
        self.assert_has(validate_trial(trial), "max_lift_m")

    def test_pose_hash_and_utc(self) -> None:
        trial = make_formal()
        trial["case"]["object_pose"]["quaternion_wxyz"] = [1.0, 1.0, 0.0, 0.0]
        trial["manifest_sha256"] = "BAD"
        trial["timing"]["started_at_utc"] = "2026-10-06T12:00:00"
        errors = validate_trial(trial)
        self.assert_has(errors, "quaternion norm")
        self.assert_has(errors, "manifest_sha256")
        self.assert_has(errors, "ending in Z")

    def test_candidate_bookkeeping(self) -> None:
        trial = make_smoke()
        trial["candidates"]["samples_generated"] = 4
        trial["candidates"]["selected_sample_index"] = 4
        trial["candidates"]["attempted_sample_indices"] = [0, 0, 5]
        errors = validate_trial(trial)
        self.assert_has(errors, "cannot exceed samples_requested")
        self.assert_has(errors, "selected_sample_index")
        self.assert_has(errors, "duplicate indices")

    def test_conditioning_provenance(self) -> None:
        trial = make_smoke()
        trial["input"]["constraint_bundle_sha256"] = None
        self.assert_has(validate_trial(trial), "constraint_bundle_sha256")

        trial = make_smoke()
        trial["input"]["conditioning_regime"] = "text_only"
        self.assert_has(validate_trial(trial), "expert constraints require")

    def test_runtime_frames_and_failure_taxonomy(self) -> None:
        trial = make_smoke()
        trial["execution"].update(
            {
                "completed": False,
                "recorded_frames": 0,
                "frame_coverage_complete": False,
                "state_finite": None,
                "hand_synchronized": None,
            }
        )
        trial["outcome"].update(
            {
                "runtime_valid": False,
                "task_success": False,
                "physical_execution_success": False,
            }
        )
        trial["failures"].update(
            {
                "runtime_failure_category": "generation_timeout",
                "failure_phase": "generate",
                "failure_reason": "timeout",
            }
        )
        self.assertEqual([], validate_trial(trial))

        trial["failures"]["runtime_failure_category"] = None
        self.assert_has(validate_trial(trial), "runtime_failure_category")

    def test_task_safety_overall_and_place(self) -> None:
        trial = make_formal()
        trial["outcome"]["overall_success"] = False
        trial["metrics"]["place_error_m"] = 0.0
        errors = validate_trial(trial)
        self.assert_has(errors, "overall_success")
        self.assert_has(errors, "place_error_m")

        trial = make_formal()
        trial["outcome"].update({"unsafe_collision": True, "safety_success": False, "overall_success": False})
        trial["failures"]["safety_failure_categories"] = []
        errors = validate_trial(trial)
        self.assert_has(errors, "must include unsafe_collision")
        self.assert_has(errors, "required when safety_success=false")

    def test_jsonl_cli_and_batch_pairing(self) -> None:
        ardy = make_formal("ardy")
        kimodo = make_formal("kimodo")
        kimodo["environments"]["generation"]["host_class"] = "different-generation-hardware"
        labeled = [("ardy", ardy), ("kimodo", kimodo)]
        self.assertEqual([], validate_records(labeled, require_formal=True, check_pairs=True))

        broken = copy.deepcopy(kimodo)
        broken["case"]["object_pose"]["position_xyz_m"][0] += 0.01
        issues = validate_records([("ardy", ardy), ("kimodo", broken)], check_pairs=True)
        self.assertTrue(any("pair mismatch for case" in message for _, message in issues), issues)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trials.jsonl"
            path.write_text(json.dumps(ardy) + "\n{bad json}\n", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main([str(path), "--require-formal"])
            self.assertEqual(1, code)
            self.assertIn("invalid JSON", output.getvalue())

            empty_path = Path(directory) / "empty.jsonl"
            empty_path.write_text("", encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main([str(empty_path)])
            self.assertEqual(1, code)
            self.assertIn("no TrialLog records found", output.getvalue())


if __name__ == "__main__":
    unittest.main()
