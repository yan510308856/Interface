# R1 decision

```text
status: incomplete
artifact:
  - experiment/configs/model.yaml
  - experiment/model_runtime.py
  - experiment/tests/test_model_config.py
  - scripts/prefetch_model_colab.py
  - scripts/smoke_model_colab.py
  - artifacts/r1/R1_DECISION.md
  - external: /content/drive/MyDrive/Interface-R1/prefetch_manifest.json
  - external: /content/drive/MyDrive/Interface-R1/quick_inference.json
decision: revise
host: local preparation; Colab CPU prefetch; Colab A100 quick inference
code_commit_used_on_colab: cd4d050d246a9a257d87faa846230a72e96c8183
environment: NVIDIA A100-SXM4-80GB (81920 MiB), driver 580.82.07, reported CUDA 13.0; exact Colab/Python/PyTorch identity not frozen
validation:
  - PYTHONDONTWRITEBYTECODE=1 python3 -m unittest experiment.tests.test_model_config: exit 0, 13 tests
  - python3 scripts/smoke_model_colab.py --config experiment/configs/model.yaml --dry-run --process-count 2: exit 0, DRY_RUN_OK
  - python3 scripts/check_repository.py: exit 0
  - PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s experiment/tests -p 'test_*.py': exit 0, 19 tests
  - git diff --check: exit 0
  - Colab CPU prefetch: completed, approximately 57 GiB cached on Google Drive, supporting manifest generated
  - Colab A100 quick inference: PASS, exact output QWEN_INFERENCE_OK
cloud_sync:
  github: r1-modelscope-a100 pushed through cd4d050d246a9a257d87faa846230a72e96c8183
  google_drive: prefetch manifest, ModelScope cache, and quick-inference JSON retained privately
open_risks:
  - The resolved model/tokenizer revision and exact Colab runtime are not frozen in tracked model.yaml.
  - Full snapshot SHA-256 hashing was intentionally interrupted to minimize A100 cost.
  - The three fixed R1 prompts and 16,384-token context probe were not completed as a formal attempt.
  - Two separate real worker processes and their identity comparison were not completed.
  - No complete frozen-config rerun exists, so the protocol's R1 exit criteria are unmet.
next_stage: stop if only basic Qwen inference was required; otherwise complete formal R1 before R2
```

Local source SHA-256 values before the A100 run:

```text
experiment/configs/model.yaml          e314089d64ae8daae8e699f456aeb68e6e987b500368c9f359de3899650b8671
experiment/model_runtime.py            a299535e77cfe5556bda68f344550a46901918652bf9efc0256af95f7f60308c
experiment/tests/test_model_config.py  56692d53d12868170f1e8b2654598423dfd009302d5ff77e4b5ed66021dae600
scripts/smoke_model_colab.py           50e5d04d406d825120ece574e8211dd8184d5b18d6a5fdea9c3c1fc48ce44d70
scripts/prefetch_model_colab.py        d69f50ead8d279d7e445bb1e05cea811f8fecf1db318be17354e22605f446733
```

## Colab quick-inference observation

The user completed a cost-minimized A100 check after a CPU prefetch to Google
Drive. This observation is useful evidence that the selected checkpoint can load
and produce a short response, but it deliberately bypasses the formal R1 digest,
full-context, and two-process requirements.

```text
result: PASS
evidence_role: quick_inference_only
model_id: Qwen/Qwen3-Coder-30B-A3B-Instruct
resolved_revision: 5ea29678865934640d71cfece1aedfa1e84599a4
prompt: Reply with exactly QWEN_INFERENCE_OK.
output: QWEN_INFERENCE_OK
load_seconds: 318.30028647899985
generation_seconds: 2.151317279000068
peak_gpu_memory_gib: 57.66936111450195
external_result: /content/drive/MyDrive/Interface-R1/quick_inference.json
external_result_size: 333 bytes
```

The original JSON remains on the user's private Google Drive and was not copied
into Git. These values were transcribed from the user-provided terminal output;
they are not a substitute for a complete runner-produced R1 attempt bundle.

## What the local implementation establishes

The local tests establish only config validation, fixed prompt/parser behavior,
ModelScope Git-ref resolution, attempt non-overwrite, and complete success/failure
artifact writing. Fake output is labelled `PASS_LOCAL_ONLY` and cannot satisfy R1.

The real loader resolves `refs/heads/master` to a ModelScope Git commit, passes that
commit explicitly to `snapshot_download`, hashes every safetensors shard plus key
config/tokenizer files, and loads the model onto `cuda:0` with BF16. CPU offload,
disk offload, quantization, multiple GPUs, non-A100 devices, and insufficient GPU or
cache storage are controlled failures.

## Formal Colab A100 commands (optional only if formal R1 is still required)

From the Colab-connected terminal, first confirm that the terminal itself sees the
GPU and repository:

```bash
nvidia-smi
git status --short --branch
```

Install the pinned R1 user-space packages. PyTorch comes from the selected Colab
runtime and is recorded rather than replaced:

```bash
python3 -m pip install \
  "modelscope==1.39.1" \
  "modelscope-hub==0.2.0" \
  "transformers==5.16.1" \
  "accelerate==1.14.0"
```

Run the first two-process smoke from a clean committed checkout:

```bash
R1_MODELSCOPE_CACHE=/content/modelscope-cache \
python3 scripts/smoke_model_colab.py \
  --config experiment/configs/model.yaml \
  --output-dir artifacts/r1/qwen-a100-discovery \
  --attempt-id attempt-00 \
  --process-count 2
```

Each attempt is a new Python process. The first downloads and cold-loads; the second
reuses only the ModelScope cache and cold-loads in a fresh process. Both preserve
`run_manifest.json`, `environment.json`, stdout/stderr, metrics, validation,
generation records, and digests.

Because the tracked config is intentionally unresolved before the first A100 run,
the discovery command ends with `R1: REVISE` even if both model processes succeed.
It writes `resolved_model_config.json`. Review that file, copy its immutable model/
tokenizer revision and exact torch version into the tracked `model.yaml`, commit the
freeze, then rerun both processes using a new output directory. Only that frozen
rerun can produce `R1: PASS`.
