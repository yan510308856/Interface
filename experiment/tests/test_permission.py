from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from experiment import permission


class PermissionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repo = Path(self.temporary.name) / "repo"
        self.repo.mkdir()
        self.policy = permission.load_policy()
        self.engine = permission.PermissionEngine(self.repo, self.policy)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_repository_path_is_allowed(self):
        decision = self.engine.decide("read_file", {"path": "src/example.py"})
        self.assertTrue(decision["allowed"])

    def test_outside_and_absolute_paths_are_denied(self):
        self.assertFalse(
            self.engine.decide("read_file", {"path": "../secret"})["allowed"]
        )
        self.assertFalse(
            self.engine.decide("read_file", {"path": "/etc/passwd"})["allowed"]
        )

    def test_symlink_escape_and_git_write_are_denied(self):
        outside = Path(self.temporary.name) / "outside.txt"
        outside.write_text("secret", encoding="utf-8")
        (self.repo / "link").symlink_to(outside)
        self.assertFalse(self.engine.decide("read_file", {"path": "link"})["allowed"])
        self.assertFalse(
            self.engine.decide("create_file", {"path": ".git/config"})["allowed"]
        )

    def test_process_requires_exact_argv(self):
        allowed = ["python3", "-m", "unittest", "tests.test_sample"]
        self.assertTrue(self.engine.decide("run_process", {"argv": allowed})["allowed"])
        self.assertFalse(
            self.engine.decide("run_process", {"argv": ["python3", "-c", "print(1)"]})[
                "allowed"
            ]
        )


if __name__ == "__main__":
    unittest.main()
