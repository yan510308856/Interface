# R6-P Decision — Agent-loop implementation pilot

status: complete (pilot scope); formal R6 remains incomplete  
artifact: `artifacts/r6p/runner_summary.json`; implementation at `fa5dced`  
decision: pilot_only  
open_risks: real Qwen Colab pipeline has not yet been run from the pushed commit; frozen SWE-bench oracle remains unavailable without the formal R2 x86_64 Docker host  
provenance: implementation `fa5dced`; missing-import failure fixed at `b10585c`; audited release-only drift support added at `60ad57b`; 72 offline tests passed; repository check and diff check passed; six fresh fake bundles (Atomic Clean, Restricted Python Clean, malformed, model timeout, task failure, empty patch) passed digest and metric recomputation validation  
next_stage: user-run R6-P Qwen Clean pipeline smoke on Colab A100, then review the two Drive bundles; formal path remains R2

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
SWE-bench harness, the real Qwen smoke is pending the user's Colab A100 session,
and neither the local bundles nor the future Colab pilot bundles are eligible for
formal R6, R7, or R8 claims.

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
