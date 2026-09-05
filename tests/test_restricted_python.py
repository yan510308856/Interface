from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from experiment.interfaces.restricted_python import (
    RESTRICTED_PYTHON_TOOL_NAME,
    RESTRICTED_PYTHON_TOOLS,
    _extract_program,
    execute_action as execute_envelope,
    execute_code as execute_action,
)
from tests.helpers import git_repo, make_backend


def envelope(arguments: object, name: str = RESTRICTED_PYTHON_TOOL_NAME) -> list[dict[str, object]]:
    return [{
        "id": "call-rp",
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }]


class RestrictedPythonTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.backend = make_backend(git_repo(root / "repo"), root / "log.jsonl")

    def tearDown(self):
        self.temporary.cleanup()

    def test_envelope_schema_has_only_required_code_string(self):
        self.assertEqual(1, len(RESTRICTED_PYTHON_TOOLS))
        function = RESTRICTED_PYTHON_TOOLS[0]["function"]
        self.assertEqual(RESTRICTED_PYTHON_TOOL_NAME, function["name"])
        parameters = function["parameters"]
        self.assertEqual({"code": {"type": "string"}}, parameters["properties"])
        self.assertEqual(["code"], parameters["required"])
        self.assertFalse(parameters["additionalProperties"])

    def test_exactly_one_envelope_executes_and_aggregates_multiple_operations(self):
        code = 'r1 = repo.read_file("sample.py")\nr2 = repo.git_diff()'
        result = execute_envelope(envelope({"code": code}), self.backend, "structured")
        self.assertEqual("ok", result.status)
        self.assertEqual(["read_file", "git_diff"], [item["operation"] for item in result.responses])
        self.assertEqual(result.responses, json.loads(result.observation))
        self.assertEqual(2, self.backend.operation_count)

    def test_invalid_envelopes_never_execute_backend(self):
        invalid_inputs = (
            'repo.read_file("sample.py")',
            [],
            envelope({"code": 'repo.read_file("sample.py")'}) * 2,
            envelope({"code": 'repo.read_file("sample.py")'}, name="read_file"),
            envelope({}),
            envelope({"code": 1}),
            envelope({"code": 'repo.read_file("sample.py")', "extra": True}),
        )
        for tool_calls in invalid_inputs:
            result = execute_envelope(tool_calls, self.backend, "invalid-envelope")
            self.assertEqual("invalid", result.status)
        self.assertEqual(0, self.backend.operation_count)

    def test_validation_observation_has_stable_specific_reason(self):
        cases = (
            ('print("x")', "builtin is not allowed: print"),
            ('content = "abc"\ncontent.replace("a", "b")', "method is not allowed: content.replace"),
            ('try:\n    repo.git_diff()\nexcept Exception:\n    pass', "syntax is not allowed: Try"),
            ('while True:\n    break', "syntax is not allowed: While"),
            ('finish("not done")', 'completion must be exactly finish("done")'),
            ('repo.read_file("sample.py")\nfinish("done")', "finish must be the only statement"),
            ('finish("done")\nfinish("done")', "multiple finish calls are not allowed"),
        )
        for code, reason in cases:
            result = execute_envelope(envelope({"code": code}), self.backend, "specific")
            payload = json.loads(result.observation)
            self.assertEqual("invalid", result.status)
            self.assertEqual("restricted_python_validation_error", payload["error_type"])
            self.assertEqual(reason, payload["reason"])
            self.assertEqual(0, payload["backend_operations_executed"])

    def test_validation_is_all_or_nothing_before_backend_execution(self):
        programs = (
            'r = repo.read_file("sample.py")\nprint("bad")',
            'r = repo.search_text("VALUE", path=".")\nif r["ok"]:\n    repo.read_file("sample.py")\ntry:\n    pass\nexcept Exception:\n    pass',
        )
        for code in programs:
            result = execute_envelope(envelope({"code": code}), self.backend, "all-or-nothing")
            payload = json.loads(result.observation)
            self.assertEqual("invalid", result.status)
            self.assertEqual(0, payload["backend_operations_executed"])
        self.assertEqual(0, self.backend.operation_count)

    def test_finish_is_submitted_inside_envelope(self):
        done = execute_envelope(envelope({"code": 'finish("done")'}), self.backend, "done")
        other = execute_envelope(envelope({"code": 'finish("other")'}), self.backend, "other")
        mixed = execute_envelope(
            envelope({"code": 'repo.read_file("sample.py")\nfinish("done")'}),
            self.backend,
            "mixed",
        )
        self.assertEqual("finish", done.status)
        self.assertEqual("invalid", other.status)
        self.assertEqual("invalid", mixed.status)
        self.assertEqual(0, self.backend.operation_count)

    def test_raw_and_fenced_programs_work(self):
        program = 'repo.read_file("sample.py")'
        for source in (program, f"```python\n{program}\n```", f"I'll inspect the file.\n\n```python\n{program}\n```"):
            result = execute_action(source, self.backend, "1")
            self.assertEqual("ok", result.status)
        self.assertEqual(3, self.backend.operation_count)

    def test_empty_action_executes_zero_backend_operations(self):
        result = execute_action("", self.backend, "empty")
        self.assertEqual("ok", result.status)
        self.assertEqual([], result.responses)
        self.assertEqual(0, self.backend.operation_count)

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
            'if True:\n    finish("done")',
        ):
            result = execute_action(source, self.backend, "invalid-finish")
            self.assertEqual("invalid", result.status)
        self.assertEqual(0, self.backend.operation_count)

    def test_literal_finish_still_works(self):
        result = execute_action('finish("done")', self.backend, "finish")
        self.assertEqual("finish", result.status)
        self.assertEqual(0, self.backend.operation_count)

    def test_action_composes_backend_operations_in_order_through_permission(self):
        original_check = self.backend.permission.check
        self.backend.permission.check = Mock(wraps=original_check)
        source = (
            'r1 = repo.read_file("sample.py")\n'
            'r2 = repo.search_text("VALUE", path=".")\n'
            'if r1["ok"] and r2["ok"]:\n'
            '    r3 = repo.git_diff()'
        )
        result = execute_action(source, self.backend, "1")
        self.assertEqual("ok", result.status)
        self.assertEqual(3, self.backend.operation_count)
        self.assertEqual(["read_file", "search_text", "git_diff"], [
            response["operation"] for response in result.responses
        ])
        self.assertEqual(3, self.backend.permission.check.call_count)
        self.assertEqual(["read_file", "search_text", "git_diff"], [
            event["operation"] for event in self.backend.logger.read()
            if event["event"] == "backend_operation"
        ])

    def test_if_skips_later_backend_call_after_failed_response(self):
        source = (
            'r = repo.read_file("missing.py")\n'
            'if r["ok"]:\n'
            '    s = repo.search_text("never", path=".")'
        )
        result = execute_action(source, self.backend, "conditional")
        self.assertEqual("ok", result.status)
        self.assertEqual(1, self.backend.operation_count)
        self.assertFalse(result.responses[0]["ok"])

    def test_v5_pure_local_computation_drives_backend_call(self):
        source = (
            'text = "  Alpha beta  "\n'
            'prefix = text[2:7]\n'
            'parts = text.strip().split()\n'
            'if "Alpha" in text and "Gamma" not in text:\n'
            '    if prefix == "Alpha" and text.find("beta") >= 0:\n'
            '        if text.startswith("  ") and text.endswith("  ") and len(parts) == 2:\n'
            '            d = repo.git_diff()'
        )
        result = execute_action(source, self.backend, "pure")
        self.assertEqual("ok", result.status)
        self.assertEqual(["git_diff"], [item["operation"] for item in result.responses])

    def test_v5_range_enumerate_min_max_mutation_and_control_flow(self):
        source = (
            'items = []\n'
            'items.append("b")\n'
            'items.insert(0, "a")\n'
            'low = min([3, 1, 2])\n'
            'high = max([3, 1, 2])\n'
            'for i, item in enumerate(items):\n'
            '    if i == 0:\n'
            '        continue\n'
            '    if i == 2:\n'
            '        break\n'
            '    if item == "b" and low + 2 == high:\n'
            '        d = repo.git_diff()\n'
            'for j in range(1, 3):\n'
            '    if j == 2:\n'
            '        break'
        )
        result = execute_action(source, self.backend, "pure-loop")
        self.assertEqual("ok", result.status)
        self.assertEqual(1, self.backend.operation_count)

    def test_v5_backend_result_processing_and_multi_operation_order(self):
        source = (
            'r = repo.search_text("VALUE", path=".")\n'
            'if r["ok"] and r["result"]["matches"]:\n'
            '    for match in r["result"]["matches"]:\n'
            '        p = match["path"]\n'
            '        f = repo.read_file(p)\n'
            '        if f["ok"]:\n'
            '            text = f["result"]["content"]\n'
            '            if "VALUE" in text and text.find("VALUE") >= 0:\n'
            '                d = repo.git_diff()'
        )
        original_check = self.backend.permission.check
        self.backend.permission.check = Mock(wraps=original_check)
        result = execute_action(source, self.backend, "processed")
        self.assertEqual("ok", result.status)
        self.assertEqual(["search_text", "read_file", "git_diff"], [
            item["operation"] for item in result.responses
        ])
        self.assertEqual(3, self.backend.permission.check.call_count)

    def test_v5_reassignment_nested_subscripts_and_index_arithmetic(self):
        source = (
            'data = {"outer": {"items": ["zero", "one", "two"]}}\n'
            'data = data["outer"]\n'
            'items = data["items"]\n'
            'index = 1 - 0\n'
            'item = items[index]\n'
            'if item == "one" and items[0:2] == ["zero", "one"]:\n'
            '    d = repo.git_diff()'
        )
        result = execute_action(source, self.backend, "reassigned")
        self.assertEqual("ok", result.status)
        self.assertEqual(1, self.backend.operation_count)

    def test_v5_operation_budget_is_still_enforced(self):
        self.backend.max_operations = 1
        result = execute_action(
            'repo.git_diff()\nrepo.git_diff()', self.backend, "budget",
        )
        self.assertEqual("ok", result.status)
        self.assertEqual(2, self.backend.operation_count)
        self.assertEqual(["success", "error"], [item["status"] for item in result.responses])

    def test_general_python_computation_not_in_v5_subset_is_rejected(self):
        for source in (
            'content = "abc"\ncontent.replace("a", "b")',
            'items = []\nitems.pop()',
            'len([1])\nprint("x")',
            'for i in range(1):\n    pass',
            'while True:\n    break', 'break', 'continue', 'pass',
            'sum([1])', 'sorted([1])', 'try:\n    pass\nexcept Exception:\n    pass',
            'def f():\n    pass', 'lambda x: x', '[x for x in [1]]',
            '"abc".upper()', 'data = {}\ndata.get("x")',
            "foo()", "m.some_model()", "separability_matrix()",
            'replace_text("sample.py", "1", "2")', "git_diff()",
        ):
            result = execute_action(source, self.backend, "bad")
            self.assertEqual("invalid", result.status)
            self.assertFalse(result.unsafe_attempt)

    def test_direct_environment_apis_are_rejected(self):
        forbidden_sources = (
            'open("x", "w")', "exec(\"x\")", 'eval("x")', 'compile("x", "x", "exec")',
            '__import__("os")', "import os", 'os.system("id")',
            'subprocess.run(["id"])', "socket.socket()", 'pathlib.Path("x")',
            'Path("x")',
            'shutil.copy("a", "b")', 'tempfile.mkstemp()', 'requests.get("https://example.com")',
            'glob.glob("*")', 'repo.unknown_operation()',
            'runner.unknown_operation()', 'm._private()',
            'sys.exit()', 'inspect.getsource("x")', 'globals()', 'locals()',
            'vars()', 'getattr(data, "x")', 'setattr(data, "x", 1)',
            'delattr(data, "x")', 'hasattr(data, "x")', 'type(data)', 'object()',
        )
        for forbidden in forbidden_sources:
            result = execute_action(forbidden, self.backend, "bad")
            self.assertEqual("invalid", result.status)
            self.assertTrue(result.unsafe_attempt)
        syntax_error = execute_action("repo.read_file(", self.backend, "bad")
        self.assertEqual("invalid", syntax_error.status)
        self.assertFalse(syntax_error.unsafe_attempt)
        self.assertEqual(0, self.backend.operation_count)

    def test_v5_advanced_runtime_constructs_are_rejected(self):
        for source in (
            'with repo.read_file("sample.py") as value:\n    pass',
            'raise ValueError("x")',
            'async def f():\n    await repo.git_diff()',
            'class Example:\n    pass',
            'yield 1',
        ):
            result = execute_action(source, self.backend, "advanced")
            self.assertEqual("invalid", result.status)
            self.assertEqual(0, self.backend.operation_count)

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
