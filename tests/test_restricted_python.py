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
    execute_code,
)
from tests.helpers import git_repo, make_backend


def envelope(arguments: object, name: str = RESTRICTED_PYTHON_TOOL_NAME) -> list[dict[str, object]]:
    return [{
        "id": "call-rp",
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }]


class RestrictedPythonBatchTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        repo = git_repo(root / "repo")
        (repo / "a.py").write_text("A = 1\n", encoding="utf-8")
        (repo / "b.py").write_text("B = 2\n", encoding="utf-8")
        self.backend = make_backend(repo, root / "log.jsonl")

    def tearDown(self):
        self.temporary.cleanup()

    def payload(self, result):
        return json.loads(result.observation)

    def assert_invalid(self, code: str, reason: str | None = None):
        result = execute_code(code, self.backend, "invalid")
        self.assertEqual("invalid", result.status)
        payload = self.payload(result)
        self.assertEqual("invalid", payload["status"])
        self.assertEqual("restricted_python_validation_error", payload["error_type"])
        self.assertEqual(0, payload["backend_operations_executed"])
        if reason is not None:
            self.assertEqual(reason, payload["reason"])
        return result

    def test_envelope_schema_is_one_code_string(self):
        function = RESTRICTED_PYTHON_TOOLS[0]["function"]
        self.assertEqual(RESTRICTED_PYTHON_TOOL_NAME, function["name"])
        self.assertEqual({"code": {"type": "string"}}, function["parameters"]["properties"])
        self.assertEqual(["code"], function["parameters"]["required"])
        self.assertFalse(function["parameters"]["additionalProperties"])

    def test_valid_batch_reads_two_files_and_diff_in_order(self):
        result = execute_code(
            'repo.read_file("a.py")\nrepo.read_file("b.py")\nrepo.git_diff()',
            self.backend,
            "valid-1",
        )
        self.assertEqual("ok", result.status)
        payload = self.payload(result)
        self.assertEqual("ok", payload["status"])
        self.assertEqual(["read_file", "read_file", "git_diff"], [
            item["name"] for item in payload["operations"]
        ])
        self.assertEqual([1, 2, 3], [item["index"] for item in payload["operations"]])
        self.assertEqual("a.py", payload["operations"][0]["arguments"]["path"])
        self.assertEqual(3, self.backend.operation_count)

    def test_valid_batch_searches_then_reads_diff(self):
        result = execute_code('repo.search_text("Foo", path=".")\nrepo.git_diff()', self.backend, "valid-2")
        self.assertEqual("ok", result.status)
        self.assertEqual(["search_text", "git_diff"], [item["name"] for item in self.payload(result)["operations"]])

    def test_valid_batch_runs_process_then_diff(self):
        result = execute_code(
            'runner.run_process(["python", "-m", "pytest", "--version"])\nrepo.git_diff()',
            self.backend,
            "valid-3",
        )
        self.assertEqual("ok", result.status)
        self.assertEqual(["run_process", "git_diff"], [item["name"] for item in self.payload(result)["operations"]])

    def test_backend_permission_is_used_for_every_batch_operation(self):
        original_check = self.backend.permission.check
        self.backend.permission.check = Mock(wraps=original_check)
        result = execute_code('repo.read_file("a.py")\nrepo.git_diff()', self.backend, "permission")
        self.assertEqual("ok", result.status)
        self.assertEqual(2, self.backend.permission.check.call_count)
        self.assertEqual(["read_file", "git_diff"], [
            event["operation"] for event in self.backend.logger.read()
            if event["event"] == "backend_operation"
        ])

    def test_local_assignment_is_rejected(self):
        self.assert_invalid('r = repo.read_file("a.py")', "local assignment is not allowed in batch mode")

    def test_result_dependent_name_and_subscript_are_rejected(self):
        self.assert_invalid('repo.read_file(r["path"])', "local computation is not allowed in batch mode")
        self.assert_invalid('repo.read_file(r)', "local computation is not allowed in batch mode")

    def test_control_flow_is_rejected(self):
        self.assert_invalid('if True:\n    repo.git_diff()', "control flow is not allowed in batch mode")
        self.assert_invalid('for item in ["a"]:\n    repo.git_diff()', "control flow is not allowed in batch mode")
        self.assert_invalid('while True:\n    break', "control flow is not allowed in batch mode")

    def test_local_builtins_and_string_processing_are_rejected(self):
        self.assert_invalid('len("x")', "only canonical Backend capability calls are allowed")
        self.assert_invalid('content.split(" ")', "local computation is not allowed in batch mode")
        self.assert_invalid('print("x")', "only canonical Backend capability calls are allowed")
        self.assert_invalid('content.replace("a", "b")', "local computation is not allowed in batch mode")

    def test_try_augassign_and_other_statements_are_rejected(self):
        self.assert_invalid(
            'try:\n    repo.git_diff()\nexcept Exception:\n    pass',
            "try/except is not allowed in batch mode",
        )
        self.assert_invalid('total += 1', "local assignment is not allowed in batch mode")
        self.assert_invalid('pass', "only canonical Backend capability calls are allowed")
        self.assert_invalid('"literal"', "only canonical Backend capability calls are allowed")
        self.assert_invalid('repo.read_file("a.py", "b.py", "c.py", "d.py")', "too many positional arguments")
        self.assert_invalid('repo.read_file("a.py", path="b.py")', "duplicate argument: path")

    def test_only_canonical_capabilities_are_allowed(self):
        unsafe_sources = (
            'open("x", "w")',
            'os.system("id")',
            'subprocess.run(["id"])',
            'pathlib.Path("x")',
            'git.Repo(".")',
            'repo.unknown_operation()',
            'runner.unknown_operation()',
            'm.some_model()',
        )
        for source in unsafe_sources:
            self.assert_invalid(source, "only canonical Backend capability calls are allowed")
        for source in ('open("x", "w")', 'os.system("id")', 'subprocess.run(["id"])', 'pathlib.Path("x")'):
            result = execute_code(source, self.backend, "unsafe")
            self.assertTrue(result.unsafe_attempt, source)

    def test_imports_direct_apis_and_arbitrary_methods_are_rejected(self):
        for source in (
            "import os", "from pathlib import Path", 'socket.socket()', 'requests.get("https://example.com")',
            'shutil.copy("a", "b")', 'repo.read_file("a.py").get("result")',
        ):
            self.assert_invalid(source)
        self.assertEqual(0, self.backend.operation_count)

    def test_whole_action_validation_prevents_partial_execution(self):
        for code in (
            'repo.read_file("a.py")\nprint("bad")',
            'repo.read_file("a.py")\nif True:\n    repo.git_diff()',
        ):
            self.assert_invalid(code)
        self.assertEqual(0, self.backend.operation_count)

    def test_aggregated_observation_includes_success_and_error(self):
        result = execute_code(
            'repo.read_file("a.py")\nrepo.read_file("missing.py")\nrepo.git_diff()',
            self.backend,
            "aggregate",
        )
        payload = self.payload(result)
        self.assertEqual(["read_file", "read_file", "git_diff"], [item["name"] for item in payload["operations"]])
        self.assertEqual(["success", "error", "success"], [item["status"] for item in payload["operations"]])
        self.assertIn("result", payload["operations"][0])
        self.assertIn("error", payload["operations"][1])
        self.assertEqual(3, len(result.responses))

    def test_operation_budget_error_is_still_aggregated(self):
        self.backend.max_operations = 1
        result = execute_code('repo.git_diff()\nrepo.git_diff()', self.backend, "budget")
        self.assertEqual("ok", result.status)
        self.assertEqual(["success", "error"], [item["status"] for item in self.payload(result)["operations"]])

    def test_structured_envelope_requires_exactly_one_call_and_code_only(self):
        invalid_inputs = (
            [],
            envelope({"code": 'repo.read_file("a.py")'}) * 2,
            envelope({"code": 'repo.read_file("a.py")'}, name="read_file"),
            envelope({}),
            envelope({"code": 1}),
            envelope({"code": 'repo.read_file("a.py")', "extra": True}),
        )
        for tool_calls in invalid_inputs:
            self.assertEqual("invalid", execute_envelope(tool_calls, self.backend, "envelope").status)
        self.assertEqual(0, self.backend.operation_count)

    def test_invalid_batch_returns_model_visible_structured_feedback(self):
        result = execute_envelope(envelope({"code": 'r = repo.search_text("Foo", path=".")'}), self.backend, "feedback")
        payload = self.payload(result)
        self.assertEqual({
            "status": "invalid",
            "error_type": "restricted_python_validation_error",
            "reason": "local assignment is not allowed in batch mode",
            "backend_operations_executed": 0,
        }, payload)

    def test_finish_is_only_valid_terminal_statement(self):
        done = execute_envelope(envelope({"code": 'finish("done")'}), self.backend, "done")
        self.assertEqual("finish", done.status)
        self.assertEqual(0, self.backend.operation_count)
        self.assert_invalid('finish("other")', 'completion must be exactly finish("done")')
        self.assert_invalid('finish("done")\nrepo.git_diff()', "finish must be the only statement")
        self.assert_invalid('repo.git_diff()\nfinish("done")', "finish must be the only statement")
        self.assert_invalid('finish("done")\nfinish("done")', "multiple finish calls are not allowed")

    def test_fenced_code_remains_deterministic_but_prose_is_not_executable(self):
        program = 'repo.read_file("a.py")'
        self.assertEqual(program + "\n", _extract_program(f"```python\n{program}\n```"))
        self.assertEqual("ok", execute_code(f"```python\n{program}\n```", self.backend, "fenced").status)
        self.assertEqual("invalid", execute_code("prose only", self.backend, "prose").status)

    def test_no_runtime_result_can_flow_between_operations(self):
        edited = execute_code('repo.replace_text("sample.py", "1", "2")', self.backend, "edit")
        self.assertEqual("ok", edited.status)
        self.assert_invalid('repo.read_file(edited["result"]["path"])', "local computation is not allowed in batch mode")
        reread = execute_code('repo.read_file("sample.py")', self.backend, "read")
        self.assertIn("VALUE = 2", reread.responses[0]["result"]["content"])


if __name__ == "__main__":
    unittest.main()
