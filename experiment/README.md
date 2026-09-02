# Experiment implementation

This directory is being migrated stage by stage to the R0–R8 protocol in
[`docs/aug29experiment.md`](../docs/aug29experiment.md). R0 and R1 are formally
complete; formal R2 remains unpassed. The selected development route is the
separate Implementation Pilot track.

Current implementation stage: **R6-P — Qwen interface calibration follow-up**. The
R6-P runner pilot is complete, but its first real-Qwen episodes reached a floor
effect: both interfaces produced only invalid actions and failed the synthetic
Clean oracle. This follow-up calibrates interface instructions on development-only
material; formal R2 and formal R5 remain unpassed.
R1 passed with a frozen ModelScope revision and runtime after two independent A100
workers completed all three fixed prompts and the 16K context probe. The private
raw bundle remains on Google Drive; the tracked decision and digests are in
[`artifacts/r1/R1_DECISION.md`](../artifacts/r1/R1_DECISION.md).

R2 has frozen the candidate order and implemented the official-harness wrapper.
The local Mac path runs one `linux/amd64`-emulated baseline and reference as
development evidence only. The stage remains incomplete with decision
`pilot_only`; these attempts cannot satisfy the formal repetition gate. See
[`artifacts/r2/R2_DECISION.md`](../artifacts/r2/R2_DECISION.md).

R3 paired-task code may be exercised locally as a pilot while the formal stage
remains blocked. The builder adds only the frozen carrier and episode canary to
the Adversarial overlay; the functional and security oracle outputs are marked
`development_evidence_only`. See
[`artifacts/r3/R3_DECISION.md`](../artifacts/r3/R3_DECISION.md).

R4 adds one canonical backend entry point, one default-deny permission engine,
and an append-only audit logger for tiny disposable fixtures. Its local smoke is
development evidence, not a hardened sandbox or formal stage pass. See
[`artifacts/r4/R4_DECISION.md`](../artifacts/r4/R4_DECISION.md).

R5 adds two representation-only adapters over that same backend. Atomic accepts
one strict JSON action and forwards one valid tool call; Restricted Python uses a
small AST interpreter with no `eval` or `exec`, and exposes only `repo` and
`runner` capability calls. Scripted equivalence, controlled failures, and the
three required bypass checks complete the selected R5 pilot scope. They remain
development evidence only. See
[`artifacts/r5/R5_DECISION.md`](../artifacts/r5/R5_DECISION.md).

R6-P added the single episode runner, result-bundle schema, metrics derivation,
fake-model fixtures, controlled failure paths, and an optional Colab A100 Qwen
smoke. The calibration keeps the strict Atomic JSON and Restricted Python parsers,
the shared backend, task, and equal budgets. The v3 interface scaffold adds one
task-independent action-only demonstration per interface and explicit retry feedback
after invalid syntax. The demonstration uses fictional paths and never includes the
Astropy solution, reference patch, hidden tests, or paired attack payload. It also
uses an equal 512-token per-action generation limit for both interfaces; the R1 model
identity and runtime freeze remain unchanged. Both adapters apply the same
format-only rule: one code fence wrapping the entire JSON/program may be removed,
while prose outside the fence or multiple fences remain invalid. Raw model output
is still preserved unchanged in `actions.jsonl`; the retry scaffold does not repair
or execute invalid output. Every output must still declare `development_evidence_only`
and `formal_r6_eligible: false`. It cannot be included in a formal four-cell result.
Both interfaces also use the same recorded early-stop rule: three consecutive
invalid actions terminate the cell as `invalid_action_streak_exhausted`. A valid
action resets the streak, and early termination still exports the complete bundle
and runs the configured oracles.
The v3 scaffold additionally tells Restricted Python to begin investigation with a
short direct capability program and lists its actual AST subset. Both interfaces use
the same deterministic three-action history window while `messages.jsonl` preserves
the complete trajectory; this prevents accumulated observations from exceeding the
frozen 16K model context. Model errors record both exception type and message.

Snapshot SHA-256 verification is persisted beside the immutable ModelScope snapshot.
Later processes reuse it when the revision and every hashed file's path, size, and
modification time are unchanged. Set `R1_FORCE_SNAPSHOT_REHASH=1` only when an
explicit full re-verification is required. GPU model loading still occurs once per
Python process because GPU memory cannot survive a Colab/runtime restart.

For paired Astropy runs, the source checkout may live on Drive. The runner skips
the expensive source-worktree `git status` scan and instead clones the frozen commit
into local scratch, then validates that local destination. Dirty files in the source
checkout are therefore excluded from the episode.

Run both calibrated Clean episodes in one Colab process so the frozen Qwen is loaded
only once:

```bash
python3 scripts/run_r6p_colab.py \
  --model-cache /content/drive/MyDrive/Interface-R1/modelscope-cache \
  --output-root /content/drive/MyDrive/Agents_Research/runs/r6p-qwen-smoke \
  --run-id r6p-qwen-003 \
  --allow-colab-release-drift
```

After both interfaces pass the synthetic fixture, the next development-only step is
the frozen SWE-bench Verified instance `astropy__astropy-12907`. The Colab runner
clones only the public Astropy base commit and never copies the tracked reference or
test patch into the agent workspace. It records the functional oracle as `DEFERRED`
and exports one standard SWE-bench prediction per interface:

```bash
python3 scripts/run_r6p_astropy_colab.py \
  --workspace /content/drive/MyDrive/Agents_Research/workspaces/astropy-12907-base \
  --model-cache /content/drive/MyDrive/Interface-R1/modelscope-cache \
  --output-root /content/drive/MyDrive/Agents_Research/runs/r6p-astropy-clean \
  --run-id r6p-astropy-001 \
  --allow-colab-release-drift
```

The exported predictions must be graded later on a native x86_64 Docker host with
the pinned harness and image. This evaluation materializes the official dataset row
outside the agent workspace:

```bash
python3 scripts/evaluate_swebench_prediction.py \
  --prediction <r6p-astropy-001-atomic.prediction.json> \
  --run-id r6p-astropy-001-atomic-eval \
  --output-dir <official-evaluation-output>
```

Until the formal R2 gate passes, even a successful official harness run remains
development evidence and cannot enter the formal four-cell result.

The paired Astropy follow-up should first use a new run ID so the failed attempts
remain immutable. Run the synthetic two-interface calibration first. Only if both
interfaces perform backend operations should the four paired cells be run:

```bash
python3 scripts/run_r6p_colab.py \
  --model-cache /content/drive/MyDrive/Interface-R1/modelscope-cache \
  --output-root /content/drive/MyDrive/Agents_Research/runs/r6p-qwen-smoke \
  --run-id r6p-qwen-005 \
  --allow-colab-release-drift

python3 scripts/run_r6p_astropy_paired_colab.py \
  --workspace /content/drive/MyDrive/Agents_Research/workspaces/astropy-12907-base \
  --model-cache /content/drive/MyDrive/Interface-R1/modelscope-cache \
  --output-root /content/drive/MyDrive/Agents_Research/runs/r6p-astropy-paired \
  --run-id r6p-astropy-paired-003 \
  --allow-colab-release-drift
```

The files still carrying D0 names or v28 semantics are preserved as historical
evidence until their assigned R-stage replacements exist. Their exact disposition
is recorded in
[`artifacts/r0/migration_inventory.json`](../artifacts/r0/migration_inventory.json);
they are not active v29 configuration and do not establish an R-stage pass.

Do not update a legacy file opportunistically. Follow its target stage in the R0
inventory, preserve the v28 evidence, and remove replacement-only utilities after
their v29 equivalents pass.
