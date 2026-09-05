# Interface

This repository contains a minimal experiment comparing two action interfaces for a coding agent while holding the model, SWE-bench task, Backend, permission policy, sandbox, and budgets fixed.

```text
Atomic ------------------\
                          > Shared Backend -> Permission -> Repository
Restricted Python -------/
```

## Harness v3.2 experiment

The current experiment is `harness-v3-2-qwen-orchestration-three-small-tasks`.
It uses the official `princeton-nlp/SWE-bench_Verified` task collection, three small tasks, the same Qwen model and Harness v2 budget/policy, and the existing synthetic `repository_comment_hijack_v1` attack. The Restricted Python language is deliberately narrowed for orchestration; this is not a claim of improved success or security.

| Instance | Repository | Why it is a small calibration task |
|---|---|---|
| `pallets__flask-5014` | `pallets/flask` | One Blueprint-constructor validation and one focused regression test. |
| `sphinx-doc__sphinx-8265` | `sphinx-doc/sphinx` | A localized Python AST unparser fix and one parameterized regression case. |
| `sympy__sympy-12481` | `sympy/sympy` | A localized permutation-constructor guard and one focused assertion. |

Each instance has 2 interfaces × 2 conditions × 3 seeds = 12 runs. The complete plan is 3 × 2 × 2 × 3 = 36 unique runs:

| Interface | Clean | Attack |
|---|---:|---:|
| Atomic | 3 seeds | 3 seeds |
| Restricted Python | 3 seeds | 3 seeds |

The three repositories are independent and the gold patches are small, but the checkouts are historical projects with their own dependency constraints. Flask, Sphinx, and SymPy may require compatible Python/dependency versions in Colab; no GPU is needed for source preparation or unit tests.

The v3.2 protocol gives both interfaces the same task objective and environment-facing capabilities through the same canonical Backend and permission policy. Atomic permits exactly one Backend operation per model action. Restricted Python is a small executable orchestration language: one model action may sequentially compose multiple Backend operations, store their responses, and use minimal `if` control flow before returning one aggregated observation. It does not support general-purpose Python content analysis, methods, built-ins, or loops. The sandbox, budgets, attack definition, logging metrics, and official SWE-bench scoring path are unchanged.

The v3 and v3.1 smoke results must not be mixed with the current `qwen-orchestration-v3.2` rollout. Prepared source checkouts are intentionally shared because the task IDs and exact base commits did not change; run outputs use the new experiment ID.

## Local CPU preparation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/prepare_sources.py --config configs/experiment_v3_2_qwen_orchestration_three_small_tasks.yaml
python scripts/run_experiment.py --config configs/experiment_v3_2_qwen_orchestration_three_small_tasks.yaml --plan
```

The preparation command checks exact base commits, unique source anchors, carrier syntax, one payload insertion, empty attack baseline diff, clean-condition absence of the carrier, protected `.git` target behavior, and cleanup. The plan command does not construct a model client or call a model; it prints `planned_runs: 36`. `sources/` and `runs/` are ignored and must not be committed.

## Colab A100 rollout

The repository remote and branch for this version are:

```text
https://github.com/yan510308856/Interface.git
codex/restricted-python-orchestration-v3-2
```

From a fresh Colab session, mount Drive, clone the branch, install the repository and vLLM dependencies, then prepare sources and validate the plan:

```bash
from google.colab import drive
drive.mount('/content/drive')
```

```bash
cd /content
git clone --branch codex/restricted-python-orchestration-v3-2 https://github.com/yan510308856/Interface.git Agents_Research
cd /content/Agents_Research
git checkout codex/restricted-python-orchestration-v3-2
git pull --ff-only origin codex/restricted-python-orchestration-v3-2
git rev-parse HEAD
python -m pip install -r requirements.txt
python -m pip install 'vllm>=0.10.0'
python scripts/prepare_sources.py --config configs/experiment_v3_2_qwen_orchestration_three_small_tasks.yaml
python scripts/run_experiment.py --config configs/experiment_v3_2_qwen_orchestration_three_small_tasks.yaml --plan
```

The configured model is `Qwen/Qwen3-Coder-30B-A3B-Instruct`. Start its OpenAI-compatible vLLM server in a second Colab cell:

```bash
cd /content/Agents_Research
QWEN_CONFIG=$(find /content/drive/MyDrive -path '*Qwen3-Coder-30B-A3B-Instruct*/snapshots/*/config.json' -print -quit)
test -n "$QWEN_CONFIG"
QWEN_SNAPSHOT=${QWEN_CONFIG%/config.json}
while IFS= read -r -d '' shard; do
  dd if="$shard" of=/dev/null bs=64M status=none
done < <(find -L "$QWEN_SNAPSHOT" -type f -name '*.safetensors' -print0)
nohup vllm serve "$QWEN_SNAPSHOT" \
  --served-model-name Qwen/Qwen3-Coder-30B-A3B-Instruct \
  --host 127.0.0.1 --port 8000 --dtype bfloat16 \
  --gpu-memory-utilization 0.90 --max-model-len 32768 --max-num-seqs 1 \
  --enable-auto-tool-choice --tool-call-parser qwen3_xml \
  > /tmp/qwen-vllm.log 2>&1 &
until curl --fail --silent http://127.0.0.1:8000/v1/models >/dev/null; do sleep 5; done
curl --fail --silent http://127.0.0.1:8000/v1/models
```

The commands locate the existing Drive snapshot, prefetch its safetensors shards through the CPU page cache, and preserve the configured endpoint at `http://127.0.0.1:8000/v1`.

Smoke rollouts (no official grading):

```bash
python scripts/run_experiment.py --config configs/experiment_v3_2_qwen_orchestration_three_small_tasks.yaml --task pallets__flask-5014 --interface atomic --condition clean --seed 1 --skip-evaluation
python scripts/run_experiment.py --config configs/experiment_v3_2_qwen_orchestration_three_small_tasks.yaml --task pallets__flask-5014 --interface restricted_python --condition clean --seed 1 --skip-evaluation
python scripts/run_experiment.py --config configs/experiment_v3_2_qwen_orchestration_three_small_tasks.yaml --task pallets__flask-5014 --interface atomic --condition attack --seed 1 --skip-evaluation
```

Run all 12 cells for one task, then all 36 cells:

```bash
python scripts/run_experiment.py --config configs/experiment_v3_2_qwen_orchestration_three_small_tasks.yaml --task pallets__flask-5014 --skip-evaluation
python scripts/run_experiment.py --config configs/experiment_v3_2_qwen_orchestration_three_small_tasks.yaml --skip-evaluation
```

The output directory is `runs/harness-v3-2-qwen-orchestration-three-small-tasks/`. Completed run directories containing `result.json` are skipped when the same command is rerun. If a process was interrupted before a result was written, its old trajectory is retained as `trajectory.partial.*.jsonl` and that run is restarted. This makes rerunning the same command the resume procedure.

Persist results to Drive without putting them in Git:

```bash
mkdir -p /content/drive/MyDrive/Agents_Research/harness-v3-2-qwen-orchestration-three-small-tasks
rsync -a /content/Agents_Research/runs/harness-v3-2-qwen-orchestration-three-small-tasks/ \
  /content/drive/MyDrive/Agents_Research/harness-v3-2-qwen-orchestration-three-small-tasks/
```

After interruption, clone/fetch the same branch, run `prepare_sources.py` again, restore the Drive directory under `runs/harness-v3-2-qwen-orchestration-three-small-tasks/`, and rerun the same single-task or full command. `result.json` files are the resume markers.

## Official SWE-bench scoring

This project does not reimplement the SWE-bench scorer. After rollouts, install the official harness from `requirements.txt`, keep the generated `prediction.jsonl`/patch artifacts under the ignored run directories, and invoke the official harness for the selected instance IDs. A typical evaluation command is:

```bash
python -m swebench.harness.run_evaluation \
  --dataset_name princeton-nlp/SWE-bench_Verified \
  --predictions_path runs/harness-v3-2-qwen-orchestration-three-small-tasks/<run-dir>/prediction.jsonl \
  --instance_ids pallets__flask-5014 \
  --max_workers 1 \
  --run_id harness-v3-2-qwen-orchestration-three-small-tasks
```

Old Harness v2, v3, or v3.1 results must not be mixed with v3.2 results: the prompt protocol, experiment ID, and output directory are versioned separately. The official dataset guide and dataset card define the benchmark fields and split used here: [SWE-bench dataset guide](https://github.com/SWE-bench/SWE-bench/blob/main/docs/guides/datasets.md) and [SWE-bench Verified](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Verified).
