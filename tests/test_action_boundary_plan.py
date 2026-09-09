from __future__ import annotations

import json
import unittest
from pathlib import Path

from experiment.runner import build_experiment_plan, load_config


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/experiment_action_boundary_granularity.yaml"
CLEAN_CONFIG = ROOT / "configs/experiment_action_boundary_granularity_clean.yaml"


class ActionBoundaryPlanTests(unittest.TestCase):
    def test_full_matrix_is_three_granularities_by_two_conditions(self):
        config = load_config(CONFIG)
        plan_config = json.loads(json.dumps(config))
        plan_config["task"]["require_prepared_sources"] = False
        plan = build_experiment_plan(plan_config)
        self.assertEqual(54, len(plan))
        self.assertEqual({"G1", "G2", "G4"}, {item.interface for item in plan})
        self.assertEqual({"clean", "attack"}, {item.condition for item in plan})
        self.assertEqual(54, len({(item.instance_id, item.interface, item.condition, item.seed) for item in plan}))

    def test_clean_config_contains_all_primary_treatments(self):
        config = load_config(CLEAN_CONFIG)
        plan_config = json.loads(json.dumps(config))
        plan_config["task"]["require_prepared_sources"] = False
        plan = build_experiment_plan(plan_config)
        self.assertEqual({"G1", "G2", "G4"}, {item.interface for item in plan})
        self.assertEqual({"clean"}, {item.condition for item in plan})
        self.assertEqual({1, 2, 4}, {
            plan_config["granularity"][item.interface]["max_ops_per_action"] for item in plan
        })


if __name__ == "__main__":
    unittest.main()
