"""Append-only JSONL audit events for the canonical backend."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping


class AuditLogger:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event: Mapping[str, Any]) -> None:
        payload = (json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n").encode(
            "utf-8"
        )
        descriptor = os.open(
            self.path,
            os.O_APPEND | os.O_CREAT | os.O_WRONLY,
            0o600,
        )
        try:
            os.write(descriptor, payload)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def read_events(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [
            json.loads(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line
        ]
