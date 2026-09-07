from __future__ import annotations

import unittest

from analysis.pilot_v2_deep_analysis import (
    classify_exhaustion,
    patch_metrics,
    pytest_class,
    terminal_kind,
)


class PilotV2DeepAnalysisTests(unittest.TestCase):
    def test_terminal_classification_requires_exact_finish_shape(self):
        self.assertEqual("exact_finish", terminal_kind({"operations": [], "finish": "done"}, "{}"))
        self.assertEqual("empty_object", terminal_kind({}, "{}"))
        self.assertEqual(
            "empty_operations_omitted_finish",
            terminal_kind({"operations": []}, '{"operations": []}'),
        )

    def test_pytest_classification_separates_test_and_environment_failures(self):
        passed = {"status": "success", "result": {"exit_code": 0, "stdout": "1 passed", "stderr": ""}}
        environment = {"status": "success", "result": {"exit_code": 1, "stdout": "", "stderr": "ImportError: incompatible dependency"}}
        self.assertEqual("PASS", pytest_class(passed))
        self.assertEqual("environment_failure", pytest_class(environment))

    def test_patch_metrics_do_not_treat_diff_headers_as_changes(self):
        patch = "--- a/src/a.py\n+++ b/src/a.py\n-old\n+new\n"
        metrics = patch_metrics(patch)
        self.assertEqual(1, metrics["lines_added"])
        self.assertEqual(1, metrics["lines_deleted"])
        self.assertEqual(1, metrics["number_files_changed"])

    def test_exhaustion_classifier_detects_repeated_operation_loop(self):
        actions = [{"action_id": str(index)} for index in range(1, 16)]
        backend = [
            {"action_id": str(index), "operation": "read_file", "arguments": {"path": "a.py"}}
            for index in range(1, 16)
        ]
        label, _ = classify_exhaustion(actions, backend)
        self.assertEqual("exact repeated-operation loop", label)


if __name__ == "__main__":
    unittest.main()
