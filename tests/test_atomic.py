from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiment.interfaces.atomic import execute_action
from tests.helpers import git_repo, make_backend


class AtomicTests(unittest.TestCase):
    def test_one_action_maps_to_one_operation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            backend = make_backend(git_repo(root / "repo"), root / "log.jsonl")
            action = json.dumps({"type": "tool_call", "operation": "read_file", "arguments": {"path": "sample.py"}})
            result = execute_action(action, backend, "1")
            self.assertEqual("ok", result.status)
            self.assertEqual(1, backend.operation_count)
            execute_action('{"type":"finish"}', backend, "2")
            self.assertEqual(1, backend.operation_count)


if __name__ == "__main__":
    unittest.main()

