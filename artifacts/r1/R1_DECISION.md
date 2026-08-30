# R1 decision

```text
status: complete
artifact:
  - experiment/configs/model.yaml
  - experiment/model_runtime.py
  - experiment/tests/test_model_config.py
  - requirements.txt
  - scripts/prefetch_model_colab.py
  - scripts/smoke_model_colab.py
  - artifacts/r1/R1_DECISION.md
  - external: /content/drive/MyDrive/Interface-R1/artifacts/qwen-a100-formal-frozen-01/
decision: pass
host: Google Colab A100
code_commit_used_on_colab: 515e908180a0cc6810107c48da89e6243d61a30c
model: Qwen/Qwen3-Coder-30B-A3B-Instruct
resolved_revision: 5ea29678865934640d71cfece1aedfa1e84599a4
snapshot_sha256: b408027c9c3351245a516347d656c7a1c56d55fcdd65e040adbad322104a9c05
environment: Python 3.13.15; torch 2.11.0+cu128; CUDA runtime 12.8; NVIDIA driver 580.82.07; NVIDIA A100-SXM4-80GB (81920 MiB)
validation:
  - python3 -m unittest experiment.tests.test_model_config: exit 0, 14 tests
  - python3 -m unittest discover -s experiment/tests -p 'test_*.py': exit 0, 20 tests
  - python3 scripts/check_repository.py: exit 0
  - python3 scripts/smoke_model_colab.py --config experiment/configs/model.yaml --dry-run --process-count 2: exit 0, DRY_RUN_OK
  - frozen Colab run attempt-00: PASS
  - frozen Colab run attempt-01: PASS
  - frozen Colab two-process validation: PASS
cloud_sync:
  github: branch r1-modelscope-a100; frozen config commit 515e908180a0cc6810107c48da89e6243d61a30c
  google_drive: complete private frozen-run bundle and optional ModelScope cache
open_risks: none for the R1 feasibility gate; R1 does not validate the agent loop, interfaces, SWE-bench task, backend, permissions, or security oracle
provenance: runner-generated Drive artifacts plus the user-provided terminal capture showing attempt-01 PASS, worker exit code 0, and two-process R1 status PASS on 2026-08-30
next_stage: R2 — Clean task feasibility and task manifest freeze
```

## Gate evidence

The frozen run used the same immutable model and tokenizer revision, BF16 settings,
sampling parameters, seed, runtime identity, snapshot digest, and fixed input token
IDs in two fresh worker processes. Both workers:

- loaded the model on `cuda:0` without CPU or disk offload;
- loaded approximately 56.92 GiB of model weights on the GPU;
- produced non-empty output for the plain, Atomic JSON, and Restricted Python prompts;
- passed the JSON and Python syntax parsers;
- completed the 16,384-token context probe without OOM; and
- wrote complete attempt bundles before exiting with code 0.

The private Drive directory contains `attempt-00/`, `attempt-01/`, and
`two_process_validation.json`. Each attempt contains the runner-generated
`run_manifest.json`, `environment.json`, `metrics.json`, `validation.json`,
`generations.jsonl`, stdout/stderr logs, and `digests.json`. Model weights and the
ModelScope cache are intentionally excluded from Git.

## Tracked R1 source digests

```text
experiment/configs/model.yaml          330ed27be02a5126d143fee82dcea3303dd5d58b863e74ed86a06848ceb72b21
experiment/model_runtime.py            65dddbc9a89a3a76dd483b5d3154bed7d18ecceeef48384b54db891e7539fdc5
experiment/tests/test_model_config.py  a62df0171102ead82302db23f5d4ef9c03c5848b4694c7a70bdb2aa3d87fdfdf
scripts/smoke_model_colab.py           50e5d04d406d825120ece574e8211dd8184d5b18d6a5fdea9c3c1fc48ce44d70
scripts/prefetch_model_colab.py        d69f50ead8d279d7e445bb1e05cea811f8fecf1db318be17354e22605f446733
scripts/check_repository.py            a77b17ffc550cc391d4313f95db65d64a44352d90c2db9fd1e4163a8be0a9a08
requirements.txt                       3563dcbcf5a78f968a3e8585c8f6282095ce49ff69af3ae94d23a9bac2b10d1f
```

R1 `pass` means only that the frozen Qwen/ModelScope/A100 inference stack is
feasible and reproducible enough for later stages. It is not evidence that either
action interface is better or that the final four-cell agent experiment works.
