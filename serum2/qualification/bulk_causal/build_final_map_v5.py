"""Fold closure pass 2 (b74222d) into the final map. control map v4 is kept unchanged; this writes v5.

    python build_final_map_v5.py

Pass 2 covered exactly the 58 controls still open after pass 1: the 17 NEEDS_CONTEXT (LFO 10x/swing, filter balance),
the 9 NEEDS_REREAD, and one direct hover for each of the 31 HOST_TEXT_UNVALIDATED controls (env curves, filter2 knobs,
LFO smooth/delay, filter wet). Every one of the 58 gets a terminal conclusion here; none is carried forward open,
except the 4 filter_balance controls that hit a NEW blocker (see below) and stay open by design, not by default.
"""
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ED = os.path.join(REPO, "parameter_characterization", "bulk_causal_evidence")
BUV = os.path.join(HERE, "giant_verify_out", "bulk_ui_verification")
SRC = "CLOSURE_PASS_2_results.json (b74222d)"

VERDICT = {
    # LFO 10x / swing: genuinely not present as named/separate controls in Hz mode in this Serum build. The only other
    # visible toggle ("Anchored") is a DIFFERENT, unidentified parameter -- not assumed to be swing.
    **{"lfo%d.rate_10x" % i: ("UI_UNOBSERVABLE", "no 10x control in Hz mode; rate free-runs to 62.5 Hz directly. The What's New "
                              "PDF's '10x Rate' may describe the free rate range itself, not a separate button, in this build.")
       for i in range(1, 7)},
    **{"lfo%d.swing" % i: ("UI_UNOBSERVABLE", "no control named swing; the only other toggle ('Anchored') is a distinct, "
                           "unidentified parameter and is not assumed to be this one") for i in range(1, 7)},
    # filter balance: osc A (enabled) confirmed; B/C/noise/sub are dimmed because CAL_02 left them disabled -- a second,
    # narrower context bug, not the routing fix. Kept open rather than guessed.
    "mixer.osc_a.filter_balance": ("DIRECT_UI_CONFIRMED", "'A> Filter Balance (15)' matches written 15, routed to FILTER"),
    **{"mixer.%s.filter_balance" % m: ("NEEDS_CONTEXT", "routed to FILTER (confirmed) but the channel itself is disabled in "
                                       "CAL_02, so the balance knob is dimmed with no tooltip; needs the channel enabled too")
       for m in ("osc_b", "osc_c", "noise", "sub")},
    # re-reads
    "global.portamento_curve": ("DIRECT_UI_CONFIRMED", "'Porta Curve (-37 %)' matches written -37"),
    "global.voice_control.random.cutoff": ("DIRECT_UI_CONFIRMED", "'37%' matches written 37"),
    "global.voice_control.random.detune": ("DIRECT_UI_CONFIRMED", "'4.6' matches written 23 (display = raw/5, per campaign host text)"),
    "lfo4.beat_sync": ("DIRECT_UI_CONFIRMED", "'LFO 4 BPM (On)' matches written 1.0"),
    "lfo5.beat_sync": ("DIRECT_UI_CONFIRMED", "'LFO 5 BPM (On)' matches written 1.0"),
    "lfo6.beat_sync": ("DIRECT_UI_CONFIRMED", "'LFO 6 BPM (On)' matches written 1.0"),
    "oscB.warp_var2": ("DIRECT_UI_CONFIRMED", "'B Warp 2 Var (0.2200)' matches written 0.22 exactly"),
    "oscA.warp_var2": ("UI_UNOBSERVABLE", "warp_mode2 AM(B) has no VAR control on screen (only a Var bar for warp 1); "
                       "the value cannot be read in this warp mode"),
    "oscC.warp_var2": ("UI_UNOBSERVABLE", "warp_mode2 PWM has no VAR control on screen either"),
    "lfo6.rise": ("DIRECT_UI_CONFIRMED", "'LFO 6 Rise (2 bar t)' is a beat-synced note-value label, consistent with beat_sync=On"),
    "mixer.filter1.wet": ("DIRECT_UI_CONFIRMED", "'Filter 1 Wet (13 %)' read directly on the MIX page"),
    "mixer.filter2.wet": ("DIRECT_UI_CONFIRMED", "'Filter 2 Wet (90 %)' read directly on the MIX page"),
}
# every other Part-3 hover was UNREADABLE: env curves, filter1/2 remaining knobs, LFO smooth/delay
DEFAULT_UNREADABLE_REASON = "hovered directly (not just via its class representative); still no exact value after the attempt"


def main():
    cmap = json.load(open(os.path.join(ED, "serum_full_control_map_v4.json")))
    touched0 = None
    all_rows = [json.loads(l) for l in open(os.path.join(BUV, "CLOSURE_PASS_2_results.json")) if l.strip()]
    R = {r["atlas_id"]: r for r in all_rows if not r["atlas_id"].startswith(("context:", "reference:")) and r["atlas_id"] not in
         ("lfo1.beat_sync", "lfo2.beat_sync", "lfo3.beat_sync")}   # already DIRECT_UI_CONFIRMED in pass 1; CAL_02 re-showed the same state
    touched = {c["atlas_id"] for c in cmap["controls"] if c["final_conclusion"] in
              ("NEEDS_CONTEXT", "NEEDS_REREAD", "HOST_TEXT_UNVALIDATED")}
    assert touched == set(R), (touched - set(R), set(R) - touched)

    for c in cmap["controls"]:
        a = c["atlas_id"]
        if a not in R:
            continue
        r = R[a]
        if a in VERDICT:
            concl, why = VERDICT[a]
        elif r["result"] == "UNREADABLE":
            concl, why = "UI_OBSERVABLE_BUT_UNREADABLE", DEFAULT_UNREADABLE_REASON
        else:
            concl, why = "DIRECT_UI_CONFIRMED", "screen %r" % r["screen"]
        c["final_conclusion"], c["final_reason"] = concl, why
        c["evidence"]["C_direct_ui"]["closure_pass_2"] = {"source": SRC, **r}

    cmap["version"] = 5
    cmap["supersedes"] = "serum_full_control_map_v1-v4 (kept unchanged); v5 folds in closure pass 2"
    counts = Counter(c["final_conclusion"] for c in cmap["controls"])
    cmap["final_counts"] = dict(sorted(counts.items(), key=lambda x: -x[1]))
    assert sum(counts.values()) == 330 and len({c["atlas_id"] for c in cmap["controls"]}) == 330
    json.dump(cmap, open(os.path.join(ED, "serum_full_control_map_v5.json"), "w"), indent=1, default=repr, ensure_ascii=False)

    term = ["DIRECT_UI_CONFIRMED", "HOST_TEXT_VALIDATED", "UI_OBSERVABLE_BUT_UNREADABLE", "UI_UNOBSERVABLE", "UI_MISMATCH", "UI_SCHEMA_MISMATCH"]
    open_ct = {k: v for k, v in counts.items() if k not in term}
    L = ["# Final closure report v2 (control map v5)", "",
         "330 controls. Terminal: %d. Open: %d." % (sum(v for k, v in counts.items() if k in term), sum(open_ct.values())), "",
         "| conclusion | controls |", "|---|---|"]
    L += ["| %s%s | %d |" % (k, "" if k in term else " (open)", v) for k, v in cmap["final_counts"].items()]
    L += ["", "## Remaining open work, exactly", ""]
    for k in sorted(open_ct):
        ids = sorted(c["atlas_id"] for c in cmap["controls"] if c["final_conclusion"] == k)
        L.append("**%s (%d)**: %s" % (k, len(ids), ", ".join("`%s`" % i for i in ids)))
        L.append("")
    open(os.path.join(BUV, "FINAL_CLOSURE_REPORT_v2.md"), "w").write("\n".join(L) + "\n")
    print(json.dumps(cmap["final_counts"], indent=1))


if __name__ == "__main__":
    main()
