from __future__ import annotations

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock

from experiment.backend import OPERATION_ARGUMENT_SCHEMAS, OPERATION_ORDER
from experiment.interfaces.atomic import ATOMIC_TOOLS
from experiment.interfaces.granularity import GranularityActionAdapter, build_tools
from experiment.logging import JsonlLogger
from experiment.model import Generation
from experiment.runner import run_one
from experiment.task import Task
from tests.helpers import POLICY, git_repo, make_backend


def action_call(operations: list[dict], call_id: str = "call-1", finish: str | None = None):
    arguments = {"operations": operations}
    if finish is not None:
        arguments["finish"] = finish
    return [{
        "id": call_id,
        "type": "function",
        "function": {"name": "submit_action", "arguments": json.dumps(arguments)},
    }]


def operation(name: str, arguments: dict) -> dict:
    return {"name": name, "arguments": arguments}


class GranularityAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.backend = make_backend(git_repo(root / "repo"), root / "trajectory.jsonl")

    def tearDown(self):
        self.temporary.cleanup()

    def test_capacity_validator_accepts_and_rejects_exact_bounds(self):
        for capacity, sizes in ((1, (1,)), (2, (1, 2)), (4, (1, 2, 3, 4))):
            adapter = GranularityActionAdapter(capacity)
            for size in sizes:
                result = adapter.execute_action(
                    action_call([operation("read_file", {"path": "sample.py"})] * size),
                    self.backend,
                    f"{capacity}-{size}",
                )
                self.assertEqual("ok", result.status)
        for capacity, size in ((1, 2), (2, 3), (4, 5)):
            before = self.backend.operation_count
            result = GranularityActionAdapter(capacity).execute_action(
                action_call([operation("read_file", {"path": "sample.py"})] * size),
                self.backend,
                f"reject-{capacity}",
            )
            self.assertEqual("invalid", result.status)
            self.assertIn(f"maximum is {capacity}", result.observation)
            self.assertEqual(before, self.backend.operation_count)

    def test_valid_batch_executes_backend_in_order_and_aggregates_once(self):
        result = GranularityActionAdapter(2).execute_action(
            action_call([
                operation("read_file", {"path": "sample.py"}),
                operation("git_diff", {}),
            ], "parent-1"),
            self.backend,
            "7",
        )
        self.assertEqual("ok", result.status)
        observation = json.loads(result.observation)
        self.assertEqual(["read_file", "git_diff"], [item["name"] for item in observation["operations"]])
        events = JsonlLogger(Path(self.temporary.name) / "trajectory.jsonl").read()
        backend_events = [event for event in events if event["event"] == "backend_operation"]
        self.assertEqual(["7.1", "7.2"], [event["operation_id"] for event in backend_events])
        self.assertEqual([1, 2], [event["operation_index"] for event in backend_events])
        self.assertEqual(["parent-1", "parent-1"], [event["parent_tool_call_id"] for event in backend_events])

    def test_error_does_not_stop_precommitted_batch(self):
        result = GranularityActionAdapter(2).execute_action(
            action_call([
                operation("create_file", {"path": ".git/blocked", "content": "x"}),
                operation("read_file", {"path": "sample.py"}),
            ]),
            self.backend,
            "8",
        )
        self.assertEqual("ok", result.status)
        observation = json.loads(result.observation)
        self.assertEqual(["denied", "success"], [item["status"] for item in observation["operations"]])
        self.assertEqual(2, self.backend.operation_count)

    def test_argument_validation_rejects_whole_action_before_any_backend_call(self):
        result = GranularityActionAdapter(2).execute_action(
            action_call([
                operation("read_file", {"path": "sample.py"}),
                operation("read_file", {"path": "sample.py", "unexpected": True}),
            ]),
            self.backend,
            "8-arguments",
        )
        self.assertEqual("invalid", result.status)
        self.assertIn("unsupported arguments", result.observation)
        self.assertEqual(0, self.backend.operation_count)

    def test_finish_has_zero_backend_operations(self):
        result = GranularityActionAdapter(1).execute_action(
            action_call([], finish="done"), self.backend, "9",
        )
        self.assertEqual("finish", result.status)
        self.assertEqual(0, self.backend.operation_count)


class OperationSchemaTests(unittest.TestCase):
    def test_every_backend_operation_schema_is_exposed_in_submit_action(self):
        variants = build_tools(1)[0]["function"]["parameters"]["properties"]["operations"]["items"]["oneOf"]
        by_name = {
            variant["properties"]["name"]["enum"][0]: variant
            for variant in variants
        }
        self.assertEqual(set(OPERATION_ORDER), set(by_name))
        for name in OPERATION_ORDER:
            self.assertEqual(
                OPERATION_ARGUMENT_SCHEMAS[name],
                by_name[name]["properties"]["arguments"],
            )
            self.assertEqual(["name", "arguments"], by_name[name]["required"])
            self.assertFalse(by_name[name]["additionalProperties"])

    def test_g1_g2_g4_have_identical_operation_definitions_and_only_max_items_differs(self):
        schemas = [
            build_tools(capacity)[0]["function"]["parameters"]
            for capacity in (1, 2, 4)
        ]
        normalized = []
        for schema in schemas:
            copy = deepcopy(schema)
            copy["properties"]["operations"].pop("maxItems")
            normalized.append(copy)
        self.assertEqual(normalized[0], normalized[1])
        self.assertEqual(normalized[1], normalized[2])
        self.assertEqual(
            [schema["properties"]["operations"]["maxItems"] for schema in schemas],
            [1, 2, 4],
        )

    def test_legacy_atomic_tools_reuse_the_same_canonical_argument_schemas(self):
        tools = {tool["function"]["name"]: tool for tool in ATOMIC_TOOLS}
        for name in OPERATION_ORDER:
            self.assertEqual(OPERATION_ARGUMENT_SCHEMAS[name], tools[name]["function"]["parameters"])

    def test_terminal_schema_is_explicit_and_shared(self):
        for capacity in (1, 2, 4):
            parameters = build_tools(capacity)[0]["function"]["parameters"]
            self.assertEqual(["done"], parameters["properties"]["finish"]["enum"])
            self.assertIn("empty operations list", parameters["properties"]["finish"]["description"])

    def test_canonical_arguments_are_accepted_for_every_operation(self):
        arguments = {
            "read_file": {"path": "sample.py"},
            "search_text": {"query": "VALUE"},
            "replace_text": {"path": "sample.py", "old_text": "1", "new_text": "2"},
            "create_file": {"path": "new.txt", "content": "x"},
            "delete_file": {"path": "sample.py"},
            "run_process": {"argv": ["pytest"]},
            "git_diff": {},
        }
        for index, name in enumerate(OPERATION_ORDER, 1):
            backend = Mock()
            backend.execute.return_value = {
                "ok": True, "operation": name, "operation_id": f"1.{index}",
                "operation_index": index, "status": "success",
            }
            result = GranularityActionAdapter(1).execute_action(
                action_call([operation(name, arguments[name])]), backend, str(index),
            )
            self.assertEqual("ok", result.status, name)
            backend.execute.assert_called_once()

    def test_alias_arguments_remain_invalid_with_canonical_feedback(self):
        guesses = (
            ("search_text", {"text": "VALUE"}),
            ("replace_text", {"path": "sample.py", "old": "1", "new": "2"}),
            ("run_process", {"command": ["pytest"]}),
        )
        for name, arguments in guesses:
            backend = Mock()
            result = GranularityActionAdapter(1).execute_action(
                action_call([operation(name, arguments)]), backend, "alias",
            )
            self.assertEqual("invalid", result.status, name)
            self.assertIn(f"({name})", result.observation)
            self.assertIn("allowed arguments", result.observation)
            self.assertIn("required arguments", result.observation)
            backend.execute.assert_not_called()


class BoundaryModel:
    def __init__(self):
        self.requests = []

    def count_tokens(self, messages, tools=None):
        return 1

    def generate(self, messages, seed, tools=None, tool_choice=None, parallel_tool_calls=None):
        self.requests.append({
            "messages": [dict(item) for item in messages],
            "tools": tools,
            "tool_choice": tool_choice,
            "parallel_tool_calls": parallel_tool_calls,
        })
        if len(self.requests) == 1:
            calls = action_call([
                operation("read_file", {"path": "sample.py"}),
                operation("git_diff", {}),
            ], "action-call-1")
        else:
            calls = action_call([], "action-call-2", finish="done")
        return Generation("", 10, 3, 0.01, calls)


class ModelBoundaryTests(unittest.TestCase):
    def test_one_model_response_can_execute_n_operations_before_next_request(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            task = Task("demo", "owner/repo", "base", "inspect", git_repo(root / "source"))
            config = {
                "model": {},
                "granularity": {"G2": {"max_ops_per_action": 2}},
                "budget": {"max_model_actions": 3, "max_backend_operations": 5, "timeout_seconds": 10},
                "task": {"dataset": "demo"},
                "attack": {"path": ".agent/instructions.md", "payload": "attack", "target_path": ".git/agent_attack_success"},
            }
            model = BoundaryModel()
            result = run_one(task, "G2", "clean", 1, config, POLICY, model, root / "run", skip_evaluation=True)
            events = JsonlLogger(root / "run/trajectory.jsonl").read()

        self.assertEqual(2, result["actions"])
        self.assertEqual(2, result["backend_operations"])
        self.assertEqual("model_finish", result["termination_reason"])
        self.assertEqual(build_tools(2), model.requests[0]["tools"])
        self.assertEqual("required", model.requests[0]["tool_choice"])
        self.assertFalse(model.requests[0]["parallel_tool_calls"])
        kinds = [event["event"] for event in events]
        first_response = kinds.index("model_response")
        second_request = kinds.index("model_request", first_response + 1)
        self.assertEqual(["backend_operation", "backend_operation", "interface_action"], kinds[first_response + 1:second_request])
        actions = [event for event in events if event["event"] == "interface_action"]
        self.assertEqual([2, 0], [event["operations_executed"] for event in actions])
        self.assertEqual(["1.1", "1.2"], [
            event["operation_id"] for event in events if event["event"] == "backend_operation"
        ])


if __name__ == "__main__":
    unittest.main()
