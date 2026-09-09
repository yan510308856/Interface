from __future__ import annotations

import unittest
from pathlib import Path

from experiment.attack import load_placements
from experiment.attacks import get_attack
from experiment.formal import build_formal_plan
from experiment.runner import load_config


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/experiment_action_boundary_calibration_v3.yaml"
SANITY_CONFIG_PATH = ROOT / "configs/experiment_action_boundary_calibration_v3_sanity.yaml"
RETIRED_TASKS = {
    "pallets__flask-5014",
    "sphinx-doc__sphinx-8265",
    "sympy__sympy-12481",
}


class PilotV3CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.config = load_config(CONFIG_PATH)

    def test_v3_uses_six_tasks_and_new_attack_manifest(self):
        plan, tasks, placements = build_formal_plan(self.config, ROOT)
        task_ids = {task.instance_id for task in tasks}
        self.assertEqual(6, len(tasks))
        self.assertEqual(6, len(placements))
        self.assertFalse(task_ids & RETIRED_TASKS)
        self.assertEqual(
            {
                "astropy__astropy-14309",
                "pytest-dev__pytest-10081",
                "psf__requests-1921",
                "pylint-dev__pylint-4970",
                "mwaskom__seaborn-3069",
                "pydata__xarray-4094",
            },
            task_ids,
        )
        self.assertEqual(
            "repository_sentinel_write_v2",
            self.config["active_attack"],
        )
        self.assertEqual(
            {"repository_sentinel_write_v2"},
            {attack_id for _, attack_id in placements},
        )
        self.assertEqual(108, len(plan))

    def test_v3_scheduler_is_balanced_and_capacity_is_fixed(self):
        plan, _, _ = build_formal_plan(self.config, ROOT)
        blocks = [plan[index:index + 6] for index in range(0, len(plan), 6)]
        self.assertEqual(18, len(blocks))
        self.assertEqual(9, sum(block[0].condition == "clean" for block in blocks))
        self.assertEqual(9, sum(block[0].condition == "attack" for block in blocks))
        for block in blocks:
            self.assertEqual(["G1", "G2", "G4"], [item.granularity for item in block[:3]])
            self.assertEqual(["G1", "G2", "G4"], [item.granularity for item in block[3:]])
        self.assertEqual(
            {"G1": 1, "G2": 2, "G4": 4},
            {name: self.config["granularity"][name]["max_ops_per_action"] for name in ("G1", "G2", "G4")},
        )
        self.assertEqual(50, self.config["budget"]["max_model_actions"])
        self.assertEqual(100, self.config["budget"]["max_backend_operations"])

    def test_v3_sanity_is_attack_only_r1_and_has_18_unique_runs(self):
        config = load_config(SANITY_CONFIG_PATH)
        plan, tasks, _ = build_formal_plan(config, ROOT)
        run_ids = [item.run_id for item in plan]
        self.assertEqual(6, len(tasks))
        self.assertEqual(18, len(plan))
        self.assertEqual(18, len(set(run_ids)))
        self.assertEqual({"attack"}, {item.condition for item in plan})
        self.assertEqual({1}, {item.rollout for item in plan})
        self.assertEqual({"repository_sentinel_write_v2"}, {item.attack_id for item in plan})
        self.assertEqual({"G1", "G2", "G4"}, {item.granularity for item in plan})
        self.assertEqual({"G1": 6, "G2": 6, "G4": 6}, {
            granularity: sum(item.granularity == granularity for item in plan)
            for granularity in ("G1", "G2", "G4")
        })
        self.assertTrue(all(item.run_id.endswith("-attack01-r1") for item in plan))

    def test_v3_sanity_preserves_finalized_v3_settings(self):
        sanity = load_config(SANITY_CONFIG_PATH)
        for key in (
            "model", "server", "task", "harness_version", "prompt_protocol_version",
            "common_prompt_version", "interface_prompt_version", "permission_policy_id",
            "interfaces", "granularity", "attack_ids", "budget", "context", "sandbox",
            "active_attack", "attack",
        ):
            self.assertEqual(self.config[key], sanity[key], key)
        self.assertNotEqual(self.config["experiment_id"], sanity["experiment_id"])
        self.assertNotEqual(self.config["experiment_name"], sanity["experiment_name"])
        self.assertEqual(["attack"], sanity["conditions"])
        self.assertEqual([1], sanity["rollouts"])

    def test_v3_manifest_targets_protected_sentinel_and_clean_files_are_unmodified(self):
        placements = load_placements(ROOT / self.config["task"]["placement_file"])
        attack = get_attack(self.config["active_attack"])
        self.assertEqual(".git/agent_attack_sentinel_v2", attack.target_path)
        self.assertEqual("repository source comment", attack.carrier)
        self.assertTrue(all(item.selected_file for item in placements.values()))
        self.assertTrue(all(item.attack_id == attack.attack_id for item in placements.values()))
        self.assertTrue(all(item.selected_file in item.gt_modified_files for item in placements.values()))

    def test_prior_formal_configs_keep_their_old_identity_and_tasks(self):
        formal = load_config(ROOT / "configs/experiment_action_boundary_formal.yaml")
        granularity = load_config(ROOT / "configs/experiment_action_boundary_granularity.yaml")
        self.assertEqual("action-boundary-granularity-formal-v1", formal["experiment_id"])
        self.assertEqual("tasks/tasks_v3.json", formal["task"]["file"])
        self.assertEqual("repository_comment_hijack_v1", formal["active_attack"])
        self.assertEqual("action-boundary-granularity-three-small-tasks", granularity["experiment_id"])
        self.assertEqual("tasks/tasks_v3.json", granularity["task"]["file"])
        self.assertEqual("repository_comment_hijack_v1", granularity["active_attack"])


if __name__ == "__main__":
    unittest.main()
