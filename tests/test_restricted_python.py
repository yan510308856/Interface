from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from experiment.interfaces.restricted_python import execute_action
from tests.helpers import git_repo, make_backend


class RestrictedPythonTests(unittest.TestCase):
    def test_program_composes_operations_and_blocks_python_apis(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = git_repo(root / "repo")
            backend = make_backend(repo, root / "log.jsonl")
            source = 'value = repo.read_file("sample.py")\nif "VALUE" in value["result"]["content"]:\n    repo.replace_text("sample.py", "1", "2")'
            result = execute_action(source, backend, "1")
            self.assertEqual("ok", result.status)
            self.assertEqual(2, backend.operation_count)
            for forbidden in ('open("x", "w")', "import os", 'subprocess.run(["id"])', 'eval("1")'):
                result = execute_action(forbidden, backend, "bad")
                self.assertEqual("invalid", result.status)
                self.assertTrue(result.unsafe_attempt)
            self.assertEqual(2, backend.operation_count)


if __name__ == "__main__":
    unittest.main()
