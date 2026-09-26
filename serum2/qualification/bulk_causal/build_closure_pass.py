"""Closure pass plan: class-validated host text for the HOST_TEXT_LANDED controls + a BULK_01 checklist for the rest.

    python build_closure_pass.py

Rule (agreed 2026-09-26). Three terminal evidence conclusions, never merged into one "closed":
  DIRECT_UI_CONFIRMED    an actual Serum screen read matched
  HOST_TEXT_VALIDATED    host text (get_parameter_text after a native preset load) shows the expected display AND every
                         class it belongs to has a representative whose screen read equals its host text
  UI_UNOBSERVABLE / UI_OBSERVABLE_BUT_UNREADABLE   the available UI cannot give an exact reading (explicit, not "closed")

Class key for host-text controls = everything that can change how a value is encoded or displayed:
  module family, mutation mechanism, declared domain kind, host display unit class (dB, %, Hz, time, note, pan, int,
  decimal, label), fitted display model, host-text status, and a known-risk flag. Known-risk controls (anchors, warp
  amounts, pans with the open off-by-one, alias pairs, signed/log domains) each form their OWN class, so each is read.
Outputs in giant_verify_out/bulk_ui_verification/: CLOSURE_PASS_plan.json and CLOSURE_PASS_checklist.md.
"""
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ED = os.path.join(REPO, "parameter_characterization", "bulk_causal_evidence")
BUV = os.path.join(HERE, "giant_verify_out", "bulk_ui_verification")
RISK_FIELDS = ("sustain", "warp_amount", "warp_var2", "pan", "fine", "transpose", "bend_range", "tuning")


def J(p):
    return json.load(open(p))


def unit_class(t):
    t = t.strip()
    if "dB" in t:
        return "dB"
    if "%" in t:
        return "%"
    if "Hz" in t:
        return "Hz"
    if re.search(r"\bms\b|\d\s*s$", t):
        return "time"
    if re.search(r"\d+/\d+", t):
        return "note"
    if re.search(r"\d\s*[LR]$", t):
        return "pan"
    if re.fullmatch(r"[-+]?\d+", t):
        return "int"
    if re.fullmatch(r"[-+]?\d+\.\d+", t):
        return "decimal"
    return "label"


def family(aid):
    return re.sub(r"\d|osc[ABC]|Noise", lambda m: "osc" if m.group(0).startswith("osc") else "", aid.split(".")[0])


def manifest_rows():
    rows = {}
    for f in ("BULK_01_WAVETABLE_MAIN", "BULK_02_SAMPLE_CALIBRATION"):
        for w in J(os.path.join(BUV, f + ".controls.json"))["controls"]:
            for a in [w["atlas_id"]] + w["aliases"]:
                rows.setdefault(a, dict(w, preset=f))
    return rows


def main():
    cmap = J(os.path.join(ED, "serum_full_control_map_v3.json"))["controls"]
    host = J(os.path.join(ED, "host_text_bulk_evidence_v1.json"))["controls"]
    rows = manifest_rows()
    pend = [c for c in cmap if c["closure_classification"] == "HOST_TEXT_LANDED_UI_PENDING"]
    rest = [c for c in cmap if c["closure_classification"] == "UI_PENDING"]

    classes = defaultdict(list)
    for c in pend:
        a = c["atlas_id"]
        r = next(x for x in host[a] if "host_text" in x)
        w = rows[a]
        kind = (c["declared_domain"] or {}).get("kind")
        risky = (a.split(".")[-1].startswith(RISK_FIELDS) or bool(c["context_requirements"]["alias_of"] or c["context_requirements"]["aliases"])
                 or kind in ("signed", "log") or r["status"] not in ("HOST_MATCHES_PREDICTION", "HOST_LANDED") or w.get("anchor"))
        key = (family(a), c["mutation_mechanism"], kind, unit_class(r["host_text"]),
               (w.get("predicted_display") or {}).get("model"), r["status"],
               ("RISK:" + (c["context_requirements"]["alias_of"] or a)) if risky else "")   # an alias pair shares one raw path: one read
        root = c["context_requirements"]["alias_of"] or (a if c["context_requirements"]["aliases"] else None)
        if root:
            key = ("ALIAS_PATH", root)          # both names write one raw path: one screen read covers the pair
        classes[key].append({"atlas_id": a, "preset": r["preset"], "view": w["view"], "value_written": r["value_written"],
                             "host_param": r["host_param"], "host_index": r["host_index"], "host_text": r["host_text"]})
    sample = []
    for key, members in sorted(classes.items(), key=lambda kv: str(kv[0])):
        rep = sorted(members, key=lambda x: x["atlas_id"])[0]
        sample.append(dict(rep, class_key=[str(k) for k in key], class_size=len(members),
                           covers=[x["atlas_id"] for x in members]))
    assert sum(s["class_size"] for s in sample) == len(pend)

    checklist = []
    for c in rest:
        a = c["atlas_id"]
        w = rows.get(a)
        checklist.append({"atlas_id": a, "preset": w["preset"] if w else None, "view": w["view"] if w else None,
                          "value_written": w["value"] if w else None,
                          "readability_known": c["gui_readability"]["class"], "note": c["gui_readability"]["note"]})
    plan = {"rule": {"DIRECT_UI_CONFIRMED": "actual Serum screen read matched",
                     "HOST_TEXT_VALIDATED": "host text shows the expected display AND its class representative's screen read equals its host text",
                     "UI_OBSERVABLE_BUT_UNREADABLE": "control is on screen but no exact value can be read (no tooltip / no readout)",
                     "UI_UNOBSERVABLE": "control is not represented in the available UI",
                     "never": "these conclusions are never merged into one closed status"},
            "host_text_controls": len(pend), "classes": len(sample),
            "sample": sample,
            "if_representative_disagrees": "the whole class drops to DIRECT_UI-required and every member is read",
            "no_host_text_controls": len(rest), "bulk01_checklist": checklist}
    json.dump(plan, open(os.path.join(BUV, "CLOSURE_PASS_plan.json"), "w"), indent=1, default=repr)

    L = []
    L.append("# Closure pass checklist")
    L.append("")
    L.append("Two parts, both on presets you already have. Record each line as: screen text, or UNREADABLE (on screen, no exact value), or ABSENT (not in the UI).")
    L.append("")
    L.append("## Part A: class representatives (%d reads validate %d host-text controls)" % (len(sample), len(pend)))
    L.append("")
    L.append("Pass condition: the screen shows exactly the host text. If one disagrees, that whole class needs a full read.")
    L.append("")
    L.append("| # | preset | view | control | written | screen must show | class size |")
    L.append("|---|---|---|---|---|---|---|")
    for i, s in enumerate(sorted(sample, key=lambda x: (x["preset"], x["view"], x["atlas_id"])), 1):
        L.append("| %d | %s | %s | `%s` | %r | `%s` | %d |" % (i, s["preset"][:7], s["view"], s["atlas_id"], s["value_written"], s["host_text"], s["class_size"]))
    L.append("")
    L.append("## Part B: controls with no host text (%d), BULK_01/02 page by page" % len(rest))
    L.append("")
    byv = defaultdict(list)
    for x in checklist:
        byv[(x["preset"] or "-", x["view"] or "-")].append(x)
    for (p, v), xs in sorted(byv.items()):
        L.append("**%s / %s** (%d)" % ((p or "-")[:7], v, len(xs)))
        L.append("")
        for x in sorted(xs, key=lambda x: x["atlas_id"]):
            flag = "" if x["readability_known"] == "UNKNOWN_OR_READABLE" else " (scan note: %s)" % x["note"]
            L.append("- [ ] `%s` written %r%s" % (x["atlas_id"], x["value_written"], flag))
        L.append("")
    L.append("## Part C: residuals (unchanged)")
    L.append("")
    L.append("- `arp.transpose.shape`: set each of the 18 labels, save, read the file back.")
    L.append("- `global.voice_priority`: list the menu labels, then save/read back per label.")
    L.append("- `global.use_ultra_on_render`: toggle once, save, read the file.")
    L.append("- filter balance: locate the control for the 5 mixer strips.")
    open(os.path.join(BUV, "CLOSURE_PASS_checklist.md"), "w").write("\n".join(L) + "\n")
    print("host-text controls %d -> %d classes (reads); no-host-text controls %d" % (len(pend), len(sample), len(rest)))


if __name__ == "__main__":
    main()
