"""Final 330-control map (v4) from the closure pass (1e71cb8). No existing file is modified.

    python build_final_map.py

Every control gets exactly ONE conclusion. Terminal conclusions (agreed rule, never merged):
  DIRECT_UI_CONFIRMED            an actual Serum screen read matched the written value
  HOST_TEXT_VALIDATED            host text shows the expected display AND its class representative's screen read matched
  UI_OBSERVABLE_BUT_UNREADABLE   on screen, but no exact value can be read (no tooltip / no readout)
  UI_UNOBSERVABLE                not represented in the available UI
  UI_MISMATCH / UI_SCHEMA_MISMATCH   the screen contradicts the written value / the schema domain or vocabulary
Non-terminal (open work, listed explicitly):
  UI_LANDED_CURVE_OPEN           value landed and was read, display curve unknown, so no match verdict
  HOST_TEXT_UNVALIDATED          host text landed but the class representative was unreadable, so the class is not validated
  NEEDS_CONTEXT                  hidden in the tested context (named), needs a different context
  NEEDS_REREAD                   read was misattributed or indistinguishable from the default
  RESIDUAL_*                     cannot be carried by a preset (unchanged)

Operator readings are data; the per-row verdicts below are my judgement of screen text vs written value, stated per row.
"""
import json
import os
import re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ED = os.path.join(REPO, "parameter_characterization", "bulk_causal_evidence")
BUV = os.path.join(HERE, "giant_verify_out", "bulk_ui_verification")
SRC = "CLOSURE_PASS_results.json (1e71cb8)"

# Part B READ rows judged individually (screen vs written). Anything not listed here and READ = clean match.
B_VERDICT = {
    "arp.transpose.range": ("UI_SCHEMA_MISMATCH", "written 16, screen 8: Serum's range appears to stop at 8; declared domain too wide"),
    "mixer.noise.pan": ("UI_MISMATCH", "written -20, screen -19 L (host text agrees): pan display off by one"),
    "oscNoise.pan": ("UI_MISMATCH", "alias of mixer.noise.pan: written -20, screen -19 L"),
    "mixer.sub.pan": ("UI_MISMATCH", "written -4, screen -3 L (host text agrees): pan display off by one"),
    "fx.distortion.freq": ("UI_LANDED_CURVE_OPEN", "raw 0.51 -> 355 Hz; curve unknown"),
    "fx.filter.cutoff": ("UI_LANDED_CURVE_OPEN", "raw 0.67 -> 1629 Hz; curve unknown"),
    "global.voice_control.random.cutoff": ("NEEDS_REREAD", "written 0.1 shows 0%: indistinguishable from the default; needs a larger value"),
    "global.voice_control.random.detune": ("NEEDS_REREAD", "written 0.01 shows 0.0: indistinguishable from the default; needs a larger value"),
    "global.portamento_curve": ("NEEDS_REREAD", "written -0.001 shows 0 %: indistinguishable from the default; needs a larger value"),
}
B_NOTE = {"arp.pattern.rate": "raw 0.4 -> '1/8' (label)", "fx.delay.mode": "raw 2 -> 'TAP->DELAY' (label)", "global.swing_div": "raw 1 -> '1/4' (label)",
          "oscA.wavetable": "analog_basic -> 'Basic Shapes'", "oscB.wavetable": "analog_warm -> 'DM - OSCAR' (the mapped file)",
          "oscC.wavetable": "analog_mini -> 'Basic Mini'", "global.global_tuning": "450 -> 'A = 450 Hz'"}
ABSENT_VERDICT = {
    **{"macro%d.name" % i: ("UI_MISMATCH", "Serum shows 'Macro %d', not the written name: macro names are normally shown in the UI, "
                            "so the raw write ['Macro%d','name'] likely does not take effect" % (i, i - 1)) for i in range(1, 9)},
    **{"lfo%d.swing" % i: ("NEEDS_CONTEXT", "hidden while the LFO is in BPM mode (bulk preset set beat_sync on for every LFO); needs beat_sync off")
       for i in range(1, 7)},
    **{"lfo%d.rate_10x" % i: ("NEEDS_CONTEXT", "the 10x button exists only in Hz mode; needs beat_sync off") for i in range(1, 7)},
}
# Part A corrections: the DIFFERS rows were attribution errors on our side, not Serum divergence
A_OVERRIDE = {
    "lfo2.beat_sync": ("DIRECT_UI_CONFIRMED", "screen 'LFO 2 BPM (On)' matches written 1.0; the host comparison used a wrong crosswalk ('LFO 2 Delay')"),
    "lfo3.beat_sync": ("DIRECT_UI_CONFIRMED", "screen 'LFO 3 BPM (On)' matches written 1.0; wrong crosswalk ('LFO 3 Delay')"),
    "oscA.warp_var2": ("NEEDS_REREAD", "the read '63 %' is the warp 2 AMOUNT knob (host 'A Warp 2' = 63); var2 not read"),
    "oscB.warp_var2": ("NEEDS_REREAD", "the read '1.49 %' is the warp 2 AMOUNT knob; var2 not read"),
    "oscC.warp_var2": ("NEEDS_REREAD", "the read '39 %' is the warp 2 AMOUNT knob; var2 not read"),
}
# incidental screen confirmations from the misattributed reads above
INCIDENTAL = {"oscA.warp_amount2": "screen '63 %' (AM mode, raw 0.63)", "oscB.warp_amount2": "screen '1.49 %' (Sync mode, raw 0.32; host text agrees)",
              "oscC.warp_amount2": "screen '39 %' (PWM mode inverted, raw 0.61)"}
# D tier: manufacturer documentation (Serum 2 "What's New", v1.0.0). Never counts as a screen read; it can only change
# which CONTEXT a read needs, or corroborate a schema finding.
DOC = "Serum 2 What's New PDF (uploaded 2026-09-26)"
DOC_EVIDENCE = {
    **{"mixer.%s.filter_balance" % m: ("NEEDS_CONTEXT", "p16 'Balance Routing: balance routing to filters and FX busses': the balance "
                                       "control appears on the MIX page only when the channel routes to the filters; the bulk preset "
                                       "routed to MAIN. Needs a routing context.") for m in ("osc_a", "osc_b", "osc_c", "noise", "sub")},
}
DOC_NOTES = {
    **{"lfo%d.swing" % i: "p14 'LFOs can now follow swing': likely an on/off follow-swing setting; read as a toggle" for i in range(1, 7)},
    **{"lfo%d.rate_10x" % i: "p14 '10x Rate: set rates up to 1000 Hz': Hz-mode control" for i in range(1, 7)},
    "global.transpose": "p19 keyboard transpose 'within a range of two octaves': corroborates +-24 (schema +-48)",
    "fx.reverb.type": "p12 new reverb types 'Vintage, Nitrous, and Basin' (+ Plate, Hall): corroborates the 5-type menu",
}
DOC_GLOBAL = {"lfo7_tab": "p14 'LFO 7 to LFO 10 appear after you assign LFO 6': LFO 7 IS viewable once LFO 6 has a mod route; "
                          "the earlier 'no UI tab' conclusion is withdrawn (the conflict itself is proven on LFO1, CAL_01)",
              "coverage_gap": "p11 '13 powerful effects': the 330 candidates cover 12 FX types; the new Utility effect has none",
              "multiple_instances": "p11 'Multiple instances of a single effect': supports CAL_01's 8-compressor rack"}
# class whose identity was wrong: its members' host text is void, so they are not validated
VOID_CLASS_OF = "lfo3.beat_sync"


def J(p):
    return json.load(open(p))


def main():
    cmap = J(os.path.join(ED, "serum_full_control_map_v3.json"))
    plan = J(os.path.join(BUV, "CLOSURE_PASS_plan.json"))
    R = [json.loads(l) for l in open(os.path.join(BUV, "CLOSURE_PASS_results.json")) if l.strip()]
    A = {r["atlas_id"]: r for r in R if r["part"] == "A"}
    B = {r["atlas_id"]: r for r in R if r["part"] == "B"}
    reps = {s["atlas_id"]: s for s in plan["sample"]}
    member_of = {m: s["atlas_id"] for s in plan["sample"] for m in s["covers"]}
    assert set(A) == set(reps) and set(B) == {x["atlas_id"] for x in plan["bulk01_checklist"]}

    out = []
    for c in cmap["controls"]:
        a = c["atlas_id"]
        prev = c["closure_classification"]
        concl, why, ev = None, None, None
        if a in INCIDENTAL:
            concl, why, ev = "DIRECT_UI_CONFIRMED", INCIDENTAL[a], {"part": "A (incidental)", "screen": INCIDENTAL[a]}
        elif a in A_OVERRIDE:
            concl, why = A_OVERRIDE[a]
            ev = A[a]
        elif a in reps:                                     # class representative read on screen
            r = A[a]
            ev = r
            concl = {"MATCH": "DIRECT_UI_CONFIRMED", "UNREADABLE": "UI_OBSERVABLE_BUT_UNREADABLE"}[r["result"]]
            why = "class representative: screen %r vs host %r" % (r["screen"], reps[a]["host_text"])
        elif a in member_of:                                # validated (or not) through its class
            rep = member_of[a]
            rr = A[rep]
            if rep == VOID_CLASS_OF:
                concl, why = "NEEDS_REREAD", "its class used a wrong host identity ('LFO N Delay'); read the BPM toggle on screen"
            elif rr["result"] == "MATCH" or (rep in A_OVERRIDE and A_OVERRIDE[rep][0] == "DIRECT_UI_CONFIRMED"):
                concl, why = "HOST_TEXT_VALIDATED", "host text matches; class representative %s matched on screen" % rep
            else:
                concl, why = "HOST_TEXT_UNVALIDATED", "host text landed; class representative %s was %s" % (rep, rr["result"])
            ev = {"class_representative": rep, "representative_result": rr["result"]}
        elif a in B:
            r = B[a]
            ev = r
            if r["result"] == "READ":
                concl, why = B_VERDICT.get(a, ("DIRECT_UI_CONFIRMED", B_NOTE.get(a, "screen %r matches written value" % r["screen"])))
            elif r["result"] == "UNREADABLE":
                concl, why = "UI_OBSERVABLE_BUT_UNREADABLE", "no exact value after 2 hover attempts"
            else:
                concl, why = ABSENT_VERDICT.get(a, ("UI_UNOBSERVABLE", "not represented in the UI"))
        else:
            concl = {"UI_CONFIRMED": "DIRECT_UI_CONFIRMED"}.get(prev, prev)
            why = "carried from control map v3 (%s)" % prev
        if a in DOC_EVIDENCE and concl in ("HOST_TEXT_UNVALIDATED", "UI_OBSERVABLE_BUT_UNREADABLE", "UI_UNOBSERVABLE"):
            concl, why = DOC_EVIDENCE[a]
        c["evidence"]["D_vendor_doc"] = ({"source": DOC, "note": DOC_EVIDENCE.get(a, (None, DOC_NOTES.get(a)))[1]}
                                         if (a in DOC_EVIDENCE or a in DOC_NOTES) else None)
        c["final_conclusion"] = concl
        c["final_reason"] = why
        c["evidence"]["C_direct_ui"]["closure_pass"] = ev
        out.append(c)

    cmap["vendor_doc_findings"] = DOC_GLOBAL
    cmap["version"] = 4
    cmap["supersedes"] = "serum_full_control_map_v1-v3 (kept unchanged); v4 adds the closure pass"
    cmap["terminal"] = ["DIRECT_UI_CONFIRMED", "HOST_TEXT_VALIDATED", "UI_OBSERVABLE_BUT_UNREADABLE", "UI_UNOBSERVABLE",
                        "UI_MISMATCH", "UI_SCHEMA_MISMATCH"]
    counts = Counter(c["final_conclusion"] for c in out)
    cmap["final_counts"] = dict(sorted(counts.items(), key=lambda x: -x[1]))
    assert sum(counts.values()) == 330 and len({c["atlas_id"] for c in out}) == 330
    json.dump(cmap, open(os.path.join(ED, "serum_full_control_map_v4.json"), "w"), indent=1, default=repr, ensure_ascii=False)

    term = sum(v for k, v in counts.items() if k in cmap["terminal"])
    L = ["# Final closure report (control map v4)", "",
         "330 controls, each with exactly one conclusion. Terminal: %d. Open: %d." % (term, 330 - term), "",
         "| conclusion | controls |", "|---|---|"]
    L += ["| %s%s | %d |" % (k, "" if k in cmap["terminal"] else " (open)", v) for k, v in cmap["final_counts"].items()]
    L += ["", "## Open work, exactly", ""]
    for k in ("NEEDS_CONTEXT", "NEEDS_REREAD", "HOST_TEXT_UNVALIDATED", "UI_LANDED_CURVE_OPEN", "RESIDUAL_NOT_DERIVED", "RESIDUAL_NOT_STORED"):
        ids = sorted(c["atlas_id"] for c in out if c["final_conclusion"] == k)
        if ids:
            L.append("**%s (%d)**: %s" % (k, len(ids), ", ".join("`%s`" % i for i in ids)))
            L.append("")
    L += ["## Vendor documentation (D tier, never a screen read)", ""] + ["- %s" % v for v in DOC_GLOBAL.values()] + [""]
    L += ["## Mismatches found (terminal, reported not fixed)", ""]
    for c in sorted(out, key=lambda c: c["atlas_id"]):
        if c["final_conclusion"] in ("UI_MISMATCH", "UI_SCHEMA_MISMATCH"):
            L.append("- `%s` (%s): %s" % (c["atlas_id"], c["final_conclusion"], c["final_reason"]))
    open(os.path.join(BUV, "FINAL_CLOSURE_REPORT.md"), "w").write("\n".join(L) + "\n")
    print(json.dumps(cmap["final_counts"], indent=1))


if __name__ == "__main__":
    main()
