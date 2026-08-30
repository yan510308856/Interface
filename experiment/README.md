# Experiment implementation

This directory currently contains the legacy D0 implementation described by
`docs/archive/aug28experiment.md`. It has not yet been migrated to the current
R0–R8 protocol in `docs/aug29experiment.md`.

Current gate: **D0 — Freeze Demo Spec (`D0: REVISE`)**.

The D0 configuration, task, schemas, schedule, digests, and local validation
boundaries are frozen. The benchmark baseline and reference-patch oracles pass in
the pinned task image. D0 remains at `REVISE` because the pinned model and vLLM
runtime have not completed the required live Atomic and Restricted Python smoke
tests on compatible hardware. No D1 backend, adapter, runner, or experiment result
exists yet.

The `.yaml` files use JSON syntax, which is valid YAML 1.2, so the D0 utilities can
parse them with the Python standard library and add no dependency.
