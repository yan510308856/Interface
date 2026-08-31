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
  - artifacts/r2/pilot_summary.json
  - artifacts/r2/R2_DECISION.md
  - docs/archive/v28/experiment/tasks/manifest.yaml
decision: pilot_only
host: arm64 Mac using linux/amd64 Docker emulation; no native x86_64 replay
validation:
  - python3 scripts/validate_task.py --manifest-only: exit 0, R2_MANIFEST_OK
  - python3 -m unittest experiment.tests.test_task_manifest: exit 0, 10 tests
  - python3 -m unittest discover -s experiment/tests -p 'test_*.py': exit 0, 30 tests
  - python3 scripts/check_repository.py: exit 0
  - baseline pilot r2-pilot-baseline-02: expected exit 1, 2 failed and 13 passed
  - reference pilot r2-pilot-reference-01: exit 0, 15 passed
open_risks:
  - no native x86_64 Docker replay
  - baseline/reference were not independently repeated
  - results are development evidence only
provenance:
  - source commit before working-tree changes: 0b1cf5834ef680fb859fc435bb8e51c8f729f3b6
  - Docker 29.6.1; arm64 server; fixed linux/amd64 image digest 7485c1e3c8861efd0c6a4a78b952857592e541031039000d25e9481f045dc4a3
  - pilot scope is a direct frozen pytest smoke inside the task image, not an official-harness report
  - manifest sha256: 1d2ca427e79a464fb7e435cfc5c0de18a0ff2a0156335347049568667edec056
  - candidate order frozen before any R2 agent or interface task run
  - v28 Docker results are historical supporting evidence and are not counted as R2 repetitions
  - the replaced v28 task manifest is preserved byte-for-byte for its historical digest check
  - initial baseline attempt r2-pilot-baseline-01 retained as an infrastructure failure because Docker Desktop was not running
next_stage: local implementation work may continue as a concept demo; formal R3 remains blocked on formal R2 pass
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

The local pilot completed one effective baseline and one reference run. Both are
explicitly ineligible for the formal R2 gate. R2 can become `pass` only after two
unique baseline run IDs and two unique reference run IDs run on a native x86_64
Docker host and produce complete official-harness reports with identical
dataset-row, image, and fresh workspace-tree identities.
