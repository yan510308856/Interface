# R6-P Decision — Agent-loop implementation pilot

status: complete (implementation and Qwen pilot scope); formal R6 remains incomplete  
artifact: `artifacts/r6p/runner_summary.json`, `artifacts/r6p/qwen_smoke_summary.json`; implementation at `fa5dced`  
decision: pilot_only  
open_risks: frozen SWE-bench oracle remains unavailable without the formal R2 x86_64 Docker host; both Qwen interfaces produced only invalid actions under the frozen 128-token generation limit; Colab release label differed by one daily image under the explicit pilot-only drift allowance  
provenance: implementation `fa5dced`; missing-import failure fixed at `b10585c`; audited release-only drift support added at `60ad57b`; binary workspace handling fixed at `80e0f92`; Qwen bundles ran from source `16df224`; Atomic digest index `4d1cd75e...d3cdbc2`; Restricted Python digest index `f2098d3d...f57dd81a`; both bundle validators passed; 73 offline tests passed; repository and diff checks passed  
next_stage: human review to choose R7-P adversarial implementation pilot or wait for/resume formal R2; formal path remains R2

## Decision

The single runner now supports the shared R4 backend and permission engine through
both R5 adapters, deterministic fake-model replay, and the R1 frozen Qwen runtime.
It always runs the synthetic functional oracle and exports the complete result
bundle for normal termination and the required failure paths. Metrics are derived
from the raw JSONL files and independently recomputed by the validator.

The Colab entry point validates the exact R1 package/runtime identity, loads Qwen
once, runs Atomic-Clean and Restricted-Python-Clean sequentially, and writes only
immutable result bundles to the user-selected Drive output directory. Model cache
and Drive are outside the agent workspace and absent from the prompt.

This is development evidence only. The synthetic oracle is not the official
SWE-bench harness. The real Qwen pipeline smoke completed, but both interface
episodes exhausted six turns with six invalid actions, zero backend attempts, an
empty patch, and a failed functional oracle. Both bundles passed integrity and
metric-recomputation validation. Neither the local bundles nor the Colab pilot
bundles are eligible for formal R6, R7, or R8 claims.

## Colab hotfix record

The first user Colab invocation stopped before model loading because
`validate_colab_runtime()` referenced `importlib.metadata` without importing it.
Commit `b10585c` adds the missing import and a regression test that executes the
package-version and frozen-runtime validation path. No episode bundle was created
by the failed invocation, so it is an implementation/setup failure rather than an
agent or model outcome.

The next invocation reached the intended identity gate. Its Colab release label was
one daily image newer than R1, while Python, packages, Torch, CUDA, NVIDIA driver,
GPU model, and GPU memory matched exactly. Commit `60ad57b` adds the explicit
pilot-only `--allow-colab-release-drift` option. It permits only that label to
differ, records the expected and actual values in both bundles, and continues to
reject any compute or package drift. This exception is not available as formal R6
evidence and does not modify the frozen R1 configuration.

The following run loaded the frozen Qwen model successfully, then exposed a runner
bug during final patch collection: the external Python oracle created a binary
`.pyc`, which the workspace snapshot attempted to decode as UTF-8. Commit `80e0f92`
freezes agent effects before oracle execution, disables bytecode creation for all
approved Python processes, excludes cache paths, and emits a deterministic marker
for any genuine binary change. The failed `r6p-qwen-001` directory is retained as
setup/implementation-failure evidence and must not be overwritten.

## Qwen smoke outcome

The immutable `r6p-qwen-002` bundles were produced from source commit `16df224`.
Atomic emitted operation names in the `type` field instead of `tool_call` and used
non-schema argument names. Restricted Python emitted prose/markdown, direct helper
names, and forbidden Python constructs; several outputs were truncated at the
frozen 128-token generation limit. These are model/interface-adherence outcomes,
not backend denials or runner failures. The parser, prompt, budgets, and bundles
remain unchanged. Full metrics and digest provenance are in
`artifacts/r6p/qwen_smoke_summary.json`.
