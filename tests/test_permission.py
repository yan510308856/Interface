from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from experiment.permission import PermissionEngine
from tests.helpers import POLICY


class PermissionTests(unittest.TestCase):
    def test_boundary_git_writes_and_commands_are_denied(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            repo.mkdir()
            engine = PermissionEngine(repo, POLICY)
            self.assertFalse(engine.check("read_file", {"path": "../secret"})[0])
            self.assertFalse(engine.check("create_file", {"path": ".git/config"})[0])
            self.assertFalse(engine.check("run_process", {"argv": ["sh", "-c", "id"]})[0])
            self.assertTrue(engine.check("read_file", {"path": "README.md"})[0])


if __name__ == "__main__":
    unittest.main()

