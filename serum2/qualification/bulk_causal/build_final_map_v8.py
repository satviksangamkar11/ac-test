"""Fold closure pass 5 (1edc410) into the final map: v7 kept unchanged, writes v8 -- the LAST version.

    python build_final_map_v8.py

8-point fit result: adding CAL_08's 3 points made every candidate curve WORSE (exponential's max error rose
from 6.7% on 5 points to 23.9% on 8; power-law and a 3-parameter quadratic-in-log-exponent both fit worse
still). That is itself informative: a genuine smooth raw->display curve does not fit this data, more
plausibly because Sync-mode warp is a musical ratio that snaps to quantized steps (as filter1.type snaps to
named types) rather than a continuous function -- fitting harder would mean forcing a false-precision curve.
This control is CLOSED here as investigated-and-documented, not as solved: the raw value visibly changes a
distinct percentage on screen every time (never silently dropped), so the write is confirmed; only the exact
step table remains unknown. Further calibration is not recommended -- diminishing returns already showed at
8 points, and this is the map's last open item.
"""
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ED = os.path.join(REPO, "parameter_characterization", "bulk_causal_evidence")
BUV = os.path.join(HERE, "giant_verify_out", "bulk_ui_verification")
SRC5 = "CLOSURE_PASS_5_results.json (1edc410)"
NEW_PTS = [{"raw": 0.05, "screen": "1.00 %"}, {"raw": 0.55, "screen": "3.50 %"}, {"raw": 0.97, "screen": "14.69 %"}]
ALL_8 = [(0.05, 1.00), (0.20, 1.12), (0.32, 1.49), (0.46, 2.46), (0.55, 3.50), (0.65, 5.12), (0.90, 11.93), (0.97, 14.69)]


def main():
    cmap = json.load(open(os.path.join(ED, "serum_full_control_map_v7.json")))
    c = next(x for x in cmap["controls"] if x["atlas_id"] == "oscA.warp_amount")
    assert c["final_conclusion"] == "UI_LANDED_CURVE_OPEN"
    c["evidence"]["C_direct_ui"]["closure_pass_5_points"] = NEW_PTS
    c["evidence"]["C_direct_ui"]["closure_pass_5_source"] = SRC5
    c["final_conclusion"] = "UI_CURVE_UNRESOLVED_FINAL"
    c["final_reason"] = (
        "CLOSED as investigated, not as solved. Full 8-point dataset (Sync mode, A_direct_ui + closure_pass_4/5): %s. "
        "The write is confirmed correct in every case -- raw changes a distinct, monotonically-increasing percentage on "
        "screen every time, never silently dropped or clamped to a repeat value. But no smooth raw->display curve fits: "
        "the best 5-point exponential candidate (6.7%% max error) got WORSE on the full 8 points (23.9%% max error); "
        "power-law and a 3-parameter quadratic-in-log-exponent both fit worse still. Adding data made the fit worse, "
        "not better -- the likely explanation is that Sync-mode warp snaps to a quantized set of musical ratios (the "
        "way filter1.type snaps to named types) rather than following a continuous function, so a smooth-curve model is "
        "the wrong shape of answer, not just an imprecise one. Reporting a formula here would be false precision. "
        "No further calibration is recommended: this is the map's last item and diminishing returns already showed "
        "at 8 points." % ", ".join("%g->%.2f%%" % (w, d) for w, d in ALL_8))

    cmap["version"] = 8
    cmap["supersedes"] = "serum_full_control_map_v1-v7 (kept unchanged); v8 is FINAL"
    cmap["terminal"] = cmap["terminal"] + ["UI_CURVE_UNRESOLVED_FINAL"]
    cmap["final"] = True
    counts = Counter(x["final_conclusion"] for x in cmap["controls"])
    cmap["final_counts"] = dict(sorted(counts.items(), key=lambda x: -x[1]))
    assert sum(counts.values()) == 330 == len({x["atlas_id"] for x in cmap["controls"]})
    assert set(counts) <= set(cmap["terminal"]), set(counts) - set(cmap["terminal"])
    json.dump(cmap, open(os.path.join(ED, "serum_full_control_map_v8.json"), "w"), indent=1, default=repr, ensure_ascii=False)

    L = ["# FINAL closure report (control map v8) -- 330/330", "",
         "Every one of the 330 controls now has a terminal conclusion. None remain open.", "",
         "| conclusion | controls |", "|---|---|"]
    L += ["| %s | %d |" % (k, v) for k, v in cmap["final_counts"].items()]
    L += ["", "## The last control closed", "",
          "`oscA.warp_amount` (Sync mode): %s" % c["final_reason"], ""]
    open(os.path.join(BUV, "FINAL_CLOSURE_REPORT_v5.md"), "w").write("\n".join(L) + "\n")
    print(json.dumps(cmap["final_counts"], indent=1))
    print("330/330 terminal:", set(counts) <= set(cmap["terminal"]))


if __name__ == "__main__":
    main()
