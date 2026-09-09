# SWE-bench oracle adapter

This directory extends the validated offline oracle artifact contract under
`harness-v6-1-python-batch-nine-task-clean/`. That historical artifact is the
source of truth for the evaluator semantics: one rollout per invocation of the
official `swebench eval` command, `resolved` read from the instance
`report.json`, and no custom grader.

The tracked Python implementation is intentionally one shared adapter:
`adapter.py`. The three CLI files are thin compatibility entry points around
it. They accept both the new formal root (`PLAN.json` plus `runs/<run-id>/`)
and the old `input/runs/<run-directory>/` artifact. Old `interface=atomic` and
`interface=restricted_python` rows remain legacy treatments; they are never
renamed to G1/G2/G4.

Empty patches are recorded as `not_attempted_empty_patch` with `resolved=null`
and are failures in the agent-level resolution denominator. Missing reports,
Docker/setup failures, harness errors, and host failures are recorded as
`infrastructure_failure` and excluded from that denominator. A finite retry
count is recorded for infrastructure failures; local Docker image preparation
or aliasing remains an explicit environment step, as it was in the validated
historical run.

After downloading a frozen formal rollout, use:

```text
python oracle/prepare_predictions.py --experiment <formal-root>
python oracle/run_official_swebench.py \
  --experiment <formal-root> \
  --task-metadata <verified-task-json> \
  --output <oracle-output-root>
python oracle/summarize_oracle.py \
  --experiment <formal-root> \
  --oracle <oracle-output-root>
```

The second command is the only command that invokes the official evaluator. It
is intentionally not run by repository tests or by this implementation task.
