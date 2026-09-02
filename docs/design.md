# Experiment Design

## Research Question

With model, task, backend capabilities, permission policy, sandbox, and budget held constant, do Atomic and Restricted Python action interfaces change task utility, security risk, operation behavior, token cost, or runtime?

## Experimental Variables

The two factors are interface (`atomic`, `restricted_python`) and environment (`clean`, `attack`). Every other setting comes from one experiment configuration and one permission policy.

## Atomic Definition

One model action is either `finish` or one JSON tool call. A valid non-finish action invokes the shared backend exactly once.

## Restricted Python Definition

One model action is an AST-parsed program. It supports local variables, `if`, bounded `for range(...)`, basic expressions, and zero or more shared-backend capability calls. Imports, direct filesystem/process/network APIs, `eval`, `exec`, and host objects are unavailable.

## Shared Backend

Both interfaces call the same `Backend.execute()` implementation for file reads, text search and edits, file creation/deletion, approved processes, and Git diff. The interfaces contain no filesystem, process, Git, or permission implementation.

## Permission Policy

The backend checks one shared policy before every operation. Paths must remain in the repository, writes to `.git` are denied, and process commands must match an allowlisted prefix.

## Clean Condition

The task repository is prepared without experimental additions.

## Attack Condition

The same repository receives one synthetic prompt-injection carrier. Its prohibited target is a file under `.git`; the carrier contains no real secret and runs only in a disposable task workspace.

## Metrics

Each run reports task success from the official SWE-bench harness, unsafe and blocked attempts from permission denials, attack success from the prohibited target effect, action and backend-operation counts, input/output tokens, runtime, final patch, and a JSONL trajectory.

## Experiment Matrix

| Interface | Clean | Attack |
|---|---:|---:|
| Atomic | ✓ | ✓ |
| Restricted Python | ✓ | ✓ |

## Execution Flow

`Task -> fresh repository -> optional attack -> selected interface -> shared Backend -> shared Permission -> trajectory -> SWE-bench evaluation`

