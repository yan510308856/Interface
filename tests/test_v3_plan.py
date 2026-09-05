from __future__ import annotations

import json
import unittest
from pathlib import Path

from experiment.attack import load_placements
from experiment.runner import build_experiment_plan, load_config


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/experiment_v3_qwen_protocol_three_small_tasks.yaml"
V3_2_CONFIG = ROOT / "configs/experiment_v3_2_qwen_orchestration_three_small_tasks.yaml"
V4_CONFIG = ROOT / "configs/experiment_v4_structured_python_three_small_tasks.yaml"
V5_CONFIG = ROOT / "configs/experiment_v5_structured_python_local_compute_three_small_tasks.yaml"
V5_1_CONFIG = ROOT / "configs/experiment_v5_1_structured_python_validation_feedback_three_small_tasks.yaml"
V6_CONFIG = ROOT / "configs/experiment_v6_python_batch_three_small_tasks.yaml"
V6_1_CONFIG = ROOT / "configs/experiment_v6_1_python_batch_prompt_calibration.yaml"


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

    def test_v4_plan_is_the_same_36_cells_with_new_protocol_identity(self):
        old = load_config(V3_2_CONFIG)
        new = load_config(V4_CONFIG)
        self.assertEqual("harness-v4-structured-python-three-small-tasks", new["experiment_id"])
        self.assertEqual("structured-python-v4", new["prompt_protocol_version"])
        plan = build_experiment_plan(new)
        self.assertEqual(36, len(plan))
        self.assertEqual(36, len({
            (item.instance_id, item.interface, item.condition, item.seed) for item in plan
        }))
        for instance_id in {item.instance_id for item in plan}:
            self.assertEqual(12, sum(item.instance_id == instance_id for item in plan))
        versioned = {
            "experiment_name", "experiment_id", "harness_version",
            "prompt_protocol_version", "interface_prompt_version",
        }
        self.assertEqual(
            {key: value for key, value in old.items() if key not in versioned},
            {key: value for key, value in new.items() if key not in versioned},
        )

    def test_v5_plan_is_the_same_36_cells_with_new_protocol_identity(self):
        old = load_config(V4_CONFIG)
        new = load_config(V5_CONFIG)
        self.assertEqual("harness-v5-structured-python-local-compute-three-small-tasks", new["experiment_id"])
        self.assertEqual("structured-python-local-compute-v5", new["prompt_protocol_version"])
        plan = build_experiment_plan(new)
        self.assertEqual(36, len(plan))
        self.assertEqual(36, len({
            (item.instance_id, item.interface, item.condition, item.seed) for item in plan
        }))
        for instance_id in {item.instance_id for item in plan}:
            self.assertEqual(12, sum(item.instance_id == instance_id for item in plan))
        versioned = {
            "experiment_name", "experiment_id", "harness_version",
            "prompt_protocol_version", "interface_prompt_version",
        }
        self.assertEqual(
            {key: value for key, value in old.items() if key not in versioned},
            {key: value for key, value in new.items() if key not in versioned},
        )

    def test_v5_1_plan_is_the_same_36_cells_with_new_protocol_identity(self):
        old = load_config(V5_CONFIG)
        new = load_config(V5_1_CONFIG)
        self.assertEqual(
            "harness-v5-1-structured-python-validation-feedback-three-small-tasks",
            new["experiment_id"],
        )
        self.assertEqual("structured-python-validation-feedback-v5.1", new["prompt_protocol_version"])
        plan = build_experiment_plan(new)
        self.assertEqual(36, len(plan))
        self.assertEqual(36, len({
            (item.instance_id, item.interface, item.condition, item.seed) for item in plan
        }))
        for instance_id in {item.instance_id for item in plan}:
            self.assertEqual(12, sum(item.instance_id == instance_id for item in plan))
        versioned = {
            "experiment_name", "experiment_id", "harness_version",
            "prompt_protocol_version", "interface_prompt_version",
        }
        self.assertEqual(
            {key: value for key, value in old.items() if key not in versioned},
            {key: value for key, value in new.items() if key not in versioned},
        )

    def test_v6_batch_plan_is_36_cells_and_is_separate_from_v5_1(self):
        old = load_config(V5_1_CONFIG)
        new = load_config(V6_CONFIG)
        self.assertEqual("harness-v6-python-batch-three-small-tasks", new["experiment_id"])
        self.assertEqual("python-batch-orchestration-v6", new["prompt_protocol_version"])
        self.assertNotEqual(old["experiment_id"], new["experiment_id"])
        self.assertNotEqual(old["task"]["source_root"], new["task"]["source_root"])
        plan_config = json.loads(json.dumps(new))
        plan_config["task"]["require_prepared_sources"] = False
        plan = build_experiment_plan(plan_config)
        self.assertEqual(36, len(plan))
        self.assertEqual(36, len({
            (item.instance_id, item.interface, item.condition, item.seed) for item in plan
        }))
        for instance_id in {item.instance_id for item in plan}:
            self.assertEqual(12, sum(item.instance_id == instance_id for item in plan))

    def test_v6_1_prompt_calibration_only_changes_version_identity(self):
        old = load_config(V6_CONFIG)
        new = load_config(V6_1_CONFIG)
        self.assertEqual("harness-v6-1-python-batch-prompt-calibration", new["experiment_id"])
        self.assertEqual("python-batch-prompt-calibration-v6.1", new["prompt_protocol_version"])
        versioned = {
            "experiment_name", "experiment_id", "harness_version",
            "prompt_protocol_version", "interface_prompt_version",
        }
        self.assertEqual(
            {key: value for key, value in old.items() if key not in versioned},
            {key: value for key, value in new.items() if key not in versioned},
        )
        plan_config = json.loads(json.dumps(new))
        plan_config["task"]["require_prepared_sources"] = False
        plan = build_experiment_plan(plan_config)
        self.assertEqual(36, len(plan))
        for instance_id in {item.instance_id for item in plan}:
            self.assertEqual(12, sum(item.instance_id == instance_id for item in plan))


if __name__ == "__main__":
    unittest.main()
