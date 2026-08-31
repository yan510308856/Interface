# Experiment implementation

This directory is being migrated stage by stage to the R0–R8 protocol in
[`docs/aug29experiment.md`](../docs/aug29experiment.md). R0 and R1 are formally
complete; formal R2 remains unpassed. The selected development route is the
separate Implementation Pilot track.

Current implementation stage: **R6-P — agent-loop implementation pilot**. The R5
pilot is complete; formal R5 is not passed.
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
three required bypass checks complete the selected R5 pilot scope. They remain
development evidence only. See
[`artifacts/r5/R5_DECISION.md`](../artifacts/r5/R5_DECISION.md).

R6-P will add the single episode runner, result-bundle schema, metrics derivation,
fake-model fixtures, and controlled failure paths. An optional Colab A100 Qwen
smoke may exercise the same pipeline, but every R6-P output must declare
`development_evidence_only` and `formal_r6_eligible: false`. It cannot be included
in a formal four-cell result.

The files still carrying D0 names or v28 semantics are preserved as historical
evidence until their assigned R-stage replacements exist. Their exact disposition
is recorded in
[`artifacts/r0/migration_inventory.json`](../artifacts/r0/migration_inventory.json);
they are not active v29 configuration and do not establish an R-stage pass.

Do not update a legacy file opportunistically. Follow its target stage in the R0
inventory, preserve the v28 evidence, and remove replacement-only utilities after
their v29 equivalents pass.
