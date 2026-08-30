# R2 decision

```text
status: incomplete
artifact:
  - experiment/tasks/candidates.yaml
  - experiment/tasks/manifest.yaml
  - experiment/tasks/astropy__astropy-12907/baseline.patch
  - experiment/tasks/astropy__astropy-12907/reference.patch
  - experiment/tasks/astropy__astropy-12907/test.patch
  - experiment/task_runtime.py
  - scripts/validate_task.py
  - experiment/tests/test_task_manifest.py
  - requirements-r2.txt
  - artifacts/r2/selection_report.json
  - artifacts/r2/R2_DECISION.md
  - docs/archive/v28/experiment/tasks/manifest.yaml
decision: revise
host: local implementation only; formal x86_64 Docker host pending
validation:
  - python3 scripts/validate_task.py --manifest-only: exit 0, R2_MANIFEST_OK
  - python3 -m unittest experiment.tests.test_task_manifest: exit 0, 7 tests
  - python3 -m unittest discover -s experiment/tests -p 'test_*.py': exit 0, 27 tests
  - python3 scripts/freeze_d0.py --check: exit 0, historical v28 digest preserved
  - python3 scripts/check_repository.py: exit 0
open_risks:
  - Two fresh official-harness baseline attempts have not run under R2.
  - Two fresh official-harness reference attempts have not run under R2.
  - The fresh prepared-image workspace tree identity has not been repeated.
  - Full Docker logs have not yet been copied to private Google Drive storage.
provenance:
  - candidate order frozen before any R2 agent or interface task run
  - v28 Docker results are historical supporting evidence and are not counted as R2 repetitions
  - the replaced v28 task manifest is preserved byte-for-byte for its historical digest check
next_stage: remain at R2 until the four official-harness attempts pass
```

R2 uses the first row of the frozen SWE-bench Verified test split:
`astropy__astropy-12907`. The candidate list contains one candidate by design. If it
fails a non-infrastructure screening criterion, R2 stops instead of adding a more
favorable candidate after observing outcomes.

The official harness does not execute a prediction whose `model_patch` is empty.
The baseline therefore uses a frozen inert patch that only creates
`.r2_baseline_probe`; it does not modify source code, tests, issue semantics, or the
functional oracle. Baseline success means the official report is unresolved with
the two frozen FAIL_TO_PASS tests failing and all 13 PASS_TO_PASS tests passing.

R2 can become `pass` only after two unique baseline run IDs and two unique reference
run IDs produce complete reports with identical dataset-row, image, and fresh
workspace-tree identities.
