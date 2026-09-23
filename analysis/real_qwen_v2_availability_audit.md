# Real-Qwen v2 calibration investigation: availability and integrity gate

Date: 2026-09-07 (Asia/Shanghai)  
Mode: analysis-only; no model inference, experiment rerun, artifact mutation, or SWE-bench evaluation

## Executive decision

The requested outcome analysis is **blocked at the artifact-integrity gate**. Neither
the primary v2 experiment nor the comparison v1 experiment is available in this
environment. In fact, the `/content` mount point itself does not exist.

Exact unavailable locations:

- `/content/drive/MyDrive/Interface-R1/experiments/action-boundary-attack-pilot-v2`
- `/content/drive/MyDrive/Interface-R1/experiments/action-boundary-attack-pilot-v1`

Consequently, none of the supplied sanity targets (54 runs, 49 budget exhaustions,
5 model finishes, approximately 236 `list_files` calls, or 18 exposed attack runs)
has been treated as an observed result. They remain hypotheses to verify from raw
artifacts. No derived CSV/JSON or plots were created because doing so would imply a
data-backed analysis that the available environment cannot support.

## Availability checks

The following read-only checks were performed from
`/Users/yan/Downloads/Agents_Research`:

```text
/content                                                        UNAVAILABLE
/content/drive                                                  UNAVAILABLE
/content/drive/MyDrive/Interface-R1/experiments/action-boundary-attack-pilot-v2  UNAVAILABLE
/content/drive/MyDrive/Interface-R1/experiments/action-boundary-attack-pilot-v1  UNAVAILABLE
```

A bounded search of the repository and `/Volumes` found no directory named
`action-boundary-attack-pilot-v1` or `action-boundary-attack-pilot-v2`. The
repository does contain artifacts under
`oracle/harness-v6-1-python-batch-nine-task-clean/`, but those belong to a different
clean nine-task experiment. They do not provide the requested G1/G2/G4 ×
clean/attack v1/v2 matrix and were deliberately not substituted.

## What can and cannot be verified

| Requested item | Status | Evidence/limitation |
|---|---|---|
| Current branch | Confirmed | `codex/granularity-formal-matrix` |
| Current commit | Confirmed | `42829b969845a505fe8d4ffe7c51b6fbc4fe96c7` |
| Required baseline commit included | Confirmed for local checkout | HEAD is exactly `42829b9...` |
| v2/v1 artifact presence | Not available | Both roots absent; `/content` absent |
| 54-run v2 completeness and matrix coverage | Not verifiable | Requires run directories and completion markers |
| Duplicate/incomplete run audit | Not verifiable | Requires run IDs and all run directories |
| Provenance/config hashes used by runs | Not verifiable | Requires experiment-level and run-level metadata |
| Model/runtime settings actually used | Not verifiable | Repository config is intent, not proof of executed settings |
| Global, granularity, operation, loop, pruning, test, patch, permission, attack, and v1→v2 metrics | Not verifiable | Requires `result.json`, `trajectory.jsonl`, `patch.diff`, and metadata |
| SWE-bench task success | Not evaluated | Official oracle was intentionally not run |

Artifact completeness and task success are separate concepts. Even if all expected
files and `COMPLETE.json` markers were present, that would show execution
completeness only. It would not establish that any SWE-bench task was resolved.

## Locally confirmed implementation facts

These facts describe the checked-out implementation, not necessarily the missing v2
run artifacts:

- The formal config defines 3 tasks × G1/G2/G4 × clean/attack × 3 rollouts, which
  plans 54 runs.
- Nominal capacities are G1=1, G2=2, and G4=4 backend operations per model action.
  These are capacity bounds; realized execution depth must be measured from
  `interface_action.operations_executed` or backend events.
- The formal config names `Qwen/Qwen3-Coder-30B-A3B-Instruct`, temperature 0,
  50 model actions, 100 backend operations, 1,800-second run timeout, and 32,768
  model context length. The runner CLI defaults to parallelism 3, while the server
  config specifies `max_num_seqs: 3`. Actual v2 values still require run provenance.
- For G1/G2/G4, the runner sends `parallel_tool_calls=false` and logs that value in
  each `model_request` event.
- The terminal action parser accepts only an empty operations list combined with
  `finish="done"`; an empty non-terminal action is invalid. Validation failures are
  returned as deterministic structured feedback with zero backend operations.
- The runner records `model_finish`, `action_budget_exhausted`,
  `operation_budget_exhausted`, `timeout`, `model_api_error`, or `runner_error` as
  distinct termination reasons.
- `list_files` is a shared backend operation. It excludes `.git` and symlinks,
  sorts paths, bounds results, and reports truncation.
- The model-visible process schema describes the pytest-only allowlist. The checked
  policy permits `pytest ...`, `python -m pytest ...`, and
  `python3 -m pytest ...`, with `shell=False`.
- The repository includes analysis-only loop metrics for repeated operations,
  overlapping reads, repeated searches, ENOENT retries, denial retries, and actions
  since edit/successful test.

These implementation observations confirm that the local checkout contains the
requested instrumentation and shared capabilities. They do **not** confirm that the
missing artifacts were produced by this exact checkout or configuration.

## Requested research questions: present disposition

| Question | Decision with current evidence |
|---|---|
| Is v2 pipeline technically healthy? | Not established; implementation is inspectable, run health is not. |
| Is repository navigation sufficiently repaired? | Not established; no v1/v2 navigation events are available. |
| Is terminal protocol technically functioning? | Parser/runner support is confirmed; real-model usage is not. |
| What explains 49/54 budget exhaustion? | Cannot assess because 49/54 itself is unverified here. |
| Is realized G separation adequate? | Cannot assess without action-level operation counts. |
| Is the attack strong enough? | Cannot assess without structured exposure/attempt events. |
| Should the action budget remain 50? | No evidence-backed decision is possible from this environment. |
| What should change next? | Restore read-only access to the exact v1 and v2 roots, then rerun analysis only. |
| What must not change? | Model, tasks, backend, permissions, prompts, G treatments, attack payload/placement, budgets, runner behavior, and existing artifacts. |

## Resume requirements and analysis order

To resume without contaminating the experiment, mount or copy both exact experiment
roots read-only, preserving timestamps and filenames. At minimum, v2 must expose all
run directories and their `COMPLETE.json`, `result.json`, `trajectory.jsonl`,
`patch.diff`, and `metadata.json` files, plus experiment-level config/provenance
records. The same artifact classes are needed for matched v1 comparison.

Once available, the first pass should:

1. Enumerate run IDs and validate the exact 54-cell v2 matrix before reading results.
2. Compare completion-marker and artifact counts, detect duplicates/incomplete runs,
   and validate provenance/config hashes.
3. Parse raw trajectories into one run-level table, one action-level table, and one
   operation-level table; derive every requested aggregate from those tables.
4. Manually audit the named Pallets r1 trajectories and structured terminal actions.
5. Classify tests, loops, pruning, patches, permission denials, and attack exposure.
6. Compare v1→v2 only as a matched calibration diagnostic, not as a causal estimate.
7. Keep task-level and rollout-level raw values visible; avoid action-level
   pseudoreplication and confirmatory p-value claims.

## Integrity notes

- No A100/vLLM/model inference was started.
- No experiment artifact was read, modified, moved, or regenerated because the
  requested roots were absent.
- The SWE-bench official evaluator was not run.
- No supplied sanity target was promoted to a result.
- No unrelated local oracle artifact was used as a proxy.

## Audit trail and handoff

Skill: `agent-security-empirical-study`  
Skill source: `/Users/yan/.codex/skills/agent-security-empirical-study/SKILL.md`  
Request SHA-256: `15979ba763af3962c91970b8a9299455c53ce15baec1f047e59fd8b294e8119a`  
Relevant local config SHA-256: `74cac4f4443a17c7ae82b0852ea640577f1c65523ec2e92d47e65c4fece79b3c`  
Permission config SHA-256: `bc42b4042ecc0456737a7c275e05f10249ee849a3ecfa4ed2cae894a0528fb7e`  
Commands: read-only `git`, `stat`, `find`, `rg`, `sed`, and `shasum`; report created with `apply_patch`  

```text
status: blocked
artifact: analysis/real_qwen_v2_availability_audit.md
decision: blocked
open_risks: exact v1/v2 artifacts and run provenance unavailable
provenance: local checkout 42829b9 plus the request and implementation hashes above
exact next Skill: statistical-analysis, only after artifact integrity and raw-table construction pass
```
