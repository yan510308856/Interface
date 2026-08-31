# Experiment implementation

This directory is being migrated stage by stage to the R0–R8 protocol in
[`docs/aug29experiment.md`](../docs/aug29experiment.md). R0 and R1 are complete;
R2 is the current, pilot-only gate.

Current gate: **R2 — local implementation-feasibility pilot**.
R1 passed with a frozen ModelScope revision and runtime after two independent A100
workers completed all three fixed prompts and the 16K context probe. The private
raw bundle remains on Google Drive; the tracked decision and digests are in
[`artifacts/r1/R1_DECISION.md`](../artifacts/r1/R1_DECISION.md).

R2 has frozen the candidate order and implemented the official-harness wrapper.
The local Mac path runs one `linux/amd64`-emulated baseline and reference as
development evidence only. The stage remains incomplete with decision
`pilot_only`; these attempts cannot satisfy the formal repetition gate. See
[`artifacts/r2/R2_DECISION.md`](../artifacts/r2/R2_DECISION.md).

R3 paired-task code may be exercised locally as a pilot while the formal stage
remains blocked. The builder adds only the frozen carrier and episode canary to
the Adversarial overlay; the functional and security oracle outputs are marked
`development_evidence_only`. See
[`artifacts/r3/R3_DECISION.md`](../artifacts/r3/R3_DECISION.md).

R4 adds one canonical backend entry point, one default-deny permission engine,
and an append-only audit logger for tiny disposable fixtures. Its local smoke is
development evidence, not a hardened sandbox or formal stage pass. See
[`artifacts/r4/R4_DECISION.md`](../artifacts/r4/R4_DECISION.md).

R5 adds two representation-only adapters over that same backend. Atomic accepts
one strict JSON action and forwards one valid tool call; Restricted Python uses a
small AST interpreter with no `eval` or `exec`, and exposes only `repo` and
`runner` capability calls. Scripted equivalence, controlled failures, and the
three required bypass checks are development evidence only. See
[`artifacts/r5/R5_DECISION.md`](../artifacts/r5/R5_DECISION.md).

The files still carrying D0 names or v28 semantics are preserved as historical
evidence until their assigned R-stage replacements exist. Their exact disposition
is recorded in
[`artifacts/r0/migration_inventory.json`](../artifacts/r0/migration_inventory.json);
they are not active v29 configuration and do not establish an R-stage pass.

Do not update a legacy file opportunistically. Follow its target stage in the R0
inventory, preserve the v28 evidence, and remove replacement-only utilities after
their v29 equivalents pass.
