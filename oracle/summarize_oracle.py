#!/usr/bin/env python3
"""Normalize official SWE-bench reports and optionally join formal analysis."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def _json_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(path.rglob("*.json"))


def _normalize(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for report in _json_files(path):
        try:
            value = json.loads(report.read_text(encoding="utf-8"))
        except ValueError:
            value = []
            for line in report.read_text(encoding="utf-8").splitlines():
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if isinstance(item, dict):
                    value.append(item)
        if isinstance(value, list):
            rows.extend(item for item in value if isinstance(item, dict))
            continue
        if not isinstance(value, dict):
            continue
        if isinstance(value.get("results"), list):
            rows.extend(item for item in value["results"] if isinstance(item, dict))
            continue
        resolved_ids = set(value.get("resolved_ids", []))
        unresolved_ids = set(value.get("unresolved_ids", []))
        if resolved_ids or unresolved_ids:
            for instance_id in sorted(resolved_ids | unresolved_ids):
                rows.append({
                    "instance_id": instance_id,
                    "resolved": instance_id in resolved_ids,
                    "evaluator_status": "resolved" if instance_id in resolved_ids else "unresolved",
                    "source_report": str(report),
                })
            continue
        if "instance_id" in value and ("resolved" in value or "status" in value):
            row = dict(value)
            if "resolved" not in row:
                row["resolved"] = row.get("status") == "resolved"
            rows.append(row)
    return rows


def summarize(results_path: Path) -> list[dict[str, Any]]:
    rows = _normalize(results_path)
    output = []
    for row in rows:
        output.append({
            "run_id": row.get("run_id"),
            "instance_id": row.get("instance_id"),
            "resolved": row.get("resolved"),
            "evaluator_status": row.get("evaluator_status", "resolved" if row.get("resolved") else "unresolved"),
            "source_report": row.get("source_report"),
        })
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", type=Path, help="Official harness JSON/JSONL report or directory.")
    parser.add_argument("--experiment-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--run-id", help="Formal run ID represented by this single official report.")
    args = parser.parse_args()
    rows = summarize(args.results)
    if args.run_id:
        for row in rows:
            row["run_id"] = args.run_id
    output = args.output or ((args.experiment_root / "oracle") if args.experiment_root else Path("oracle-summary"))
    output.mkdir(parents=True, exist_ok=True)
    (output / "oracle_results.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8",
    )
    summary = {
        "rows": len(rows),
        "resolved": sum(row.get("resolved") is True for row in rows),
        "unresolved": sum(row.get("resolved") is False for row in rows),
    }
    (output / "oracle_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with (output / "oracle_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary))
        writer.writeheader()
        writer.writerow(summary)
    if args.experiment_root:
        long_path = args.experiment_root / "summaries" / "formal_analysis_long.csv"
        combined_path = output / "rollout_oracle_combined.csv"
        oracle_by_run = {row.get("run_id"): row for row in rows if row.get("run_id")}
        if long_path.is_file():
            with long_path.open(newline="", encoding="utf-8") as handle:
                combined = list(csv.DictReader(handle))
            for row in combined:
                oracle = oracle_by_run.get(row.get("run_id"), {})
                row["resolved"] = oracle.get("resolved")
                row["evaluator_status"] = oracle.get("evaluator_status")
            if combined:
                with combined_path.open("w", newline="", encoding="utf-8") as handle:
                    writer = csv.DictWriter(handle, fieldnames=list(combined[0]))
                    writer.writeheader()
                    writer.writerows(combined)
    print(json.dumps({"output": str(output), **summary}, indent=2))


if __name__ == "__main__":
    main()
