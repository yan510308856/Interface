# R1 decision

```text
status: incomplete
artifact:
  - experiment/configs/model.yaml
  - experiment/model_runtime.py
  - experiment/tests/test_model_config.py
  - scripts/smoke_model_colab.py
  - artifacts/r1/R1_DECISION.md
decision: revise
host: local (preparation only); colab-a100 evidence pending
code_commit: working tree on r1-modelscope-a100; exact commit will be recorded before A100 execution
environment: local Python 3.9.6; real package/CUDA/GPU versions pending Colab capture
validation:
  - PYTHONDONTWRITEBYTECODE=1 python3 -m unittest experiment.tests.test_model_config: exit 0, 11 tests
  - python3 scripts/smoke_model_colab.py --config experiment/configs/model.yaml --dry-run --process-count 2: exit 0, DRY_RUN_OK
  - python3 scripts/check_repository.py: exit 0
  - PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s experiment/tests -p 'test_*.py': exit 0, 17 tests
  - git diff --check: exit 0
cloud_sync:
  github: not pushed; branch under local review
  google_drive: not applicable until real A100 bundles exist
open_risks:
  - ModelScope master ref has not yet been resolved to an immutable commit on A100.
  - The unquantized BF16 checkpoint requires an 80 GB-class A100; a 40 GB A100 is expected to produce REVISE without offload.
  - Two separate real processes, full-context probe, weight digests, and GPU metrics are not yet recorded.
next_stage: R1 Colab A100 execution; do not start R2
```

Local source SHA-256 values before the A100 run:

```text
experiment/configs/model.yaml          e314089d64ae8daae8e699f456aeb68e6e987b500368c9f359de3899650b8671
experiment/model_runtime.py            3548256dfacbab497860012dc18c3ff96386d0ae87b084c1fb4f6e036cd3b955
experiment/tests/test_model_config.py  5625da3c91eaa04fb488cb3eeeafb946c2451fc54437ad2defc5212532f291fe
scripts/smoke_model_colab.py           eeceacc74f4b3b5f2bc7a67553bcf921de1406323cdc11f60685863956bca5f5
```

## What the local implementation establishes

The local tests establish only config validation, fixed prompt/parser behavior,
ModelScope Git-ref resolution, attempt non-overwrite, and complete success/failure
artifact writing. Fake output is labelled `PASS_LOCAL_ONLY` and cannot satisfy R1.

The real loader resolves `refs/heads/master` to a ModelScope Git commit, passes that
commit explicitly to `snapshot_download`, hashes every safetensors shard plus key
config/tokenizer files, and loads the model onto `cuda:0` with BF16. CPU offload,
disk offload, quantization, multiple GPUs, non-A100 devices, and insufficient GPU or
cache storage are controlled failures.

## Colab A100 commands

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
