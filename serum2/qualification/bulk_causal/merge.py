"""Merge causal evidence + GUI observations into one semantic verdict per test (pure; no Serum needed).

    python merge.py <causal_evidence.json> <gui_plan.json> <gui_evidence.json> <registry.json> <out.json>

The verdict never edits the registry/binding table: it only says how far up the evidence hierarchy a candidate got.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from classify import semantic_classify  # noqa: E402


def main(causal, plan, gui, registry, out):
    recs = {r["id"]: r for r in json.load(open(causal))["records"]}
    tests = {p["n"]: p["test"] for p in json.load(open(plan))["presets"]}
    reg = json.load(open(registry))["canonical_registry"]
    by_test = {}
    for o in json.load(open(gui))["observations"]:
        by_test.setdefault(tests[o["n"]], []).append(o)
    res = {}
    for tid, obs in by_test.items():
        c = recs[tid]
        labels = reg[c["atlas_id"]]["enum_values"]
        res[tid] = {"atlas_id": c["atlas_id"], "candidate": c["candidate"], "causal_status": c["status"],
                    "atlas_labels": labels, **semantic_classify(c, obs, labels)}
    json.dump({"sources": {"causal": causal, "gui": gui}, "tests": res}, open(out, "w"), indent=1)
    for t, v in res.items():
        print("%-34s %-26s %s" % (t, v["status"], v["raw_to_label"]))


if __name__ == "__main__":
    main(*sys.argv[1:6])
