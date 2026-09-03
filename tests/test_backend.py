from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import git_repo, make_backend


class BackendTests(unittest.TestCase):
    def test_read_file_default_bound_and_explicit_ranges(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = git_repo(root / "repo")
            backend = make_backend(repo, root / "trajectory.jsonl")

            small = backend.execute("read_file", {"path": "sample.py"}, "small")
            self.assertTrue(small["ok"])
            self.assertEqual({"start_line": 1, "end_line": 1, "total_lines": 1, "truncated": False}, {
                key: small["result"][key] for key in ("start_line", "end_line", "total_lines", "truncated")
            })

            (repo / "large.py").write_text("".join(f"line {number}\n" for number in range(1, 806)), encoding="utf-8")
            first_page = backend.execute("read_file", {"path": "large.py"}, "first")
            self.assertTrue(first_page["ok"])
            first_result = first_page["result"]
            self.assertEqual((1, 400, 805, True), tuple(first_result[key] for key in ("start_line", "end_line", "total_lines", "truncated")))
            self.assertEqual(400, len(first_result["content"].splitlines()))
            self.assertNotIn("line 401\n", first_result["content"])

            second_page = backend.execute("read_file", {"path": "large.py", "start_line": 401}, "second")
            self.assertTrue(second_page["ok"])
            second_result = second_page["result"]
            self.assertEqual((401, 800, 805, True), tuple(second_result[key] for key in ("start_line", "end_line", "total_lines", "truncated")))
            self.assertEqual("line 401\n", second_result["content"].splitlines(keepends=True)[0])

            exact = backend.execute("read_file", {"path": "large.py", "start_line": 10, "end_line": 12}, "exact")
            self.assertTrue(exact["ok"])
            self.assertEqual("line 10\nline 11\nline 12\n", exact["result"]["content"])
            self.assertEqual((10, 12, 805, False), tuple(exact["result"][key] for key in ("start_line", "end_line", "total_lines", "truncated")))

            invalid = backend.execute("read_file", {"path": "large.py", "start_line": 12, "end_line": 10}, "invalid")
            self.assertFalse(invalid["ok"])
            self.assertIn("invalid line range", invalid["error"])

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
