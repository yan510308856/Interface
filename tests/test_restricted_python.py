from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from experiment.interfaces.restricted_python import _extract_program, execute_action
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

    def test_multiple_python_fenced_programs_are_not_salvaged(self):
        source = (
            'prose\n```python\nrepo.search_text("x", ".")\n```\n'
            'more prose\n```py\nrepo.read_file("sample.py")\n```'
        )
        with self.assertRaisesRegex(ValueError, "at most one"):
            _extract_program(source)
        result = execute_action(source, self.backend, "1")
        self.assertEqual("invalid", result.status)
        self.assertEqual(0, self.backend.operation_count)

    def test_mixed_or_non_python_fenced_programs_are_invalid(self):
        mixed = '```python\nrepo.read_file("sample.py")\n```\n```javascript\nopen("x")\n```'
        non_python = '```javascript\nrepo.read_file("sample.py")\n```'
        for source in (mixed, non_python):
            result = execute_action(source, self.backend, "bad")
            self.assertEqual("invalid", result.status)
        self.assertEqual(0, self.backend.operation_count)

    def test_malformed_or_unclosed_fences_are_invalid(self):
        for source in (
            "```python\nrepo.read_file(\"sample.py\")",
            "```python repo.read_file(\"sample.py\")\n```",
            "```python\nrepo.read_file(\"sample.py\")\n``` trailing text",
        ):
            result = execute_action(source, self.backend, "bad")
            self.assertEqual("invalid", result.status)
        self.assertEqual(0, self.backend.operation_count)

    def test_prose_only_is_invalid(self):
        result = execute_action("Looking at this issue, I need to inspect the file.", self.backend, "prose")
        self.assertEqual("invalid", result.status)
        self.assertEqual(0, self.backend.operation_count)

    def test_prose_with_standalone_finish_is_invalid(self):
        for source in (
            'Task completed.\nfinish("done")',
            "Done.\n\nfinish('done')",
        ):
            result = execute_action(source, self.backend, "finish")
            self.assertEqual("invalid", result.status)
        self.assertEqual(0, self.backend.operation_count)

    def test_a100_style_prose_fences_and_finish_are_invalid(self):
        sources = (
            """Natural-language final summary...
```python
cright[...] = 1
```

Explanation...

finish("done")""",
            """The example below is quoted for context.
```python
repo.read_file("sample.py")
```
The task is complete.
finish('done')""",
            """prose
```python
repo.read_file("sample.py")
```
finish("done")""",
        )
        for source in sources:
            result = execute_action(source, self.backend, "quoted-finish")
            self.assertEqual("invalid", result.status)
        self.assertEqual(0, self.backend.operation_count)

    def test_finish_with_other_actions_is_still_terminal_only(self):
        for source in (
            'Summary\nrepo.read_file("sample.py")\nfinish("done")',
            'Summary\nrepo.replace_text("sample.py", "1", "2")\nfinish("done")',
            'Summary\nfinish("done")\nfinish("done")',
        ):
            result = execute_action(source, self.backend, "invalid-finish")
            self.assertEqual("invalid", result.status)
        self.assertEqual(0, self.backend.operation_count)

    def test_finish_is_the_only_terminal_action(self):
        for source in (
            'finish("done")\nfinish("done")',
            'repo.read_file("sample.py")\nfinish("done")',
            'finish("done")\nrepo.read_file("sample.py")',
            'print("x")\nfinish("done")',
            'value = 1\nfinish("done")',
            'foo()\nfinish("done")',
            'finish(variable)',
            'finish()',
            'finish("complete")',
            'finish(message="done")',
        ):
            result = execute_action(source, self.backend, "invalid-finish")
            self.assertEqual("invalid", result.status)
        self.assertEqual(0, self.backend.operation_count)

    def test_literal_finish_still_works(self):
        result = execute_action('finish("done")', self.backend, "finish")
        self.assertEqual("finish", result.status)
        self.assertEqual(0, self.backend.operation_count)

    def test_program_composes_operations_and_blocks_python_apis(self):
        source = 'value = repo.read_file("sample.py")\nif "VALUE" in value["result"]["content"]:\n    repo.replace_text("sample.py", "1", "2")'
        result = execute_action(source, self.backend, "1")
        self.assertEqual("ok", result.status)
        self.assertEqual(2, self.backend.operation_count)
        for source in (
            'print("x")', "foo()", "m.some_model()", "separability_matrix()",
            'replace_text("sample.py", "1", "2")', "git_diff()",
        ):
            result = execute_action(source, self.backend, "bad")
            self.assertEqual("invalid", result.status)
            self.assertFalse(result.unsafe_attempt)
        forbidden_sources = (
            'open("x", "w")', "exec(\"x\")", 'eval("x")', 'compile("x", "x", "exec")',
            '__import__("os")', "import os", 'os.system("id")',
            'subprocess.run(["id"])', "socket.socket()", 'repo.unknown_operation()',
            'runner.unknown_operation()', 'm._private()',
        )
        for forbidden in forbidden_sources:
            result = execute_action(forbidden, self.backend, "bad")
            self.assertEqual("invalid", result.status)
            self.assertTrue(result.unsafe_attempt)
        syntax_error = execute_action("repo.read_file(", self.backend, "bad")
        self.assertEqual("invalid", syntax_error.status)
        self.assertFalse(syntax_error.unsafe_attempt)
        self.assertEqual(2, self.backend.operation_count)

    def test_locals_reset_but_repository_changes_persist_between_responses(self):
        edited = execute_action(
            'r = repo.replace_text("sample.py", "1", "2")', self.backend, "edit",
        )
        self.assertEqual("ok", edited.status)

        stale_local = execute_action('repo.read_file(r["result"]["path"])', self.backend, "stale")
        self.assertEqual("invalid", stale_local.status)

        reread = execute_action('repo.read_file("sample.py")', self.backend, "read")
        self.assertEqual("ok", reread.status)
        self.assertIn("VALUE = 2", reread.responses[0]["result"]["content"])


if __name__ == "__main__":
    unittest.main()
