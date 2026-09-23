"""Small deterministic harness checks, NOT LLM results or attack performance."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from runner import guard_messages, plan_from, resolve, run_episode
from tasks import make_tasks
from tasks import Backend
from inference import inspect_local_model


class ScriptedModel:
    def __init__(self, plans, verdict="allow"):
        self.plans = iter(plans)
        self.verdict = verdict

    def generate(self, messages, **kwargs):
        text = json.dumps(dict(verdict=self.verdict, reason="smoke fixture") if kwargs.get("guard")
                          else next(self.plans, {"finish": "done"}))
        return dict(text=text, input_tokens=0, output_tokens=0, seconds=0.0)


def smoke():
    tasks = make_tasks()
    assert len(tasks) == 12 and sum(t["split"] == "eval" for t in tasks) == 8
    task = next(t for t in tasks if t["id"] == "directory-0")
    lookup = dict(id="a", tool="lookup_record", args={"record_id": "route"})
    write = dict(id="b", tool="write_report", args={"path": task["expected"]["path"],
                                                   "content": " ".join(task["facts"])})
    dependent = dict(id="b", tool="write_report", args={**write["args"], "path": {"$ref": "a.target"}})
    assert resolve(dependent["args"], {"a": {"target": "reports/test.txt"}})["path"] == "reports/test.txt"
    for mode, calls in [("S", [lookup, write]), ("P", [lookup, dependent]), ("P", [write, {**write, "id": "c"}])]:
        try:
            plan_from({"calls": calls}, mode)
        except ValueError:
            pass
        else:
            raise AssertionError("Invalid plan accepted")
    for mode in "SPD":
        plans = [{"calls": [lookup, dependent]}] if mode == "D" else [{"calls": [lookup]}, {"calls": [write]}]
        for guard in ("G0", "G1", "G2"):
            events = []
            result = run_episode(ScriptedModel(plans), task, mode, guard, "clean", 1, events.append)
            assert result["SCR"] == 1 and result["tool_calls"] == 3
            proposals = [e for e in events if e["type"] == "proposal"]
            for e in proposals:
                g1 = guard_messages(e["task_request"], e["history"], e["current"], e["events"], "G1")
                g2 = guard_messages(e["task_request"], e["history"], e["current"], e["events"], "G2")
                if mode == "S" or not e["events"]:
                    assert g1 == g2
            if mode == "D":
                assert proposals[-1]["events"][0]["result"]["target"] == task["expected"]["path"]
    denied = run_episode(ScriptedModel([{"calls": [write]}], "deny"), task, "S", "G1", "clean", 1, lambda e: None)
    assert not denied["effects"]
    bad = dict(id="bad", tool="write_report", args={**write["args"], "path": "reports/unrequested.txt"})
    result = run_episode(ScriptedModel([{"calls": [lookup]}, {"calls": [write, bad]}]), task, "P", "G0", "attack", 1, lambda e: None)
    assert result["TSR"] == result["UER"] == result["ASR"] == 1 and result["SCR"] == 0
    bypass = run_episode(ScriptedModel([{"calls": [write]}]), task, "S", "G0", "clean", 1, lambda e: None)
    assert bypass["TSR"] == 0  # A lucky target guess does not complete the required lookup.
    chain = next(t for t in tasks if t["id"] == "chain-0")
    assert "target" not in chain["records"]["route"]
    parallel = next(t for t in tasks if t["id"] == "parallel-0")
    assert all(f not in parallel["notes"]["brief"] for f in parallel["facts"])
    reads = [{"id": n, "tool": "read_note", "args": {"note_id": n}} for n in ("detail", "extra")]
    delivery = dict(id="send", tool="send_message", args={"recipient": parallel["expected"]["recipient"],
                                                           "content": " ".join(parallel["facts"])})
    paired = run_episode(ScriptedModel([{"calls": reads}, {"calls": [delivery]}]), parallel, "P", "G0", "clean", 1, lambda e: None)
    assert paired["SCR"] == 1
    backend = Backend(chain, "clean")
    for status in ("reviewed", "closed"):
        backend.execute(dict(tool="set_status", args={"record_id": "ticket", "status": status}))
    assert backend.metrics()["affected_resources"] == 1
    with TemporaryDirectory() as folder:
        root = Path(folder)
        for name, data in {"config.json": {"model_type": "qwen3_moe"}, "tokenizer_config.json": {},
                           "tokenizer.json": {}, "model.safetensors.index.json": {"weight_map": {"x": "part.safetensors"}}}.items():
            (root/name).write_text(json.dumps(data))
        try:
            inspect_local_model(folder)
        except ValueError:
            pass
        else:
            raise AssertionError("Missing model shard was accepted")
        (root/"part.safetensors").write_bytes(b"fixture-only")
        assert inspect_local_model(folder)["shards"] == 1
    print("PASS: plan validation, reference resolution, S/P/D execution, G1/G2 views, denial, effect oracles.")
    print("PASS: required reads, parallel task opportunity, non-leaking chain, resource counts, local model preflight.")
    print("Scripted fixtures only; no model inference and no research results.")
