# R5 decision

```text
status: incomplete
artifact:
  - experiment/interfaces/__init__.py
  - experiment/interfaces/atomic.py
  - experiment/interfaces/restricted_python.py
  - experiment/interface_equivalence.py
  - experiment/tests/test_atomic.py
  - experiment/tests/test_restricted_python.py
  - experiment/tests/test_interface_equivalence.py
  - scripts/validate_interfaces.py
  - artifacts/r5/equivalence_report.json
  - artifacts/r5/atomic_trajectory.jsonl
  - artifacts/r5/python_trajectory.jsonl
  - artifacts/r5/R5_DECISION.md
decision: pilot_only
host: local single-process disposable fixtures
code_commit: b958cc9785511460541c2bccde49e15e4518e10c (dirty during development)
environment: Python 3.9.6; standard library only; shared R4 schema and policy
validation:
  - python3 -m unittest experiment.tests.test_atomic experiment.tests.test_restricted_python experiment.tests.test_interface_equivalence: exit 0, 12 tests
  - python3 scripts/validate_interfaces.py --output artifacts/r5: exit 0, PASS
  - PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s experiment/tests -p 'test_*.py': exit 0, 62 tests
  - python3 scripts/check_repository.py: exit 0
  - python3 scripts/freeze_d0.py --check: exit 0, 9 historical artifacts preserved
  - Python compile check with PYTHONPYCACHEPREFIX=/tmp/r5-pycache: exit 0
  - git diff --check and trailing-whitespace scan: exit 0
  - scripted comparison: 6 operation attempts per interface; normalized facts, errors, tree hash, and diff digest equal
  - each interface: 1 controlled invalid output, 1 permission denial, and 1 timeout
  - Restricted Python open/import os/subprocess bypass checks: rejected with 0 backend events
cloud_sync:
  github: not committed or pushed; pending user review
  google_drive: not-applicable
open_risks:
  - formal R2, R3, and R4 have not passed, so formal R5 remains blocked
  - the AST interpreter has only the protocol-required minimal bypass tests, not broad sandbox fuzzing
  - the R4 host process boundary still lacks OS-level network isolation and hardened descendant cleanup
  - results are development evidence only
provenance:
  - branch: codex/r5-interface-pilot
  - source commit before working-tree changes: b958cc9785511460541c2bccde49e15e4518e10c
  - operations schema sha256: c2a24c3d794c7dfda45d0defe179b89037490fb7fe07de30355ca48b9fb30d50
  - permission policy sha256: ce8945300f3f7f09b9470dae19b842c9f29448518064de3947bf75d5def07c06
  - agent-security-empirical-study SKILL.md sha256: f979f105f84f3cd69367d5672640b7bc4f512d434838efdbef4439435b4c51b1
  - Atomic adapter sha256: 1445075ef2a97c1ce456bcec2fa1d4c85f598986475adc064b98fc1eb5a17f14
  - Restricted Python adapter sha256: da79fc596f42536db58b7f9c474c89d37263b7d9437155fcffbf548dc1988587
  - equivalence report sha256: 76173d23f92fafa4ef72717d056dfb4f6d9bed37f5c5cba45d53df362b1f8731
  - Atomic trajectory sha256: 1b230da73c1f58d1a6ca18e8402f3c93562a88187412325fc68389802c4b48a6
  - Restricted Python trajectory sha256: ab9a187f5c64c757132881fa49a33ad4f2ba5a8dff4d3f2f6d6c0cb01c5d3128
  - no model invocation, network access, real credential, or external attack target was used
next_stage: remain in local R5 pilot; formal R6 is blocked on formal R2-R5 passes
```

The local report passes every scripted R5 comparison, but it is explicitly not
a formal stage pass. The `PASS` inside `equivalence_report.json` describes only
the deterministic development fixture and cannot unlock real-model R6 runs.
