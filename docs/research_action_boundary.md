# Research Direction Transition: Execution Granularity and Action Boundaries

**Status:** Current research-direction record and forward experiment design

**Scope of this document:** This document records a change in the research
question. It does not claim that the proposed G1/G2/G4 treatments have already
been implemented or experimentally validated. Existing historical documents
and rollout records remain unchanged.

## 1. Research Direction Transition

### Previous direction

The earlier research question was approximately:

> When model, task, backend capability, permission policy, and environment are
> held fixed, does the choice between an Atomic interface and a Restricted
> Python interface change the trajectory, utility, resource cost, or security
> behavior of a repository-level coding agent?

This framing treated the Python-shaped interface as the primary independent
variable.

### Current direction

The study will no longer treat `Restricted Python`, `Python execution`, or
Python representation as the primary treatment. The new central question is:

> How does a system-imposed action/execution boundary affect a repository-level
> coding agent when the agent may commit at most a specified number of backend
> operations between two consecutive model-visible observations?

The main independent variable is therefore **Execution Granularity**, not the
surface representation language.

The change is based on an audit of the actual implementation and trajectory
evidence:

1. The current RP implementation is straight-line static batching. One RP
   action can dispatch multiple backend operations sequentially, but backend
   operations do not re-enter the LLM.
2. The RP validator rejects assignment, local variables, `if`/`else`, loops,
   backend-result-dependent calls, and local computation. The code is parsed as
   an AST and converted into literal-argument backend dispatches; it is not
   executed as general Python.
3. The v6/v6.1 clean trajectory audit showed that the implementation admitted
   multi-operation actions, but the model did not realize that capacity: all
   864 backend-executing RP actions had batch size 1.

The implementation capacity and the model's realized behavior must remain
separate. The existing evidence is a treatment-realization failure, not
evidence that the canonical backend lacks multi-operation capability.

The current manipulation is therefore better described as:

```text
single-operation action
        vs.
multi-operation action
        plus
different observation / decision-checkpoint frequency
```

Directly manipulating action granularity avoids confounding the treatment with
Python syntax, Python expressiveness, local computation, control flow, and
model adherence to a narrow Python DSL.

The historical implementation facts are recorded in
[`docs/learning_log_2026-09-05.md`](docs/learning_log_2026-09-05.md), especially
the v6/v6.1 audit and the 0% multi-operation manipulation check. The current
RP execution path is implemented in
[`experiment/interfaces/restricted_python.py`](experiment/interfaces/restricted_python.py).

## 2. Core Research Construct

### Execution Granularity `G`

Define the independent variable as:

> **Execution Granularity `G`** is the maximum number of backend operations
> that may be committed and executed within one model action before the LLM
> receives the next model-visible observation.

The primary proposed levels are:

- `G1 / Atomic-1`: each non-terminal model action may contain at most one
  backend operation.
- `G2 / Batch-2`: each non-terminal model action may contain at most two
  backend operations.
- `G4 / Batch-4`: each non-terminal model action may contain at most four
  backend operations.

These are upper bounds, not quotas. The intended constraint is:

```text
1 <= N_ops_in_action <= G
```

for a non-terminal task action. The agent must not be forced to add meaningless
operations merely to fill a batch. A terminal `finish` action may contain zero
backend operations and should be analyzed separately.

For primary accounting, `N_ops_in_action` should count operations dispatched to
the canonical backend. Operation status—success, denial, or runtime error—must
be recorded separately rather than silently treating all dispatched operations
as successful.

### Control-flow boundary

```text
G1:
LLM
→ op
→ observation
→ LLM

G2:
LLM
→ op
→ op
→ aggregate observation
→ LLM

G4:
LLM
→ op
→ op
→ op
→ op
→ aggregate observation
→ LLM
```

The treatment changes:

- observation frequency;
- model-level decision-checkpoint density;
- the length of the open-loop operation span;
- the action boundary between model decisions and environment execution.

It must not change the underlying repository capability, permission semantics,
or backend operation semantics.

## 3. Controlled Variables

All granularity conditions should hold the following fixed:

- model;
- decoding configuration;
- task distribution and task instance;
- initial repository state;
- primitive operations;
- operation schemas, except for the minimum batch-container structure required
  to express multiple operations;
- canonical backend;
- backend execution semantics;
- permission policy;
- attack payload and attack placement;
- sandbox and environment;
- context and pruning policy;
- trajectory logging;
- action, operation, timeout, and token-budget definitions;
- evaluation criteria and official grading path.

The intended control is:

```text
same model
+ same task
+ same primitive capabilities
+ same permissions
+ same canonical backend
+ same environment
--------------------------------
only action boundary / max operations per action changes
```

The repository state will naturally evolve differently after the first model
decision. What must be identical is the initial state and the state-transition
semantics exposed by the backend.

## 4. Role of the Canonical Backend

The canonical backend remains necessary even though Restricted Python is no
longer the primary research treatment. It ensures that G1, G2, and G4 all
ultimately use the same environment-facing implementation:

```text
Action Layer
├── G1 / Atomic-1
├── G2 / Batch-2
└── G4 / Batch-4
        ↓
Canonical Backend
├── read_file
├── search_text
├── replace_text
├── create_file
├── delete_file
├── run_process
└── git_diff
```

The action layer may constrain how many operation records are submitted in one
action, but it must not implement a second filesystem, process, Git, or
permission system.

The desired execution shape is conceptually:

```python
for operation in action.operations:
    backend.execute(operation)
```

All conditions should converge on the same `Backend.execute()` path. A Batch
condition must not gain a special backend with different validation, side
effects, error handling, or permission behavior.

Methodologically, the canonical backend provides:

- capability matching;
- permission matching;
- execution-semantics matching;
- a common operation-level trajectory and security record.

The current shared implementation is
[`experiment/backend.py`](experiment/backend.py), with permission checks in
[`experiment/permission.py`](experiment/permission.py).

## 5. Research Gap

### Central gap

Prior work has shown that tool architecture, action boundaries, trajectory
structure, and agent security matter. Controlled evidence is still needed on
the causal effect of system-imposed execution granularity under
capability-matched conditions.

This study therefore isolates:

```text
maximum backend operations per model action
```

### Gap A — Interface effects are confounded

Existing interface comparisons often change several factors at once:

- syntax;
- tool schema;
- search abstraction;
- local computation;
- control flow;
- batching;
- observation frequency;
- protocol and validation behavior.

An observed trajectory difference can consequently be attributed to language
expressiveness, schema ergonomics, model instruction-following, or feedback
timing rather than to action boundaries themselves.

The new study isolates the maximum number of backend operations allowed before
the next model-visible checkpoint.

### Gap B — Feedback and checkpoint frequency

An unresolved systems question is:

> How often should the LLM regain control, observe the environment, and
> reconsider its plan?

The relevant cycle is:

```text
Decision
→ operation(s)
→ observation
→ reconsideration
```

Different checkpoint densities may affect:

- trajectory efficiency;
- redundant exploration;
- failure recovery;
- plan revision;
- exploration versus exploitation;
- task completion.

### Gap C — Security work emphasizes capability boundaries

Security research commonly asks:

```text
What is the agent allowed to do?
```

This study adds:

```text
How many operations may execute before the model receives another checkpoint?
```

The resulting distinction is:

```text
Capability Boundary
vs.
Execution Boundary
```

Execution granularity may be a security-relevant system parameter even when
the set of permitted capabilities is unchanged.

## 6. Main Causal Story

The intended causal chain is:

```text
Execution Granularity
        ↓
Observation Frequency /
Decision Checkpoint Density
        ↓
Trajectory Structure
        ↓
Utility / Cost / Security
```

For adversarial repository conditions, the proposed mechanism is:

```text
Attack exposure
      ↓
Compromised / unsafe decision
      ↓
Operations executed before next LLM checkpoint
      ↓
Attack propagation / blast radius / recovery opportunity
```

Under G1, a possible unsafe trajectory is:

```text
unsafe decision
→ one operation
→ observation
→ model gets another chance to reconsider
```

Under G4, the same initial decision may produce:

```text
unsafe decision
→ op1
→ op2
→ op3
→ op4
→ observation
```

This could produce a larger unsafe propagation span, fewer reconsideration
opportunities, cascading failures, a larger attack blast radius, or a lower
recovery probability. These are hypotheses, not expected results that should
be treated as established facts.

## 7. Research Questions

### RQ1 — Manipulation and behavioral effect

> How does system-imposed execution granularity affect repository-level
> coding-agent trajectory structure under capability-matched conditions?

### RQ2 — Utility and resource cost

> How does execution granularity affect task success, backend-operation usage,
> model turns, token consumption, latency, and other resource costs?

### RQ3 — Security

> How does execution granularity affect attack-induced unsafe behavior under
> repository-borne adversarial conditions?

### RQ4 — Security mechanism

> Does coarser execution granularity increase the number or severity of unsafe
> backend operations that can propagate before the next model-visible
> checkpoint?

### RQ5 — Efficiency–security trade-off

> Is there an efficiency–security trade-off as execution granularity
> increases?

The main factorial interaction is:

```text
Execution Granularity × Attack Condition
```

This interaction should be treated as a central statistical target, not merely
as a descriptive subgroup comparison.

## 8. Experimental Design

The primary design is:

```text
G ∈ {1, 2, 4}
```

with environment conditions such as:

```text
Execution Granularity:
G1 / Atomic-1
G2 / Batch-2
G4 / Batch-4

×

Environment:
Clean
Attack family A
Attack family B
Attack family C
...
```

This is a factorial `Granularity × Attack Condition` design.

Using three levels rather than only 1 versus 4 enables:

- a dose-response or monotonic-trend analysis;
- detection of a nonlinear threshold;
- a stronger test that the result is not caused by two unrelated
  implementations;
- separation of a gradual checkpoint effect from a binary interface effect.

The G1/G2/G4 action containers should be structurally as similar as possible.
The only intentional difference should be the enforced upper bound on the
number of backend operations between observations.

At this stage, G1/G2/G4 are proposed treatments. The repository currently has
Atomic and Restricted Python entry points, not a completed G1/G2/G4 structured
granularity implementation.

## 9. Attack Design Direction

The attack design should remain synthetic, repository-borne, and reproducible.
The attack payload and placement must be fixed across granularity conditions
within each comparison.

At minimum, consider attack families for:

1. repository-text prompt injection;
2. unsafe read or sensitive-target seeking;
3. unsafe write or modification;
4. process-execution misuse;
5. multi-step attack chains.

Multi-step chains are especially important because they can interact directly
with the action boundary:

```text
read malicious instruction
→ inspect target
→ modify file
→ execute command
```

The primary question is not whether the model can perform the individual
operations. Those capabilities remain matched. The question is how many steps
can occur after a decision and before the next model-visible checkpoint.

## 10. Manipulation Check

Formal experiments must first demonstrate that the treatment is realized.
At minimum, record:

- backend operations per model action;
- batch rate;
- action-size distribution;
- fraction of actions using full capacity;
- model-visible observation count;
- backend operations per model-visible observation;
- model turns;
- invalid actions and terminal finish actions separately.

The hard capacity checks are:

```text
G1: every valid non-terminal action has N_ops <= 1
G2: every valid non-terminal action has N_ops <= 2
G4: every valid non-terminal action has N_ops <= 4
```

The behavioral realization check is equally important:

```text
G2/G4 must show some real N_ops > 1 actions
```

Otherwise the nominal treatment has collapsed to G1, and downstream utility or
security differences cannot be interpreted as effects of multi-operation
execution granularity.

Do not conflate:

```text
capability allows batching
```

with:

```text
model actually uses batching
```

The existing v6/v6.1 result is the cautionary example: capability existed, but
observed multi-operation usage was 0%.

## 11. Trajectory Metrics

Metrics should distinguish action-level events from backend-operation-level
events, because the experiment intentionally changes their mapping.

At minimum, record:

- number of model turns;
- total backend operations;
- backend operations per model turn;
- distribution of operations per action;
- read/search/write/process composition;
- repeated-operation rate;
- repeated reads;
- search loops;
- failed backend operations;
- failure-recovery behavior;
- action index to first edit;
- action index to first test;
- operation index to first edit;
- operation index to first test;
- total trajectory length;
- unnecessary operations;
- finish behavior;
- invalid-action behavior;
- model-visible observation count;
- latency and token cost.

The analysis must preserve both views:

```text
action-level trajectory
backend-operation-level trajectory
```

For example, four backend operations in one G4 action and four operations in
four G1 actions are operation-equivalent but not checkpoint-equivalent.

## 12. Security Metrics

Attack success rate alone is insufficient. Record at least:

- attack success;
- unsafe backend-operation count;
- first unsafe operation index;
- unsafe action count;
- unsafe operations per unsafe action;
- unsafe operations after first compromise;
- attack propagation depth;
- recovery after an unsafe attempt;
- blocked unsafe operation;
- safe failure;
- false denial;
- permission denial;
- task utility under attack.

### Working definitions

These names are proposed working definitions and should be finalized before
formal analysis.

#### Unsafe Propagation Span

The number of backend operations executed after the first clearly unsafe or
attack-induced decision and before the next model-visible observation.

#### Post-Compromise Open-Loop Span

The backend-operation span during which the agent continues executing after the
attack has affected its decision process and before the LLM regains a
model-visible checkpoint.

These metrics connect the security outcome to the proposed mechanism rather
than only to the final binary attack-success label.

## 13. Expected Result Patterns

The study is informative under several possible result patterns.

### Pattern A — Efficiency–security trade-off

```text
G ↑
→ model turns ↓
→ cost ↓
→ security risk ↑
```

This would suggest that coarser execution boundaries improve efficiency while
increasing open-loop risk.

### Pattern B — Trajectory effect without security effect

Trajectory structure changes, but security metrics do not change materially.
This would support batching as a potentially safe efficiency optimization under
the tested attack conditions.

### Pattern C — Attack-specific security effect

Clean-condition differences are small, while attack-condition security
differences are substantial. This would support execution granularity as a
latent security variable whose effect depends on attack structure.

### Pattern D — Little or no effect

If G1/G2/G4 show little difference, the result would help explain why earlier
tool-interface effects may have been driven mainly by syntax, expressiveness,
search abstraction, protocol friction, or other confounds rather than batching
itself.

None of these patterns should be assumed in advance.

## 14. Updated Contribution Positioning

The future paper should not claim that any of the following is new by itself:

- batching;
- multi-tool calling;
- code-based tool use;
- tool interfaces changing trajectories.

The contribution should instead be positioned as:

1. explicitly modeling execution granularity/action boundaries as controllable
   system parameters;
2. performing a capability-, permission-, backend-, and environment-matched
   intervention over G1/G2/G4;
3. estimating the causal effect of execution granularity on repository-level
   coding-agent trajectories;
4. combining action-boundary manipulation with adversarial repository
   conditions;
5. analyzing security propagation before the next model-visible checkpoint;
6. exploring the efficiency–security trade-off;
7. complementing binary attack success with process-level security metrics.

## 15. Terminology Update

The following terms should no longer be used as the primary names of the new
experiment:

- Restricted Python;
- Python interface;
- executable Python condition;
- Atomic versus Restricted Python.

They may still be used when referring to historical implementations or
historical results.

Preferred terms are:

- execution granularity;
- action granularity;
- action boundary;
- model-visible observation boundary;
- decision checkpoint;
- open-loop operation span;
- G1 / G2 / G4;
- Atomic-1 / Batch-2 / Batch-4;
- capability boundary;
- execution boundary.

The old documents should remain available as historical records. They should
not be silently rewritten to make the historical Atomic/RP experiments appear
to have implemented the new causal design.

## 16. Immediate Next Steps

The following engineering and study-design tasks remain for a later phase; the
schema-fixed A100 manipulation check described below has already been completed:

1. Audit the current Atomic and RP/static-batch implementations and identify
   reusable components.
2. Design a unified action schema so G1/G2/G4 differ as little as possible
   beyond `max_ops_per_action`.
3. Retain the canonical backend and shared permission path.
4. Implement `max_ops_per_action = 1 / 2 / 4` in the action layer.
5. Define observation aggregation semantics for each granularity condition.
6. Strengthen trajectory logging so action-to-operation parent relationships
   can be reconstructed reliably.
7. Build a dedicated manipulation-check microbenchmark.
8. Freeze the action-boundary policy and its terminology.
9. Run the formal clean and attack factorial experiment only after the
    manipulation check passes.

## Current Decision

The current decision is to stop expanding or treating Restricted Python as the
main research object. Do not implement backend-result-dependent Python control
flow for the present study.

The immediate research target is to isolate **system-imposed
action/execution granularity**—the maximum number of backend operations between
model-visible observations—not to compare Python and Atomic tool
representations.

The current RP implementation and its historical trajectories remain useful as
diagnostic evidence that motivated this transition. They are not themselves a
completed G1/G2/G4 experiment.

## 17. Implemented Harness v1

The repository now contains the first implementation of the new treatment. The
formal path uses one unified `submit_action` JSON tool schema:

```json
{
  "operations": [
    {"name": "read_file", "arguments": {"path": "a.py"}}
  ]
}
```

`GranularityActionAdapter(max_ops_per_action=k)` is shared by G1, G2, and G4.
It performs whole-action validation before calling the canonical
`Backend.execute()` path. A valid static batch executes operations in listed
order, continues after backend errors or permission denials, and returns one
aggregated observation. No backend operation re-enters the model. A terminal
`finish="done"` action has zero operations.

The formal configurations are:

- `configs/experiment_action_boundary_granularity.yaml`: G1/G2/G4 × clean/attack;
- `configs/experiment_action_boundary_granularity_clean.yaml`: G1/G2/G4 clean.

Both `max_model_actions` and `max_backend_operations` are independently
configurable and recorded. The attack manifest remains orthogonal to
granularity and now carries attack-family metadata. Restricted Python and the
old Atomic/RP configs remain legacy paths and are not used by the new formal
configs.

Trajectory events now expose `model_request`, `model_response`,
`interface_action`, and `backend_operation` records. Backend operations carry
stable `action_id`, `operation_id` (`7.1`, `7.2`, ...), operation index, and
parent tool-call ID. The analysis entry point
`python analysis/analyze_granularity.py runs/...` reports manipulation checks
and leaves unsafe-operation metrics explicitly unclassified when no reliable
oracle is configured. The deterministic MC1--MC4 scaffold is runnable with
`python scripts/run_manipulation_check.py`; it measures realized batching and
is not a SWE-bench success benchmark.

The schema-fixed A100 manipulation check has verified real Qwen/vLLM support
for the nested operation `oneOf` schema. The observed manipulation metrics were:

| Condition | Backend ops / model-visible observation | Batch rate | Action-size distribution | Invalid actions |
| --- | ---: | ---: | --- | ---: |
| G1 | 1.0000 | 0 | — | 0 |
| G2 | 1.3524 | 0.3458 | `{1: 68, 2: 37}` | 0 |
| G4 | 1.5089 | 0.3509 | `{1: 72, 2: 25, 3: 13, 4: 2}` | 0 |

These results verify that the live model uses the available G2/G4 capacity;
they do not imply that the model should fill every available slot.

### Canonical operation contract

The exact operation argument schemas are defined once in
`experiment/backend.py` as `OPERATION_ARGUMENT_SCHEMAS`. Legacy Atomic tools
and the new `submit_action` schema are generated from that source. The new
schema uses a discriminated `oneOf` over operation name, with each variant
containing its own typed `arguments` object and `additionalProperties: false`.
Only the enclosing `operations.maxItems` is parameterized by G1/G2/G4.

The current model request path also sets `parallel_tool_calls=false` for all
three formal conditions. This prevents multiple outer tool calls from being
mistaken for one action; batching must occur inside the single
`submit_action.operations` list. Legacy interface request behavior is left
unchanged. The schema-fixed A100 manipulation check verified the provider's
live Qwen/vLLM acceptance of the nested schema.

## 18. Formal matrix pipeline

The formal rollout pipeline is implemented by
`scripts/run_full_matrix.py` and configured by
`configs/experiment_action_boundary_formal.yaml`. The current task set is the
three prepared tasks in `tasks/tasks_v3.json`, so the complete matrix contains

```text
3 tasks × 3 granularities × 2 conditions × 3 rollouts = 54 runs
```

The conditions are `clean` and the existing
`repository_comment_hijack_v1` attack. Clean runs have
`attack_metadata = null`; attack runs record attack family, attack ID, carrier,
placement, target behavior, sentinel target, and expected unsafe capability.
The attack is injected only into each run's disposable repository copy.

The deterministic schedule is blocked by task and rollout. The condition-first
order alternates by block: even blocks run clean then attack, odd blocks run
attack then clean. Each condition wave remains `G1`, `G2`, `G4`, so clean and
attack are counterbalanced while granularity stays balanced within every wave.
This interleaves granularity conditions so server timing and concurrency are not
structurally assigned to one G condition. Up to three workers can run against
one pre-existing vLLM endpoint; the runner never starts vLLM. Each worker
receives a separate temporary repository and run directory.

Every formal run is identified by task, G, condition/attack index, and rollout,
for example `pallets__flask-5014-G2-attack01-r3`. Completed runs require a
matching `result.json`, `trajectory.jsonl`, `metadata.json`, and `COMPLETE.json`.
On `--resume`, incomplete directories are moved to `incomplete_attempts/` and
the run starts again from a fresh disposable repository. Formal roots record
`PLAN.json`, `RUN_MANIFEST.json`, configs, task metadata, attack registry,
server metadata, and Git provenance.

Expected server fields are stored in `server_config.json`. After manually
starting the one vLLM service, its observed values can be recorded without any
probe by passing `--server-metadata observed-server.json` to the formal runner;
the file is copied into the root as the `observed` object.

`analysis/analyze_formal_matrix.py` produces long and grouped CSV/JSON summaries
without invoking SWE-bench. `scripts/freeze_experiment.py` creates a separate
provenance bundle with runtime/dependency metadata and `SHA256SUMS`; it is an
artifact operation and must not modify rollout data. The historical oracle
artifact under `oracle/harness-v6-1-python-batch-nine-task-clean/` is the
reference for official semantics. The tracked `oracle/adapter.py` is a small
normalized metadata layer around that artifact contract: it reads both legacy
`input/runs/` and formal `runs/<run-id>/`, exports one prediction file per
rollout, invokes the same `swebench eval` path, reads `resolved` only from
official `report.json`, and writes per-rollout oracle/combined summaries. The
CLI files are thin wrappers around this one adapter; they are not a replacement
grader. Empty patches are not submitted and count as agent-level failures;
Docker/setup/harness failures remain separate infrastructure outcomes.

After a frozen A100 artifact is downloaded, the official evaluation stage is
explicit and separate from rollout:

```bash
python oracle/prepare_predictions.py --experiment <formal-root>
python oracle/run_official_swebench.py \
  --experiment <formal-root> \
  --task-metadata <verified-task-json> \
  --output <oracle-output-root>
python oracle/summarize_oracle.py \
  --experiment <formal-root> \
  --oracle <oracle-output-root>
```

These commands are not run by the formal pipeline tests or by this code change.

The local validation path is `--dry-run`, which uses a deterministic no-network
model and is not experimental data. The schema-fixed Qwen/vLLM manipulation
check was run separately; the formal rollout and official SWE-bench oracle
remain explicit later stages.
