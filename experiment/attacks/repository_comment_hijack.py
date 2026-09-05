"""The v1 synthetic repository-comment hijack attack."""

from experiment.attacks import AttackSpec, get_attack


ATTACK_ID = "repository_comment_hijack_v1"


def spec() -> AttackSpec:
    return get_attack(ATTACK_ID)
