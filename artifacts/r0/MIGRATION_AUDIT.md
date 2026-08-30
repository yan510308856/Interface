# R0 migration audit

## Scope and conclusion

This audit reconciles the tracked implementation inherited from v28 D0 with the
v29 research design in `docs/interface29.md` and execution protocol in
`docs/aug29experiment.md`. The two authoritative documents agree on the model
source, 2×2 cells, paired task, shared permission boundary, functional/security
oracles, and R0–R8 order. No experiment functionality was implemented in R0.

The complete 18-file disposition is machine-readable in
`migration_inventory.json`. Four D0 artifacts are retained as v28 evidence,
eleven reusable files are assigned to their owning R-stage, and three mixed or
monolithic D0 utilities are marked for removal only after their replacements pass.

## Deviations found

| Area | Existing D0 state | Required v29 state | Owner |
|---|---|---|---|
| Model source | `demo.yaml` uses Hugging Face and an FP8 checkpoint | ModelScope model ID plus resolved immutable revision, proven on A100 | R1 |
| Stage semantics | One D0 gate combines model, task, interface, and digest checks | Separate dependency-ordered R0–R8 gates | R1–R8 |
| Task | Candidate task and Docker evidence were selected under v28 rules | Reapply the v29 preregistered screening and official oracle gate | R2 |
| Paired task | Fixed carrier paths and a partial oracle manifest | Episode-specific synthetic fixture and full paired functional/security oracle | R3 |
| Permission | Candidate default-deny policy is task-specific but unimplemented | One tested permission engine used by one canonical backend | R4 |
| Interface | D0 validator contains a provisional AST/name check | Dedicated Atomic adapter and isolated AST-allowlisted Restricted Python runtime | R5 |
| Schedule | D0 IDs and a monolithic config are already frozen | Regenerate only after R1–R7 pass and compare expanded configs | R8 |

No floating `main`, `master`, `latest`, or `dev` revision was found in the active
machine-readable D0 inputs. References to archived v28 documents remain only where
they describe historical provenance or the migration itself; the active repository
entry points route normative work to v29.

## Deletion boundary

R0 deliberately does not delete legacy code or evidence. `test_d0.py`,
`freeze_d0.py`, and `validate_d0.py` span several new stages and can only be removed
after their stage-specific replacements exist and pass. Deleting them now would
destroy the only executable verifier for the preserved v28 evidence. The two
authoritative documents require this preserve-then-replace order.

## Three-item inventory spot check

- `experiment/configs/demo.yaml` → R8: R1 must first establish immutable
  ModelScope identity; only R8 can assemble the final four-cell config.
- `experiment/configs/permission.yaml` → R4: shared permission is implemented and
  tested with the shared backend before either interface exists.
- `experiment/configs/attack_manifest.yaml` → R3: paired-task construction and
  oracle self-tests precede adversarial model episodes.

## R1 handoff file list

R1 may create only the model-feasibility surface defined by the protocol:

- `experiment/configs/model.yaml`
- `experiment/model_runtime.py`
- `experiment/tests/test_model_config.py`
- `scripts/smoke_model_colab.py`
- `artifacts/r1/<run_id>/<attempt_id>/...`
- `artifacts/r1/R1_DECISION.md`

R1 must not edit the task, carrier, backend, permission, adapter, or demo schedule.
It passes only with two A100 processes using ModelScope and a recorded resolved
immutable revision; local fake-model tests alone are insufficient.

## Safety and provenance

The preserved carrier uses a synthetic local canary and must only run in an
isolated disposable workspace. No network, real credential, production target, or
third party is authorized. Large/private runtime bundles remain outside the agent
workspace and are digest-verified before use.
