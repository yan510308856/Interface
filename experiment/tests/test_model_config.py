"""Offline deterministic tests for the R1 model config and artifact boundary."""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from experiment import model_runtime  # noqa: E402
import smoke_model_colab  # noqa: E402


CONFIG_PATH = ROOT / "experiment/configs/model.yaml"
REQUIREMENTS_PATH = ROOT / "requirements.txt"


class BrokenRuntime:
    """Test double that fails during model loading."""

    @staticmethod
    def load_model(config):
        raise RuntimeError("synthetic load failure")

    @staticmethod
    def release_model():
        return None


class R1ModelConfigTests(unittest.TestCase):
    def setUp(self):
        self.config = model_runtime.load_config(CONFIG_PATH)

    def test_pending_config_is_explicit_and_modelscope_only(self):
        self.assertEqual("modelscope", self.config["provider"])
        self.assertEqual("Qwen/Qwen3-Coder-30B-A3B-Instruct", self.config["model_id"])
        self.assertEqual("pending_a100", self.config["freeze_status"])
        self.assertIsNone(self.config["resolved_revision"])
        self.assertFalse(self.config["engine"]["allow_cpu_offload"])
        self.assertFalse(self.config["engine"]["allow_disk_offload"])

    def test_requirements_match_config_without_replacing_colab_torch(self):
        actual = {
            line.strip()
            for line in REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        expected = {
            f"{package}=={version}"
            for package, version in self.config["packages"].items()
            if package != "torch"
        }
        self.assertEqual(expected, actual)
        self.assertFalse(any(line.startswith("torch") for line in actual))

    def test_config_rejects_wrong_provider_and_partial_revision(self):
        wrong_provider = copy.deepcopy(self.config)
        wrong_provider["provider"] = "huggingface"
        with self.assertRaises(model_runtime.ConfigError):
            model_runtime.validate_config(wrong_provider)

        partial = copy.deepcopy(self.config)
        partial["resolved_revision"] = "a" * 40
        with self.assertRaises(model_runtime.ConfigError):
            model_runtime.validate_config(partial)

    def test_frozen_config_requires_exact_torch_version(self):
        frozen = copy.deepcopy(self.config)
        frozen["resolved_revision"] = "a" * 40
        frozen["tokenizer_revision"] = "a" * 40
        frozen["freeze_status"] = "frozen"
        with self.assertRaises(model_runtime.ConfigError):
            model_runtime.validate_config(frozen)
        frozen["packages"]["torch"] = "2.9.0+cu128"
        frozen["runtime"] = {
            "colab_release": "2026.08",
            "python": "3.12.11",
            "torch": "2.9.0+cu128",
            "cuda_runtime": "12.8",
            "nvidia_driver": "570.00",
            "gpu_name": "NVIDIA A100-SXM4-80GB",
            "gpu_memory_mib": 81920,
        }
        model_runtime.validate_config(frozen)

    def test_three_fixed_prompts_cover_all_parsers(self):
        prompts = self.config["prompts"]
        self.assertEqual(3, len(prompts))
        self.assertEqual(
            {"nonempty", "atomic_json", "python_ast"},
            {prompt["parser"] for prompt in prompts},
        )

    def test_output_parsers_accept_expected_syntax_and_reject_bad_syntax(self):
        self.assertTrue(model_runtime.parse_output("nonempty", "ok")["ok"])
        self.assertTrue(
            model_runtime.parse_output(
                "atomic_json",
                '{"type":"tool_call","operation":"read_file","arguments":{}}',
            )["ok"]
        )
        self.assertFalse(model_runtime.parse_output("atomic_json", "not-json")["ok"])
        self.assertTrue(model_runtime.parse_output("python_ast", "x = 1")["ok"])
        self.assertFalse(model_runtime.parse_output("python_ast", "x =")["ok"])

    @mock.patch("experiment.model_runtime.subprocess.run")
    def test_modelscope_ref_is_resolved_to_full_commit(self, run):
        run.return_value = mock.Mock(
            returncode=0,
            stdout=f"{'b' * 40}\trefs/heads/master\n",
            stderr="",
        )
        self.assertEqual("b" * 40, model_runtime.resolve_modelscope_revision(self.config))
        command = run.call_args.args[0]
        self.assertEqual("git", command[0])
        self.assertEqual(self.config["repository_url"], command[2])

    def test_fake_attempt_writes_complete_success_bundle(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "run"
            exit_code = smoke_model_colab.run_attempt(
                CONFIG_PATH,
                output,
                "attempt-00",
                "fake",
                runtime=smoke_model_colab.FakeRuntime(),
            )
            self.assertEqual(0, exit_code)
            attempt = output / "attempt-00"
            required = {
                "run_manifest.json",
                "environment.json",
                "stdout.log",
                "stderr.log",
                "metrics.json",
                "validation.json",
                "digests.json",
                "generations.jsonl",
            }
            self.assertEqual(required, {path.name for path in attempt.iterdir()})
            validation = json.loads((attempt / "validation.json").read_text())
            self.assertEqual("PASS_LOCAL_ONLY", validation["overall"])
            rows = (attempt / "generations.jsonl").read_text().splitlines()
            self.assertEqual(3, len(rows))
            self.assertTrue(all(json.loads(row)["parse"]["ok"] for row in rows))
            stdout = (attempt / "stdout.log").read_text()
            self.assertIn("attempt-00 started", stdout)
            self.assertIn("prompt 1/3 (plain)", stdout)
            self.assertIn("context probe complete", stdout)
            self.assertIn("validation=PASS_LOCAL_ONLY", stdout)

    def test_heartbeat_reports_start_and_finish(self):
        with mock.patch("experiment.model_runtime._progress") as report:
            with model_runtime._heartbeat(
                "test operation", lambda: "units=3", interval_seconds=0.001
            ):
                pass
        messages = [call.args[0] for call in report.call_args_list]
        self.assertTrue(any("started" in message for message in messages))
        self.assertTrue(any("finished" in message for message in messages))

    def test_cpu_prefetch_uses_resolved_revision_without_gpu(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary) / "cache"
            snapshot = cache / "snapshot"

            def fake_download(**kwargs):
                self.assertEqual("b" * 40, kwargs["revision"])
                self.assertEqual(str(cache), kwargs["cache_dir"])
                snapshot.mkdir(parents=True)
                (snapshot / "model.safetensors").write_bytes(b"weights")
                return str(snapshot)

            environment_name = self.config["cache_policy"]["environment_variable"]
            with (
                mock.patch.dict(os.environ, {environment_name: str(cache)}),
                mock.patch.object(
                    model_runtime, "resolve_modelscope_revision", return_value="b" * 40
                ),
            ):
                result = model_runtime.prefetch_snapshot(
                    self.config, downloader=fake_download
                )
            self.assertEqual("b" * 40, result["resolved_revision"])
            self.assertEqual(snapshot.resolve(), Path(result["snapshot_path"]))
            self.assertGreater(result["cache_bytes"], 0)

    def test_failure_still_writes_complete_attempt_bundle(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "run"
            exit_code = smoke_model_colab.run_attempt(
                CONFIG_PATH,
                output,
                "attempt-00",
                "fake",
                runtime=BrokenRuntime(),
            )
            self.assertEqual(1, exit_code)
            attempt = output / "attempt-00"
            manifest = json.loads((attempt / "run_manifest.json").read_text())
            validation = json.loads((attempt / "validation.json").read_text())
            self.assertEqual("RuntimeError", manifest["error"]["class"])
            self.assertEqual("REVISE", validation["overall"])
            self.assertTrue((attempt / "digests.json").is_file())

    def test_attempt_ids_increment_without_overwrite(self):
        self.assertEqual("attempt-01", smoke_model_colab.increment_attempt("attempt-00", 1))
        with self.assertRaises(ValueError):
            smoke_model_colab.increment_attempt("attempt", 1)

    def test_runtime_identity_must_be_complete_and_match_when_frozen(self):
        actual = {
            "colab_release": "2026.08",
            "python": "3.12.11",
            "torch": "2.9.0",
            "cuda_runtime": "12.8",
            "nvidia_driver": "570.00",
            "gpu_name": "NVIDIA A100-SXM4-80GB",
            "gpu_memory_mib": 81920,
        }
        smoke_model_colab.validate_runtime_identity(self.config, actual)
        incomplete = dict(actual)
        incomplete["colab_release"] = None
        with self.assertRaises(RuntimeError):
            smoke_model_colab.validate_runtime_identity(self.config, incomplete)

        frozen = copy.deepcopy(self.config)
        frozen["freeze_status"] = "frozen"
        frozen["runtime"] = actual
        smoke_model_colab.validate_runtime_identity(frozen, actual)
        changed = dict(actual)
        changed["nvidia_driver"] = "different"
        with self.assertRaises(RuntimeError):
            smoke_model_colab.validate_runtime_identity(frozen, changed)

    def test_two_fake_process_bundles_propose_but_do_not_freeze_config(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "run"
            for attempt in ("attempt-00", "attempt-01"):
                self.assertEqual(
                    0,
                    smoke_model_colab.run_attempt(
                        CONFIG_PATH,
                        output,
                        attempt,
                        "fake",
                        runtime=smoke_model_colab.FakeRuntime(),
                    ),
                )
            summary, candidate = smoke_model_colab.compare_attempts(
                self.config, output, ["attempt-00", "attempt-01"]
            )
            self.assertEqual("REVISE", summary["status"])
            self.assertIn("tracked_model_config_not_frozen", summary["blockers"])
            self.assertIsNotNone(candidate)
            self.assertEqual("frozen", candidate["freeze_status"])
            self.assertEqual("a" * 40, candidate["resolved_revision"])


if __name__ == "__main__":
    unittest.main()
