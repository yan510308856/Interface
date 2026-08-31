from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiment import audit, backend, permission
from experiment.interfaces import atomic


class AtomicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.repo = root / "repo"
        self.repo.mkdir()
        (self.repo / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
        self.logger = audit.AuditLogger(root / "audit/events.jsonl")
        self.context = backend.BackendContext(
            repo_root=self.repo,
            permission=permission.PermissionEngine(self.repo, permission.load_policy()),
            audit=self.logger,
            episode_id="atomic-test",
            action_id="pending",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_valid_tool_call_creates_exactly_one_backend_attempt(self):
        source = json.dumps({"type": "tool_call", "operation": "read_file", "arguments": {"path": "sample.py"}})
        result = atomic.execute_action(source, self.context, "action-1")
        self.assertEqual("ok", result.parse_status)
        self.assertEqual(1, len(result.backend_op_ids))
        self.assertEqual(1, len(self.logger.read_events()))
        self.assertTrue(json.loads(result.observation)["responses"][0]["ok"])

    def test_finish_and_malformed_actions_do_not_call_backend(self):
        finish = atomic.execute_action('{"type":"finish","message":"done"}', self.context, "finish")
        malformed = atomic.execute_action("{", self.context, "bad")
        self.assertEqual("finish", finish.parse_status)
        self.assertEqual("invalid", malformed.parse_status)
        self.assertEqual([], self.logger.read_events())

    def test_permission_denial_is_returned_and_audited(self):
        source = json.dumps({"type": "tool_call", "operation": "read_file", "arguments": {"path": "../secret"}})
        result = atomic.execute_action(source, self.context, "denied")
        self.assertEqual("permission_denied", result.error["code"])
        self.assertEqual("permission_denied", self.logger.read_events()[0]["status"])


if __name__ == "__main__":
    unittest.main()
