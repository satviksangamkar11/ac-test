"""CAL_01: one preset that calibrates the compressor's raw->display curves and shows the LFO S&H+Envelope conflict on a
visible LFO tab. Generation only.

    python build_compressor_calibration.py

Why: the BULK session showed the schema's compressor domains do not describe Serum's stored scale (ratio 210/430/31622 all
'Limit'; attack raw 100 -> 1.0 ms while release raw 100 -> 100 ms; thresh/gain nonlinear). One header-row read per unit
gives 8 points per column. All values stay inside the DECLARED domain (nothing out-of-schema is written); ratio points
are concentrated at the low end where BULK showed Serum stops at 'Limit'.
The S&H+Envelope conflict reference sits on LFO1 (the BULK_01 reference on LFO 7 has no UI tab in Serum 2.0.23).
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from bulk_engine import body_get  # noqa: E402
from campaign_derive import leaves as diff_leaves  # noqa: E402
from preset_build import BASE, SPEC0, pack_file, pack_unpack, unpack_file  # noqa: E402
from serum_mcp.generation.spec import FxUnitSpec  # noqa: E402
from serum_mcp.preset.mapping import apply_spec  # noqa: E402
from serum_mcp.preset.packer import SerumPreset  # noqa: E402

OUT = os.path.join(HERE, "giant_verify_out", "bulk_ui_verification")
NAME = "CAL_01_COMPRESSOR_CURVES"
# 8 units; each column strictly increasing so a unit's position in the rack identifies its row
POINTS = {
    "kParamRatio":   [1.0, 1.5, 2.0, 3.0, 4.0, 8.0, 20.0, 100.0],     # BULK: 210 -> Limit; find where it starts
    "kParamAttack":  [0.1, 0.5, 2.0, 5.0, 30.0, 150.0, 500.0, 1000.0],  # tests display = raw/100 ms across the range
    "kParamRelease": [0.1, 1.0, 5.0, 20.0, 50.0, 250.0, 600.0, 1000.0],  # tests display = raw ms (identity) across the range
    "kParamMakeup":  [1.0, 2.0, 3.0, 5.0, 12.0, 20.0, 27.0, 32.0],     # gain: 1..32 declared
    "kParamThresh":  [0.05, 0.15, 0.3, 0.45, 0.6, 0.7, 0.85, 1.0],     # thresh: earlier 0.25/0.4/0.49 excluded
}
ATLAS = {"kParamRatio": "fx.compressor.ratio", "kParamAttack": "fx.compressor.attack", "kParamRelease": "fx.compressor.release",
         "kParamMakeup": "fx.compressor.gain", "kParamThresh": "fx.compressor.thresh"}
DOMAIN = {"kParamRatio": (1.0, 1e6), "kParamAttack": (0.1, 1000.0), "kParamRelease": (0.1, 1000.0), "kParamMakeup": (1.0, 32.0),
          "kParamThresh": (0.0, 1.0)}
LFO_REF = [(["LFO0", "plainParams", "kParamType"], "RandomSH"), (["LFO0", "plainParams", "kParamMode"], "Envelope")]


def main():
    n = len(next(iter(POINTS.values())))
    for k, v in POINTS.items():
        lo, hi = DOMAIN[k]
        assert len(v) == n and all(lo <= x <= hi for x in v) and v == sorted(set(v)), k
    base = apply_spec(BASE.data, SPEC0.model_copy(update={"fx_chain": [FxUnitSpec(type="FXComp", params={}, wet=100.0) for _ in range(n)]}))
    body = copy.deepcopy(base)
    rows, intended = [], []
    for i in range(n):
        pp = body["FXRack0"]["FX"][i]["FXComp"]
        if not isinstance(pp.get("plainParams"), dict):
            pp["plainParams"] = {}
        for k, v in POINTS.items():
            pp["plainParams"][k] = v[i]
            intended.append(json.dumps(["FXRack0", "FX", i, "FXComp", "plainParams", k]))
        rows.append({"unit": i + 1, "rack_slot": i, **{ATLAS[k]: v[i] for k, v in POINTS.items()}})
    for p, v in LFO_REF:
        body["LFO0"]["plainParams"] = body["LFO0"]["plainParams"] if isinstance(body["LFO0"]["plainParams"], dict) else {}
        body["LFO0"]["plainParams"][p[-1]] = v
        intended.append(json.dumps(p))
    path = os.path.join(OUT, NAME + ".SerumPreset")
    pack_file(SerumPreset(metadata=dict(BASE.metadata, presetName=NAME), data=body), path)
    back = unpack_file(path).data
    assert back == pack_unpack(BASE.metadata, body)
    changed = {json.dumps(p) for p, _a, _b in diff_leaves(pack_unpack(BASE.metadata, base), back)}
    assert changed - set(intended) == set(), sorted(changed - set(intended))[:5]
    for i in range(n):
        for k, v in POINTS.items():
            assert body_get(back, ["FXRack0", "FX", i, "FXComp", "plainParams", k]) == v[i]
    assert back["LFO0"]["plainParams"] == {"kParamType": "RandomSH", "kParamMode": "Envelope"}
    json.dump({"preset": NAME + ".SerumPreset", "generated_only": True,
               "read_instructions": "FX page: read the 5-value header row (THRESH | RATIO | ATTACK | RELEASE | GAIN) of each of the 8 "
                                    "COMPRESSOR units top to bottom (use the left FX list to select units; never scroll over knobs). "
                                    "Then LFO 1 tab: expect shape S&H with ENVELOPE greyed out and FREE lit.",
               "units": rows,
               "lfo1_conflict_reference": {"leaves": LFO_REF, "expect": "S&H shown, ENVELOPE greyed, FREE lit"},
               "earlier_points": {"fx.compressor.thresh": {"0.25": "-7.5 dB", "0.4": "-13.3 dB", "0.49": "-17.5 dB"},
                                  "fx.compressor.ratio": {"210": "Limit", "430": "Limit", "31622.78": "Limit"},
                                  "fx.compressor.attack": {"10": "0.1 ms", "22": "0.2 ms", "100": "1.0 ms"},
                                  "fx.compressor.release": {"100": "100.0 ms"},
                                  "fx.compressor.gain": {"8": "23.8 dB", "11": "26.7 dB", "16.5": "30.4 dB"}}},
              open(os.path.join(OUT, NAME + ".controls.json"), "w"), indent=1)
    print("wrote", path, "units", n)


if __name__ == "__main__":
    main()
