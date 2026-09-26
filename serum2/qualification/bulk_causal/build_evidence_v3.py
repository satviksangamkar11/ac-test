"""Fold the BULK_01/02 session (395277f, e4e3203) into NEW evidence files; nothing existing is modified.

    python build_evidence_v3.py

Writes (parameter_characterization/bulk_causal_evidence/):
  direct_ui_evidence_v4.json      = direct_ui_evidence_v2 observations + session-2 WT readings + BULK screen reads (C tier only)
  host_text_bulk_evidence_v1.json = per-control host text from BULK_01/02_host_texts.json (B tier only, never DIRECT_UI)
  serum_full_control_map_v3.json  = control map v1 + both new tiers + recomputed closure (330 entries)

C-tier rows below are transcribed from ui_scan_2026-09-26.md sections that the operator marked as on-screen reads
(zoomed labels, header rows, mode buttons, tooltips). Host-dump rows from the same doc are NOT transcribed here: they are
recomputed from the dump files into the B-tier file, so the two tiers cannot mix.
"""
import copy
import json
import math
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from closure_ledger import ED  # noqa: E402

BUV = os.path.join(HERE, "giant_verify_out", "bulk_ui_verification")
SCAN = "serum2/qualification/bulk_causal/giant_verify_out/ui_scan_2026-09-26.md (395277f, corrected e4e3203)"


def J(p):
    return json.load(open(p))


def ctrl_value(preset, aid):
    for w in J(os.path.join(BUV, preset + ".controls.json"))["controls"]:
        if w["atlas_id"] == aid or aid in w["aliases"]:
            return w["value"]
    raise KeyError((preset, aid))


B1, B2 = "BULK_01_WAVETABLE_MAIN", "BULK_02_SAMPLE_CALIBRATION"

# (atlas_id, preset, screen text, verdict, method, note). Verdict vocabulary adds, beyond v2:
#   MATCH_ON_KNOWN_CURVE   screen value equals the written raw value through an established display curve
#   CURVE_OBSERVED         value landed and a display point was read, but the curve is not established (no verdict on meaning)
#   DOMAIN_SCALE_MISMATCH  display shows the declared domain does not describe what Serum stores (schema range wrong)
#   VOCABULARY_MAPPED      schema word displays under a different Serum label; mapping now known
BULK_READS = [
    ("oscA.warp_mode", B1, "SYNC", "NORMALIZED_MATCH", "zoomed label", "kSync -> 'Sync'"),
    ("oscB.warp_mode", B1, "PWM", "NORMALIZED_MATCH", "zoomed label", "kPWM -> 'PWM'"),
    ("oscC.warp_mode", B1, "BEND+", "NORMALIZED_MATCH", "zoomed label", "kBendPos -> 'Bend +'"),
    ("oscA.warp_mode2", B1, "AM(B)", "NORMALIZED_MATCH", "zoomed label", "leaf-set word am -> kAM_OSC -> 'AM (B)' (modulator named by the other osc)"),
    ("oscB.warp_mode2", B1, "SYNC", "NORMALIZED_MATCH", "zoomed label", "sync -> kSync -> 'Sync'"),
    ("oscC.warp_mode2", B1, "PWM", "NORMALIZED_MATCH", "zoomed label", "pwm -> kPWM -> 'PWM'"),
    ("oscA.warp_amount", B1, "A Warp (2.46 %)", "CURVE_OBSERVED", "hover tooltip",
     "raw 0.46 landed (file + host text agree); in SYNC mode the display is a mode-dependent nonlinear scale (0.32 -> 1.49, 0.46 -> 2.46). "
     "Not a write mismatch; curve formula unknown."),
    ("env1.sustain", B1, "-31.8 dB", "MATCH_ON_KNOWN_CURVE", "panel read",
     "display = 40*log10(raw) = 20*log10(raw^2): 40*log10(0.16) = -31.84 dB. Resolves the earlier sustain 'mismatch' as a squared display curve."),
    ("fx.compressor.thresh", B1, "-17.5 dB", "CURVE_OBSERVED", "header row", "second point: raw 0.25 -> -7.5, 0.4 -> -13.3, 0.49 -> -17.5 dB"),
    ("fx.compressor.ratio", B1, "Limit", "DOMAIN_SCALE_MISMATCH", "header row",
     "raw 430 shows 'Limit' (so do 210 and 31622): the schema ratio domain 1..1e6 does not describe Serum's stored scale"),
    ("fx.compressor.attack", B1, "0.2 ms", "DOMAIN_SCALE_MISMATCH", "header row",
     "raw 22 -> 0.2 ms with ratio at Limit. CAL_01 shows attack displays raw ms when the ratio is numeric and raw/100 only in "
     "Limit mode; see CAL_01 rows"),
    ("fx.compressor.gain", B1, "26.7 dB", "CURVE_OBSERVED", "header row", "raw 8 -> 23.8, 11 -> 26.7, 16.5 -> 30.4 dB; close to 20*log10(2*raw), unverified"),
    ("fx.reverb.type", B1, "HALL", "MATCH", "label", "kHall -> 'Hall'"),
    ("global.oversampling", B1, "QUALITY Ultra", "NORMALIZED_MATCH", "label", "raw 2.0 -> 'Ultra'"),
    ("global.fx_bus1_destination", B1, "BUS 1 -> DIRECT", "VOCABULARY_MISMATCH", "MIX page label",
     "raw 1.0 (schema word 'master') displays DIRECT"),
    ("global.fx_bus2_destination", B1, "BUS 2 -> BUS 1", "VOCABULARY_MISMATCH", "MIX page label",
     "raw 2.0 (schema word 'direct') displays BUS 1: the schema's master/direct words do not match Serum's destination labels"),
] + [("lfo%d.mode" % i, B1, "ENVELOPE lit (shape Normal)", "MATCH", "tab click",
      "compatible context: mode=Envelope under the default shape. The S&H + Envelope conflict remains a native constraint "
      "(v2 CONTEXT_CONFLICT evidence retained).") for i in range(1, 7)] + [
    ("fx.compressor.thresh", B2, "-13.3 dB", "CURVE_OBSERVED", "header row", "see BULK_01 row"),
    ("fx.compressor.ratio", B2, "Limit", "DOMAIN_SCALE_MISMATCH", "header row", "raw 210 still 'Limit'"),
    ("fx.compressor.attack", B2, "0.1 ms", "DOMAIN_SCALE_MISMATCH", "header row", "raw 10 -> 0.1 ms, ratio at Limit (limiter-mode scale)"),
    ("fx.compressor.gain", B2, "23.8 dB", "CURVE_OBSERVED", "header row", "raw 8 -> 23.8 dB"),
    ("fx.reverb.type", B2, "BASIN", "VOCABULARY_MAPPED", "label",
     "kSpace -> 'Basin' (Basin relabels DECAY -> FEEDBACK and SPIN -> CHORUS). Known map: kHall=Hall, kSpace=Basin, kAbyss=Nitrous; "
     "kVintage untested; 'Plate' has no schema word."),
    ("lfo3.shape", B2, "S&H", "NORMALIZED_MATCH", "label", "RandomSH -> 'S&H'"),
    ("lfo4.shape", B2, "Chaos: Rossler", "NORMALIZED_MATCH", "label", "category prefix 'Chaos:'"),
    ("lfo5.shape", B2, "Chaos: Lorenz", "NORMALIZED_MATCH", "label", "category prefix 'Chaos:'"),
    ("lfo6.shape", B2, "Path", "MATCH", "label", ""),
]
CAL = "CAL_01_COMPRESSOR_CURVES"
CAL_SRC = "ui_scan_2026-09-26.md CAL_01 section (5d9c424)"
# (atlas_id, [(raw, screen)], verdict, note). Values from the operator's header-row table; interpretation is mine.
CAL_READS = [
    ("fx.compressor.thresh", [(0.05, "-1.3 dB"), (0.15, "-4.2 dB"), (0.3, "-9.3 dB"), (0.45, "-15.6 dB"), (0.6, "-23.9 dB"),
                              (0.7, "-31.4 dB"), (0.85, "-49.4 dB"), (1.0, "-120.0 dB")], "MATCH_ON_KNOWN_CURVE",
     "display = 60*log10(1-raw) dB (raw 1.0 = -120 floor): fits all 11 points (incl. earlier 0.25/0.4/0.49) within 0.05 dB. "
     "Unit 7 was first recorded as -40.4; the operator's zoomed recheck (screenshot, 2026-09-26 14:55) reads -49.4."),
    ("fx.compressor.ratio", [(1.0, "1.0:1"), (1.5, "1.5:1"), (2.0, "2.0:1"), (3.0, "3:1"), (4.0, "4:1"), (8.0, "8:1"),
                             (20.0, "32:1"), (100.0, "Limit")], "DOMAIN_SCALE_MISMATCH",
     "display = raw for 1..8; raw 20 shows 32:1 and 100 shows Limit (so do 210/430/31622). Schema domain 1..1e6 is wrong; "
     "whether ratios above 8 are stepped (e.g. 16, 32, Limit) is open: points 10/12/16/24/32/50 would settle it."),
    ("fx.compressor.attack", [(0.1, "1000.0"), (0.5, "0.5"), (2.0, "2.0"), (5.0, "5.0"), (30.0, "30.0"), (150.0, "150.0"),
                              (500.0, "500.0"), (1000.0, "10.0")], "DOMAIN_SCALE_MISMATCH",
     "display = raw ms while the ratio is numeric (0.5..500); in Limit mode display = raw/100 (unit 8 and all BULK/giant points "
     "were Limit). raw 0.1, the declared minimum, shows 1000: the declared min is not valid in Serum."),
    ("fx.compressor.release", [(0.1, "1000.0"), (1.0, "1.0"), (5.0, "5.0"), (20.0, "20.0"), (50.0, "50.0"), (250.0, "250.0"),
                               (600.0, "600.0"), (1000.0, "1000.0")], "DOMAIN_SCALE_MISMATCH",
     "display = raw ms for 1..1000 (incl. Limit mode); raw 0.1, the declared minimum, shows 1000: declared min invalid."),
    ("fx.compressor.gain", [(1.0, "0.0 dB"), (2.0, "6.0 dB"), (3.0, "9.5 dB"), (5.0, "14.0 dB"), (12.0, "21.6 dB"),
                            (20.0, "28.0 dB"), (27.0, "28.6 dB"), (32.0, "36.0 dB")], "CURVE_OBSERVED",
     "display = 20*log10(raw) dB for units 1-5 and 7 (within 0.1 dB); in Limit mode about +6 dB (unit 8 +5.9; BULK 8/11/16.5 "
     "+5.7/+5.9/+6.1). Outlier CONFIRMED by zoomed recheck: raw 20 at ratio 8:1 reads 28.0 vs 26.0 (unit 7, raw 27 at 32:1, fits exactly), "
     "so the offset is not explained by ratio alone. CAL_02 holds gain = 20 across 8 ratios to test it."),
]
REFERENCE_READS = [{"reference": "LFO7_CONTEXT_CONFLICT", "preset": B1, "verdict": "NOT_OBSERVABLE_IN_UI",
                    "note": "Serum 2.0.23 shows only LFO1-6 tabs; file slot LFO6 (UI LFO 7) cannot be viewed. The conflict reference "
                            "moves to a visible LFO in the calibration preset."}]
CONFIRMING = {"MATCH", "NORMALIZED_MATCH", "MATCH_ON_KNOWN_CURVE", "VOCABULARY_MAPPED"}


def host_tier(cmap):
    """B tier: host text of each control's crosswalked host parameter in the preset it was assigned to."""
    dumps = {p: J(os.path.join(BUV, p[:7] + "_host_texts.json")) for p in (B1, B2)}   # BULK_01_host_texts.json
    out = {}
    for c in cmap["controls"]:
        hid = (c["serum_native_identity"]["host_parameter"] or {}).get("name")
        rows = []
        if c["serum_native_identity"]["confidence"] not in ("HIGH", "MEDIUM") or c["atlas_id"].endswith(".name"):
            out[c["atlas_id"]] = [{"status": "NO_RELIABLE_HOST_IDENTITY",
                                   "note": "only a name-heuristic guess (%s); not used as evidence" % (hid,)}] if c["verification"]["assignments"] else []
            continue
        for a in c["verification"]["assignments"]:
            d = dumps[a["preset"]]
            if not hid or hid not in d["reference"]:
                continue
            txt = d["reference"][hid]["text"].strip()
            init = (d["init"].get(hid) or {}).get("text", "").strip()
            pred = None
            for w in J(os.path.join(BUV, a["preset"] + ".controls.json"))["controls"]:
                if w["atlas_id"] == c["atlas_id"] or c["atlas_id"] in w["aliases"]:
                    pred = (w.get("predicted_display") or {}).get("value")
            num = None
            try:
                num = float(txt.replace("%", "").replace("dB", "").split()[0])
            except (ValueError, IndexError):
                pass
            if pred is not None and num is not None:
                status = "HOST_MATCHES_PREDICTION" if abs(num - pred) <= max(0.6, 0.02 * abs(pred)) else "HOST_DIFFERS_FROM_PREDICTION"
            elif txt != init:
                status = "HOST_LANDED"
            else:
                status = "HOST_UNCHANGED_FROM_INIT"
            expl = None
            if status == "HOST_DIFFERS_FROM_PREDICTION" and "warp_amount" in c["atlas_id"]:
                expl = "explained: warp amount display depends on warp mode (PWM = (1-raw)*100, Sync nonlinear); prediction assumed linear"
                status = "HOST_LANDED_MODE_DEPENDENT_CURVE"
            elif status == "HOST_DIFFERS_FROM_PREDICTION" and c["atlas_id"].endswith(".pan"):
                expl = "off by one unit (-20 -> '-19 L', -4 -> '-3 L') although -25 showed -25 on screen earlier: pan display rounding/scale open"
            elif status == "HOST_UNCHANGED_FROM_INIT":
                expl = "written value did not change the host text: possible clamp or ignored key; needs a screen read"
            rows.append({"explanation": expl, "preset": a["preset"], "value_written": a["value"], "host_param": hid,
                         "host_index": d["reference"][hid]["index"], "host_text": txt, "init_text": init,
                         "predicted_display": pred, "status": status})
        out[c["atlas_id"]] = rows
    return out


def main():
    v2 = J(os.path.join(ED, "direct_ui_evidence_v2.json"))
    cmap1 = J(os.path.join(ED, "serum_full_control_map_v1.json"))
    v3 = copy.deepcopy(v2)
    v3["supersedes"] = "direct_ui_evidence_v2.json and v3 (both kept unchanged); v4 adds CAL_01"
    v3["bulk_observations"] = []
    for aid, preset, screen, verdict, method, note in BULK_READS:
        v3["bulk_observations"].append({"atlas_id": aid, "preset": preset, "value_written": ctrl_value(preset, aid),
                                        "screen_displayed": screen, "verdict": verdict, "method": method, "note": note,
                                        "tier": "C_direct_ui", "source": SCAN})
    for aid, s in ((a, e["evidence"]["C_direct_ui"]["session2_supplementary"]) for a, e in
                   ((c["atlas_id"], c) for c in cmap1["controls"]) if e["evidence"]["C_direct_ui"]["session2_supplementary"]):
        v3["bulk_observations"].append({"atlas_id": aid, "preset": s["preset"], "value_written": s["written"],
                                        "screen_displayed": s["screen"], "verdict": s["verdict"].split(" ")[0],
                                        "method": "hover/label", "note": s["note"], "tier": "C_direct_ui", "source": s["source"]})
    for aid, pts, verdict, note in CAL_READS:
        v3["bulk_observations"].append({"atlas_id": aid, "preset": CAL, "value_written": [p for p, _ in pts],
                                        "screen_displayed": [t for _, t in pts], "points": [{"raw": p, "screen": t} for p, t in pts],
                                        "verdict": verdict, "method": "header row, 8 units", "note": note, "tier": "C_direct_ui",
                                        "source": CAL_SRC})
    v3["bulk_observations"].append({"atlas_id": "lfo1.mode", "preset": CAL, "value_written": "Envelope (with shape RandomSH)",
                                    "screen_displayed": "S&H; FREE lit, ENVELOPE dim", "verdict": "CONTEXT_CONFLICT_REFERENCE",
                                    "method": "tab click", "tier": "C_direct_ui", "source": CAL_SRC,
                                    "note": "native constraint reproduced on a clean preset; lfo1.mode itself is confirmed in BULK_01 (Normal + Envelope)"})
    v3["reference_reads"] = REFERENCE_READS
    v3["revisions"] = v3.get("revisions", []) + [{"source": SCAN, "summary": "BULK_01/02 screen reads added as bulk_observations; "
                                                  "v2 observations unchanged"}]
    json.dump(v3, open(os.path.join(ED, "direct_ui_evidence_v4.json"), "w"), indent=1, ensure_ascii=False)

    host = host_tier(cmap1)
    json.dump({"tier": "B_host_text", "is_direct_ui": False, "source": "BULK_01/02_host_texts.json (DawDreamer, 395277f)",
               "status_counts": dict(Counter(r["status"] for rows in host.values() for r in rows)), "controls": host},
              open(os.path.join(ED, "host_text_bulk_evidence_v1.json"), "w"), indent=1, ensure_ascii=False)

    by = {}
    for o in v3["bulk_observations"]:
        by.setdefault(o["atlas_id"], []).append(o)
    cmap2 = copy.deepcopy(cmap1)
    cmap2["version"] = 3
    cmap2["supersedes"] = "serum_full_control_map_v1/v2 (kept unchanged); v3 adds CAL_01"
    for c in cmap2["controls"]:
        a = c["atlas_id"]
        c["evidence"]["B_host_text"]["bulk"] = host.get(a) or None
        c["evidence"]["C_direct_ui"]["bulk_observations"] = by.get(a)
        c["evidence"]["C_direct_ui"].pop("session2_supplementary", None)   # now inside bulk_observations
        obs = by.get(a) or []
        verdicts = {o["verdict"] for o in obs}
        prev = c["closure_classification"]
        hs = {r["status"] for r in (host.get(a) or [])}
        if prev.startswith("RESIDUAL"):
            new = prev
        elif verdicts & {"DOMAIN_SCALE_MISMATCH", "VOCABULARY_MISMATCH"}:
            new = "UI_SCHEMA_MISMATCH"
        elif verdicts & CONFIRMING:
            new = "UI_CONFIRMED"
        elif "CURVE_OBSERVED" in verdicts:
            new = "UI_LANDED_CURVE_OPEN"
        elif prev == "UI_CONFIRMED":
            new = prev
        elif hs & {"HOST_MATCHES_PREDICTION", "HOST_LANDED", "HOST_LANDED_MODE_DEPENDENT_CURVE"}:
            new = "HOST_TEXT_LANDED_UI_PENDING"
        else:
            new = "UI_PENDING"
        c["closure_classification"] = new
        c["unresolved"] = {
            "UI_CONFIRMED": None,
            "UI_SCHEMA_MISMATCH": "screen shows the schema domain/vocabulary does not match Serum; needs the corrected domain or word map",
            "UI_LANDED_CURVE_OPEN": "value landed; display curve not established: more calibration points",
            "HOST_TEXT_LANDED_UI_PENDING": "host text shows the value landed (B tier); a screen read is still needed to close",
            "UI_PENDING": "no screen read and no host-text signal yet",
        }.get(new, c["unresolved"])
    cmap2["closure_counts"] = dict(Counter(c["closure_classification"] for c in cmap2["controls"]))
    assert len(cmap2["controls"]) == 330 and len({c["atlas_id"] for c in cmap2["controls"]}) == 330
    assert all(c["evidence"]["B_host_text"]["is_direct_ui"] is False for c in cmap2["controls"])
    json.dump(cmap2, open(os.path.join(ED, "serum_full_control_map_v3.json"), "w"), indent=1, default=repr, ensure_ascii=False)
    print("C bulk observations:", len(v3["bulk_observations"]), dict(Counter(o["verdict"] for o in v3["bulk_observations"])))
    print("B host:", dict(Counter(r["status"] for rows in host.values() for r in rows)))
    print("closure v2:", cmap2["closure_counts"])


if __name__ == "__main__":
    main()
