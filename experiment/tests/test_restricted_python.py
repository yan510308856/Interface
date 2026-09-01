from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiment import audit, backend, permission
from experiment.interfaces import restricted_python


class RestrictedPythonTests(unittest.TestCase):
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
            episode_id="python-test",
            action_id="pending",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_one_program_can_call_backend_multiple_times_with_control_flow(self):
        source = (
            'read = repo.read_file("sample.py")\n'
            'if "VALUE = 1" in read["result"]["content"]:\n'
            '    for index in range(1):\n'
            '        repo.replace_text("sample.py", "VALUE = 1", "VALUE = 2")\n'
        )
        result = restricted_python.execute_action(source, self.context, "action-1")
        self.assertEqual("ok", result.parse_status)
        self.assertEqual(2, len(result.backend_op_ids))
        self.assertEqual("VALUE = 2\n", (self.repo / "sample.py").read_text(encoding="utf-8"))

    def test_open_import_and_subprocess_are_rejected_without_backend_events(self):
        programs = ('open("x", "w")', "import os", 'subprocess.run(["true"])')
        for number, source in enumerate(programs):
            with self.subTest(source=source):
                result = restricted_python.execute_action(source, self.context, f"bad-{number}")
                self.assertEqual("invalid", result.parse_status)
        self.assertEqual([], self.logger.read_events())
        self.assertFalse((self.repo / "x").exists())

    def test_one_whole_output_python_fence_is_format_only(self):
        result = restricted_python.execute_action(
            '```python\nrepo.read_file("sample.py")\n```', self.context, "fenced"
        )
        self.assertEqual("ok", result.parse_status)
        self.assertEqual(1, len(result.backend_op_ids))

    def test_qwen_fenced_clean_action_executes_unchanged_payload(self):
        source = '''```python
result = repo.read_file("sample.py")
if result["ok"]:
    content = result["result"]["content"]
    if "VALUE = 1" in content:
        repo.replace_text("sample.py", "VALUE = 1", "VALUE = 2")
        finish("done")
    else:
        finish("VALUE = 1 not found in sample.py")
else:
    finish("failed to read sample.py")
```'''
        result = restricted_python.execute_action(source, self.context, "qwen-fenced")
        self.assertEqual("finish", result.parse_status)
        self.assertEqual(2, len(result.backend_op_ids))
        self.assertEqual("VALUE = 2\n", (self.repo / "sample.py").read_text(encoding="utf-8"))

    def test_fence_with_prose_or_wrong_language_is_rejected(self):
        programs = (
            'Here is code:\n```python\nrepo.read_file("sample.py")\n```',
            '```javascript\nrepo.read_file("sample.py")\n```',
            '```python\nrepo.read_file("sample.py")\n```\n```python\nfinish("done")\n```',
        )
        for number, source in enumerate(programs):
            with self.subTest(source=source):
                result = restricted_python.execute_action(source, self.context, f"fence-{number}")
                self.assertEqual("invalid", result.parse_status)
        self.assertEqual([], self.logger.read_events())

    def test_loop_limit_is_enforced_before_body_execution(self):
        result = restricted_python.execute_action(
            'for index in range(1001):\n    repo.read_file("sample.py")',
            self.context,
            "loop",
        )
        self.assertEqual("invalid", result.parse_status)
        self.assertEqual([], self.logger.read_events())

    def test_backend_calls_before_an_interpreter_error_remain_in_result(self):
        result = restricted_python.execute_action(
            'repo.read_file("sample.py")\nmissing_name', self.context, "partial"
        )
        self.assertEqual("invalid", result.parse_status)
        self.assertEqual(1, len(result.backend_responses))
        self.assertEqual(1, len(self.logger.read_events()))

    def test_observation_is_valid_json_and_bounded(self):
        (self.repo / "large.txt").write_text("x" * 10000, encoding="utf-8")
        result = restricted_python.execute_action(
            'repo.read_file("large.txt")', self.context, "large"
        )
        observation = json.loads(result.observation)
        self.assertTrue(observation["truncated"])
        self.assertLessEqual(len(result.observation), 8192)

    def test_permission_denial_is_returned_and_audited(self):
        result = restricted_python.execute_action('repo.read_file("../secret")', self.context, "denied")
        self.assertEqual("permission_denied", result.error["code"])
        self.assertEqual("permission_denied", self.logger.read_events()[0]["status"])

    def test_finish_is_explicit_control_without_backend_authority(self):
        result = restricted_python.execute_action(
            'finish("complete")\nrepo.delete_file("sample.py")', self.context, "finish"
        )
        self.assertEqual("finish", result.parse_status)
        self.assertEqual([], result.backend_op_ids)
        self.assertEqual([], self.logger.read_events())
        self.assertTrue((self.repo / "sample.py").is_file())

    def test_prefilled_assignment_can_finish_without_backend_authority(self):
        result = restricted_python.execute_action(
            'result = finish("complete")', self.context, "prefilled-finish"
        )
        self.assertEqual("finish", result.parse_status)
        self.assertEqual([], result.backend_op_ids)


if __name__ == "__main__":
    unittest.main()
