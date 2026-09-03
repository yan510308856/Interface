"""Prepare clean or synthetic repository prompt-injection conditions."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def prepare_condition(repo: Path, condition: str, attack_config: dict[str, Any]) -> Path | None:
    if condition == "clean":
        return None
    if condition != "attack":
        raise ValueError(f"unknown condition: {condition}")
    carrier = repo / attack_config["path"]
    carrier.parent.mkdir(parents=True, exist_ok=True)
    carrier.write_text(attack_config["payload"], encoding="utf-8")
    return carrier
