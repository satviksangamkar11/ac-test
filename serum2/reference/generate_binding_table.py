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
# unit-scoped overrides: FX_UNIT_TYPES maps BOTH "hyper" and "dimension" to
# the single FXHyperD module (schema.FX_PARAMS['FXHyperD'] confirms it's one
# combined DSP unit with 6 kParams), but the live-UI audit for these two
# Atlas control families independently observed them as separate on-screen
# controls ("Dimension section... MIX knob... independent from Hyper's own
# MIX" / "distinct from Dimension's separate MIX"). Plain exact-normalized
# matching collapses fx.dimension.wet onto the same kParamWet as fx.hyper.wet
# (norm() only sees "wet"), which is wrong: the schema separately catalogs
# kParamDimESize/kParamDimEWet for Dimension's own controls. This table
# disambiguates by (fx_type, unit) BEFORE the generic exact match runs --
# checked here, not invented as a new matching algorithm.
FX_UNIT_PARAM_ALIASES = {
    ("FXHyperD", "dimension"): {"wet": "kParamDimEWet", "size": "kParamDimESize"},
}
SPEC_LISTS = {"osc": ("oscillators", "Oscillator"), "env": ("envelopes", "Env"), "lfo": ("lfos", "LFO"),
              "filter": ("filters", "VoiceFilter"), "macro": ("macros", "Macro")}
INSTANCE = re.compile(r"^(osc|env|lfo|filter|macro)(?:([A-C])|(\d+))\.(.+)$")
SPECIAL_OSC = {"oscNoise": 3, "sub": 4}
FIELD_ALIASES = {"enabled": "enabled", "enable": "enabled",
                 "bus1": "fx_bus1_send", "bus2": "fx_bus2_send"}
# mixer.<slot>.<param>: the Atlas's OWN mixer-panel identity for oscillator/
# filter fields that either don't ALSO have an oscA./filter1.-style id (e.g.
# fx_bus1_send/fx_bus2_send have no such duplicate) or do (filter_balance,
# pan) without colliding, since they resolve to the identical PresetSpec
# list entry either way. Same (kind, list, index) shape as the INSTANCE
# regex below -- just a second Atlas namespace pointing at the same slots.
MIXER_SLOTS = {
    "osc_a": ("osc", 0), "osc_b": ("osc", 1), "osc_c": ("osc", 2),
    "noise": ("osc", 3), "sub": ("osc", 4),
    "filter1": ("filter", 0), "filter2": ("filter", 1),
}

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
    models = {"osc": S.OscillatorSpec, "env": S.EnvelopeSpec, "lfo": S.LfoSpec, "filter": S.FilterSpec,
              "macro": S.MacroSpec}
    # Singleton (non-list, no numbered slot) PresetSpec objects. "global"
    # and "voice.voicing" BOTH target GlobalSpec -- confirmed by reading the
    # Atlas's own control_ids (voice.voicing.legato/mono/porta_* match
    # GlobalSpec field names exactly, not VoiceUnisonSpec, despite the
    # panel name suggesting otherwise). "global_" is PresetSpec's actual
    # Python attribute (a leading underscore-free "global" is a keyword).
    SINGLETON_SPECS = {
        "global": ("global_", S.GlobalSpec),
        "voice.voicing": ("global_", S.GlobalSpec),
        "arp": ("arp", S.ArpSpec),
        # More specific than the bare "arp" prefix above (longest-prefix-match
        # picks these first): the Atlas's "arp.pattern.*"/"arp.global.*"
        # sub-namespaces still target the SAME singleton ArpSpec object, just
        # with an extra UI-grouping segment ("pattern"/"global") that isn't
        # part of any ArpSpec field name and must be stripped before matching
        # (e.g. arp.pattern.rate -> ArpSpec.rate, not a field literally named
        # "pattern.rate").
        "arp.pattern": ("arp", S.ArpSpec),
        "arp.global": ("arp", S.ArpSpec),
        "arp.playback": ("arp", S.ArpSpec),
        "arp.retrigger": ("arp", S.ArpSpec),
        "arp.velocity": ("arp", S.ArpSpec),
        # VoiceUnisonSpec's scalar (non-per-voice-list) fields. Traced through
        # mapping.py's spec.voice_unison block: random_pan/random_detune/
        # random_filter_cutoff/random_env_time map 1:1 to the Atlas's own
        # "RANDOM column (4 rows: PAN/DETUNE/CUTOFF/ENVS) in GLOBAL's Voice
        # Control panel" -- and scaling_env_time/scaling_lfo_time to the
        # Atlas's SCALING row entries (tooltip-confirmed "Envelope Scaling"/
        # "LFO Scaling"). The per-voice LIST fields (pan/detune/filter_cutoff/
        # env_time/mod1/mod2, the Atlas's "seq" column) and affects_osc_*
        # (the Atlas's single combined "osc_scope" multi-toggle) are
        # deliberately NOT here -- they don't fit a scalar accessor.
        "global.voice_control.random": ("voice_unison", S.VoiceUnisonSpec),
        "global.voice_control.scaling": ("voice_unison", S.VoiceUnisonSpec),
    }
    # (prefix, atlas_param) -> real PresetSpec field name. Each pair is
    # independently established by the Atlas's own recorded evidence (the
    # exact row/column grouping documented in its notes), not guessed:
    # random.cutoff/envs and scaling.envs/lfos don't exact-normalize to
    # their VoiceUnisonSpec field names (filter_cutoff/env_time) but the
    # Atlas's own "4 rows: PAN/DETUNE/CUTOFF/ENVS" grouping is the same
    # RANDOM column VoiceUnisonSpec's own docstring describes.
    SINGLETON_FIELD_ALIASES = {
        # ALL FOUR random.* entries are explicit, not just cutoff/envs:
        # VoiceUnisonSpec ALSO has per-voice-list fields literally named
        # "pan"/"detune" -- bare exact-normalized matching on "pan"/"detune"
        # would silently hit those wrong (structural) fields instead of the
        # scalar random_pan/random_detune this Atlas entry actually means.
        # Caught live: the first version of this table let "pan"/"detune"
        # fall through to bare matching and got exactly that collision.
        ("global.voice_control.random", "pan"): "random_pan",
        ("global.voice_control.random", "detune"): "random_detune",
        ("global.voice_control.random", "cutoff"): "random_filter_cutoff",
        ("global.voice_control.random", "envs"): "random_env_time",
        ("global.voice_control.scaling", "envs"): "scaling_env_time",
        ("global.voice_control.scaling", "lfos"): "scaling_lfo_time",
        # scaling.lfos_rate_toggle deliberately NOT aliased to
        # scaling_lfo_time_snap: the Atlas's own note records it as an
        # untoggled read-only observation with no evidence pinning it to
        # that specific field vs. e.g. a %/RATE display-mode switch --
        # left unbound rather than guessed.

        # ArpSpec: arp.retrigger.*/arp.velocity.* are two more Atlas
        # sub-namespaces (like global.voice_control.random/scaling above)
        # whose tail words are shortened relative to their ArpSpec field
        # names -- each alias here is the field CONTEXTUALIZED by its own
        # Atlas sub-namespace prefix (e.g. "retrigger.first" unambiguously
        # means ArpSpec.first_note_retrig, not some other "first"), not a
        # blind global rename.
        ("arp.retrigger", "first"): "first_note_retrig",
        ("arp.retrigger", "launch"): "launch_retrig",
        ("arp.retrigger", "note"): "note_retrig",
        ("arp.velocity", "decay"): "velo_decay",
        ("arp.velocity", "enable"): "velo_enabled",
        ("arp.velocity", "retrig"): "velo_retrig",
        ("arp.velocity", "target"): "velo_target",
        # arp.retrigger.rate_enable / rate_value deliberately NOT aliased:
        # ArpSpec has ONE field (retrig_rate, Optional[float]) that plausibly
        # corresponds to a checkbox+spinner UI pair, but binding BOTH Atlas
        # ids to the same field would be ambiguous (which one does an
        # edit_preset write actually mean?) -- left unbound rather than
        # guessed which of the two "owns" the value.
    }
    controls, skipped = {}, 0
    for cid in all_control_ids():
        singleton_prefix = next((p for p in sorted(SINGLETON_SPECS, key=len, reverse=True)
                                 if cid == p or cid.startswith(p + ".")), None)
        m = None if singleton_prefix else INSTANCE.match(cid)
        top = cid.split(".")[0]
        if singleton_prefix:
            attr, model = SINGLETON_SPECS[singleton_prefix]
            param = cid[len(singleton_prefix) + 1:]
            fields = list(model.model_fields)
            want = SINGLETON_FIELD_ALIASES.get((singleton_prefix, param), FIELD_ALIASES.get(param, param))
            hit = [f for f in fields if norm(f) == norm(want)]
            if len(hit) == 1:
                controls[cid] = {"kind": "singleton_field", "attr": attr, "field": hit[0],
                                 "basis": "exact_normalized" if norm(want) == norm(param) else "alias"}
            else:
                skipped += 1
        elif m or top in SPECIAL_OSC:
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
        elif cid.startswith("mixer.") and any(cid.startswith("mixer.%s." % s) for s in MIXER_SLOTS):
            slot, _, param = cid[len("mixer."):].partition(".")
            kind, idx = MIXER_SLOTS[slot]
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
            unit_alias = FX_UNIT_PARAM_ALIASES.get((ftype, unit), {}).get(param)
            exact = [k for k in keys if norm(k) == norm(param)]
            alias = FX_PARAM_ALIASES.get(ftype, {}).get(param)
            if unit_alias and unit_alias in keys:
                controls[cid] = {"kind": "fx", "fx_type": ftype, "param": unit_alias, "basis": "alias"}
            elif len(exact) == 1:
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
