"""Fold closure pass 3 (81aef94) into the final map. v5 is kept unchanged; this writes v6.

    python build_final_map_v6.py

Pass 3 covered the 4 remaining NEEDS_CONTEXT filter_balance controls (mixer.osc_a was already
DIRECT_UI_CONFIRMED from pass 2 and is not re-touched). All 5 tooltips matched their expected value exactly.
"""
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ED = os.path.join(REPO, "parameter_characterization", "bulk_causal_evidence")
BUV = os.path.join(HERE, "giant_verify_out", "bulk_ui_verification")
SRC = "CLOSURE_PASS_3_results.json (81aef94)"


def main():
    cmap = json.load(open(os.path.join(ED, "serum_full_control_map_v5.json")))
    R = {r["atlas_id"]: r for r in (json.loads(l) for l in open(os.path.join(BUV, "CLOSURE_PASS_3_results.json")) if l.strip())
         if r["atlas_id"] != "mixer.osc_a.filter_balance"}   # already DIRECT_UI_CONFIRMED in pass 2; CAL_03 re-showed the same state
    touched = {c["atlas_id"] for c in cmap["controls"] if c["final_conclusion"] == "NEEDS_CONTEXT"}
    assert touched == set(R), (touched - set(R), set(R) - touched)

    for c in cmap["controls"]:
        a = c["atlas_id"]
        if a not in R:
            continue
        r = R[a]
        assert r["result"] == "READ", (a, r)
        c["final_conclusion"] = "DIRECT_UI_CONFIRMED"
        c["final_reason"] = "screen %r matches the written/expected value exactly" % r["screen"]
        c["evidence"]["C_direct_ui"]["closure_pass_3"] = {"source": SRC, **r}

    cmap["version"] = 6
    cmap["supersedes"] = "serum_full_control_map_v1-v5 (kept unchanged); v6 folds in closure pass 3"
    counts = Counter(c["final_conclusion"] for c in cmap["controls"])
    cmap["final_counts"] = dict(sorted(counts.items(), key=lambda x: -x[1]))
    assert sum(counts.values()) == 330 and len({c["atlas_id"] for c in cmap["controls"]}) == 330
    assert "NEEDS_CONTEXT" not in counts
    json.dump(cmap, open(os.path.join(ED, "serum_full_control_map_v6.json"), "w"), indent=1, default=repr, ensure_ascii=False)

    term = ["DIRECT_UI_CONFIRMED", "HOST_TEXT_VALIDATED", "UI_OBSERVABLE_BUT_UNREADABLE", "UI_UNOBSERVABLE", "UI_MISMATCH", "UI_SCHEMA_MISMATCH"]
    open_ct = {k: v for k, v in counts.items() if k not in term}
    L = ["# Final closure report v3 (control map v6)", "",
         "330 controls. Terminal: %d. Open: %d." % (sum(v for k, v in counts.items() if k in term), sum(open_ct.values())), "",
         "| conclusion | controls |", "|---|---|"]
    L += ["| %s%s | %d |" % (k, "" if k in term else " (open)", v) for k, v in cmap["final_counts"].items()]
    L += ["", "## Remaining open work, exactly", ""]
    for k in sorted(open_ct):
        ids = sorted(c["atlas_id"] for c in cmap["controls"] if c["final_conclusion"] == k)
        L.append("**%s (%d)**: %s" % (k, len(ids), ", ".join("`%s`" % i for i in ids)))
        L.append("")
    open(os.path.join(BUV, "FINAL_CLOSURE_REPORT_v3.md"), "w").write("\n".join(L) + "\n")
    print(json.dumps(cmap["final_counts"], indent=1))


if __name__ == "__main__":
    main()
