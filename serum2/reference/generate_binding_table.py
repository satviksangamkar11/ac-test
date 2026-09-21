"""Generate serum2/reference/serum_mcp_binding_table.json: the ONLY thing the state pipeline uses to turn an
Atlas canonical control id into a serum-mcp target.

Rules (no fuzzy matching, no prefix matching, no value-domain guessing):
  * instance controls (oscA-C, oscNoise, env1-4, lfo1-6, filter1-2): the control's param must EXACTLY equal a
    serum-mcp PresetSpec field after case/punctuation normalisation (plus the single documented alias
    enabled == enable);
  * fx.<unit>.<param>: <unit> must be in FX_UNIT_TYPES and <param> must EXACTLY equal a catalog kParam after
    normalisation, or be listed in FX_PARAM_ALIASES (reviewed data, per FX type);
  * enum VALUE mappings: exact normalised equality against the serum-mcp domain, or an entry in
    ENUM_VALUE_ALIASES, each of which must cite the evidence that established it.
Anything else has no entry and is therefore UNBOUND at runtime. Run:  python -m serum2.reference.generate_binding_table
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vendor" / "serum-mcp" / "src"))

OUT = Path(__file__).parent / "serum_mcp_binding_table.json"

FX_UNIT_TYPES = {"distortion": "FXDistortion", "hyper": "FXHyperD", "dimension": "FXHyperD", "filter": "FXFilter",
                 "equalizer": "FXEQ", "delay": "FXDelay", "compressor": "FXComp", "convolve": "FXConv",
                 "reverb": "FXReverb", "chorus": "FXChorus", "flanger": "FXFlanger", "phaser": "FXPhaser",
                 "bode": "FXBode"}
# reviewed per-FX-type aliases: Atlas/UI parameter name -> serum-mcp kParam
FX_PARAM_ALIASES = {
    "FXEQ": {"left_freq": "kParamFreq1", "left_gain": "kParamGain1", "left_q": "kParamReso1",
             "right_freq": "kParamFreq2", "right_gain": "kParamGain2", "right_q": "kParamReso2"},
    "FXDistortion": {"type": "kParamMode"},
    "FXComp": {"gain": "kParamMakeup", "thresh": "kParamThresh"},
    "FXDelay": {"bpm": "kParamBeatSync", "time_l": "kParamTimeL", "time_r": "kParamTimeR"},
    "FXHyperD": {"unison": "kParamUnison"},
    "FXFilter": {"type": "kParamType", "cutoff": "kParamFreq", "res": "kParamReso"},
}
SPEC_LISTS = {"osc": ("oscillators", "Oscillator"), "env": ("envelopes", "Env"), "lfo": ("lfos", "LFO"),
              "filter": ("filters", "VoiceFilter")}
INSTANCE = re.compile(r"^(osc|env|lfo|filter)(?:([A-C])|(\d+))\.(.+)$")
SPECIAL_OSC = {"oscNoise": 3, "sub": 4}
FIELD_ALIASES = {"enabled": "enabled", "enable": "enabled"}

# value aliases that exact normalisation cannot express. Each must cite its evidence.
_WT_UI = {"evidence": "ui_readback: Serum 2.0.23 UI displayed 'Default Shapes' as the wavetable name of an oscillator "
                      "written with wavetable=default (2026-09-21, LD - Plucky Lead authorized)"}
ENUM_VALUE_ALIASES = {
    "oscA.wavetable": {"Default Shapes": {"value": "default", **_WT_UI}},
    "oscB.wavetable": {"Default Shapes": {"value": "default", **_WT_UI}},
    "oscC.wavetable": {"Default Shapes": {"value": "default", **_WT_UI}},
    "lfo1.shape": {
        "Chaos: Lorenz": {"value": "lorenz",
                          "evidence": "ui_readback: Serum 2.0.23 UI displayed 'Chaos: Lorenz' in the LFO 1 shape dropdown for an LFO "
                                      "written with shape=lorenz (2026-09-21, LD - Beautiful Plucky Lead)"}},
    "filter1.type": {
        "MG Low 18": {"value": "MgL18",
                      "evidence": "ui_readback: Serum 2.0.23 UI displayed 'MG Low 18' in the Filter 1 panel after loading "
                                  "a preset written with type MgL18 (2026-09-21, LD - Plucky Lead authorized)"},
    },
}


# UI matrix destination label -> serum-mcp MOD_DEST_TARGETS key, generated from these reviewed label tables and kept
# only if the key really exists in serum-mcp's own destination list.
OSC_DEST_LABELS = {"Fine": "fine", "Level": "volume", "Pan": "pan", "Octave": "octave", "Pitch": "pitch"}
FILTER_DEST_LABELS = {"Freq": "cutoff", "Res": "resonance", "Drive": "drive"}
ENV_DEST_LABELS = {"Attack": "attack", "Decay": "decay", "Sustain": "sustain", "Release": "release"}


def route_destinations(dest_keys):
    out = {}
    for i, L in enumerate("ABC"):
        for ui, p in OSC_DEST_LABELS.items():
            if "oscillator%d.%s" % (i, p) in dest_keys:
                out["%s %s" % (L, ui)] = "oscillator%d.%s" % (i, p)
    for ui, p in OSC_DEST_LABELS.items():
        if "oscillator3.%s" % p in dest_keys:
            out["Noise %s" % ui] = "oscillator3.%s" % p
    for n in (1, 2):
        for ui, p in FILTER_DEST_LABELS.items():
            if "filter%d.%s" % (n - 1, p) in dest_keys:
                out["Filter %d %s" % (n, ui)] = "filter%d.%s" % (n - 1, p)
    for n in range(1, 5):
        for ui, p in ENV_DEST_LABELS.items():
            if "env%d.%s" % (n - 1, p) in dest_keys:
                out["Env %d %s" % (n, ui)] = "env%d.%s" % (n - 1, p)
    return out


def norm(s) -> str:
    s = re.sub(r"^kParam", "", str(s))
    if re.match(r"^k[A-Z]", s):
        s = s[1:]
    return re.sub(r"[^a-z0-9]", "", s.lower())


def main():
    from serum_mcp.generation import spec as S
    from serum2.reference.serum_atlas import all_control_ids
    from serum2.producer.state_ledger import catalog
    cat = catalog()
    models = {"osc": S.OscillatorSpec, "env": S.EnvelopeSpec, "lfo": S.LfoSpec, "filter": S.FilterSpec}
    controls, skipped = {}, 0
    for cid in all_control_ids():
        m = INSTANCE.match(cid)
        top = cid.split(".")[0]
        if m or top in SPECIAL_OSC:
            if m:
                kind, letter, num, param = m.groups()
                idx = (ord(letter) - 65) if letter else int(num) - 1
            else:
                kind, idx, param = "osc", SPECIAL_OSC[top], cid.split(".", 1)[1]
            fields = list(models[kind].model_fields)
            want = FIELD_ALIASES.get(param, param)
            hit = [f for f in fields if norm(f) == norm(want)]
            if len(hit) == 1:
                lst, _ = SPEC_LISTS[kind]
                controls[cid] = {"kind": "field", "module": kind, "list": lst, "index": idx, "field": hit[0],
                                 "basis": "exact_normalized" if norm(want) == norm(param) else "alias"}
            else:
                skipped += 1
        elif cid.startswith("fx."):
            unit, _, param = cid[3:].partition(".")
            ftype = FX_UNIT_TYPES.get(unit)
            if not ftype or not param:
                skipped += 1
                continue
            keys = list(cat["fx_params"].get(ftype, {}))
            exact = [k for k in keys if norm(k) == norm(param)]
            alias = FX_PARAM_ALIASES.get(ftype, {}).get(param)
            if len(exact) == 1:
                controls[cid] = {"kind": "fx", "fx_type": ftype, "param": exact[0], "basis": "exact_normalized"}
            elif alias and alias in keys:
                controls[cid] = {"kind": "fx", "fx_type": ftype, "param": alias, "basis": "alias"}
            else:
                skipped += 1
    out = {"version": 1, "generated_by": "serum2/reference/generate_binding_table.py",
           "rules": "exact normalised equality or reviewed alias only; no fuzzy/prefix/value-domain inference",
           "controls": dict(sorted(controls.items())), "value_aliases": ENUM_VALUE_ALIASES,
           "route_destinations": route_destinations(set(__import__("serum_mcp.preset.schema", fromlist=["x"]).MOD_DEST_TARGETS)),
           "unbound_atlas_ids": skipped}
    OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print("bound controls:", len(controls), " atlas ids without an approved binding:", skipped)


if __name__ == "__main__":
    main()
