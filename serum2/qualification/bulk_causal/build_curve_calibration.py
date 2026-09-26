"""3 presets to close the last 4 open display curves: compressor gain, distortion freq, filter cutoff, warp amount
(Sync mode). Generation only.

    python build_curve_calibration.py

Each FX preset holds 8 units of ONE type, matching CAL_01's proven pattern (8 compressors loaded and read fine).
Only the target column varies; everything else is a safe, non-Limit, non-edge value so the header stays readable.
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from bulk_engine import body_get, body_set  # noqa: E402
from campaign_derive import leaves as diff_leaves  # noqa: E402
from preset_build import BASE, SPEC0, pack_file, pack_unpack, unpack_file  # noqa: E402
from serum_mcp.generation.spec import FxUnitSpec  # noqa: E402
from serum_mcp.preset.mapping import apply_spec  # noqa: E402
from serum_mcp.preset.packer import SerumPreset  # noqa: E402

OUT = os.path.join(HERE, "giant_verify_out", "bulk_ui_verification")

GAIN_PTS = [1.0, 4.0, 7.0, 11.0, 15.0, 18.0, 23.0, 30.0]     # dense 11-23 to localize where the +6dB offset starts
FREQ_PTS = [0.05, 0.15, 0.28, 0.40, 0.52, 0.64, 0.76, 0.90]  # spread across the whole 0..1 range
SYNC_PTS = [0.10, 0.20, 0.35, 0.50, 0.65, 0.80, 0.90, 0.99]  # oscA only (a single control, one preset can't give 8 at once
                                                              # -- see NOTE); still 8 points via 8 loads is too slow, so
                                                              # this reuses 3 oscillator slots + rides prior 2 known points


def build_fx(name, fxtype, param, pts, extra):
    base = apply_spec(BASE.data, SPEC0.model_copy(update={"fx_chain": [FxUnitSpec(type=fxtype, params={}, wet=100.0) for _ in pts]}))
    body = copy.deepcopy(base)
    rows = []
    for i, v in enumerate(pts):
        pp = body["FXRack0"]["FX"][i][fxtype]
        if not isinstance(pp.get("plainParams"), dict):
            pp["plainParams"] = {}
        pp["plainParams"][param] = v
        for k, ev in extra.items():
            pp["plainParams"][k] = ev
        rows.append({"unit": i + 1, "raw": v})
    path = os.path.join(OUT, name + ".SerumPreset")
    pack_file(SerumPreset(metadata=dict(BASE.metadata, presetName=name), data=body), path)
    back = unpack_file(path).data
    assert back == pack_unpack(BASE.metadata, body)
    intended = {json.dumps(["FXRack0", "FX", i, fxtype, "plainParams", k]) for i in range(len(pts)) for k in [param, *extra]}
    changed = {json.dumps(p) for p, _a, _b in diff_leaves(pack_unpack(BASE.metadata, base), back)}
    assert changed - intended == set(), (name, sorted(changed - intended))
    for i, v in enumerate(pts):
        assert body_get(back, ["FXRack0", "FX", i, fxtype, "plainParams", param]) == v
    json.dump({"preset": name + ".SerumPreset", "generated_only": True, "target_control": param, "rows": rows},
              open(os.path.join(OUT, name + ".controls.json"), "w"), indent=1)
    print("wrote", path)


def build_warp():
    """oscA/B/C, Sync mode, 3 NEW points (0.20, 0.65, 0.90) -- combined with the 2 already screen-read (0.32->1.49,
    0.46->2.46) that's 5 points total for the curve fit, without a 6th oscillator to burn on repeats."""
    name = "CAL_07_WARP_SYNC"
    base = apply_spec(BASE.data, SPEC0)   # INIT default: oscillators A/B/C already enabled, wavetable mode
    body = copy.deepcopy(base)
    pts = {0: 0.20, 1: 0.65, 2: 0.90}
    for i, v in pts.items():
        wt = body["Oscillator%d" % i]["WTOsc%d" % i]
        if not isinstance(wt.get("plainParams"), dict):
            wt["plainParams"] = {}
        wt["plainParams"]["kParamWarpMenu"] = "kSync"
        wt["plainParams"]["kParamWarp"] = v
    path = os.path.join(OUT, name + ".SerumPreset")
    pack_file(SerumPreset(metadata=dict(BASE.metadata, presetName=name), data=body), path)
    back = unpack_file(path).data
    assert back == pack_unpack(BASE.metadata, body)
    intended = {json.dumps(["Oscillator%d" % i, "WTOsc%d" % i, "plainParams", k]) for i in pts for k in ("kParamWarpMenu", "kParamWarp")}
    changed = {json.dumps(p) for p, _a, _b in diff_leaves(pack_unpack(BASE.metadata, base), back)}
    assert changed - intended == set(), sorted(changed - intended)
    for i, v in pts.items():
        assert body_get(back, ["Oscillator%d" % i, "WTOsc%d" % i, "plainParams", "kParamWarp"]) == v
    json.dump({"preset": name + ".SerumPreset", "generated_only": True, "target_control": "oscA/B/C.warp_amount (mode=Sync)",
               "rows": [{"osc": "ABC"[i], "raw": v} for i, v in pts.items()],
               "prior_points_already_screen_read": [{"raw": 0.32, "screen": "1.49"}, {"raw": 0.46, "screen": "2.46"}]},
              open(os.path.join(OUT, name + ".controls.json"), "w"), indent=1)
    print("wrote", path)


def main():
    build_fx("CAL_04_COMPRESSOR_GAIN", "FXComp", "kParamMakeup", GAIN_PTS,
             {"kParamRatio": 4.0, "kParamThresh": 0.5, "kParamAttack": 50.0, "kParamRelease": 200.0})  # safe, non-Limit
    build_fx("CAL_05_DISTORTION_FREQ", "FXDistortion", "kParamFreq", FREQ_PTS, {})
    build_fx("CAL_06_FILTER_CUTOFF", "FXFilter", "kParamFreq", FREQ_PTS, {})
    build_warp()


if __name__ == "__main__":
    main()
