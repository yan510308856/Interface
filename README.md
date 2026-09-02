# Interface

Minimal repository-level experiment comparing Atomic and Restricted Python coding-agent interfaces.

## Research Question

When model, task, backend, permissions, sandbox, and budget are identical, does the action interface change utility, security, operation behavior, token cost, or runtime?

## Experimental Design

The four cells are Atomic × Clean, Atomic × Attack, Restricted Python × Clean, and Restricted Python × Attack. Atomic permits one backend operation per model action. Restricted Python permits zero or multiple backend operations through a small AST interpreter.

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

```bash
python scripts/run_experiment.py
```

Run one cell:

```bash
python scripts/run_experiment.py --interface atomic --condition clean
```

## Output

Each run writes `runs/<batch>/<task>-<interface>-<condition>-<seed>/result.json` and `trajectory.jsonl`. Results include task success, unsafe/blocked attempts, attack success, backend operations, tokens, runtime, and final patch. `runs/` is ignored by Git.

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
