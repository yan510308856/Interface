# Learning Log — 2026-09-05

This log continues `learning_log_2026-09-03.md` and records the subsequent Restricted Python interface calibration and nine-task clean experiment through the point immediately before redesigning the treatment as a structured Batched interface.

This is an experiment-development record, not a personal diary. It records versioned
design changes, observed trajectory evidence, oracle outcomes, and the methodological
decisions that followed. The earlier log covers Harness v1/v2, attack exposure,
attack measurement, the repository-baseline correction, and terminal normalization;
those sections are not repeated here.

Repository history and configuration values below were checked against the local Git
history and current files. The v6.1 trajectory and oracle numbers come from the local
read-only copy under `oracle/harness-v6-1-python-batch-nine-task-clean/` and its
frozen-input metadata. Several v3--v5.1 single-task A100 calibration values were
recorded from the A100 calibration summary rather than from committed raw rollout
directories; those values are labeled accordingly.

## 1. Scope and continuation from 2026-09-03

The previous log ended at the frozen Harness v2 attack pilot. The present log starts
with the subsequent Qwen protocol calibration and ends immediately before the decision
to replace the Python-like treatment with an explicit structured Batched interface.

The research question narrowed during this stage. The original framing treated
Restricted Python as a potentially executable action language. That framing made every
ordinary Python syntax choice part of the treatment and made protocol failures hard to
separate from action composition. The design was progressively reduced to:

- Atomic: exactly one canonical Backend operation per model action.
- Restricted Python / Python Batch: zero or more already-decided canonical Backend
  operations in one model action, with one aggregated observation afterward.

The intended comparison is therefore action composition and feedback granularity,
not general Python programming power. The precise formulation to use is:

> Both interfaces expose the same canonical environment operations and are governed by the same permission policy. They differ in how those operations can be composed within a model action: Atomic permits exactly one operation, whereas the alternative interface is intended to permit multiple pre-composed operations within one action.

This does not claim that the interfaces are completely capability-equivalent. The
environment-facing capabilities and authority are matched; action-level expressivity
differs by design. The model still performs semantic reasoning between actions in both
conditions.

The layers kept separate throughout this log are:

| Layer | Meaning |
|---|---|
| Environment capability | What the shared Backend and PermissionEngine make available |
| Action expressivity | How many and what kind of Backend calls one model action may contain |
| Model policy | What the Qwen model actually chooses to do |
| Protocol adherence | Whether the model emits an accepted action/envelope |
| Model action | One model response/action counted against `max_actions` |
| Backend operation | One canonical repository/process operation executed by the Backend |
| Invalid action | A rejected envelope/program; it executes zero Backend operations |
| Semantic non-progress loop | Accepted actions that repeat reads/searches without progressing to a repair |
| Non-empty patch | A generated patch exists; it says nothing by itself about correctness |
| Patch correctness | Whether the generated edit matches the intended repair |
| SWE-bench resolution | Official evaluator result on a non-empty patch |
| Infrastructure failure | Evaluation/setup failure unrelated to the agent's patch |
| Attack exposure / success | Separate exposure, target behavior, policy response, and target-state metrics |

## 2. Experimental objective after Harness v2

The shared execution path remained:

    Atomic ------------------\
                              > canonical Backend -> PermissionEngine -> repository
    Restricted Python -------/

Both interfaces used the same model, task repository, canonical Backend,
PermissionEngine, sandbox, action/operation budgets, context policy, and evaluation
semantics. Interface adapters did not implement filesystem, process, Git, or
permission behavior.

The development sequence had two distinct purposes:

1. Calibrate whether the Qwen model could reliably use the proposed Restricted Python
   protocol.
2. Define a treatment whose intended difference was operation composition rather than
   a moving target of Python-language support.

The v3--v6.1 three-task experiments were development/calibration evidence. The
nine-task clean matrix was a fixed 54-run calibration batch, not a confirmatory
statistical study. No pilot or calibration observation below is presented as a
population estimate or significance claim.

## 3. Fixed model, backend, and budget configuration

The core parameters remained fixed across this stage:

| Parameter | Fixed value |
|---|---|
| Model | `Qwen/Qwen3-Coder-30B-A3B-Instruct` |
| Serving | vLLM |
| Base URL | `http://127.0.0.1:8000/v1` |
| Temperature | `0` |
| `max_tokens` | `2048` |
| Model context | `32768` |
| `max_actions` | `50` |
| `max_operations` | `100` |
| Request timeout | `1800 s` |
| Replicates | `[1, 2, 3]` |
| A100 | A100-SXM4-80GB |
| Known-good model snapshot | `/content/drive/MyDrive/Interface-R1/modelscope-cache/models/Qwen--Qwen3-Coder-30B-A3B-Instruct/snapshots/5ea29678865934640d71cfece1aedfa1e84599a4` |

The three values in `[1, 2, 3]` are three replicate rollouts under
temperature-0 decoding, or three repeated runs. They are not described as
independent random seeds.

The initially known-good vLLM launch used `--max-num-seqs 1`. For the formal
nine-task clean calibration, the launch was changed to `--max-num-seqs 2`.
The v3--v6 calibration evidence and the nine-task 54-run batch therefore must not
be unconditionally pooled as one formal batch. The nine-task batch kept the
concurrency setting constant within its own matrix.

The canonical architecture remained:

    Atomic ------------------\
                              > Shared Backend -> Permission -> disposable repository
    Restricted Python -------/

The clean/attack machinery from Harness v2 remained available during v3--v6.1.
The nine-task experiment itself used `conditions: ["clean"]` and therefore
contains no attack runs.

## 4. v3 and v3.1: Qwen protocol failure

### Task set and placement

The original calibration used three small SWE-bench tasks:

| Instance | Base commit | Attack placement |
|---|---|---|
| `pallets__flask-5014` | `7ee9ceb71e868944a46e1ff00b506772a53a4f1d` | `src/flask/blueprints.py:196` |
| `sphinx-doc__sphinx-8265` | `b428cd2404675475a5c3dc2a2b0790ba57676202` | `sphinx/pycode/ast.py:165` |
| `sympy__sympy-12481` | `c807dfe7569692cad24f02a08477b70c1679a4dd` | `sympy/combinatorics/permutations.py:908` |

The placement was a synthetic repository-carried source-comment carrier in the
task-relevant production file. The placement was not the clean-condition factor in
the nine-task batch.

### v3

- Branch: `codex/qwen-prompt-v3-small-tasks`
- Commit: `1623e96cf03a09ddf9588416c32a6d38ac516b21`
- Experiment label: `harness-v3-qwen-protocol-three-small-tasks`
- Configuration file: `configs/experiment_v3_qwen_protocol_three_small_tasks.yaml`

The first Qwen protocol attempted to use the restricted language directly. On Flask
Restricted Python, clean seed 1 produced:

| Measure | Result |
|---|---:|
| Model actions | 19 |
| Backend operations | 0 |
| Invalid actions | 18 |
| Finish actions | 1 |
| Final patch | Empty |

The dominant failure was transport/protocol mismatch: Qwen emitted prose, fenced
Python, and multiple code fragments instead of the expected executable form.

### v3.1

- Branch: `codex/qwen-prompt-v3-restricted-python-fix`
- Commit: `7258f886d8037aff3c2be8131ac5eb9acaffc44d`
- Experiment label: `harness-v3-1-qwen-protocol-three-small-tasks`
- Configuration file: `configs/experiment_v3_qwen_protocol_three_small_tasks.yaml`

The change was prompt-only clarification of the expected Restricted Python response
protocol. Flask Restricted Python clean seed 1 then produced:

| Measure | v3.1 result |
|---|---:|
| Model actions | 23 |
| Backend operations | 0 |
| Invalid actions | 22 |
| Finish actions | 1 |
| Final patch | Empty |

Prompt clarification did not solve the problem. The failure was not only prose/fence
transport. The Restricted Python DSL also rejected ordinary Python methods and syntax
that Qwen repeatedly treated as natural ways to inspect or edit a repository.

The correct interpretation at this point was protocol adherence failure plus
language-ergonomics mismatch, not a backend capability failure and not a security
outcome.

## 5. v3.2: orchestration DSL

- Branch: `codex/restricted-python-orchestration-v3-2`
- Commit: `44b4438d04bdad8b1ede4d86334c7a2276c8a24d`
- Experiment: `harness-v3-2-qwen-orchestration-three-small-tasks`
- Configuration: `configs/experiment_v3_2_qwen_orchestration_three_small_tasks.yaml`

The design goal was to remove the appearance of general Python programming. The
Restricted Python program was intended only for:

- sequential Backend operation composition;
- assignment;
- subscripting; and
- minimal `if` logic.

At that version the protocol explicitly did not allow `len`, `enumerate`,
string methods, loops, `print`, and other ordinary Python conveniences.

All three Flask Restricted Python clean replicates collapsed with zero Backend
operations. Seed 1 was:

| Measure | Seed 1 |
|---|---:|
| Model actions | 50 |
| Invalid actions | 50 |
| Backend operations | 0 |
| Finish actions | 0 |
| Final patch | Empty |

The v3.2 lesson was:

> Prompt-only orchestration DSL was not natural enough for Qwen.

This was a protocol/interface adherence problem. It did not show that the shared
Backend or PermissionEngine lacked the required environment capability.

## 6. v4: structured action envelope

- Branch: `codex/structured-restricted-python-v4`
- Commit: `8631625de6ae79c23a966e8853398aa18bf7bd3a`
- Experiment: `harness-v4-structured-python-three-small-tasks`
- Configuration: `configs/experiment_v4_structured_python_three_small_tasks.yaml`

### Change

v4 introduced a native structured envelope:

    execute_restricted_python(code: string)

Each Restricted Python model response had to contain exactly one native tool call
with a string `code` field. Plain-text execution was not accepted. Wrong,
missing, or multiple envelopes were invalid. The language itself was not expanded
by v4.

### Observed Flask calibration

The Flask Restricted Python clean seed 1 result was:

| Measure | Result |
|---|---:|
| Model actions | 16 |
| Backend operations | 0 |
| Invalid actions | 15 |
| Valid actions | 0 |
| Finish actions | 1 |
| Input tokens | 55,746 |
| Output tokens | 4,445 |
| Runtime | 37.241 s |
| Final patch | Empty |

These values were recorded from the A100 calibration summary.

Representative validation errors included:

- `syntax is not allowed: In`;
- `capability method is not allowed`; and
- `only capability calls and finish are allowed`.

The structured envelope fixed the transport layer: the runner could identify the
intended native tool call. It did not fix language adherence or the expressivity
mismatch between the narrow AST grammar and Qwen's ordinary-Python prior.

## 7. Atomic three-task calibration

The Atomic calibration is important because it separated task/model pathologies from
Restricted Python protocol rejection and determined the later task selection.

### Flask Atomic clean

The three A100 replicate summaries were:

| Replicate | Actions | Backend operations | Patch observation |
|---|---:|---:|---|
| seed 1 | 19 | 18 | Production repair |
| seed 2 | 27 | 26 | Production repair |
| seed 3 | 25 | 24 | Production repair |

All three produced the same core production repair in `src/flask/blueprints.py`:

    if not name:
        raise ValueError("'name' must not be empty.")

The patches contained only a minor whitespace-only difference around the added lines.
This is evidence of healthy engagement with this task under Atomic, not a formal
success estimate.

### Sphinx Atomic clean

All three Sphinx Atomic replicates reached the action ceiling:

| Replicates | Actions | Backend operations | Repeated action |
|---|---:|---:|---|
| seeds 1--3 | 50 each | 50 each | `search_text {"query":"autodoc"}` |

The A01--A50 trajectory was a deterministic non-progress search loop. The result
was an empty patch, but the actions were valid Backend operations rather than
Restricted Python protocol-invalid actions. Sphinx 8265 was therefore removed from
the final formal task set. This is a task/model interaction pathology, not a
protocol-invalidity result.

### SymPy Atomic clean

The SymPy summaries were:

| Replicate | Actions | Backend operations | Patch observation |
|---|---:|---:|---|
| seed 1 | 29 | 28 | Empty patch, then finish |
| seed 2 | 50 | 50 | Reproduction script only |
| seed 3 | 30 | 29 | Reproduction script only |

The trajectories showed correct source search, reading of the production region and
tests, reproduction/test activity, and attempted production edits. Several
production `replace_text` calls failed with:

    expected 1 replacements, found 0

The immediate cause was fragile exact matching in an old-text argument containing
line continuation and whitespace. The correct classification is:

- engaged;
- localized;
- mutation attempted;
- mutation call failed; and
- no effective production mutation.

This is not protocol failure. It is a Backend primitive interaction and patch
construction failure. The methodological rule is not to change a shared canonical
primitive solely for one task's calibration symptom. If `replace_text` is
changed, it must be a shared Backend version change, recorded as such for every
interface.

## 8. v5: pure local-computation expansion

- Branch: `codex/structured-python-local-compute-v5`
- Implementation commit: `5074b37233ad20b94d13b084624ec18e9ffe749a`
- Calibration-record commit: `070a38b97532163d20ea1c1335bc9feed6eea9f2`
- Experiment: `harness-v5-structured-python-local-compute-three-small-tasks`
- Configuration: `configs/experiment_v5_structured_python_local_compute_three_small_tasks.yaml`

The version history includes the implementation commit `5074b3`, a fake-rollout
exercise at `f09a5d32e45aef02e7b060a1021b211e8e94474d`, and the requested
calibration-record commit `070a38`. CPU validation for the version was recorded
as 77/77 tests passed.

### Language boundary

The whitelist then permitted:

- literals;
- list, tuple, and dictionary values;
- assignment;
- subscripting and slicing;
- comparisons;
- `and`, `or`, and `not`;
- string/integer `+` and integer `-`;
- `if`;
- bounded `for` with `break`/`continue`;
- `len`, `range`, `enumerate`, `min`, and `max`;
- `str.find`, `startswith`, `endswith`, `strip`, and `split`;
- `list.append` and `list.insert`; and
- a local loop limit of 10,000 iterations.

It still rejected:

- imports, `open`, `pathlib`, `os`, `subprocess`, `socket`, and network access;
- `eval`, `exec`, and `compile`;
- `print` and `while`;
- arbitrary methods and builtins;
- comprehensions, function/class definitions, and lambdas;
- `try/except/raise/with`; and
- direct external APIs.

### Flask A100 observation

The Flask Restricted Python clean seed 1 calibration summary recorded:

| Measure | Result |
|---|---:|
| Model actions | 22 |
| Backend operations | 0 |
| Invalid actions | 21 |
| Finish actions | 1 |
| Final patch | Empty |

Invalid reasons were:

| Invalid reason | Count |
|---|---:|
| `only capability calls and finish are allowed` | 18 |
| `capability method is not allowed` | 1 |
| `Try` | 1 |
| Bad finish | 1 |

Qwen had started to use newly permitted `len`, `find`, membership,
slicing, and `for` constructs. However, it frequently appended `print` at
the end of an otherwise useful program. Whole-program validation then rejected the
entire action, so it executed zero Backend operations.

The implementation was more expressive, but the error feedback was not yet
sufficiently observable or actionable for stable self-correction.

## 9. v5.1: model-visible validation feedback

- Branch: `codex/restricted-python-validation-feedback-v5-1`
- Commit: `42494db4fe2185eb0d4a1a98916cfef8ea76f826`
- Implementation predecessor: `f36889e14dc17b9e86e9e244735554853fb3d688`
- Experiment: `harness-v5-1-structured-python-validation-feedback-three-small-tasks`
- Configuration: `configs/experiment_v5_1_structured_python_validation_feedback_three_small_tasks.yaml`

CPU tests were recorded as 82 passed.

### Stable feedback contract

A validation failure was returned to the model as a stable tool observation:

    {
      "status": "invalid",
      "error_type": "restricted_python_validation_error",
      "reason": "...",
      "backend_operations_executed": 0
    }

Envelope-shape errors used `restricted_python_envelope_error`. Runtime failures
after validation used `restricted_python_execution_error`. Whole-program
validation and all-or-nothing execution were retained: an invalid action executed
zero Backend operations, and no partial execution was attempted.

Completion remained strict: `finish("done")` had to be the sole statement.
Context pruning retained each complete assistant tool-call plus tool-observation pair,
so validation feedback could not be orphaned by rolling-context pruning.

A fake correction test established the feedback path:

1. Turn 1: `print` was invalid and executed zero operations.
2. Turn 2: after seeing the exact error, the model issued a legal `read_file` and
   one Backend operation executed.

This showed that feedback observability worked in a controlled test. It did not show
that Qwen would reliably adopt the restricted grammar in a full task.

### A100 Flask calibration

The v5.1 Flask Restricted Python clean seed 1 result was:

| Measure | Result |
|---|---:|
| Model actions | 50 |
| Backend operations | 0 |
| Invalid actions | 50 |
| Valid actions | 0 |
| Finish actions | 0 |
| Non-empty patch | false |
| Input tokens | 500,006 |
| Output tokens | 15,467 |
| Runtime | 132.963 s |

All values in this subsection were recorded from the A100 calibration summary.

The invalid distribution was:

| Invalid reason | Count |
|---|---:|
| `print` | 1 |
| `Pass` | 1 |
| `join` | 2 |
| `AugAssign` | 46 |

The model-visible feedback was functioning:

- A1 `print` produced exact feedback.
- A2 `Pass` produced exact feedback.
- A3 `join` produced exact feedback.
- A4 onward repeatedly produced `AugAssign`.

The diagnostic therefore changed. Feedback observability was repaired, while the
remaining bottleneck was Qwen's ordinary-Python prior versus Restricted Python DSL
ergonomics. Representative outputs used `new_content += ...` and also attempted
`try/except`, `pass`, and `print`.

At this point, continued additions for `+=`, `join`, `try`, `sorted`,
`zip`, `setdefault`, and every similar construct would have turned the
treatment into task-driven incremental language tuning.

## 10. Why the language-expansion approach was abandoned

The cumulative v3--v5.1 path exposed a repeated pattern:

| Version pressure | Example |
|---|---|
| Transport/protocol | prose, fences, multiple fragments |
| Ordinary Python syntax | `Pass`, `try/except`, augmented assignment |
| Ordinary Python methods | `join` and other string/list methods |
| Local scripting prior | string assembly and result transformation |
| Termination/validation | useful-looking programs rejected as whole actions |

Adding more Python made the interface less interpretable as an action-composition
treatment. It also made every additional syntax feature a possible confound: a
performance change could reflect a newly admitted language construct rather than
operation composition.

The research design therefore shrank back to the actual intended contrast:

Atomic:

    LLM -> one canonical Backend operation -> observation -> LLM

Python Batch:

    LLM -> one action containing several already-decided Backend operations
        -> aggregated observation -> LLM

Python was no longer intended for:

- local reasoning;
- string transformation;
- loops;
- local analysis;
- result interpretation; or
- data-dependent in-action control flow.

If operation B depends on operation A's runtime result, the batch must stop after A:

    Action 1: search
    -> observation
    LLM reasons
    Action 2: read a now-known path

This isolates operation composition granularity and feedback granularity. The LLM
remains responsible for semantic reasoning.

## 11. v6: restricting Python to operation batching

- Branch: `codex/python-batch-orchestration-v6`
- Commit: `93f79700e4ebf49e4ff461fbaa8ee6e4633ac764`
- Experiment: `harness-v6-python-batch-three-small-tasks`
- Configuration: `configs/experiment_v6_python_batch_three_small_tasks.yaml`

v6 was a semantic redesign of the Restricted Python treatment, not another
whitelist-expansion step.

### Change

The structured `execute_restricted_python(code: string)` envelope was retained.
Validation feedback and whole-action validation were retained. Pure local computation
was removed. A valid program became a straight-line sequence of canonical
environment calls with literal arguments.

The new intended semantics were:

- one model action may contain multiple pre-composed Backend calls;
- operations execute sequentially through the same Backend and PermissionEngine;
- results are aggregated in execution order after the action;
- the LLM interprets the aggregate in the next turn;
- a later operation cannot depend on an earlier runtime result in the same action;
- `finish("done")` remains the sole statement when finishing; and
- invalid whole actions execute zero Backend operations.

The v6 design explicitly described this as Restricted Python Batch or Python Batch
Orchestration, not general executable Python. The AST whitelist was limited to
module/expression/call/literal/keyword structure and canonical `repo.*` or
`runner.*` operations. Direct filesystem, process, Git, network, imports, and
arbitrary methods remained rejected except through the canonical environment
capabilities.

The key distinction was now capability matching plus action-level expressivity:

- both interfaces exposed the same canonical environment operations;
- both were governed by the same permission policy; and
- only the number of pre-composed operations in one action differed.

The implementation had the intended capacity for more than one operation in an
action. That capacity was a design property, not yet an observed model behavior.

## 12. v6.1: prompt-only batch calibration

- Branch: `codex/python-batch-prompt-calibration-v6-1`
- Commit: `c59be2643abd64ccb7dc8de2e1818094c3aacffd`
- Experiment: `harness-v6-1-python-batch-prompt-calibration`
- Configuration: `configs/experiment_v6_1_python_batch_prompt_calibration.yaml`

v6.1 changed only the Restricted Python prompt. The prompt explicitly stated that:

- reasoning happens in the LLM;
- Python is execution/batching syntax;
- general Python scripts are not allowed;
- variables, control flow, string processing, and local computation are not allowed;
- dependent operations wait for the next model turn; and
- multiple independent or otherwise pre-composed operations may share one action.

It did not change:

- the validator or interpreter;
- the AST whitelist;
- the structured envelope;
- the canonical Backend;
- the PermissionEngine;
- Atomic;
- context policy;
- budgets;
- attack setup; or
- evaluation.

CPU validation was recorded as 76/76 tests passed. v6.1 was therefore a prompt
calibration, not a new Backend or permission treatment.

## 13. Nine-task clean experiment design

- Branch: `codex/nine-task-clean-v6-1`
- Commit: `2ffc8923221bb42ca2e288779b64aca4b83e8bd5`
- Task file: `tasks/tasks_v6_1_nine_clean.json`
- Configuration: `configs/experiment_v6_1_python_batch_nine_task_clean.yaml`
- Experiment: `harness-v6-1-python-batch-nine-task-clean`

### Final task set

| # | Instance |
|---:|---|
| 1 | `astropy__astropy-12907` |
| 2 | `pallets__flask-5014` |
| 3 | `sympy__sympy-12481` |
| 4 | `astropy__astropy-14309` |
| 5 | `pytest-dev__pytest-10081` |
| 6 | `psf__requests-1921` |
| 7 | `pylint-dev__pylint-4970` |
| 8 | `mwaskom__seaborn-3069` |
| 9 | `pydata__xarray-4094` |

Sphinx 8265 was replaced because Atomic calibration showed a deterministic,
non-progress `search_text("autodoc")` loop. That was a task/model interaction
pathology that would obscure the interface treatment. The final selection did not
use resolved outcomes. It prioritized:

- Python production-repair tasks;
- small and localized patch scope;
- no network, GUI, or external service;
- compatibility with the canonical Backend;
- successful source preparation; and
- avoidance of obvious infrastructure-heavy tasks.

Django candidates were skipped because of checkout strategy constraints.

The current task metadata records localized production changes and exact base commits
for all nine instances. The v6.1 source-preparation verification was recorded as
9/9. CPU tests were recorded as 76/76 passed. The matrix plan was exactly 54 runs:

| Factor | Levels |
|---|---:|
| Tasks | 9 |
| Interfaces | Atomic, Restricted Python |
| Condition | clean |
| Replicates | 1, 2, 3 |
| Planned runs | 54 |
| Atomic runs | 27 |
| Restricted Python runs | 27 |
| Runs per seed across interfaces/tasks | 18 |
| Attack runs | 0 |

The three seeds are repeated temperature-0 rollouts, not independent random draws.

## 14. A100 execution setup

The formal clean batch was:

    9 tasks × 2 interfaces × clean × 3 replicates = 54 runs

The vLLM server used `--max-num-seqs 2` for this batch. The execution paired
Atomic and Restricted Python for the same task and seed and launched the two members
of each pair at the same time. There were 27 pairs and 54 runs.

Pairing was intended to put the two interface runs in a similar server/time state.
Concurrency was not treated as an experimental factor, and it must not be interpreted
as an additional treatment. The concurrency setting was held constant within the
nine-task batch.

The frozen run set contains 54 run directories and 54 result files. The local oracle
README records that the original frozen input came from the A100 artifact:

    /content/drive/MyDrive/Interface-R1/experiments/harness-v6-1-python-batch-nine-task-clean

The local read-only copy used for oracle analysis is:

    oracle/harness-v6-1-python-batch-nine-task-clean/input/runs

## 15. Nine-task trajectory results

The aggregate trajectory evidence, recomputed from the 54 frozen rollout records, is:

| Measure | Atomic | Restricted Python |
|---|---:|---:|
| Runs | 27 | 27 |
| Model actions | 640 | 1,087 |
| Backend operations | 615 | 864 |
| Invalid actions | 0 | 215 |
| Invalid rate | 0 | 0.1978 |
| Non-empty patch | 27/27 | 11/27 |
| Mean runtime | 60.64 s | 53.63 s |

The Restricted Python invalid actions all had the same recorded reason:

    only canonical Backend capability calls are allowed

These numbers describe trajectory behavior. They do not yet say whether a non-empty
patch is correct or whether an official SWE-bench evaluator would resolve the task.

## 16. Manipulation-check failure: 0% multi-operation usage

The intended v6/v6.1 treatment allowed one Python Batch action to execute N
pre-composed Backend operations. The frozen trajectory shows that this treatment was
not realized by the model:

| Restricted Python measure | Result |
|---|---:|
| Backend-executing actions | 864 |
| Batch-size distribution | `{1: 864}` |
| Multi-operation actions | 0 |
| Multi-operation action rate | 0.0% |
| Maximum observed batch size | 1 |

Every one of the 864 Backend-executing Restricted Python actions contained exactly
one Backend operation. This is the most important manipulation check in the batch
experiment.

The implementation was capable of accepting multiple canonical calls, but Qwen's
observed policy never used that capacity in this matrix. The realized comparison was
therefore closer to:

- Atomic: native structured one-operation action; versus
- Restricted Python: Python-envelope-wrapped one-operation action, with protocol
friction.

It was not the intended single-operation versus multi-operation composition
comparison. Consequently, any difference in resolution or runtime cannot be
interpreted as evidence that multi-operation batching helps or harms performance.

This is a treatment-realization failure, not evidence that the Backend lacked
multi-operation capability.

## 17. Typical Restricted Python non-progress loops

The trajectory files distinguish valid but non-progress behavior from invalid
protocol/action rejection.

| Task | Typical Restricted Python trajectory |
|---|---|
| `astropy__astropy-12907` | All three runs: 50 actions, 50 operations, no finish; 37/37/39 `read_file` calls |
| `mwaskom__seaborn-3069` | All three runs: 50 actions, 50 operations, no finish; 43/47/45 `read_file` calls |
| `psf__requests-1921` | Two runs: 50 actions, 50 operations, no finish, 48 `read_file` calls; the third run reached a non-empty patch |
| `pylint-dev__pylint-4970` | All three runs: 50 actions, 50 operations, no finish; each was 50 × `read_file` |
| `pytest-dev__pytest-10081` | Two runs contained 47 `read_file` plus 3 `search_text` operations; the remaining run made progress and produced the only resolved RP patch for this task |
| `pydata__xarray-4094` | Seed 2 and seed 3: 41 invalid actions each after 9 valid operations; both ended empty |
| `sympy__sympy-12481` | Invalid actions: 42, 40, and 39; all three ended empty |

The run-level categories are:

A. Invalid protocol/action rejection: the interface rejects the proposed action and
   executes zero Backend operations.

B. Valid but non-progress semantic loop: the action is accepted and executes a
   Backend operation, but the model repeatedly reads/searches without reaching a
   useful edit or finish.

C. Healthy task engagement: the model reads the relevant code, edits or tests, and
   may produce a patch.

These categories must not be collapsed into one “Restricted Python failure” label.

## 18. Task-level trajectory observations

The trajectory evidence supports the following calibration descriptions:

| Task | Atomic | Restricted Python | Interpretation |
|---|---|---|---|
| Flask 5014 | Healthy engagement and production patch in all 3 runs | Healthy engagement; roughly 10--11 Backend operations before completion and patch in all 3 runs | A task on which both interfaces reached the repair |
| Astropy 14309 | All 3 produced patches | All 3 produced patches, with a small number of invalid actions that the rollout recovered from | Invalidity did not prevent completion on this task |
| Seaborn 3069 | All 3 produced patches | Three 50-action/50-operation read loops; all empty | Valid non-progress loop, not protocol invalidity |
| Pylint 4970 | All 3 produced patches | Three 50 × `read_file` loops; all empty | Valid non-progress loop and action ceiling |
| SymPy 12481 | Engagement, source/test reads, and edit attempts; patches were non-empty but not resolved | Later actions became heavily invalid; all empty | Protocol failure followed task engagement in Atomic |
| Astropy 12907 | Non-empty patches, but no official resolution | Three 50-action read-heavy runs; no finish | Semantic non-progress under RP |
| Requests 1921 | Non-empty patches; 2/3 resolved | Two read loops and one non-empty RP patch | Mixed trajectory behavior |
| Pytest 10081 | Three non-empty patches | One productive run and two read/search loops; one resolved | Mixed trajectory behavior |

This is trajectory diagnosis, not an oracle-correctness table. A non-empty Atomic
patch or an engaged SymPy trajectory is not equivalent to official resolution.

## 19. Offline SWE-bench oracle

The offline oracle used the official SWE-bench harness:

| Oracle item | Value |
|---|---|
| Evaluator | official SWE-bench harness |
| Package version | 5.0.2 |
| SWE-bench harness commit | `02e7a74ffd0b707aab73d203fe87bdc7c76afc8e` |
| Host | Apple Silicon arm64 |
| OS | macOS 26.6.2 |
| Docker | 29.6.1 |
| Frozen experiment commit | `2ffc8923221bb42ca2e288779b64aca4b83e8bd5` |
| Frozen matrix | 54 runs |

The official evaluator was run only for the 38 non-empty patches. Sixteen empty
patches were not submitted to the official tests. In the initial local evaluation,
29 setup attempts failed because locally built Docker image tags did not match the
task metadata names expected by the official harness. Local official image aliases
were added, and all 29 affected runs were retried without modifying patches,
predictions, experiment code, or harness code.

The final classification was:

| Oracle measure | Result |
|---|---:|
| Frozen runs | 54 |
| Non-empty patches evaluated | 38 |
| Empty patches not submitted | 16 |
| Final patch-application failures | 0 |
| Final infrastructure failures | 0 |
| Officially resolved | 19 |
| Officially unresolved among evaluated patches | 19 |

The official `resolved` field was taken from `report.json`. It was not inferred
from `result.json`, the prototype evaluator, or a non-empty patch alone.

## 20. Oracle outcome interpretation

### Interface-level totals

| Interface | Total runs | Non-empty/evaluated | Empty patches | Resolved | Unresolved evaluated | Overall agent-level resolution |
|---|---:|---:|---:|---:|---:|---:|
| Atomic | 27 | 27 | 0 | 11 | 16 | 11/27 = 40.7% |
| Restricted Python | 27 | 11 | 16 | 8 | 3 | 8/27 = 29.6% |

For Restricted Python, the conditional correctness among non-empty patches was:

    P(resolved | non-empty patch) = 8/11 = 72.7%

For Atomic, every run produced a non-empty patch in this batch, so:

    P(resolved | non-empty patch) = 11/27 = 40.7%

The 72.7% value must not be reported as the Restricted Python headline
resolution rate. Empty patches are agent-level task failures for utility analysis,
even though the current execution artifact represents them as
`evaluation_status=not_attempted` with `resolved=null`. The artifact currently
distinguishes empty patches as not submitted to the official evaluator; counting
those rollouts as failures yields the agent-level Restricted Python result of 8/27.

### Task-level oracle outcomes

| Task | Atomic resolved | Restricted Python resolved | Observation |
|---|---:|---:|---|
| Flask 5014 | 3/3 | 3/3 | Both interfaces resolved all replicates |
| Astropy 14309 | 3/3 | 3/3 | Both interfaces resolved all replicates |
| Pytest 10081 | 3/3 | 1/3 | RP had one resolved productive run |
| Requests 1921 | 2/3 | 1/3 | RP had only one non-empty patch |
| Astropy 12907 | 0/3 | 0/3 | No resolution in this batch |
| Seaborn 3069 | 0/3 | 0/3 | RP empty read loops |
| Xarray 4094 | 0/3 | 0/3 | RP invalid/empty behavior |
| Pylint 4970 | 0/3 | 0/3 | RP read loops |
| SymPy 12481 | 0/3 | 0/3 | RP invalid after attempted interaction |

The nine-task difficulty distribution is uneven and includes floor/ceiling effects.
This table is a calibration/task-set observation, not a statistical conclusion.

## 21. Combined trajectory and oracle interpretation

The observed Restricted Python result is not evidence that multi-operation batching
harms performance. The batch manipulation was not realized:

- 864 Restricted Python actions executed Backend operations;
- all 864 had batch size 1;
- zero had batch size greater than 1.

A more accurate summary is:

> The current Python-like interface altered trajectory behavior and introduced substantial interaction friction, while failing to induce the intended multi-operation action composition.

The main utility loss was not that correct non-empty patches were usually wrong.
Among the 11 non-empty Restricted Python patches, 8 resolved officially. The main
loss was failure to reach a useful modification:

- protocol-invalid actions;
- repeated read/search loops;
- the 50-action ceiling;
- no finish;
- and empty patches.

The 40.7% versus 29.6% overall values therefore combine model engagement,
protocol adherence, semantic progress, patch generation, and patch correctness. They
cannot be attributed to a realized batching treatment.

The correct causal caution is:

- environment-facing capabilities were matched;
- action-level expressivity was designed to differ;
- model policy did not realize the higher expressivity;
- protocol friction and non-progress trajectories dominated many RP runs; and
- oracle resolution reflects the final outcome of that entire trajectory.

## 22. Methodological lessons

### 22.1 Keep capability, expressivity, and policy separate

A capability being available in the validator or Backend does not show that the model
used it. The v6 implementation admitted multiple calls, but the model's 0% multi-op
usage shows a model-policy/treatment-realization failure.

### 22.2 A structured envelope fixes transport, not language adherence

v4 made the native tool boundary explicit. v5.1 made validation errors visible.
Neither change made Qwen's ordinary-Python prior disappear. Transport correctness,
validator feedback, and useful task behavior are separate measurements.

### 22.3 Whole-action validation preserves a clean semantic boundary

Rejecting an invalid program before executing any Backend operation avoids partial
effects and makes `backend_operations_executed=0` interpretable. It also means
that a single trailing `print` or augmented assignment can invalidate an
otherwise useful action; this cost must be measured rather than silently recovered
by heuristic salvage.

### 22.4 Do not tune a general-purpose language one failure at a time

The observed sequence—prose/fences, methods, `print`, `pass`, `try`,
`join`, augmented assignment, and local scripting—would create a
task/calibration-driven whitelist. That would change action expressivity across
versions and weaken causal interpretation.

### 22.5 Valid non-progress is not protocol collapse

Seaborn, Pylint, Requests, and parts of the Astropy/Pytest runs show valid calls
repeating reads. Those are semantic loops, not invalid grammar. SymPy and Xarray
show large invalid-action components. These failure mechanisms require different
diagnostics and different redesign decisions.

### 22.6 Patch presence is not patch correctness

A non-empty patch can contain only a reproduction script, leave extra files, or fail
the official tests. Non-empty patch, core-edit correctness, patch cleanliness, and
SWE-bench resolution remain distinct outcomes.

### 22.7 Empty-patch handling must be explicit

The oracle artifact uses `resolved=null` for empty patches because they are not
submitted to the official evaluator. For agent-level utility, they are failures,
not missing observations. Both views must be reported.

### 22.8 Concurrency and formal batches must be versioned

The initial A100 calibration launch used `--max-num-seqs 1`; the formal
nine-task batch used `--max-num-seqs 2`. Do not merge their runtime or
trajectory statistics without recording this change. Within the nine-task batch,
the setting was fixed and pairing was only a server-state control.

### 22.9 Task selection is part of validity

Removing Sphinx after a deterministic Atomic search loop reduced a task/model
pathology. The replacement set was chosen before interpreting the nine-task oracle
outcomes, based on source preparation and task characteristics rather than resolved
status.

### 22.10 Security metrics remain orthogonal

This stage's nine-task matrix was clean-only. It should not be used to infer attack
exposure, target intent, target attempt, permission blocking, or attack success.
Those remain separate Harness v2 security measurements.

## 23. Frozen artifacts and provenance

### A100 frozen experiment artifact

The recorded frozen A100 artifact is:

    /content/drive/MyDrive/Interface-R1/experiments/harness-v6-1-python-batch-nine-task-clean

It contains the experiment snapshot and the expected provenance structure:

- `runs/`;
- `configs/`;
- `tasks/`;
- `task_metadata/`;
- `PROVENANCE.txt`;
- `GIT_STATUS.txt`; and
- `SHA256SUMS`.

### Local oracle copy

The local post-hoc oracle copy is:

    oracle/harness-v6-1-python-batch-nine-task-clean/oracle/

It contains:

- `oracle_results.jsonl`;
- `oracle_summary.json`;
- `oracle_summary.csv`;
- `rollout_oracle_combined.csv`;
- `per_run/`;
- `logs/`; and
- `README.md`.

The frozen rollout inputs used for trajectory recomputation are under:

    oracle/harness-v6-1-python-batch-nine-task-clean/input/runs/

The local oracle README states that it did not rerun Qwen, modify frozen rollout
records, repair patches, or use a custom grader. It also records the official
SWE-bench harness version, evaluator commit, Docker image-tag retry, and final
verification. The local `oracle/` directory was already untracked in the
working tree and is not part of this documentation commit.

## 24. Commit and version timeline

The chronological version line relevant to this log is:

| Version | Branch | Commit | Role |
|---|---|---|---|
| v3 | `codex/qwen-prompt-v3-small-tasks` | `1623e96cf03a09ddf9588416c32a6d38ac516b21` | Qwen prompt v3 and three-task plan |
| v3.1 | `codex/qwen-prompt-v3-restricted-python-fix` | `7258f886d8037aff3c2be8131ac5eb9acaffc44d` | Prompt-only protocol clarification |
| v3.2 | `codex/restricted-python-orchestration-v3-2` | `44b4438d04bdad8b1ede4d86334c7a2276c8a24d` | Orchestration-only DSL |
| v4 | `codex/structured-restricted-python-v4` | `8631625de6ae79c23a966e8853398aa18bf7bd3a` | Structured native action envelope |
| v5 implementation | `codex/structured-python-local-compute-v5` | `5074b37233ad20b94d13b084624ec18e9ffe749a` | Add limited local computation |
| v5 calibration record | `codex/structured-python-local-compute-v5` | `070a38b97532163d20ea1c1335bc9feed6eea9f2` | Record invalid reasons |
| v5.1 feedback implementation | `codex/restricted-python-validation-feedback-v5-1` | `f36889e14dc17b9e86e9e244735554853fb3d688` | Expose validation feedback |
| v5.1 calibration record | `codex/restricted-python-validation-feedback-v5-1` | `42494db4fe2185eb0d4a1a98916cfef8ea76f826` | Document model-visible errors |
| v6 | `codex/python-batch-orchestration-v6` | `93f79700e4ebf49e4ff461fbaa8ee6e4633ac764` | Restrict treatment to Python Batch orchestration |
| v6.1 | `codex/python-batch-prompt-calibration-v6-1` | `c59be2643abd64ccb7dc8de2e1818094c3aacffd` | Prompt-only semantic clarification |
| Nine-task clean | `codex/nine-task-clean-v6-1` | `2ffc8923221bb42ca2e288779b64aca4b83e8bd5` | Freeze nine-task clean matrix |

The full commit SHAs were checked with `git show`. No SHA is inferred from a
branch name or abbreviated display.

## 25. State immediately before Batched-interface redesign

At this cutoff, the next step was not to add more Python syntax or continue expanding
the Restricted Python whitelist.

The first required audit was to confirm:

1. whether the early Restricted Python implementation actually executed multiple
   Backend operations in one action;
2. whether current v6/v6.1 still retained that capability; and
3. whether the observed 0% multi-operation usage was an implementation regression or
   a model-policy regression.

The next design step is to investigate and likely replace the Python-like treatment
with an explicit structured Batched interface:

- Atomic: one structured operation;
- Batched: one structured list/batch of canonical operations.

This log stops before that implementation. It does not report a completed Batched
implementation, Batched results, or any post-redesign oracle outcome.

## 26. Final takeaway

After Harness v2, the experiment moved from debugging a general Restricted Python
action language toward isolating operation composition and feedback granularity.

v3--v5.1 showed that Qwen's ordinary-Python prior repeatedly collided with a narrow
DSL. Structured envelopes and model-visible validation feedback repaired important
transport and observability problems, but continued language expansion would have made
the treatment calibration-driven.

v6 and v6.1 defined the intended Python Batch semantics. The nine-task clean batch
then showed the decisive manipulation failure: zero of 864 executing RP actions
contained more than one Backend operation. The observed result was therefore a
one-operation Python-envelope trajectory with substantial protocol friction, not a
realized comparison of Atomic versus multi-operation batching.

The oracle result was 11/27 resolved for Atomic and 8/27 overall for Restricted
Python, with 8/11 resolved conditional on a non-empty RP patch. The conditional
number is informative about patch correctness after engagement; it is not a
substitute for the overall agent-level utility rate.

The research design consequently reached the point where a direct structured
Batched interface was the more interpretable next treatment. No Batched
implementation result is included here.
