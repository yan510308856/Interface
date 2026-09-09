"""The v2 benign repository-sentinel write calibration attack."""

from experiment.attacks import AttackSpec, get_attack


ATTACK_ID = "repository_sentinel_write_v2"


def spec() -> AttackSpec:
    return get_attack(ATTACK_ID)
