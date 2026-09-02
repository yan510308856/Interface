from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import git_repo, make_backend


class BackendTests(unittest.TestCase):
    def test_file_search_edit_and_diff_use_one_backend(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = git_repo(root / "repo")
            backend = make_backend(repo, root / "trajectory.jsonl")
            self.assertTrue(backend.execute("read_file", {"path": "sample.py"}, "1")["ok"])
            self.assertEqual(1, len(backend.execute("search_text", {"query": "VALUE"}, "2")["result"]["matches"]))
            backend.execute("replace_text", {"path": "sample.py", "old_text": "1", "new_text": "2"}, "3")
            backend.execute("create_file", {"path": "new.txt", "content": "x"}, "4")
            backend.execute("delete_file", {"path": "new.txt"}, "5")
            backend.execute("create_file", {"path": "added.txt", "content": "new"}, "6")
            diff = backend.execute("git_diff", {"path": "."}, "7")
            self.assertIn("VALUE = 2", diff["result"]["diff"])
            self.assertIn("added.txt", backend.final_patch())


if __name__ == "__main__":
    unittest.main()
