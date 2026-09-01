"""Recompute R6-P episode metrics from raw bundle files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def recompute(bundle: Path) -> dict[str, Any]:
    actions = read_jsonl(bundle / "actions.jsonl")
    events = read_jsonl(bundle / "backend_events.jsonl")
    messages = read_jsonl(bundle / "messages.jsonl")
    functional = json.loads((bundle / "functional_oracle.json").read_text(encoding="utf-8"))
    security = json.loads((bundle / "security_oracle.json").read_text(encoding="utf-8"))
    manifest = json.loads((bundle / "run_manifest.json").read_text(encoding="utf-8"))
    errors = {"permission_denied", "timeout", "execution_error", "internal_error", "limit_exceeded"}
    return {
        "schema_version": "r6p-metrics-v1",
        "evidence_class": "development_evidence_only",
        "formal_r6_eligible": False,
        "model_turns": len(actions),
        "actions_invalid": sum(row.get("parse_status") == "invalid" for row in actions),
        "backend_operation_attempts": len(events),
        "backend_denials": sum(row.get("status") == "permission_denied" for row in events),
        "backend_errors": sum(row.get("status") in errors for row in events),
        "backend_timeouts": sum(row.get("status") == "timeout" for row in events),
        "prompt_tokens": sum(int(row.get("usage", {}).get("prompt_tokens", 0)) for row in actions),
        "output_tokens": sum(int(row.get("usage", {}).get("output_tokens", 0)) for row in actions),
        "model_latency_ms": round(sum(float(row.get("model_latency_ms", 0.0)) for row in actions), 3),
        "action_latency_ms": round(sum(float(row.get("action_latency_ms", 0.0)) for row in actions), 3),
        "message_count": len(messages),
        "patch_bytes": len((bundle / "final.patch").read_bytes()),
        "functional_status": functional["status"],
        "security_status": security["status"],
        "terminal_reason": manifest["terminal_reason"],
    }
