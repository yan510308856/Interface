# R3 decision

```text
status: incomplete
artifact:
  - experiment/configs/attack_carrier.txt
  - experiment/configs/attack_manifest.yaml
  - experiment/pair_builder.py
  - experiment/oracles.py
  - experiment/tests/test_pair_builder.py
  - experiment/tests/test_oracles.py
  - scripts/validate_pair.py
  - artifacts/r3/pair_diff.json
  - artifacts/r3/oracle_fixture_report.json
  - artifacts/r3/R3_DECISION.md
  - docs/archive/v28/experiment/configs/attack_carrier.txt
  - docs/archive/v28/experiment/configs/attack_manifest.yaml
decision: pilot_only
host: arm64 Mac using linux/amd64 Docker emulation; no native x86_64 replay
validation:
  - python3 -m unittest experiment.tests.test_pair_builder experiment.tests.test_oracles: exit 0, 12 tests
  - python3 -m unittest discover -s experiment/tests -p 'test_*.py': exit 0, 42 tests
  - python3 scripts/check_repository.py: exit 0
  - python3 scripts/freeze_d0.py --check: exit 0, historical v28 digests preserved
  - Clean/reference r3-pilot-clean-01: exit 0, 15 passed
  - Adversarial/reference r3-pilot-adversarial-01: exit 0, 15 passed
  - pair diff: PASS; only carrier and episode canary were added
  - security oracle negative/positive fixtures: PASS
open_risks:
  - formal R2 has not passed
  - no native x86_64 Docker replay
  - paired-task equivalence was not independently repeated
  - pair diff covers the constructed overlay, not a full post-construction /testbed tree capture
  - results are development evidence only
provenance:
  - source commit before working-tree changes: 114039107c66a784e0178cdce59d4da82fc49f0e
  - Docker 29.6.1; arm64 server; fixed linux/amd64 task image digest 7485c1e3c8861efd0c6a4a78b952857592e541031039000d25e9481f045dc4a3
  - task manifest sha256: 1d2ca427e79a464fb7e435cfc5c0de18a0ff2a0156335347049568667edec056
  - attack carrier template sha256: ba3c0598e4f6081188c35f1affb795de098601e3e3f8d231a171abe73dedac88
  - attack manifest sha256: 9a60dcb64392a86e405c48427ec50e51c6a5da6f67fa80eba8a47e942a0242ca
  - pilot scope is an ephemeral overlay plus direct frozen pytest smoke, not a full official-harness replay
  - ordinary tracked reports contain canary hashes only; plaintext remained in disposable workspaces
next_stage: remain in local R3 pilot; formal R4 is blocked on formal R2 and R3 passes
```

The local pilot demonstrates that the pair builder, file-diff allowlist,
functional smoke, and all six security-oracle fields work together. It does not
establish a formal R3 pass. Clean and Adversarial were each run once, and the
positive security fixture was produced by the test harness rather than by granting
extra authority to a real agent.
