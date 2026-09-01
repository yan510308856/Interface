from __future__ import annotations

import unittest

from experiment.interface_equivalence import run_validation


class InterfaceEquivalenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report, cls.atomic_trajectory, cls.python_trajectory = run_validation()

    def test_scripted_backend_facts_and_repository_outputs_match(self):
        self.assertEqual("PASS", self.report["status"])
        for comparison in self.report["comparisons"].values():
            self.assertEqual("equal", comparison["verdict"])

    def test_action_counts_may_differ_but_operation_counts_match(self):
        atomic = self.report["interfaces"]["atomic"]
        python = self.report["interfaces"]["restricted_python"]
        self.assertNotEqual(atomic["action_count"], python["action_count"])
        self.assertEqual(atomic["operation_count"], python["operation_count"])
        self.assertEqual(1, atomic["deny_count"])
        self.assertEqual(1, python["timeout_count"])

    def test_trajectories_include_controlled_malformed_actions(self):
        self.assertEqual("invalid", self.atomic_trajectory[-1]["result"]["parse_status"])
        self.assertEqual("invalid", self.python_trajectory[-1]["result"]["parse_status"])


if __name__ == "__main__":
    unittest.main()
