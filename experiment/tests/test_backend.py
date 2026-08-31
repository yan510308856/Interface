from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from experiment import audit, backend, permission


class BackendTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.repo = root / "repo"
        self.repo.mkdir()
        (self.repo / "sample.py").write_text("VALUE = 1\n", encoding="utf-8")
        tests = self.repo / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("", encoding="utf-8")
        (tests / "test_sample.py").write_text(
            "import unittest\n\nclass Sample(unittest.TestCase):\n"
            "    def test_value(self):\n        self.assertEqual(1, 1)\n",
            encoding="utf-8",
        )
        (tests / "test_slow.py").write_text(
            "import time\nimport unittest\n\nclass Slow(unittest.TestCase):\n"
            "    def test_slow(self):\n        time.sleep(2)\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(
            ["git", "-c", "user.name=R4", "-c", "user.email=r4@example.invalid", "commit", "-qm", "base"],
            cwd=self.repo,
            check=True,
        )
        policy = permission.load_policy()
        self.logger = audit.AuditLogger(root / "audit/events.jsonl")
        self.context = backend.BackendContext(
            repo_root=self.repo,
            permission=permission.PermissionEngine(self.repo, policy),
            audit=self.logger,
            episode_id="backend-test",
            action_id="action-01",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def call(self, operation: str, arguments: dict) -> dict:
        return backend.execute({"operation": operation, "arguments": arguments}, self.context)

    def test_all_eight_operations_and_audit_count(self):
        self.assertTrue(self.call("list_dir", {"path": ".", "recursive": False})["ok"])
        self.assertTrue(self.call("search_text", {"query": "VALUE", "path": "."})["ok"])
        self.assertTrue(self.call("read_file", {"path": "sample.py"})["ok"])
        self.assertTrue(self.call("replace_text", {"path": "sample.py", "old_text": "VALUE = 1", "new_text": "VALUE = 2", "expected_replacements": 1})["ok"])
        self.assertTrue(self.call("create_file", {"path": "created.txt", "content": "temporary\n"})["ok"])
        self.assertTrue(self.call("delete_file", {"path": "created.txt"})["ok"])
        process = self.call("run_process", {"argv": ["python3", "-m", "unittest", "tests.test_sample"], "timeout_seconds": 10})
        self.assertTrue(process["ok"])
        self.assertEqual(0, process["result"]["exit_code"])
        diff = self.call("git_diff", {"path": ".", "staged": False})
        self.assertTrue(diff["ok"])
        self.assertIn("VALUE = 2", diff["result"]["diff"])
        events = self.logger.read_events()
        self.assertEqual(8, len(events))
        self.assertTrue(all(event["result_digest"] for event in events))

    def test_denials_invalid_and_timeout_each_create_one_event(self):
        outside = self.call("read_file", {"path": "../secret"})
        command = self.call("run_process", {"argv": ["python3", "-c", "print(1)"], "timeout_seconds": 10})
        invalid = backend.execute({"operation": "unknown", "arguments": {}}, self.context)
        timed_out = self.call("run_process", {"argv": ["python3", "-m", "unittest", "tests.test_slow"], "timeout_seconds": 1})
        self.assertEqual("permission_denied", outside["error"]["code"])
        self.assertEqual("permission_denied", command["error"]["code"])
        self.assertEqual("invalid_request", invalid["error"]["code"])
        self.assertEqual("timeout", timed_out["error"]["code"])
        self.assertEqual(4, len(self.logger.read_events()))

    def test_audit_redacts_text_payloads(self):
        secret = "R3_CANARY_deadbeef"
        self.call("create_file", {"path": "note.txt", "content": secret})
        text = self.logger.path.read_text(encoding="utf-8")
        self.assertNotIn(secret, text)
        event = json.loads(text)
        self.assertIn("content_sha256", event["normalized_arguments"])

    def test_operation_budget_is_enforced_and_audited(self):
        self.context.operation_budget = 1
        self.assertTrue(self.call("read_file", {"path": "sample.py"})["ok"])
        denied = self.call("read_file", {"path": "sample.py"})
        self.assertEqual("limit_exceeded", denied["error"]["code"])
        self.assertEqual(2, len(self.logger.read_events()))


if __name__ == "__main__":
    unittest.main()
