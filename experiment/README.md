# Experiment implementation

This directory is being migrated stage by stage to the R0–R8 protocol in
[`docs/aug29experiment.md`](../docs/aug29experiment.md). R0 is complete; R1 is
the next unstarted gate.

Current gate: **R1 — Qwen / ModelScope / A100 feasibility (`REVISE`)**.
The local config, runtime, CLI, and offline tests are ready; two successful real
A100 processes and a frozen resolved revision are still required.

The files still carrying D0 names or v28 semantics are preserved as historical
evidence until their assigned R-stage replacements exist. Their exact disposition
is recorded in
[`artifacts/r0/migration_inventory.json`](../artifacts/r0/migration_inventory.json);
they are not active v29 configuration and do not establish an R-stage pass.

Do not update a legacy file opportunistically. Follow its target stage in the R0
inventory, preserve the v28 evidence, and remove replacement-only utilities after
their v29 equivalents pass.
