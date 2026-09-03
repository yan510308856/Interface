# Repository Guide

## Goal

Keep this repository minimal and directly focused on one experiment: whether Atomic and Restricted Python action interfaces differ in utility, security, operation behavior, token cost, and runtime under clean and attack conditions.

## Invariant

Hold model, task, backend, permission policy, sandbox, and budget fixed. Only interface and clean/attack condition may vary.

```text
Atomic ------------------\
                          > Shared Backend -> Permission -> Repository
Restricted Python -------/
```

## Rules

- Both interfaces must call the same `Backend` implementation.
- Atomic maps one non-finish model action to exactly one backend operation.
- Restricted Python may compose zero or more calls to that backend using its restricted AST interpreter.
- Interfaces must not implement filesystem, process, Git, or permission behavior.
- Keep repository-boundary checks, `.git` write denial, process allowlisting, and direct-Python-API restrictions.
- Use only synthetic attacks in disposable workspaces. Never use real credentials, production targets, third parties, or uncontrolled agents.
- Do not add development gates, freeze machinery, hashes, attestations, provenance chains, capability-equivalence systems, or manifest-verification systems.
- Generated runs and benchmark outputs belong under `runs/` and must not be committed.
- Prefer standard-library Python and direct code over configuration languages or abstraction layers.
- Add an abstraction only when it removes duplication from the actual four-cell experiment.
- Keep tests focused on backend behavior, permissions, interface semantics, attack injection, and runner output.
- Use the official SWE-bench harness for functional grading; do not reimplement it.
- Keep `python scripts/run_experiment.py` as the single experiment entry point.

Before changing code, read the affected execution path. After changing code, run `python -m unittest discover -s tests -v` and report any environment-dependent limitation plainly.
