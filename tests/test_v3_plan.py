from __future__ import annotations

import json
import unittest
from pathlib import Path

from experiment.attack import load_placements
from experiment.runner import build_experiment_plan, load_config


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/experiment_v3_qwen_protocol_three_small_tasks.yaml"
V3_2_CONFIG = ROOT / "configs/experiment_v3_2_qwen_orchestration_three_small_tasks.yaml"


class V3PlanTests(unittest.TestCase):
    def test_v3_plan_is_exactly_36_unique_runs(self):
        config = load_config(CONFIG)
        plan = build_experiment_plan(config)
        self.assertEqual(36, len(plan))
        keys = [(item.instance_id, item.condition, item.interface, item.seed) for item in plan]
        self.assertEqual(36, len(set(keys)))
        for instance_id in {item.instance_id for item in plan}:
            self.assertEqual(12, sum(item.instance_id == instance_id for item in plan))
        self.assertEqual(
            {
                (interface, condition, seed)
                for interface in ("atomic", "restricted_python")
                for condition in ("clean", "attack")
                for seed in (1, 2, 3)
            },
            {(item.interface, item.condition, item.seed) for item in plan},
        )

    def test_v3_metadata_and_placements_do_not_add_hash_verification(self):
        config = load_config(CONFIG)
        task_ids = [item["instance_id"] for item in json.loads((ROOT / config["task"]["file"]).read_text())]
        placements = load_placements(ROOT / config["task"]["placement_file"])
        self.assertEqual(3, len(task_ids))
        self.assertEqual(3, len(placements))
        for task_id in task_ids:
            metadata = json.loads((ROOT / "task_metadata" / task_id / "metadata.json").read_text())
            self.assertEqual(task_id, metadata["instance_id"])
            placement = placements[(task_id, config["active_attack"])]
            self.assertNotIn("sha256", placement.as_dict())
            self.assertNotIn("gold_patch", placement.as_dict())
            self.assertNotIn("test_patch", placement.as_dict())

    def test_v3_2_plan_is_exactly_the_same_36_cells(self):
        config = load_config(V3_2_CONFIG)
        self.assertEqual("harness-v3-2-qwen-orchestration-three-small-tasks", config["experiment_id"])
        self.assertEqual("qwen-orchestration-v3.2", config["prompt_protocol_version"])
        plan = build_experiment_plan(config)
        self.assertEqual(36, len(plan))
        self.assertEqual(3, len({item.instance_id for item in plan}))
        for instance_id in {item.instance_id for item in plan}:
            self.assertEqual(12, sum(item.instance_id == instance_id for item in plan))

    def test_v3_2_changes_only_protocol_identity_from_v3_1_config(self):
        old = load_config(CONFIG)
        new = load_config(V3_2_CONFIG)
        versioned = {
            "experiment_name", "experiment_id", "harness_version",
            "prompt_protocol_version", "interface_prompt_version",
        }
        self.assertEqual(
            {key: value for key, value in old.items() if key not in versioned},
            {key: value for key, value in new.items() if key not in versioned},
        )


if __name__ == "__main__":
    unittest.main()
