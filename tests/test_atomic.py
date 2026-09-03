from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiment.interfaces.atomic import execute_action
from tests.helpers import git_repo, make_backend


def tool_call(name: str, arguments: object, call_id: str = "call-1") -> list[dict[str, object]]:
    return [{
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }]


class AtomicTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.backend = make_backend(git_repo(root / "repo"), root / "log.jsonl")

    def tearDown(self):
        self.temporary.cleanup()

    def test_read_file_tool_call_maps_to_one_operation(self):
        result = execute_action(tool_call("read_file", {"path": "sample.py"}), self.backend, "1")
        self.assertEqual("ok", result.status)
        self.assertEqual(1, self.backend.operation_count)

    def test_replace_text_tool_call_maps_to_one_operation(self):
        result = execute_action(
            tool_call("replace_text", {"path": "sample.py", "old_text": "1", "new_text": "2"}),
            self.backend,
            "1",
        )
        self.assertEqual("ok", result.status)
        self.assertEqual(1, self.backend.operation_count)

    def test_finish_tool_call_does_not_execute_backend(self):
        result = execute_action(tool_call("finish", {"message": "done"}), self.backend, "1")
        self.assertEqual("finish", result.status)
        self.assertEqual(0, self.backend.operation_count)

    def test_zero_or_multiple_tool_calls_are_invalid(self):
        result = execute_action([], self.backend, "bad")
        self.assertEqual("invalid", result.status)
        calls = tool_call("read_file", {"path": "sample.py"}) + tool_call("git_diff", {})
        result = execute_action(calls, self.backend, "bad")
        self.assertEqual("invalid", result.status)
        self.assertEqual(0, self.backend.operation_count)

    def test_malformed_or_non_object_arguments_are_invalid(self):
        malformed = [{"id": "call-1", "type": "function", "function": {"name": "read_file", "arguments": "{"}}]
        non_object = tool_call("read_file", ["sample.py"])
        self.assertEqual("invalid", execute_action(malformed, self.backend, "bad").status)
        self.assertEqual("invalid", execute_action(non_object, self.backend, "bad").status)
        self.assertEqual(0, self.backend.operation_count)

    def test_unavailable_operation_is_rejected_as_unsafe(self):
        result = execute_action(tool_call("open", {"path": "sample.py"}), self.backend, "bad")
        self.assertEqual("invalid", result.status)
        self.assertTrue(result.unsafe_attempt)
        self.assertEqual(0, self.backend.operation_count)


if __name__ == "__main__":
    unittest.main()
