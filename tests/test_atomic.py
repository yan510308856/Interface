from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiment.interfaces.atomic import execute_action
from tests.helpers import git_repo, make_backend


class AtomicTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.backend = make_backend(git_repo(root / "repo"), root / "log.jsonl")

    def tearDown(self):
        self.temporary.cleanup()

    def test_raw_json_maps_to_one_operation(self):
        action = json.dumps({"type": "tool_call", "operation": "read_file", "arguments": {"path": "sample.py"}})
        result = execute_action(action, self.backend, "1")
        self.assertEqual("ok", result.status)
        self.assertEqual(1, self.backend.operation_count)

    def test_prose_and_fenced_json_are_normalized(self):
        action = '{"type":"tool_call","operation":"read_file","arguments":{"path":"sample.py"}}'
        for source in (f"Let me inspect the repository.\n\n{action}", f"```json\n{action}\n```"):
            result = execute_action(source, self.backend, "1")
            self.assertEqual("ok", result.status)
        self.assertEqual(2, self.backend.operation_count)

    def test_missing_or_multiple_json_objects_are_invalid(self):
        action = '{"type":"tool_call","operation":"read_file","arguments":{"path":"sample.py"}}'
        for source in ("Let me inspect the repository.", f"{action}\n\n{action}"):
            result = execute_action(source, self.backend, "bad")
            self.assertEqual("invalid", result.status)
        self.assertEqual(0, self.backend.operation_count)

    def test_invalid_operation_is_not_repaired(self):
        action = '{"type":"tool_call","operation":"open","arguments":{"path":"sample.py"}}'
        result = execute_action(action, self.backend, "bad")
        self.assertEqual("invalid", result.status)
        self.assertTrue(result.unsafe_attempt)
        self.assertEqual(0, self.backend.operation_count)

    def test_prose_and_finish_json_finishes_without_operation(self):
        result = execute_action('Done.\n\n{"type":"finish","message":"done"}', self.backend, "1")
        self.assertEqual("finish", result.status)
        self.assertEqual(0, self.backend.operation_count)

    def test_one_action_maps_to_at_most_one_operation(self):
        action = json.dumps({"type": "tool_call", "operation": "read_file", "arguments": {"path": "sample.py"}})
        result = execute_action(action, self.backend, "1")
        self.assertEqual("ok", result.status)
        self.assertEqual(1, self.backend.operation_count)
        execute_action('{"type":"finish"}', self.backend, "2")
        self.assertEqual(1, self.backend.operation_count)


if __name__ == "__main__":
    unittest.main()
