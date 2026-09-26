"""CAL_03_FILTER_BALANCE: the one thing CAL_02 got wrong -- B/C/noise/sub were routed to the filters but left disabled,
so their balance knobs were dimmed. This preset enables all 5 channels too. Generation only.

    python build_filter_balance_calibration.py
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
from serum_mcp.preset.mapping import apply_spec  # noqa: E402
from serum_mcp.preset.packer import SerumPreset  # noqa: E402

OUT = os.path.join(HERE, "giant_verify_out", "bulk_ui_verification")
NAME = "CAL_03_FILTER_BALANCE"

W = []
for slot, osc, bal in [(0, "Oscillator0", 12.0), (1, "Oscillator1", 34.0), (2, "Oscillator2", 56.0),
                       (3, "Oscillator3", 78.0), (4, "Oscillator4", 90.0)]:
    W += [("enable " + osc, [osc, "plainParams", "kParamEnable"], 1.0),
          ("route RoutingSlot%d" % slot, ["RoutingSlot%d" % slot, "plainParams", "kParamRoutingDest"], "kRoutingDestFilter"),
          ("balance RoutingSlot%d" % slot, ["RoutingSlot%d" % slot, "plainParams", "kParamFilterBalance"], bal)]
W += [("filter1 on", ["VoiceFilter0", "plainParams", "kParamEnable"], 1.0),
      ("filter2 on", ["VoiceFilter1", "plainParams", "kParamEnable"], 1.0)]
LABELS = {"mixer.osc_a.filter_balance": 12.0, "mixer.osc_b.filter_balance": 34.0, "mixer.osc_c.filter_balance": 56.0,
          "mixer.noise.filter_balance": 78.0, "mixer.sub.filter_balance": 90.0}


def main():
    base = apply_spec(BASE.data, SPEC0)
    body = copy.deepcopy(base)
    for _n, p, v in W:
        body_set(body, p, v)
    path = os.path.join(OUT, NAME + ".SerumPreset")
    pack_file(SerumPreset(metadata=dict(BASE.metadata, presetName=NAME), data=body), path)
    back = unpack_file(path).data
    assert back == pack_unpack(BASE.metadata, body)
    intended = {json.dumps(p) for _n, p, _v in W}
    changed = {json.dumps(p) for p, _x, _y in diff_leaves(pack_unpack(BASE.metadata, base), back)}
    assert changed - intended == set(), sorted(changed - intended)
    for _n, p, v in W:
        assert body_get(back, p) == v
    json.dump({"preset": NAME + ".SerumPreset", "generated_only": True, "expect": LABELS}, open(os.path.join(OUT, NAME + ".controls.json"), "w"), indent=1)
    print("wrote", path)


if __name__ == "__main__":
    main()
