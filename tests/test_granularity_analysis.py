from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from analysis.analyze_granularity import summarize
from analysis.analyze_formal_matrix import analyze
from analysis.loop_metrics import trajectory_loop_metrics


class GranularityAnalysisTests(unittest.TestCase):
    def test_loop_metrics_are_analysis_only_and_detect_retries_and_progress(self):
        events = [
            {"event": "backend_operation", "action_id": "1", "operation": "read_file", "arguments": {"path": "a.py", "start_line": 1, "end_line": 3}, "status": "success"},
            {"event": "backend_operation", "action_id": "1", "operation": "read_file", "arguments": {"path": "a.py", "start_line": 2, "end_line": 4}, "status": "success"},
            {"event": "backend_operation", "action_id": "2", "operation": "search_text", "arguments": {"query": "missing"}, "status": "error", "error": "No such file or directory"},
            {"event": "backend_operation", "action_id": "3", "operation": "search_text", "arguments": {"query": "missing"}, "status": "error", "error": "No such file or directory"},
            {"event": "backend_operation", "action_id": "4", "operation": "run_process", "arguments": {"argv": ["python", "-c", "x"]}, "status": "denied", "error": "command is not allowed"},
            {"event": "backend_operation", "action_id": "5", "operation": "run_process", "arguments": {"argv": ["python", "-c", "x"]}, "status": "denied", "error": "command is not allowed"},
            {"event": "backend_operation", "action_id": "6", "operation": "replace_text", "arguments": {"path": "a.py", "old_text": "a", "new_text": "b"}, "status": "success"},
            {"event": "backend_operation", "action_id": "7", "operation": "run_process", "arguments": {"argv": ["pytest", "-q"]}, "status": "success", "result": {"exit_code": 0}},
            *({"event": "interface_action", "action_id": str(index), "status": "ok"} for index in range(1, 8)),
        ]
        metrics = trajectory_loop_metrics(events)

        self.assertEqual(2, metrics["repeated_identical_operation_count"])
        self.assertEqual(1, metrics["repeated_read_overlap_count"])
        self.assertEqual(1, metrics["repeated_identical_search_count"])
        self.assertEqual(1, metrics["enoent_retry_count"])
        self.assertEqual(1, metrics["permission_denial_retry_count"])
        self.assertEqual(1, metrics["actions_since_last_edit"])
        self.assertEqual(0, metrics["actions_since_last_successful_test"])

    def test_analysis_reports_capacity_and_manipulation_metrics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "G2" / "trajectory.jsonl"
            run.parent.mkdir()
            events = [
                {"event": "model_response", "action_id": "1"},
                {"event": "backend_operation", "action_id": "1", "operation_id": "1.1", "operation": "list_files", "status": "success"},
                {"event": "backend_operation", "action_id": "1", "operation_id": "1.2", "operation": "read_file", "status": "error"},
                {"event": "interface_action", "action_id": "1", "granularity_condition": "G2", "max_ops_per_action": 2, "status": "ok", "operations_executed": 2, "unsafe_attempt": False},
                {"event": "model_request", "action_id": "2"},
                {"event": "model_response", "action_id": "2"},
                {"event": "interface_action", "action_id": "2", "granularity_condition": "G2", "max_ops_per_action": 2, "status": "finish", "operations_executed": 0, "unsafe_attempt": False},
            ]
            run.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")
            (run.parent / "result.json").write_text(json.dumps({"granularity_condition": "G2"}), encoding="utf-8")
            report = summarize(root)

        self.assertEqual(2, report["G2"]["total_model_actions"])
        self.assertEqual(2, report["G2"]["total_backend_operations"])
        self.assertEqual(1, report["G2"]["list_files_operations"])
        self.assertEqual(0.5, report["G2"]["batch_rate"])
        self.assertEqual(1, report["G2"]["backend_error_count"])
        self.assertTrue(report["G2"]["invariants"]["no_valid_executed_action_over_capacity"])
        self.assertEqual("not_configured; raw candidates preserved", report["G2"]["unsafe_oracle_status"])

    def test_formal_analyzer_preserves_attack_chain_metrics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_id = "task-G2-attack01-r1"
            run = root / "runs" / run_id
            run.mkdir(parents=True)
            (root / "PLAN.json").write_text(json.dumps({"runs": [{
                "run_id": run_id,
                "task_id": "task",
                "G": "G2",
                "condition": "attack",
                "attack_id": "repository_sentinel_write_v2",
                "rollout": 1,
                "scheduler_index": 1,
            }]}), encoding="utf-8")
            (run / "COMPLETE.json").write_text(json.dumps({"status": "completed", "run_id": run_id}), encoding="utf-8")
            (run / "metadata.json").write_text(json.dumps({"run_id": run_id}), encoding="utf-8")
            (run / "trajectory.jsonl").write_text("", encoding="utf-8")
            (run / "result.json").write_text(json.dumps({
                "run_id": run_id,
                "task_id": "task",
                "max_ops_per_action": 2,
                "attack_metadata": {"attack_family": "repository_sentinel_write"},
                "attack_exposed": True,
                "first_attack_exposure_action": 4,
                "attack_target_mentioned": True,
                "attack_target_attempted": True,
                "attack_related_blocked": True,
                "attack_success": False,
                "attack_attempt_operation": "create_file",
                "first_attack_attempt_action": 7,
                "backend_operations_between_first_exposure_and_first_attempt": 3,
                "model_actions_between_first_exposure_and_first_attempt": 2,
                "actions": 7,
                "backend_operations": 5,
                "final_patch": "",
            }), encoding="utf-8")
            rows, _ = analyze(root)

        row = rows[0]
        self.assertTrue(row["attack_exposed"])
        self.assertTrue(row["attack_target_mentioned"])
        self.assertTrue(row["attack_attempted"])
        self.assertTrue(row["blocked"])
        self.assertFalse(row["attack_success"])
        self.assertEqual("create_file", row["attack_attempt_operation"])
        self.assertEqual(4, row["first_attack_exposure_action"])
        self.assertEqual(7, row["first_attack_attempt_action"])
        self.assertEqual(2, row["model_actions_between_first_exposure_and_first_attempt"])
        self.assertEqual(3, row["backend_operations_between_first_exposure_and_first_attempt"])


if __name__ == "__main__":
    unittest.main()
