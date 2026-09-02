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
    def generate(self, messages, seed):
        text = '{"type":"finish","message":"done"}' if "JSON action" in messages[0]["content"] else 'finish("done")'
        return Generation(text, 10, 3, 0.01)


class RunnerTests(unittest.TestCase):
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
