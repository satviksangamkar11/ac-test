"""Measure the frozen 2c0h3z41K58 events through the real ProducerBrain and report B1 vs legacy separately.

Inputs are the ALREADY CAPTURED artifacts (stage_a_observation.json, transcript.json, cached frames); nothing is
re-acquired from the tutorial. Every semantic changed control of every event is run individually (the earlier
coverage table only ran the first control of each event), and resolution_mode says which brain produced it.

    python -m serum2.producer.measure_b1_baseline [out_dir]
"""
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
RUN = ROOT / "serum2" / "data" / "runs" / "2c0h3z41K58"
METADATA = ("global.", "voicing.", "env.selected", "lfo1.selected", "modsrc.", "host.", "overlay.", "tooltip.")


def _events():
    spec = importlib.util.spec_from_file_location("run_timeline_2c0", RUN / "run_timeline.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build()[1]


def _terminal(r):
    if r.refusal:
        return r.refusal["code"]
    return "EXECUTABLE" if r.admitted else (r.execution_status or "NOT_ADMITTED")


def measure():
    from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
    brain = ProducerBrain()
    rows = []
    for i, e in enumerate(_events(), 1):
        d = e.snapshot_diff
        controls = [c for c in d.get("changed_controls", []) if not c["control_id"].startswith(METADATA)]
        if not controls:
            rows.append({"event": i, "control": None, "terminal": "NO_SEMANTIC_INTENT", "resolution_mode": None})
        for c in controls:
            r = brain.execute(ProducerRequest(user_intent="set %s to %s" % (c["control_id"], c["after"]),
                                              mode="EXECUTE", visual_mode="NEVER"))
            b1 = r.b1_intent or {}
            rows.append({"event": i, "time": "%.0f-%.0f" % (e.start_timestamp_sec, e.end_timestamp_sec),
                         "control": c["control_id"], "before": c["before"], "after": c["after"],
                         "resolution_mode": r.resolution_mode, "terminal": _terminal(r),
                         "layer": (r.refusal or {}).get("layer"),
                         "canonical_target": b1.get("canonical_target"), "capability_key": b1.get("capability_key"),
                         "provenance": (b1.get("representation") or {}).get("provenance"),
                         "operation": (b1.get("operation") or {}).get("operation"),
                         "concept": r.resolved_concept})
    return rows


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "docs" / "b1_measurement"
    out.mkdir(parents=True, exist_ok=True)
    rows = measure()
    (out / "B1_BASELINE_AFTER.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    print("controls measured:", len([r for r in rows if r["control"]]))
    print("by terminal     :", dict(Counter(r["terminal"] for r in rows)))
    print("by brain        :", dict(Counter(r["resolution_mode"] for r in rows if r["control"])))
    for r in rows:
        print("%2d %-7s %-26s %-16s %-30s %-24s %s" % (r["event"], r.get("time", ""), r["control"], r["resolution_mode"],
              r["terminal"], r.get("provenance"), r.get("capability_key")))
