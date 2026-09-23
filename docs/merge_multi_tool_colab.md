# Add an independent multi-tool security pilot with Drive-backed Colab inference

The repository now has a separate Proposal A pilot for studying how S/P/D execution changes the effectiveness of the same per-call guard. The new runner shares one simulated tool backend across execution modes and compares no semantic guard, actor-history review, and review with completed runtime events. It does not reuse Restricted Python or legacy G1/G2/G4 capacity treatments.

## Changes

- Add synthetic task fixtures, S/P/D execution, G0/G1/G2 review, effect-based safety/utility metrics, full traces, resumable runs, CSV summaries, and fixed-proposal guard audits.
- Ensure parallel tasks have two unread sources, dependency chains do not reveal the final target early, and task completion requires the specified reads before delivery. Correct affected-resource counting.
- Support local Hugging Face safetensors folders and explicit NF4 loading. The Colab notebook can reuse existing Qwen3-Coder-30B-A3B-Instruct weights on mounted Drive without downloading them again from Hugging Face.
- Add model-folder preflight, explicit context/timeout options, quantization metadata, and recovery of interrupted final JSONL writes.
- Make the root README distinguish the active pilot from archived experiments, preserve existing research documents, and ignore temporary presentation builds, notebook checkpoints, and model artifacts.
- Preserve previously uncommitted legacy calibration changes in a separate commit: explicit capacity prompts, synthetic allowed-target calibration, finish-state attack measurement, target cleanup, and their tests. These are not dependencies of the new pilot.

## Validation

- Existing repository suite: `python -m unittest discover -s tests -v` — 129 tests passed.
- Pilot: `python multi_tool_pilot/scripts/run_experiment.py smoke` — deterministic harness checks passed.
- Verified configuration JSON roundtrip, interrupted JSONL recovery, CSV generation, notebook Python cell parsing, Python compilation, and whitespace checks.
- Drive inspection confirmed the model card/config and 16 safetensors shards. The local-model preflight checks file presence and size, not full tensor integrity.

## Limits

GPU inference has not been run on the development machine. The notebook starts with one real clean episode before any full matrix. Qwen3-Coder-30B-A3B-Instruct/NF4 is a separate model/precision condition from the CLI default Qwen3-8B/BF16. Actual memory use, model JSON compliance, and performance must be validated in Colab.

Tasks are synthetic diagnostics with shared templates, not AgentDojo or a coding-agent benchmark. In-memory tools are too small to establish production latency benefits. No formal statistical or novelty claims are made.
