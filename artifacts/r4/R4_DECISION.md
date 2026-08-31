# R4 decision

```text
status: incomplete
artifact:
  - experiment/backend.py
  - experiment/permission.py
  - experiment/audit.py
  - experiment/schemas/operations.yaml
  - experiment/configs/permission.yaml
  - experiment/tests/test_backend.py
  - experiment/tests/test_permission.py
  - scripts/smoke_backend.py
  - artifacts/r4/backend_smoke.json
  - artifacts/r4/R4_DECISION.md
  - docs/archive/v28/experiment/configs/permission.yaml
decision: pilot_only
host: local single-process disposable fixtures
validation:
  - python3 -m unittest experiment.tests.test_backend experiment.tests.test_permission: exit 0, 8 tests
  - python3 -m unittest discover -s experiment/tests -p 'test_*.py': exit 0, 50 tests
  - python3 scripts/smoke_backend.py --output artifacts/r4/backend_smoke.json: exit 0, PASS
  - backend smoke: 4 operation attempts, 4 audit events, test exit 0, expected diff present
  - python3 scripts/freeze_d0.py --check: exit 0, historical v28 digests preserved
  - python3 scripts/check_repository.py: exit 0
open_risks:
  - formal R2 and R3 have not passed
  - host process isolation does not enforce network denial at the OS level
  - timeout handling is not a hardened descendant-process sandbox
  - results are development evidence only
provenance:
  - source commit before working-tree changes: 5b7b707eabb53f5746e9cc5437e7aca0ae0cca53
  - operations schema sha256: c2a24c3d794c7dfda45d0defe179b89037490fb7fe07de30355ca48b9fb30d50
  - permission policy sha256: ce8945300f3f7f09b9470dae19b842c9f29448518064de3947bf75d5def07c06
  - one execute(request, context) path is shared by all operations and contains no interface branch
  - audit log is outside the repository fixture and text payloads are represented by hash and byte count
next_stage: remain in local R4 pilot; formal R5 is blocked on formal R2-R4 passes
```

This pilot establishes the shared authority boundary needed by both future
adapters. It is not a hardened sandbox and does not establish a formal R4 pass.
