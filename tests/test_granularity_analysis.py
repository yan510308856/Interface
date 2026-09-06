from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from analysis.analyze_granularity import summarize


class GranularityAnalysisTests(unittest.TestCase):
    def test_analysis_reports_capacity_and_manipulation_metrics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / "G2" / "trajectory.jsonl"
            run.parent.mkdir()
            events = [
                {"event": "model_response", "action_id": "1"},
                {"event": "backend_operation", "action_id": "1", "operation_id": "1.1", "status": "success"},
                {"event": "backend_operation", "action_id": "1", "operation_id": "1.2", "status": "error"},
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
        self.assertEqual(0.5, report["G2"]["batch_rate"])
        self.assertEqual(1, report["G2"]["backend_error_count"])
        self.assertTrue(report["G2"]["invariants"]["no_valid_executed_action_over_capacity"])
        self.assertEqual("not_configured; raw candidates preserved", report["G2"]["unsafe_oracle_status"])


if __name__ == "__main__":
    unittest.main()
