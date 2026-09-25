"""Range half of the semantic merge (pure): does the GUI's displayed value agree with what the state readback said Serum stored?

    python merge_range.py <range_evidence.json> <gui_plan.json> <gui_range_evidence.json> <out.json>

Generic checks per test (no per-parameter code):
  R1 clamp-consistency  a probe whose state readback equals a written in-range value must DISPLAY what that value displays
  R2 monotonic          displayed value must not move against the written value (in-range and probes together)
Also reports the default display (the reference preset, i.e. the key absent) and the effective display range.
State readback and the live UI are different observers; where they disagree the UI is what a user sees, and the disagreement is
recorded, never averaged away.
"""
import json
import sys


def close(a, b):
    return a is not None and b is not None and abs(a - b) <= 1e-6 * max(1.0, abs(b))


def analyse(rec, rows):
    """rec: causal range record; rows: [{written, kind, displayed_value}] for the same test."""
    obs = rec["observations"].values() if "observations" in rec else rec["values"]   # legacy per-test record | bulk record
    stored = {o["written"]: o["state_value"] for o in obs if o["written"] is not None}
    ref = next((r for r in rows if r["kind"] == "reference"), None)
    pts = sorted([r for r in rows if r["kind"] != "reference"], key=lambda r: r["written"])
    disp = {r["written"]: r["displayed_value"] for r in pts}
    violations = []
    for r in pts:
        if r["kind"] != "probe":
            continue
        s = stored.get(r["written"])
        match = [q["written"] for q in pts if q["kind"] == "value" and s is not None and close(s, q["written"])]
        if match and disp[match[0]] != r["displayed_value"]:
            violations.append({"rule": "R1", "written": r["written"], "state_readback_stored": s, "gui_shows": r["displayed_value"],
                               "expected_from_value": match[0], "that_value_shows": disp[match[0]]})
    seq = [disp[w] for w in sorted(disp)]
    up, down = all(a <= b for a, b in zip(seq, seq[1:])), all(a >= b for a, b in zip(seq, seq[1:]))
    if not (up or down):
        violations.append({"rule": "R2", "displayed_in_written_order": seq})
    vals = [r["displayed_value"] for r in pts]
    return {"default_display": ref["displayed_value"] if ref else None, "unit": (pts[0]["unit"] if pts else None),
            "effective_display_range": [min(vals), max(vals)] if vals else None, "violations": violations,
            "status": "DISPLAY_CONSISTENT" if not violations else "GUI_DISAGREES_WITH_STATE_READBACK",
            "display_map": [{"written": r["written"], "kind": r["kind"], "shows": r["displayed_value"]} for r in pts]}


def main(causal, plan, gui, out):
    recs = {r.get("id") or r["atlas_id"]: r for r in json.load(open(causal))["records"]}   # legacy: test id; bulk: atlas id
    by_n = {p["n"]: p for p in json.load(open(plan))["presets"]}
    tests = {}
    for o in json.load(open(gui))["observations"]:
        p = by_n[o["n"]]
        tests.setdefault(p["test"], []).append({"written": p["written"], "kind": p["kind"], "displayed_value": o["displayed_value"], "unit": o["unit"]})
    res = {t: {"atlas_id": recs[t]["atlas_id"], "candidate": recs[t]["candidate"], **analyse(recs[t], rows)} for t, rows in tests.items()}
    json.dump({"sources": {"causal": causal, "gui": gui}, "tests": res}, open(out, "w"), indent=1)
    for t, v in res.items():
        print("%-22s %-34s default=%s range=%s %s" % (t, v["status"], v["default_display"], v["effective_display_range"], v["violations"]))


if __name__ == "__main__":
    main(*sys.argv[1:5])
