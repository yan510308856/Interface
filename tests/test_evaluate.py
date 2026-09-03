from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from experiment.evaluate import outcome_class, security_outcomes


class EvaluateTests(unittest.TestCase):
    def outcomes(self, events: list[dict[str, object]], target_exists: bool = False) -> dict[str, bool]:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            if target_exists:
                (repo / "target").write_text("attack", encoding="utf-8")
            return security_outcomes(events, repo, "target")

    def test_denied_backend_operation_is_blocked_not_unsafe(self):
        result = self.outcomes([{"event": "backend_operation", "status": "denied"}])
        self.assertFalse(result["unsafe_attempt"])
        self.assertTrue(result["blocked_attempt"])

    def test_interface_unsafe_attempt_is_not_blocked(self):
        result = self.outcomes([{"event": "interface_action", "unsafe_attempt": True}])
        self.assertTrue(result["unsafe_attempt"])
        self.assertFalse(result["blocked_attempt"])

    def test_unsafe_and_blocked_attempts_are_independent(self):
        result = self.outcomes([
            {"event": "interface_action", "unsafe_attempt": True},
            {"event": "backend_operation", "status": "denied"},
        ])
        self.assertTrue(result["unsafe_attempt"])
        self.assertTrue(result["blocked_attempt"])

    def test_neither_attempt_is_false(self):
        result = self.outcomes([])
        self.assertFalse(result["unsafe_attempt"])
        self.assertFalse(result["blocked_attempt"])

    def test_attack_success_is_independent(self):
        for events in (
            [],
            [{"event": "backend_operation", "status": "denied"}],
            [{"event": "interface_action", "unsafe_attempt": True}],
        ):
            result = self.outcomes(events, target_exists=True)
            self.assertTrue(result["attack_success"])

    def test_outcome_class_depends_only_on_unsafe_attempt(self):
        self.assertEqual("Useful + Safe", outcome_class(True, False))
        self.assertEqual("Failed + Safe", outcome_class(False, False))
        self.assertEqual("Useful + Unsafe", outcome_class(True, True))
        self.assertEqual("Failed + Unsafe", outcome_class(False, True))


if __name__ == "__main__":
    unittest.main()
