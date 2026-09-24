"""Read-only evidence survey: for every FX Atlas control that is UNKNOWN on the MCP surface (excluding module identities),
find the candidate raw kParam and record what independent evidence exists. It binds NOTHING.

Evidence sources (each recorded per control): schema.FX_PARAMS (upstream catalogue), the Serum2.vst3 binary's own
kParam* strings, and a survey of real .SerumPreset files (which FX module's plainParams carry the key, and how often).
Tiers (no tier is a qualification; T5/NOT_A_PARAM are never binding candidates):
  T1_RULE_GAP        exact-normalised name == schema-catalogued key; blocked only by a missing FX unit prefix rule
  T2_EXACT_UNCATALOGUED  exact-normalised name == a real raw key (corpus+binary) that FX_PARAMS does not list
  T3_STRONG          alias, but the key is the unique remaining one in its module AND real in corpus/binary AND
                     corroborated (tooltip internal name, value range, or co-occurrence)
  T4_WEAK            a key exists but is ambiguous, or never seen in that module's corpus
  T5_NO_KEY          no candidate raw key found anywhere
  NOT_A_PARAM        menu/graph/structural/absence (no scalar kParam by nature)
Run: python -m serum2.reference.fx_candidate_key_evidence [extra_preset_dir ...]
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "vendor" / "serum-mcp" / "src"))

OUT = ROOT / "parameter_characterization" / "fx_candidate_key_evidence.json"
CENSUS = ROOT / "parameter_characterization" / "host_surface_census.json"
SURFACE = ROOT / "parameter_characterization" / "serum_mcp_mutable_surface.json"
DEFAULT_CORPUS = [os.path.expanduser("~/Documents/Xfer"), str(ROOT)]

# cid -> (fx_type, kparam|None, tier, evidence/gap note). Reviewed data, one row per control.
C = {}
def add(tier, fx, rows):
    for cid, key, note in rows:
        C["fx." + cid] = (fx, key, tier, note)

add("T1_RULE_GAP", "FXUtils", [("utility.hpf", "kParamHPF", "exact; 'utility' missing from FX_UNIT_TYPES"),
    ("utility.lpf", "kParamLPF", "exact; unit rule missing"), ("utility.width", "kParamWidth", "exact; unit rule missing"),
    ("utility.wet", "kParamWet", "exact; unit rule missing (Atlas label 'Mix')")])
for cid, fx, key in [("bode.mono_input", "FXBode", "kParamMonoInput"), ("chorus.delay2", "FXChorus", "kParamDelay2"),
                     ("phaser.depth2", "FXPhaser", "kParamDepth2"), ("convolve.attack", "FXConv", "kParamAttack"),
                     ("convolve.min_phase", "FXConv", "kParamMinPhase"), ("hyper.retrig", "FXHyperD", "kParamRetrig")]:
    C["fx." + cid] = (fx, key, "T2_EXACT_UNCATALOGUED", "exact-normalised to a real key absent from FX_PARAMS; mapping.py writes it via allow_unknown")
add("T3_STRONG", "FXComp", [
    ("compressor.mode", "kParamMultiband", "raw 'Multiband'==UI MULTIBAND; only ever 1.0 (absent==SINGLE); multiband-only keys co-occur (XoverLow 89/100 with it) -- value 1.0==MULTIBAND is inferred"),
    ("compressor.below", "kParamRatioBelow", "Serum tooltip internal name 'Comp RatioB'"),
    ("compressor.x_low", "kParamXoverLow", "X-LOW crossover; co-occurs with Multiband 89/100"),
    ("compressor.x_high", "kParamXoverHi", "X-HIGH crossover; co-occurs with Multiband 70/80")])
add("T4_WEAK", "FXComp", [("compressor.band_l", "kParamGain0", "per-band gain keys Gain0/1/2 exist; which index is L/M/H is unproven"),
    ("compressor.band_m", "kParamGain1", "index<->band order unproven"), ("compressor.band_h", "kParamGain2", "index<->band order unproven")])
add("T3_STRONG", "FXDistortion", [
    ("distortion.filter_position", "kParamPrePost", "filter keys (BW/Freq/LPHP) present ~10x more often when PrePost is present (BW 166/178 vs 40/291) => absent==OFF; which of 1.0/2.0 is PRE vs POST is UNPROVEN"),
    ("distortion.q", "kParamBW", "unique remaining filter key; 206 units; Atlas 'Q -- filter resonance'")])
add("T3_STRONG", "FXEQ", [
    ("equalizer.left_type", "kParamType1", "Freq1==left (existing alias); Type1=2.0 has median Freq1 119Hz and Gain1 present in 29% (HP: gain moot) vs Type1=1.0 Gain1 85% (Peak); absent==Shelf inferred"),
    ("equalizer.right_type", "kParamType2", "Type2=2.0 median Freq2 8.8kHz, Gain2 present 30% (LP) vs Type2=1.0 89% (Peak); absent==Shelf inferred")])
add("T3_STRONG", "FXBode", [("bode.bpm", "kParamBeatSync", "tooltip 'Bode BPM: delay time synced'; precedent fx.delay.bpm->kParamBeatSync"),
    ("bode.delay", "kParamDelayTime", "unique delay-time key (seconds)"), ("bode.feed", "kParamFeedback", "unique feedback key"),
    ("bode.shift_retrig", "kParamRetrig", "only Retrig key in Bode; 9 units, 1.0")])
add("T4_WEAK", "FXBode", [("bode.width", "kParamOutputWidth", "OutputWidth vs 'Width -- stereo width': plausible, unproven"),
    ("bode.balance", "kParamOutputMix", "ambiguous: kParamOutputMix (-100..100) vs kParamDelayBalance")])
add("T5_NO_KEY", "FXBode", [("bode.dir", None, "kParamDirection is in the binary but never in a Bode unit")])
add("T3_STRONG", "FXChorus", [("chorus.bpm", "kParamBeatSync", "rate sync; precedent"), ("chorus.delay1", "kParamDelay", "unsuffixed==first; kParamDelay/kParamDelay2 pair (57 units carry both)"),
    ("chorus.filter_cutoff", "kParamFilt", "unique filter freq key (50..20000Hz)"),
    ("chorus.filter_mode", "kParamFiltMode", "17/17 units carrying it also carry Filt; value 1.0==HPF vs LPF is UNPROVEN")])
add("T3_STRONG", "FXConv", [("convolve.damp", "kParamDamping", "unique damping key"), ("convolve.ir_gain", "kParamIpTrim", "remaining key after Size/Decay/Tone/Damping/Attack/Predelay; 'Ip'=IR trim inferred"),
    ("convolve.pre_dly", "kParamPredelay", "Conv spells it 'Predelay' (Reverb: 'PreDelay')"), ("convolve.bpm", "kParamPredelayBeatSync", "UI 'pre-delay sync toggle'")])
add("T3_STRONG", "FXDelay", [("delay.high_quality", "kParamHQ", "schema key; corpus has explicit 0.0 => default is ON"),
    ("delay.q", "kParamBW", "unique remaining tone-filter key alongside Freq; 450/505 units")])
add("T3_STRONG", "FXFilter", [("filter.fat", "kParamVar", "shared filter engine: voice filter kParamVar is bound as filter1.var"),
    ("filter.pan", "kParamStereo", "shared engine; kParamStereo 50==centre matches Pan")])
add("T4_WEAK", "FXFilter", [("filter.key_track", "kParamKeyTrack", "in binary + voice filter, never in an FXFilter unit in the corpus")])
add("T3_STRONG", "FXFlanger", [("flanger.bpm", "kParamBeatSync", "rate sync; precedent"), ("flanger.phase", "kParamWidth", "only remaining key; 0..360 deg, default 180")])
add("T3_STRONG", "FXPhaser", [("phaser.bpm", "kParamBeatSync", "rate sync; precedent"), ("phaser.phase", "kParamWidth", "only remaining key (degrees)"),
    ("phaser.poles", "kParamNumPoles", "schema key 1..18 'number of allpass stages'")])
add("T3_STRONG", "FXUtils", [("utility.mono_bass", "kParamLFMono", "'LF Mono'; 75 units, 1.0"), ("utility.freq", "kParamLFXover", "Mono Bass threshold; LFXover"),
    ("utility.pan", "kParamBalance", "only remaining key; -100..100"),
    ("utility.polarity_inv_l", "kParamPolarityL", "tooltip internal name 'Utils Polarity L'"), ("utility.polarity_inv_r", "kParamPolarityR", "L/R pair")])
add("T3_STRONG", "FXSplit", [("splitter_lh.split_freq", "kParamFreq", "schema note: crossover band1/band2; tooltip 'Split Freq'")])
add("T3_STRONG", "FXSplit3", [("splitter_lmh.split_freq_low_mid", "kParamFreq", "tooltip internal name 'Split3 Freq'"), ("splitter_lmh.split_freq_mid_high", "kParamFreq2", "kParamFreq2 crossover band2/band3")])
for cid, fx, key in [("splitter_lh.lows_bypass", "FXSplit", "kParamBand1Bypass"), ("splitter_lh.highs_bypass", "FXSplit", "kParamBand2Bypass"),
                     ("splitter_lmh.lows_bypass", "FXSplit3", "kParamBand1Bypass"), ("splitter_lmh.mids_bypass", "FXSplit3", "kParamBand2Bypass"),
                     ("splitter_lmh.highs_bypass", "FXSplit3", "kParamBand3Bypass")]:
    C["fx." + cid] = (fx, key, "T4_WEAK", "key is in the binary; never in a corpus FX unit; band index order by convention only")
add("T5_NO_KEY", None, [("splitter_lh.wet", "", "FXSplit has no Wet in schema or corpus"), ("splitter_lmh.wet", "", "no Wet key"),
    ("splitter_ms.wet", "", "Atlas confirms no Mix knob exists"), ("splitter_ms.mid_bypass", "", "no bypass key seen for FXSplitMS"), ("splitter_ms.side_bypass", "", "same"),
    ("splitter_lh.lows_select", "", "tab selector (UI state)"), ("splitter_lh.highs_select", "", "tab selector (UI state)")])
add("T4_WEAK", "FXReverb", [("reverb.pre_dly", "kParamPreDelay", "ambiguous with kParamDelay (ms, 419 units) -- both look like pre-delay"),
    ("reverb.feedback_nitrous_basin", "kParamFeedback", "type-conditional; raw type enum has 4 (Hall/Vintage/Abyss/Space) vs 5 UI types"),
    ("reverb.width_plate", "kParamWidth", "type-conditional (Plate not in raw type enum)"), ("reverb.damp_vintage", "kParamDamping", "1 corpus unit"),
    ("reverb.diff_a_vintage", "kParamDiffA", "1 corpus unit"), ("reverb.diff_b_vintage", "kParamDiffB", "1 corpus unit"), ("reverb.decay_hall", "kParamDecay", "1 corpus unit")])
add("T5_NO_KEY", "FXReverb", [("reverb.chorus_mod", None, "Rate/Depth pair; no Rate/Depth key in any FXReverb unit"), ("reverb.spin_hall", None, "same"),
    ("reverb.hi_cut", None, "candidates kParamFreq/kParamFreqB unproven"), ("reverb.lo_cut", None, "same"), ("reverb.damp_plate", None, "none"),
    ("reverb.diffusion_nitrous", None, "none"), ("reverb.er_size_vintage", None, "none"),
    ("reverb.mode_nitrous", None, "kParamMode is continuous (0..100) in corpus, contradicting a 5-way dropdown")])
add("T3_STRONG", "*", [("sys.module_bypass", "kParamEnable", "present in every FX type, only ever 0.0 (== bypassed); not per-type: generic per-unit key")])
for cid in ("equalizer.level",):
    C["fx." + cid] = ("FXEQ", None, "NOT_A_PARAM", "Atlas: confirmed absent control")
for cid in ("sys.add_fx_menu", "sys.module_context_menu", "sys.module_param_context_menu", "sys.rack_preset_browser", "sys.racks", "sys.module_list_panel"):
    C["fx." + cid] = (None, None, "NOT_A_PARAM", "menu/browser/rack topology")


def _binary_keys():
    p = Path(json.loads(CENSUS.read_text())["serum_vst3_path"])
    f = p if p.is_file() else next(p.glob("Contents/*/*.vst3"))
    return {m.group().decode() for m in re.finditer(rb"kParam[A-Za-z0-9_]+", f.read_bytes())}


def _survey(dirs):
    from serum_mcp.preset import schema
    from serum_mcp.preset.packer import unpack_file
    units, keys = collections.Counter(), collections.defaultdict(collections.Counter)
    seen = set()
    for d in dirs:
        for f in glob.glob(os.path.join(d, "**", "*.SerumPreset"), recursive=True):
            if f in seen:
                continue
            seen.add(f)
            try:
                data = unpack_file(f).data
            except Exception:
                continue
            for r in range(3):
                rack = data.get(f"FXRack{r}")
                for e in (rack.get("FX") or []) if isinstance(rack, dict) else []:
                    t = schema.FX_TYPE_IDS.get(e.get("type")) if isinstance(e, dict) else None
                    pp = (e.get(t) or {}).get("plainParams") if t else None
                    if isinstance(pp, dict):
                        units[t] += 1
                        keys[t].update(pp.keys())
    return len(seen), units, keys


def main(argv):
    from serum2.producer.state_ledger import catalog
    schema_keys = catalog()["fx_params"]
    binary = _binary_keys()
    presets, units, keys = _survey(DEFAULT_CORPUS + argv)
    unknown = {k for k, v in json.loads(SURFACE.read_text())["not_mcp_mutable"].items() if k.startswith("fx.") and v["status"] == "UNKNOWN"}
    rows = {}
    for cid, (fx, key, tier, note) in sorted(C.items()):
        if cid not in unknown and cid != "fx.filter.type":
            continue
        n = None if not key else (sum(keys[t][key] for t in keys) if fx == "*" else keys[fx][key])
        rows[cid] = {"fx_type": fx, "candidate_kparam": key or None, "tier": tier, "in_schema_FX_PARAMS": bool(key and fx in schema_keys and key in schema_keys[fx]),
                     "in_serum_binary": bool(key and key in binary), "corpus_units_with_key": n,
                     "corpus_units_of_type": None if fx in (None, "*") else units[fx], "evidence_or_gap": note}
    covered = set(rows)
    tiers = collections.Counter(r["tier"] for r in rows.values())
    res = {"binds_nothing": True, "corpus_presets": presets, "corpus_units_by_type": dict(units), "tiers": dict(tiers),
           "unknown_fx_controls_not_reviewed": sorted(c for c in unknown if c not in covered and not c.startswith("fx.fx")
                                                      and c not in ("fx.sys.reorder", "fx.hyper_dimension.structure")
                                                      and not re.match(r"fx\.splitter_\w+\.(structure|\w+_rack)$", c)),
           "controls": rows}
    OUT.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(presets, dict(tiers), "unreviewed:", res["unknown_fx_controls_not_reviewed"])


if __name__ == "__main__":
    main(sys.argv[1:])
