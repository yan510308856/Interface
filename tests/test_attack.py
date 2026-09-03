from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from experiment.attack import prepare_condition


class AttackTests(unittest.TestCase):
    def test_only_attack_condition_adds_carrier(self):
        config = {"path": ".agent/instructions.md", "payload": "synthetic attack"}
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            self.assertIsNone(prepare_condition(repo, "clean", config))
            carrier = prepare_condition(repo, "attack", config)
            self.assertEqual("synthetic attack", carrier.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

