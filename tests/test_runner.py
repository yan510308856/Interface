from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from experiment import runner
from experiment.model import Generation
from experiment.runner import run_one
from experiment.task import Task
from tests.helpers import POLICY, git_repo


class FakeModel:
    def generate(self, messages, seed, tools=None, tool_choice=None):
        if tools is not None:
            return Generation("", 10, 3, 0.01, [{
                "id": "call-finish", "type": "function",
                "function": {"name": "finish", "arguments": "{\"message\":\"done\"}"},
            }])
        return Generation('finish("done")', 10, 3, 0.01)


class ConversationModel:
    def __init__(self):
        self.requests = []

    def generate(self, messages, seed, tools=None, tool_choice=None):
        self.requests.append({
            "messages": [dict(message) for message in messages],
            "tools": tools,
            "tool_choice": tool_choice,
        })
        if tools is not None and len(self.requests) == 1:
            return Generation("", 10, 3, 0.01, [{
                "id": "call-read", "type": "function",
                "function": {"name": "read_file", "arguments": "{\"path\":\"sample.py\"}"},
            }])
        if tools is not None:
            return Generation("", 10, 3, 0.01, [{
                "id": "call-finish", "type": "function",
                "function": {"name": "finish", "arguments": "{\"message\":\"done\"}"},
            }])
        return Generation('finish("done")', 10, 3, 0.01)


class RunnerTests(unittest.TestCase):
    def test_interface_prompts_require_protocol_compliance(self):
        common = runner.COMMON_PROMPT
        self.assertIn("make the smallest correct repository change", common)
        self.assertIn("Reason internally", common)
        self.assertIn("Do not finish merely because", common)
        self.assertIn("only after the repository task has actually been completed", common)
        for command in ("pytest ...", "python -m pytest ...", "python3 -m pytest ..."):
            self.assertIn(command, common)
        self.assertIn("python script.py", common)
        self.assertIn("python -c ...", common)

        atomic = runner.INTERFACE_PROMPTS["atomic"]
        self.assertIn("Use the provided tools to investigate and solve", atomic)
        self.assertIn("Make the smallest correct repository change", atomic)
        self.assertIn("Inspect the resulting diff", atomic)
        self.assertIn("Use finish only after the repository task has actually been completed", atomic)
        self.assertNotIn("JSON object", atomic)

        restricted = runner.INTERFACE_PROMPTS["restricted_python"]
        self.assertIn("exactly one restricted Python program", restricted)
        self.assertIn("Never output prose, analysis, Markdown, or code fences", restricted)
        self.assertIn("provided restricted Python capabilities", restricted)
        self.assertIn("If more investigation is needed, issue another restricted Python action", restricted)
        self.assertIn("finish(\"done\") only after the repository task has actually been completed", restricted)

    def test_atomic_uses_native_tools_and_tool_conversation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            task = Task("demo", "owner/repo", "base", "fix it", git_repo(root / "source"))
            config = {
                "budget": {"max_actions": 2, "max_operations": 5, "timeout_seconds": 10},
                "task": {"dataset": "demo"},
                "attack": {"path": ".agent/instructions.md", "payload": "attack", "target_path": ".git/agent_attack_success"},
            }
            model = ConversationModel()
            result = run_one(task, "atomic", "clean", 1, config, POLICY, model, root / "run", skip_evaluation=True)

        self.assertEqual(1, result["backend_operations"])
        self.assertEqual(runner.atomic.ATOMIC_TOOLS, model.requests[0]["tools"])
        self.assertEqual("auto", model.requests[0]["tool_choice"])
        assistant = model.requests[1]["messages"][-2]
        tool = model.requests[1]["messages"][-1]
        self.assertEqual("assistant", assistant["role"])
        self.assertEqual("call-read", assistant["tool_calls"][0]["id"])
        self.assertEqual("tool", tool["role"])
        self.assertEqual("call-read", tool["tool_call_id"])

    def test_restricted_python_does_not_send_native_tools(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            task = Task("demo", "owner/repo", "base", "fix it", git_repo(root / "source"))
            config = {
                "budget": {"max_actions": 1, "max_operations": 5, "timeout_seconds": 10},
                "task": {"dataset": "demo"},
                "attack": {"path": ".agent/instructions.md", "payload": "attack", "target_path": ".git/agent_attack_success"},
            }
            model = ConversationModel()
            run_one(task, "restricted_python", "clean", 1, config, POLICY, model, root / "run", skip_evaluation=True)

        self.assertIsNone(model.requests[0]["tools"])
        self.assertIsNone(model.requests[0]["tool_choice"])

    def test_seed_filter_runs_only_requested_seed(self):
        task = Task("demo", "owner/repo", "base", "fix it")
        config = {
            "model": {}, "task": {"file": "unused", "dataset": "demo"},
            "interfaces": ["atomic"], "conditions": ["clean"], "seeds": [1, 2, 3],
        }
        with patch.object(runner, "load_tasks", return_value=[task]), patch.object(runner, "Model"), patch.object(
            runner, "run_one", return_value={"seed": 1}
        ) as mocked_run:
            results = runner.run_experiment(config, POLICY, Path("unused"), seed_filter=1)
        self.assertEqual([{"seed": 1}], results)
        self.assertEqual(1, mocked_run.call_args.args[3])

    def test_one_run_writes_complete_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            task = Task("demo", "owner/repo", "base", "fix it", git_repo(root / "source"))
            config = {
                "budget": {"max_actions": 2, "max_operations": 5, "timeout_seconds": 10},
                "task": {"dataset": "demo"},
                "attack": {"path": ".agent/instructions.md", "payload": "attack", "target_path": ".git/agent_attack_success"},
            }
            result = run_one(
                task, "atomic", "clean", 1, config, POLICY, FakeModel(), root / "run",
                evaluator=lambda *args: True,
            )
            self.assertTrue(result["task_success"])
            self.assertFalse(result["unsafe_attempt"])
            self.assertEqual(1, result["actions"])
            self.assertTrue((root / "run/result.json").exists())
            self.assertTrue((root / "run/trajectory.jsonl").exists())

    def test_skip_evaluation_still_writes_patch_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            task = Task("demo", "owner/repo", "base", "fix it", git_repo(root / "source"))
            config = {
                "budget": {"max_actions": 2, "max_operations": 5, "timeout_seconds": 10},
                "task": {"dataset": "demo"},
                "attack": {"path": ".agent/instructions.md", "payload": "attack", "target_path": ".git/agent_attack_success"},
            }
            result = run_one(
                task, "atomic", "clean", 1, config, POLICY, FakeModel(), root / "run",
                evaluator=lambda *args: self.fail("evaluator should not run"),
                skip_evaluation=True,
            )
            self.assertIsNone(result["task_success"])
            self.assertIsNone(result["outcome"])
            self.assertTrue(result["evaluation_skipped"])
            self.assertIn("final_patch", result)


if __name__ == "__main__":
    unittest.main()
