# Agent Guide for the Interface Demo

## Mission

This repository builds a minimal, auditable demo for comparing **Atomic** and
**Restricted Python** action interfaces on one repository-level coding task.

The research question and treatment are already fixed. Do not redesign them in
code.

Authoritative documents, in descending order:

1. `docs/interface29.md` — research design and claims.
2. `docs/aug29experiment.md` — implementation protocol and R0–R8 gates.
3. This file — day-to-day repository workflow.

If these documents conflict, stop and report the conflict before editing code.

## Current State

- Current formal stage: **R2 — Clean task selection and freeze** remains unpassed
  (`status: incomplete`, `decision: pilot_only`) because no native x86_64 replay is
  available.
- Selected development route: **Implementation Pilot**. The R5 interface pilot is
  complete at implementation commit `71ec91d`; the next implementation stage is
  **R6-P — local fake-model runner and optional Colab Qwen pipeline smoke**.
- R6-P artifacts are development evidence only and cannot unlock formal R6–R8 or
  support a four-cell interface-effect claim.
- **R1 — Qwen / ModelScope / A100 feasibility** passed on 2026-08-30; its frozen
  configuration and evidence summary are recorded in `artifacts/r1/R1_DECISION.md`,
  while the complete private run bundle remains on Google Drive.
- **R0 — Documentation and workspace baseline** passed on 2026-08-30; its
  migration audit and file-by-file disposition are recorded in `artifacts/r0/`.
- The existing D0 implementation remains v28 evidence and must be migrated only
  in the target stage assigned by `artifacts/r0/migration_inventory.json`.
- The notebook in `notebooks/` is exploratory support, not the experiment runner
  and not evidence that any R-stage has passed.

Do not advance the formal stage without a recorded formal passing decision. A pilot
stage may advance only when its decision records `pilot_only`, the formal status,
the claim limitation, and the next pilot stage.

## Non-Negotiable Experimental Invariants

The four demo cells must use the same:

- model and immutable model revision;
- base task, issue, repository snapshot, and functional tests;
- permissions and policy object;
- execution backend and backend capabilities;
- sandbox and execution environment;
- model-turn, backend-operation, token, time, and retry budgets.

Only these factors may vary:

- interface: `Atomic` or `Restricted Python`;
- environment: `Clean` or `Adversarial`.

Never change permissions, tasks, tests, budgets, attack definitions, or backend
capabilities to make one condition pass. Agent/task failure is an experimental
outcome. Infrastructure failure follows the frozen retry rule.

## Architecture Boundary

There must be exactly one canonical execution backend and one permission engine.

```text
Atomic adapter -----------\
                           > shared backend -> shared permission -> sandbox
Restricted Python adapter/
```

- Atomic: one parsed non-finish model action maps to exactly one backend operation
  attempt.
- Restricted Python: one model action maps to zero or more calls to that same
  backend.
- Adapters may translate syntax and format observations; they must not execute
  filesystem or process operations themselves.
- Every side effect, denial, invalid request, timeout, and execution error must be
  represented in the canonical audit trail.

Restricted Python must never receive direct access to filesystem APIs, `os`,
`pathlib`, `subprocess`, imports, sockets/network, environment variables,
`eval`/`exec`, FFI, host objects, or audit logs. All authority is exposed through
narrow capability objects backed by the shared backend.

## Safety Boundary

- Run attacks only as synthetic conditions in isolated, disposable workspaces.
- Use episode-specific fake canaries; never use real credentials or user files.
- Keep network disabled unless an explicitly frozen protocol step requires an
  allowlisted source.
- Never execute attacks against production, third parties, or uncontrolled agents.
- Keep audit logs outside the agent-writable workspace and redact canary plaintext
  from normal logs.

## Repository Layout

```text
AGENTS.md                 agent operating rules
README.md                 human-facing project entry point
docs/
  interface29.md          research design source of truth
  aug29experiment.md      R0–R8 implementation protocol
  archive/                superseded research notes; not normative
experiment/               staged demo implementation
notebooks/                exploratory notebooks only
scripts/                  lightweight repository checks
artifacts/                local generated decks/build outputs; Git-ignored
```

As implementation advances, create only the directories required by the current
stage. Follow the target structure in `docs/aug29experiment.md`. Do not
add speculative frameworks or duplicate backend layers.

## Required Workflow for Every Coding Task

1. Explain the relevant concept in plain language before writing code.
2. Inspect existing files, Git status, and the current R-stage.
3. Read the relevant protocol section and its exit criteria.
4. Propose a small implementation plan.
5. Implement the smallest useful change for the current stage.
6. Add deterministic tests for changed behavior when appropriate.
7. Run the narrow tests first, then the relevant stage validation.
8. Explain how the user can run the code or checks.
9. Report changed files, exact commands/results, and unresolved risks.
10. Ask three short questions that check the user's understanding.

Before moving to the next stage, record:

```text
status: complete | incomplete | blocked
artifact: <path(s)>
decision: pass | revise | blocked
open_risks: <none or explicit list>
provenance: <commands, versions, commit, and digests>
next_stage: <R-stage or named research skill>
```

## Testing and Validation

- Prefer deterministic, offline tests.
- Backend operations, permissions, adapters, sandbox escapes, security oracles,
  capability equivalence, reset determinism, and config invariants require
  automated tests.
- Test allowed and forbidden cases, including deny/error/timeout paths.
- Never weaken a test or oracle to make a condition pass.
- Do not claim a stage passed unless all required artifacts and exit criteria exist.

Repository-only check available now:

```bash
python3 scripts/check_repository.py
```

Once implementation tests exist, keep them under `experiment/tests/` and document
the exact command in `README.md`.

## Git and Reproducibility

- Use focused branches and small commits; do not commit directly to `main` for
  implementation work.
- Before committing, review `git status`, `git diff --check`, and the staged diff.
- Do not commit secrets, tokens, `.env` files, model weights, benchmark clones,
  generated experiment results, caches, or large build artifacts.
- Record the exact source commit, config/schema/prompt digests, model and dataset
  revisions, container digest, seed, and runtime versions for experiment runs.
- Preserve failed and retried runs according to the protocol; do not silently
  overwrite them.

## Engineering Style

- Prefer readable standard-library Python until a dependency is demonstrably
  necessary.
- Keep modules single-purpose and dependencies one-directional.
- Use typed data structures and stable, versioned schemas at experiment boundaries.
- Avoid hidden defaults, floating versions, interface-specific special cases, and
  silent fallback behavior.
- Leave the repository runnable and accurately documented. If it is not runnable,
  state exactly what is missing and keep the stage decision at `revise`.
