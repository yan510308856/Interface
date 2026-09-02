from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from experiment.interfaces.restricted_python import execute_action
from tests.helpers import git_repo, make_backend


class RestrictedPythonTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.backend = make_backend(git_repo(root / "repo"), root / "log.jsonl")

    def tearDown(self):
        self.temporary.cleanup()

    def test_raw_and_fenced_programs_work(self):
        program = 'repo.read_file("sample.py")'
        for source in (program, f"```python\n{program}\n```", f"I'll inspect the file.\n\n```python\n{program}\n```"):
            result = execute_action(source, self.backend, "1")
            self.assertEqual("ok", result.status)
        self.assertEqual(3, self.backend.operation_count)

    def test_multiple_fenced_programs_are_invalid(self):
        program = '```python\nrepo.read_file("sample.py")\n```'
        result = execute_action(f"{program}\n{program}", self.backend, "bad")
        self.assertEqual("invalid", result.status)
        self.assertEqual(0, self.backend.operation_count)

    def test_program_composes_operations_and_blocks_python_apis(self):
        source = 'value = repo.read_file("sample.py")\nif "VALUE" in value["result"]["content"]:\n    repo.replace_text("sample.py", "1", "2")'
        result = execute_action(source, self.backend, "1")
        self.assertEqual("ok", result.status)
        self.assertEqual(2, self.backend.operation_count)
        forbidden_sources = ('```python\nopen("x", "w")\n```', "import os", 'subprocess.run(["id"])', 'eval("1")')
        for forbidden in forbidden_sources:
            result = execute_action(forbidden, self.backend, "bad")
            self.assertEqual("invalid", result.status)
            self.assertTrue(result.unsafe_attempt)
        self.assertEqual(2, self.backend.operation_count)


if __name__ == "__main__":
    unittest.main()
