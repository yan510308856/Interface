"""Deterministic task x condition x interface x seed run plans."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

from experiment.attack import AttackPlacement
from experiment.attacks import get_attack
from experiment.task import Task


@dataclass(frozen=True)
class RunSpec:
    instance_id: str
    repo: str
    base_commit: str
    interface: str
    condition: str
    attack_id: str | None
    seed: int
    carrier_file: str | None = None
    enclosing_symbol: str | None = None
    placement_id: str | None = None

    @property
    def directory_name(self) -> str:
        if self.attack_id:
            return f"{self.instance_id}-{self.interface}-attack-{self.attack_id}-{self.seed}"
        return f"{self.instance_id}-{self.interface}-clean-{self.seed}"

    def as_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["run_directory"] = self.directory_name
        return result


def build_run_plan(
    tasks: Iterable[Task],
    config: dict[str, object],
    placements: dict[tuple[str, str], AttackPlacement] | None = None,
    *,
    interface_filter: str | None = None,
    condition_filter: str | None = None,
    seed_filter: int | None = None,
    task_filter: str | None = None,
    attack_id: str | None = None,
) -> list[RunSpec]:
    placements = placements or {}
    interfaces = list(config["interfaces"])
    conditions = list(config["conditions"])
    seeds = list(config["seeds"])
    active_attack_id = attack_id or config.get("active_attack")
    if not active_attack_id and config.get("attack"):
        # Preserve the frozen Harness v2 config's legacy placement path.
        active_attack_id = "repository_comment_hijack_v1"
    if active_attack_id:
        get_attack(str(active_attack_id))

    result: list[RunSpec] = []
    for task in tasks:
        if task_filter and task.instance_id != task_filter:
            continue
        for condition in conditions:
            if condition_filter and condition != condition_filter:
                continue
            condition_attack = str(active_attack_id) if condition == "attack" and active_attack_id else None
            if condition == "attack" and not condition_attack:
                raise ValueError("attack condition requires active_attack")
            placement = placements.get((task.instance_id, condition_attack)) if condition_attack else None
            if condition_attack and placement is None and config.get("task", {}).get("metadata_dir"):
                raise ValueError(f"missing placement for {task.instance_id}/{condition_attack}")
            for interface in interfaces:
                if interface_filter and interface != interface_filter:
                    continue
                for seed in seeds:
                    if seed_filter is not None and int(seed) != seed_filter:
                        continue
                    result.append(RunSpec(
                        task.instance_id, task.repo, task.base_commit,
                        str(interface), str(condition), condition_attack, int(seed),
                        placement.selected_file if placement else None,
                        placement.enclosing_symbol if placement else None,
                        placement.placement_id if placement else None,
                    ))

    keys = [(item.instance_id, item.condition, item.interface, item.seed) for item in result]
    if len(keys) != len(set(keys)):
        raise ValueError("run plan contains duplicate task/condition/interface/seed keys")
    return result
