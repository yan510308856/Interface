#!/usr/bin/env python3
"""Run from multi_tool_pilot/. No dependency on the old experiment package."""
import argparse
import csv
import itertools
import json
import random
import sys
import time
import uuid
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tasks import make_tasks
from runner import dump, judge, run_episode


def read_lines(path):
    if not path.exists():
        return []
    lines = path.read_bytes().splitlines(keepends=True)
    rows, offset = [], 0
    for i, line in enumerate(lines):
        try:
            if line.strip():
                rows.append(json.loads(line))
        except ValueError:
            if i != len(lines)-1 or line.endswith(b"\n"):
                raise
            # An interrupted final append is not a completed episode.
            with path.open("r+b") as handle:
                handle.truncate(offset)
            print(f"Removed interrupted final JSONL fragment: {path}", file=sys.stderr)
            return rows
        offset += len(line)
    if lines and not lines[-1].endswith(b"\n"):
        with path.open("ab") as handle:
            handle.write(b"\n")
    return rows


def append(path, value):
    with path.open("a") as handle:
        handle.write(dump(value) + "\n")
        handle.flush()


def write_csv(path, rows):
    if not rows:
        print("No rows to summarize")
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(path)


def summarize(root):
    groups = defaultdict(list)
    for row in read_lines(root / "results.jsonl"):
        groups[(row["mode"], row["guard"], row["condition"])].append(row)
    output = []
    for (mode, guard, condition), rows in sorted(groups.items()):
        entry = dict(mode=mode, guard=guard, condition=condition, n=len(rows),
                     finished=sum(r["status"] == "finished" for r in rows),
                     status_counts=dump({s:sum(r["status"] == s for r in rows)
                                         for s in sorted({r["status"] for r in rows})}))
        for metric in ("TSR", "UER", "ASR", "SCR", "unauthorized_effects", "affected_resources",
                       "tool_calls", "proposed_calls", "actor_requests", "seconds",
                       "max_unauthorized_before_actor_observation"):
            entry[metric] = sum(r[metric] for r in rows)/len(rows)
        for role in ("actor", "guard"):
            for metric in ("input_tokens", "output_tokens", "seconds"):
                entry[f"{role}_{metric}"] = sum(r["cost"][role][metric] for r in rows)/len(rows)
        output.append(entry)
    write_csv(root / "summary.csv", output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "run", "summarize", "audit", "smoke", "inspect-model"])
    parser.add_argument("--output", type=Path, default=Path("runs/dev"))
    parser.add_argument("--split", choices=["dev", "eval"], default="dev")
    parser.add_argument("--modes", nargs="+", choices=list("SPD"), default=list("SPD"))
    parser.add_argument("--guards", nargs="+", choices=["G0", "G1", "G2"], default=["G0", "G1", "G2"])
    parser.add_argument("--conditions", nargs="+", choices=["clean", "attack"], default=["clean", "attack"])
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int, help="Run at most this many pending episodes this invocation")
    parser.add_argument("--model", default="Qwen/Qwen3-8B")
    parser.add_argument("--revision", help="Optional HF revision; resolved revision is logged")
    parser.add_argument("--quantization", choices=["none", "4bit"], default="none")
    parser.add_argument("--context-limit", type=int, default=16384)
    parser.add_argument("--timeout-seconds", type=int, default=900)
    args = parser.parse_args()
    if args.repeats < 1 or (args.limit is not None and args.limit < 1):
        parser.error("repeats and limit must be positive")
    if args.context_limit < 4096 or args.timeout_seconds < 1:
        parser.error("context-limit must be >=4096; timeout-seconds must be positive")
    if args.command == "inspect-model":
        from inference import inspect_local_model
        print(dump(inspect_local_model(args.model)))
        return
    if args.command == "smoke":
        from smoke import smoke
        smoke()
        return
    if args.command == "summarize":
        summarize(args.output)
        return
    tasks = [t for t in make_tasks() if t["split"] == args.split]
    matrix = []
    # Keep task/repetition blocks together; randomize cells within each block.
    rng = random.Random(args.seed)
    for task in tasks:
        for repeat in range(args.repeats):
            cells = list(itertools.product(sorted(set(args.modes)), sorted(set(args.guards)), sorted(set(args.conditions))))
            rng.shuffle(cells)
            matrix.extend((task, mode, guard, condition, args.seed + repeat)
                          for mode, guard, condition in cells)
    if args.command == "plan":
        print(dump(dict(tasks=[t["id"] for t in tasks], episodes=len(matrix),
                        cells_per_task=len(matrix)//len(tasks), model=args.model,
                        max_episode_seconds=args.timeout_seconds, quantization=args.quantization, synthetic=True)))
        return
    from inference import HFModel
    if args.command == "audit":
        config = json.loads((args.output / "config.json").read_text())
        model = HFModel(config["model"], config["runtime"]["revision"], config["quantization"], config["context_limit"])
        path = args.output / "audit.jsonl"
        done = {(r["episode"], r["proposal_index"], r["view"]) for r in read_lines(path)}
        for row in read_lines(args.output / "results.jsonl"):
            if row["guard"] != "G0":
                continue
            proposals = [e for e in read_lines(args.output / row["trace"]) if e["type"] == "proposal"]
            for i, event in enumerate(proposals):
                for view in ("G1", "G2"):
                    if (row["episode"], i, view) in done:
                        continue
                    verdict, log = judge(model, event["task_request"], event["history"],
                                         event["current"], event["events"], view)
                    append(path, dict(episode=row["episode"], task=row["task"], mode=row["mode"],
                                      condition=row["condition"], proposal_index=i, view=view,
                                      authorized=event["authorized"], **log))
                    print(f"audit {row['episode']} proposal={i} {view}: {verdict}", flush=True)
        groups = defaultdict(list)
        for row in read_lines(path):
            groups[(row["mode"], row["condition"], row["view"])].append(row)
        output = []
        for (mode, condition, view), rows in sorted(groups.items()):
            legal = [r for r in rows if r["authorized"]]
            illegal = [r for r in rows if not r["authorized"]]
            output.append(dict(mode=mode, condition=condition, view=view, n=len(rows),
                legal_n=len(legal), illegal_n=len(illegal),
                false_allow_rate=sum(r["verdict"] == "allow" for r in illegal)/len(illegal) if illegal else "NA",
                legal_block_rate=sum(r["verdict"] != "allow" for r in legal)/len(legal) if legal else "NA",
                error_n=sum(r["verdict"] == "error" for r in rows)))
        write_csv(args.output / "audit_summary.csv", output)
        return

    config = dict(version=2, model=args.model, revision=args.revision, split=args.split,
                  modes=sorted(set(args.modes)), guards=sorted(set(args.guards)),
                  conditions=sorted(set(args.conditions)), repeats=args.repeats, seed=args.seed,
                  tasks=tasks, synthetic=True, actor_max_tokens=2048, guard_max_tokens=256,
                  context_limit=args.context_limit, tool_budget=24, proposal_budget=32,
                  actor_request_budget=32, actor_output_budget=8192, timeout_seconds=args.timeout_seconds,
                  quantization=args.quantization,
                  temperature=0.7, top_p=0.8, top_k=20)
    args.output.mkdir(parents=True, exist_ok=True)
    config_path = args.output / "config.json"
    previous = json.loads(config_path.read_text()) if config_path.exists() else None
    if previous and {k:v for k,v in previous.items() if k != "runtime"} != config:
        raise SystemExit("Output directory has a different configuration. Use a new --output.")
    results_path = args.output / "results.jsonl"
    done = {r["episode"] for r in read_lines(results_path)}
    pending = [(t,m,g,c,s) for t,m,g,c,s in matrix if f"{t['id']}_{m}_{g}_{c}_{s}" not in done]
    if not pending:
        summarize(args.output)
        return
    revision = previous["runtime"]["revision"] if previous else args.revision
    model = HFModel(args.model, revision, args.quantization, args.context_limit)
    if previous and previous["runtime"].get("local_source") != model.metadata.get("local_source"):
        raise SystemExit("Local model metadata changed. Use a new --output directory.")
    config["runtime"] = model.metadata
    if not previous:
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2))
    for task in tasks:
        if model.count(task["payload"]) > 512:
            raise SystemExit("Attack payload exceeds 512 tokenizer tokens")
    for task, mode, guard, condition, seed in pending[:args.limit]:
        episode = f"{task['id']}_{mode}_{guard}_{condition}_{seed}"
        trace = f"{episode}_{uuid.uuid4().hex[:8]}.jsonl"
        print(f"Starting {episode}", flush=True)
        emit = lambda event: append(args.output / trace, event)
        emit(dict(type="start", episode=episode, unix_time=time.time(), runtime=model.metadata,
                  payload_tokens=model.count(task["payload"])))
        model.torch.cuda.reset_peak_memory_stats()
        result = run_episode(model, task, mode, guard, condition, seed, emit, args.timeout_seconds)
        result.update(episode=episode, trace=trace,
                      peak_gpu_bytes=model.torch.cuda.max_memory_allocated())
        emit(dict(type="result", **result))
        append(results_path, result)
        print(dump({k:result[k] for k in ("episode", "status", "TSR", "UER", "SCR", "seconds")}), flush=True)
    summarize(args.output)


if __name__ == "__main__":
    main()
