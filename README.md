# Interface

Minimal repository-level experiment comparing Atomic and Restricted Python coding-agent interfaces.

## Research Question

When model, task, backend, permissions, sandbox, and budget are identical, does the action interface change utility, security, operation behavior, token cost, or runtime?

## Experimental Design

Harness v2 is calibrated on three SWE-bench Verified tasks × clean/attack ×
Atomic/Restricted Python × seeds 1, 2, and 3 (36 planned rollouts). Atomic
permits one backend operation per model action. Restricted Python permits zero
or multiple backend operations through a small AST interpreter. The attack is a
GT-guided repository-carried source comment; gold patches are construction-only
metadata and are never agent-visible.

## Architecture

```text
Atomic ------------------\
                          > Shared Backend -> Permission -> Repository
Restricted Python -------/
```

## Installation

Use Python 3.11+, Docker, and a local OpenAI-compatible server hosting the configured Qwen model.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The default model endpoint is `http://127.0.0.1:8000/v1`; edit `configs/experiment.yaml` if yours differs. SWE-bench task setup may download benchmark data and repositories. Agent-visible process execution remains limited by `configs/permission.yaml`.

## Run Experiment

Prepare exact local task sources and inspect the complete plan before inference:

```bash
python scripts/prepare_sources.py
python scripts/run_experiment.py --plan
```

```bash
python scripts/run_experiment.py
```

Run one cell:

```bash
python scripts/run_experiment.py --interface atomic --condition clean
```

## Output

Each run writes a unique directory containing `run_manifest.json`,
`result.json`, `trajectory.jsonl`, and `final.patch`. Results include task
success, unsafe/blocked attempts, attack exposure/success, backend operations,
tokens, runtime, and the final patch. `runs/` is ignored by Git. See
`docs/three_task_gt_guided_calibration.md` for the Colab/A100 and Google Drive
persistence workflow.

Summarize a batch with:

```bash
python analysis/analyze.py runs/<batch>
```

## Repository Structure

```text
configs/       experiment and permission configuration
experiment/    model, task, backend, interfaces, attack, evaluation, runner
scripts/       main experiment entry point
tasks/         selected SWE-bench instance IDs
tests/         deterministic component tests
analysis/      result summarization
docs/          experiment design
```

See `docs/design.md` for operational definitions.
