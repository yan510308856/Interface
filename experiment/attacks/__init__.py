"""Registered synthetic attack specifications."""

from experiment.attacks.base import AttackSpec
from experiment.attacks.repository_comment_hijack import ATTACK_SPEC


ATTACKS: dict[str, AttackSpec] = {ATTACK_SPEC.attack_id: ATTACK_SPEC}


def get_attack(attack_id: str) -> AttackSpec:
    try:
        return ATTACKS[attack_id]
    except KeyError as exc:
        raise ValueError(f"unknown attack: {attack_id}") from exc
