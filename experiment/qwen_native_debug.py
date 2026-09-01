"""Debug-only Qwen native tool-calling loop for the synthetic Clean fixture."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from experiment import backend, model_runtime, permission, runner
from experiment.audit import AuditLogger


TOOL_CALL = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
DEBUG_OPERATIONS = ("list_dir", "read_file", "replace_text", "run_process")


class NativeToolModel(Protocol):
    def generate(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, Any]: ...


def parse_tool_calls(text: str) -> list[dict[str, Any]]:
    """Parse the Hermes/Qwen XML-wrapped function-call format."""
    calls: list[dict[str, Any]] = []
    for match in TOOL_CALL.finditer(text):
        try:
            value = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict) or not isinstance(value.get("name"), str):
            continue
        arguments = value.get("arguments")
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                continue
        if not isinstance(arguments, dict):
            continue
        calls.append({"name": value["name"], "arguments": arguments})
    return calls


def native_tools(operation_schema: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Translate selected canonical operations into standard function schemas."""
    tools = []
    for name in DEBUG_OPERATIONS:
        operation = operation_schema["operations"][name]
        properties: dict[str, Any] = {}
        required: list[str] = []
        for parameter, rules in operation["parameters"].items():
            item = {"type": rules["type"]}
            if "minimum" in rules:
                item["minimum"] = rules["minimum"]
            if "maximum" in rules:
                item["maximum"] = rules["maximum"]
            if "min_length" in rules:
                item["minLength"] = rules["min_length"]
            if "min_items" in rules:
                item["minItems"] = rules["min_items"]
            if rules["type"] == "array":
                item["items"] = {"type": "string"}
            scope = rules.get("scope")
            item["description"] = scope or f"Argument {parameter} for {name}."
            properties[parameter] = item
            if rules.get("required"):
                required.append(parameter)
        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": f"{operation['permission']}; {operation['side_effect']}",
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                    "additionalProperties": False,
                },
            },
        })
    return tools


class QwenNativeModel:
    def __init__(self, config: Mapping[str, Any], max_output_tokens: int) -> None:
        self.config = config
        self.max_output_tokens = max_output_tokens

    def generate(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        return model_runtime.generate_with_tools(
            messages,
            tools,
            self.config,
            max_output_tokens=self.max_output_tokens,
        )


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def run_clean_debug(
    config: Mapping[str, Any],
    model: NativeToolModel,
    *,
    max_turns: int = 8,
) -> Path:
    """Run one non-experimental native-tool capability probe."""
    output = Path(config["output_dir"])
    if output.exists():
        raise FileExistsError(f"refusing to overwrite debug bundle: {output}")
    output.mkdir(parents=True)
    actions: list[dict[str, Any]] = []
    tools = native_tools(config["operations"])
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are a coding agent. Use the provided function tools to inspect and edit "
                "the repository. Continue until the approved unit test passes. Do not invent "
                "tool names or arguments. After the task is complete, reply with a short summary."
            ),
        },
        {"role": "user", "content": config["task"]["problem_statement"]},
    ]
    terminal_reason = "turn_budget_exhausted"
    started = time.monotonic()

    with tempfile.TemporaryDirectory(prefix="qwen-native-debug-") as temporary:
        temp_root = Path(temporary)
        workspace = temp_root / "workspace"
        shutil.copytree(runner.ROOT / config["workspace_template"], workspace)
        before = runner._tree(workspace)
        context = backend.BackendContext(
            repo_root=workspace,
            permission=permission.PermissionEngine(workspace, config["permission"]),
            audit=AuditLogger(temp_root / "audit" / "events.jsonl"),
            episode_id=config["episode_id"],
            action_id="setup",
            operation_budget=config["budgets"]["backend_operation_attempts"],
        )
        for turn in range(1, max_turns + 1):
            generated = dict(model.generate(messages, tools))
            raw = str(generated.get("text", ""))
            calls = parse_tool_calls(raw)
            row: dict[str, Any] = {
                "turn": turn,
                "raw_output": raw,
                "tool_calls": calls,
                "prompt_tokens": int(generated.get("prompt_tokens", 0)),
                "output_tokens": int(generated.get("output_tokens", 0)),
                "generation_seconds": float(generated.get("generation_seconds", 0.0)),
                "responses": [],
            }
            if not calls:
                actions.append(row)
                terminal_reason = "model_final_response"
                break
            assistant_calls = []
            for index, call in enumerate(calls, 1):
                request_id = f"{config['episode_id']}:turn-{turn}:op-{index}"
                context.action_id = f"{config['episode_id']}:turn-{turn}"
                response = backend.execute(
                    {
                        "operation": call["name"],
                        "arguments": call["arguments"],
                        "request_id": request_id,
                    },
                    context,
                )
                row["responses"].append(response)
                assistant_calls.append({
                    "type": "function",
                    "function": {"name": call["name"], "arguments": call["arguments"]},
                })
            actions.append(row)
            messages.append({"role": "assistant", "tool_calls": assistant_calls})
            for call, response in zip(calls, row["responses"]):
                messages.append({
                    "role": "tool",
                    "name": call["name"],
                    "content": json.dumps(response, sort_keys=True, ensure_ascii=False),
                })

        final_patch = runner._patch(before, runner._tree(workspace))
        functional = runner._oracle(workspace, config)
        events = context.audit.read_events()

    summary = {
        "schema_version": "qwen-native-debug-v1",
        "evidence_class": "debug_only_not_experiment_evidence",
        "formal_eligible": False,
        "episode_id": config["episode_id"],
        "source_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=runner.ROOT, check=True,
            text=True, stdout=subprocess.PIPE,
        ).stdout.strip(),
        "terminal_reason": terminal_reason,
        "functional_status": functional["status"],
        "turns": len(actions),
        "tool_calls": sum(len(row["tool_calls"]) for row in actions),
        "backend_failed_requests": sum(
            1 for row in actions for response in row["responses"] if not response["ok"]
        ),
        "patch_bytes": len(final_patch.encode("utf-8")),
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }
    _write_json(output / "summary.json", summary)
    _write_json(
        output / "environment.json",
        {
            "runtime_validation": config.get("debug_runtime_validation", {}),
            "model_metrics": (
                model_runtime.collect_metrics()
                if isinstance(model, QwenNativeModel)
                else {"runtime": "fake_native_model"}
            ),
        },
    )
    _write_jsonl(output / "actions.jsonl", actions)
    _write_jsonl(output / "backend_events.jsonl", events)
    _write_json(output / "functional_oracle.json", functional)
    _write_json(output / "tools.json", tools)
    (output / "final.patch").write_text(final_patch, encoding="utf-8")
    digests = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output.iterdir())
        if path.name != "digests.json"
    }
    _write_json(output / "digests.json", {"algorithm": "sha256", "files": digests})
    return output
