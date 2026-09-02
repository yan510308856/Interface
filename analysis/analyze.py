#!/usr/bin/env python3
"""Summarize completed run results by interface and condition."""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path


def main(root: Path) -> None:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for path in root.rglob("result.json"):
        result = json.loads(path.read_text(encoding="utf-8"))
        groups[(result["interface"], result["condition"])].append(result)
    for (interface, condition), rows in sorted(groups.items()):
        count = len(rows)
        print(
            interface, condition, f"n={count}",
            f"task_success={sum(row['task_success'] for row in rows) / count:.3f}",
            f"unsafe_attempt={sum(row['unsafe_attempt'] for row in rows) / count:.3f}",
            f"tokens={sum(row['input_tokens'] + row['output_tokens'] for row in rows) / count:.1f}",
            f"runtime={sum(row['runtime_seconds'] for row in rows) / count:.1f}s",
        )


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "runs"))

