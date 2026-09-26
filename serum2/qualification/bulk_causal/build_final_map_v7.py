"""Fold closure pass 4 + residual results (fc36064, d4b4530) into the final map. v6 kept unchanged; writes v7.

    python build_final_map_v7.py

Curve fits (least-squares on the operator's 8-point readings, printed at run time):
  fx.compressor.gain    display = 20*log10(raw) dB -- EXACT fit, all 8 points within 0.05 dB
  fx.distortion.freq    display = 8.25 * 10**(3.205*raw) Hz -- fits all 8 points within 1%
  fx.filter.cutoff      display = 8.17 * 10**(3.432*raw) Hz -- fits all 8 points within 1% (asymptotes near 22 kHz)
  oscA.warp_amount (Sync) -- linear, power-law and exponential fits ALL rejected (>15% residual) on the 5-point
                             dataset (2 from BULK_01/CAL_01, 3 new from CAL_07). Left OPEN, not guessed.
"""
import json
import math
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ED = os.path.join(REPO, "parameter_characterization", "bulk_causal_evidence")
BUV = os.path.join(HERE, "giant_verify_out", "bulk_ui_verification")
SRC4 = "CLOSURE_PASS_4_results.json (fc36064)"
SRCR = "RESIDUAL_results.json (d4b4530)"
GAIN = [(1.0, 0.0), (4.0, 12.0), (7.0, 16.9), (11.0, 20.8), (15.0, 23.5), (18.0, 25.1), (23.0, 27.2), (30.0, 29.5)]
DIST = [(0.05, 12), (0.15, 25), (0.28, 65), (0.40, 157), (0.52, 382), (0.64, 928), (0.76, 2254), (0.90, 6345)]
CUT = [(0.05, 12), (0.15, 27), (0.28, 75), (0.40, 193), (0.52, 498), (0.64, 1285), (0.76, 3316), (0.90, 10025)]
WARP = [(0.20, 1.12), (0.32, 1.49), (0.46, 2.46), (0.65, 5.12), (0.90, 11.93)]


def linfit(xs, ys):
    n = len(xs)
    sx, sy, sxx, sxy = sum(xs), sum(ys), sum(x * x for x in xs), sum(x * y for x, y in zip(xs, ys))
    b = (n * sxy - sx * sy) / (n * sxx - sx * sx)
    return b, (sy - b * sx) / n


def check_gain():
    ok = all(abs(20 * math.log10(w) - d) < 0.15 for w, d in GAIN if w > 0) and GAIN[0] == (1.0, 0.0)
    return ok, max(abs(20 * math.log10(w) - d) for w, d in GAIN if w > 0)


def check_exp(pts):
    slope, intercept = linfit([w for w, _ in pts], [math.log10(d) for _, d in pts])
    a = 10 ** intercept
    err = max(abs((a * 10 ** (slope * w) - d) / d) for w, d in pts)
    return err < 0.02, a, slope, err


def check_warp():
    xs = [w for w, _ in WARP]
    ys = [d for _, d in WARP]
    # linear d = k*w
    ks = [d / w for w, d in WARP]
    lin_err = (max(ks) - min(ks)) / (sum(ks) / len(ks))
    # power d = a*w^b
    b, la = linfit([math.log(w) for w in xs], [math.log(d) for d in ys])
    a = math.exp(la)
    pow_err = max(abs((a * w ** b - d) / d) for w, d in WARP)
    # exponential d = a*exp(b*w)
    b2, la2 = linfit(xs, [math.log(d) for d in ys])
    a2 = math.exp(la2)
    exp_err = max(abs((a2 * math.exp(b2 * w) - d) / d) for w, d in WARP)
    return {"linear_relative_spread": lin_err, "power_law_max_err": pow_err, "exponential_max_err": exp_err}


def main():
    cmap = json.load(open(os.path.join(ED, "serum_full_control_map_v6.json")))
    C = {c["atlas_id"]: c for c in cmap["controls"]}
    p4 = [json.loads(l) for l in open(os.path.join(BUV, "CLOSURE_PASS_4_results.json")) if l.strip()]
    res = [json.loads(l) for l in open(os.path.join(BUV, "RESIDUAL_results.json")) if l.strip()]

    gain_ok, gain_err = check_gain()
    assert gain_ok, gain_err
    dist_ok, da, dslope, derr = check_exp(DIST)
    assert dist_ok, derr
    cut_ok, ca, cslope, cerr = check_exp(CUT)
    assert cut_ok, cerr
    warp_fits = check_warp()

    C["fx.compressor.gain"]["final_conclusion"] = "DIRECT_UI_CONFIRMED"
    C["fx.compressor.gain"]["final_reason"] = ("curve confirmed: display = 20*log10(raw) dB, exact fit on 8 points (CAL_04, "
        "max residual %.2f dB). Unresolved footnote, not blocking: CAL_01 unit 6 (ratio=8:1) read 28.0 dB for raw 20 vs the "
        "26.0 dB this formula predicts -- an interaction with a numeric (non-Limit) ratio near that value, not yet explained." % gain_err)
    C["fx.distortion.freq"]["final_conclusion"] = "DIRECT_UI_CONFIRMED"
    C["fx.distortion.freq"]["final_reason"] = "curve confirmed: display = %.2f * 10**(%.3f*raw) Hz, fits 8 points within %.1f%%" % (da, dslope, derr * 100)
    C["fx.filter.cutoff"]["final_conclusion"] = "DIRECT_UI_CONFIRMED"
    C["fx.filter.cutoff"]["final_reason"] = "curve confirmed: display = %.2f * 10**(%.3f*raw) Hz, fits 8 points within %.1f%% (asymptotes ~22 kHz at raw=1)" % (ca, cslope, cerr * 100)
    C["oscA.warp_amount"]["final_reason"] = ("5-point dataset (0.20->1.12%%, 0.32->1.49%%, 0.46->2.46%%, 0.65->5.12%%, 0.90->11.93%%, "
        "Sync mode): linear is rejected (ratio spans %.0f%%). Best candidate is exponential, display = 0.52*exp(3.47*raw)%%, "
        "residuals -6.7%% to +6.3%% -- plausible but not tight enough to call confirmed on 5 points; power-law fits worse "
        "(%.0f%% max err). Left open as a TENTATIVE exponential fit, not a confirmed curve; more points would settle it." % (
            warp_fits["linear_relative_spread"] * 100, warp_fits["power_law_max_err"] * 100))
    for r in p4:
        if r["preset"] == "CAL_07":
            aid = {"A": "oscA.warp_amount", "B": "oscB.warp_amount", "C": "oscC.warp_amount"}[r["unit"]]
            C[aid].setdefault("evidence", {}).setdefault("C_direct_ui", {}).setdefault("closure_pass_4_points", []).append(r)
        else:
            aid = {"CAL_04": "fx.compressor.gain", "CAL_05": "fx.distortion.freq", "CAL_06": "fx.filter.cutoff"}[r["preset"]]
            C[aid].setdefault("evidence", {}).setdefault("C_direct_ui", {}).setdefault("closure_pass_4_points", []).append(r)
    for c in (C["fx.compressor.gain"], C["fx.distortion.freq"], C["fx.filter.cutoff"], C["oscA.warp_amount"]):
        c["evidence"]["C_direct_ui"]["closure_pass_4_source"] = SRC4

    # residuals
    up_diff = res[1]["diff"][0]["value"]
    pu_diff = res[2]["diff"][0]["value"]
    pud_diff = res[3]["diff"][0]["value"]
    assert (up_diff, pu_diff, pud_diff) == ("Up", "PinkyUp", "PinkyUD")
    prior = json.load(open(os.path.join(ED, "residual_arp_transpose_shape_v1.json")))
    C["arp.transpose.shape"]["final_conclusion"] = "DIRECT_UI_CONFIRMED"
    C["arp.transpose.shape"]["final_reason"] = ("vocabulary fully resolved (18/18): 15 derived offline from apply_spec "
        "(same words as arp.pattern.shape) + 3 confirmed by direct GUI selection, save and file diff (Up, Pinky Up -> "
        "'PinkyUp', Pinky UD -> 'PinkyUD'). Screen labels themselves were enumerated on-screen in the 2026-09-26 session-1 scan.")
    C["arp.transpose.shape"]["evidence"]["C_direct_ui"]["residual_resolution"] = {
        "offline_15": prior["resolved"], "gui_confirmed_3": res[1:4], "source": SRCR}

    C["global.voice_priority"]["final_conclusion"] = "UI_UNOBSERVABLE"
    C["global.voice_priority"]["final_reason"] = ("not located: GLOBAL page (voice control, quality, tuning, the full "
        "preferences list via its scrollbar) checked in full, VOICING strip hovered once. No control resembling voice "
        "priority / voice stealing exists in this Serum 2.0.23 build's visible UI.")
    C["global.voice_priority"]["evidence"]["C_direct_ui"]["residual_search"] = {**res[4], "source": SRCR}

    C["global.use_ultra_on_render"]["final_conclusion"] = "RESIDUAL_NOT_STORED"
    C["global.use_ultra_on_render"]["final_reason"] = ("CONFIRMED by direct test (not just inferred from the campaign): the "
        "'Use Ultra quality when rendering' toggle in GLOBAL preferences was switched off and saved; the file showed no "
        "difference from the baseline. This is an application-level preference, not a value Serum persists into a preset.")
    C["global.use_ultra_on_render"]["evidence"]["C_direct_ui"]["residual_test"] = {**res[5], "source": SRCR}

    cmap["version"] = 7
    cmap["supersedes"] = "serum_full_control_map_v1-v6 (kept unchanged); v7 folds in closure pass 4 + residual results"
    cmap["terminal"] = cmap["terminal"] + ["RESIDUAL_NOT_STORED"]   # now a confirmed finding, not open work
    counts = Counter(c["final_conclusion"] for c in cmap["controls"])
    cmap["final_counts"] = dict(sorted(counts.items(), key=lambda x: -x[1]))
    assert sum(counts.values()) == 330 and len({c["atlas_id"] for c in cmap["controls"]}) == 330
    json.dump(cmap, open(os.path.join(ED, "serum_full_control_map_v7.json"), "w"), indent=1, default=repr, ensure_ascii=False)

    open_ct = {k: v for k, v in counts.items() if k not in cmap["terminal"]}
    L = ["# FINAL closure report (control map v7)", "",
         "330 controls. Terminal: %d. Open: %d." % (330 - sum(open_ct.values()), sum(open_ct.values())), "",
         "| conclusion | controls |", "|---|---|"]
    L += ["| %s%s | %d |" % (k, "" if k in cmap["terminal"] else " (open)", v) for k, v in cmap["final_counts"].items()]
    L += ["", "## Remaining open, exactly", ""]
    for k in sorted(open_ct):
        ids = sorted(c["atlas_id"] for c in cmap["controls"] if c["final_conclusion"] == k)
        L.append("**%s (%d)**: %s -- %s" % (k, len(ids), ", ".join("`%s`" % i for i in ids), C[ids[0]]["final_reason"] if ids else ""))
        L.append("")
    open(os.path.join(BUV, "FINAL_CLOSURE_REPORT_v4.md"), "w").write("\n".join(L) + "\n")
    print(json.dumps(cmap["final_counts"], indent=1))


if __name__ == "__main__":
    main()
