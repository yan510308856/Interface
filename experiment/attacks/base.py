"""Small immutable attack specification shared by experiment conditions."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class AttackSpec:
    attack_id: str
    attack_family: str
    carrier_type: str
    payload: str
    target_path: str
    placement_strategy: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)
