"""CAL_02_CONTEXTS: the contexts the bulk presets lacked, in one preset. Generation only.

    python build_context_calibration.py

Contexts (why each exists):
  - LFO 1-6 in Hz mode (beat_sync 0): the 10x button and LFO swing only exist in Hz mode (screen: ABSENT in BPM mode; What's New
    p14 '10x Rate: up to 1000 Hz'). swing is written 1.0: the campaign shows Serum stores it as 0/1 (0.25 -> 0.0, 0.5 -> 1.0),
    matching p14 'LFOs can now follow swing' (a toggle).
  - Every oscillator/noise/sub channel routed to the filters AND both filters on: filter balance shows only then (schema
    ROUTING_SLOT_PARAMS note; What's New p16 'Balance Routing'). Balance values are distinct per channel.
  - LFO 6 assigned (mod route lfo5 -> oscillator0.pan) so the LFO 7 tab appears (p14), and LFO 7 carries shape S&H + mode
    Envelope: the native-conflict reference, now actually viewable.
  - random cutoff / random detune / portamento curve at values whose host text is distinct from the default (campaign host
    texts: cutoff 10 -> '10%', detune 10 -> '2.0' i.e. /5, curve 10 -> '10').
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
from serum_mcp.generation.spec import ModRouteSpec  # noqa: E402
from serum_mcp.preset.mapping import apply_spec  # noqa: E402
from serum_mcp.preset.packer import SerumPreset  # noqa: E402

OUT = os.path.join(HERE, "giant_verify_out", "bulk_ui_verification")
NAME = "CAL_02_CONTEXTS"

W = []   # (atlas_id or reference, path, value, expected screen)
for i in range(6):
    W += [("lfo%d.beat_sync" % (i + 1), ["LFO%d" % i, "plainParams", "kParamBeatSync"], 0.0, "Hz shown (BPM off)"),
          ("lfo%d.rate_10x" % (i + 1), ["LFO%d" % i, "plainParams", "kParamRate10x"], 1.0, "10x on"),
          ("lfo%d.swing" % (i + 1), ["LFO%d" % i, "plainParams", "kParamSwing"], 1.0, "swing / follow-swing on")]
for slot, (aid, bal) in enumerate([("mixer.osc_a.filter_balance", 15.0), ("mixer.osc_b.filter_balance", 30.0),
                                   ("mixer.osc_c.filter_balance", 45.0), ("mixer.noise.filter_balance", 70.0),
                                   ("mixer.sub.filter_balance", 85.0)]):
    W += [("context: RoutingSlot%d -> Filter" % slot, ["RoutingSlot%d" % slot, "plainParams", "kParamRoutingDest"], "kRoutingDestFilter", "FILTER"),
          (aid, ["RoutingSlot%d" % slot, "plainParams", "kParamFilterBalance"], bal, "%g (balance)" % bal)]
W += [("context: filter1 on", ["VoiceFilter0", "plainParams", "kParamEnable"], 1.0, "on"),
      ("context: filter2 on", ["VoiceFilter1", "plainParams", "kParamEnable"], 1.0, "on"),
      ("reference: LFO 7 shape", ["LFO6", "plainParams", "kParamType"], "RandomSH", "S&H"),
      ("reference: LFO 7 mode", ["LFO6", "plainParams", "kParamMode"], "Envelope", "ENVELOPE greyed, FREE lit"),
      ("global.voice_control.random.cutoff", ["VoicePanel0", "plainParams", "kParamGlobalRandomFilterCutoff"], 37.0, "37%"),
      ("global.voice_control.random.detune", ["VoicePanel0", "plainParams", "kParamGlobalRandomOscDetune"], 23.0, "4.6"),
      ("global.portamento_curve", ["Global0", "plainParams", "kParamPortamentoCurve"], -37.0, "-37")]


def main():
    base = apply_spec(BASE.data, SPEC0.model_copy(update={"mod_routes": [ModRouteSpec(source="lfo5", destination="oscillator0.pan", amount=10.0)]}))
    body = copy.deepcopy(base)
    for _a, p, v, _e in W:
        body_set(body, p, v)
    path = os.path.join(OUT, NAME + ".SerumPreset")
    pack_file(SerumPreset(metadata=dict(BASE.metadata, presetName=NAME), data=body), path)
    back = unpack_file(path).data
    assert back == pack_unpack(BASE.metadata, body)
    intended = {json.dumps(p) for _a, p, _v, _e in W}
    changed = {json.dumps(p) for p, _x, _y in diff_leaves(pack_unpack(BASE.metadata, base), back)}
    assert changed - intended == set(), sorted(changed - intended)
    for _a, p, v, _e in W:
        assert body_get(back, p) == v, (p, v, body_get(back, p))
    mods = [k for k in back if k.startswith("ModSlot")]
    assert mods, "LFO 6 mod route missing"
    rows = [{"control": a, "raw_path": p, "value": v, "expect_on_screen": e} for a, p, v, e in W]
    json.dump({"preset": NAME + ".SerumPreset", "generated_only": True, "mod_route": {"slot": mods[0], "plainParams": back[mods[0]]["plainParams"]},
               "read_order": ["LFO 1-6 tabs: Hz shown (not BPM), 10x lit, swing/follow-swing on (hover each)",
                              "LFO 7 tab (now visible because LFO 6 is assigned): S&H, ENVELOPE greyed, FREE lit",
                              "MIX page: each channel routed to FILTER; hover the balance control of A, B, C, Noise, Sub",
                              "GLOBAL page: random cutoff, random detune, portamento curve"],
               "rows": rows}, open(os.path.join(OUT, NAME + ".controls.json"), "w"), indent=1)
    print("wrote", path, "rows", len(rows), "mod route", mods[0])


if __name__ == "__main__":
    main()
