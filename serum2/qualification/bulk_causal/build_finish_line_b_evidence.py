"""Assemble Finish Line B live-Serum evidence into one file the promotion builder can consume.

Inputs (all machine-generated against the real Serum 2.0.23 binary, sha256 9293eb90...):
  finish_line_b_probe.jsonl      out-of-range / candidate-key writes -> Serum's own re-saved state (probe_finish_line_b.py)
  finish_line_b_gui_plan.json    every GUI preset's rack slots / domain leaves with Serum readback (gui_prepare_finish_line_b.py)
  finish_line_b_hosttext.json    Serum host-parameter display text at the domain presets (probe_finish_line_b_hosttext.py)
  mcp_exec_finish_line_b_results.jsonl   fresh run_mcp_execution_harness.py rows for the 16 controls
plus GUI_READINGS below: the display text read off the on-screen Serum 2 GUI (Ableton), in rack-slot order, one list
per preset, each backed by the PNGs in parameter_characterization/finish_line_b_gui_evidence/. Slot 1 of every enum
preset is the key left UNSET (Serum's own default). Nothing here is inferred: a mapping exists only where a GUI reading
sits at the same rack slot as a Serum-persisted body key.

    python build_finish_line_b_evidence.py -> parameter_characterization/bulk_causal_evidence/finish_line_b_live_serum_evidence_v1.json
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
BUV = os.path.join(HERE, "giant_verify_out", "bulk_ui_verification")
GUI_DIR = "parameter_characterization/finish_line_b_gui_evidence"
OUT = os.path.join(REPO, "parameter_characterization", "bulk_causal_evidence", "finish_line_b_live_serum_evidence_v1.json")

GUI_READINGS = {
    "FLB_fx_reverb_type_01": ["PLATE", "NITROUS", "HALL", "BASIN", "VINTAGE"],
    "FLB_fx_delay_mode_01": ["NORMAL", "PING-PONG", "TAP->DELAY"],
    "FLB_fx_distortion_type_01": ["TUBE", "ASYM", "DIODE 1", "DIODE 2", "DOWNSAMPLE", "HARDCLIP", "LINEAR FOLD",
                                  "OVERDRIVE", "RECTIFY", "SIN FOLD", "SINE SHAPER", "SOFTCLIP"],
    "FLB_fx_distortion_type_02": ["SOFT SAT.", "STOMP BOX", "TAPE SAT.", "X-SHAPER", "X-SHAPER (ASYM)", "ZERO-SQUARE"],
    "FLB_fx_filter_type_01": ["MG Low 6", "Low 6", "Low 12", "Low 18", "Low 24", "High 6", "High 12", "High 18",
                              "High 24", "Band 12", "Band 24", "Notch 24"],
    "FLB_fx_filter_type_02": ["BN 12", "NN 12", "B/P/N 12", "B/P/N 24", "Bandreject", "Allpasses", "LH 12", "HB 12",
                              "L/B/H 12", "L/B/H 24", "L/N/H 12", "L/N/H 24"],
    "FLB_fx_filter_type_03": ["L/P/H 24", "LN 12", "PP 12", "HP 12", "MG Low 12", "MG Low 18", "MG Low 24",
                              "MG Ladder", "Acid Ladder", "EMS Ladder", "MG Dirty", "Comb 2"],
    "FLB_fx_filter_type_04": ["Cmb -", "Cmb +", "Cmb H6-", "Cmb HL6+", "Dist.Comb 2 LP", "Dist.Comb 2 BP", "Flg -",
                              "Flg +", "FPhs 12HL6+", "Phs 24+", "Phs 36-", "Phs 36+"],
    "FLB_fx_filter_type_05": ["Phs 48H6+", "Phs 48HL6+", "Phs 48+", "Formant-I", "Formant-III", "Formant-II",
                              "DJ Mixer", "Diffusor", "Exp MM", "Exp BPF", "PZ SVF", "Ring Mod"],
    "FLB_fx_filter_type_06": ["Ring Modx2", "Reverb", "French LP", "Scream LP", "Wsp", "Add Bass", "Band EQ 12",
                              "BP 12", "Cmb HL6-", "Cmb L6-", "Combs", "Dist.Comb 1 BP"],
    "FLB_fx_filter_type_07": ["Dist.Comb 1 LP", "Flg H6+", "Flg L6+", "High EQ 12", "HN 12", "LB 12", "Notch 12",
                              "Peak 12", "Flg HL6-", "High EQ 6", "L/P/H 12", "PN 12"],
    "FLB_fx_filter_type_08": ["Phs 12-", "Phs 12+", "SampHold", "German LP", "Scream BP", "Phs 48HL6-", "Phs 48-",
                              "Flg HL6+", "Phs 24-", "Flg L6-", "SampHold-", "Cmb H6+"],
    "FLB_fx_filter_type_09": ["Low EQ 12"],
}

# GUI numeric readings from the GLOBAL page + ARP panel (PrintWindow captures, Serum's own pixels only).
GUI_DOMAIN_READINGS = {
    "FLB_DOMAIN_EXACT_LO": {"file": GUI_DIR + "/FLB_DOMAIN_EXACT_LO_global_arp_decaybox__window.png", "fields": {
        "arp.playback.offset": "-8", "arp.playback.repeats": "inf", "arp.velocity.decay": "0.00",
        "global.oversampling": "Good", "global.voice_control.random.cutoff": "--",
        "global.voice_control.random.detune": "0.0", "global.voice_control.random.envs": "--",
        "global.voice_control.scaling.envs": "10%", "global.voice_control.scaling.lfos": "10%"}},
    "FLB_DOMAIN_EXACT_MID": {"file": GUI_DIR + "/FLB_DOMAIN_EXACT_MID_global_arp_decaybox__window.png", "fields": {
        "arp.playback.offset": "-3", "arp.playback.repeats": "5", "global.oversampling": "Ultra",
        "global.voice_control.random.cutoff": "40%", "global.voice_control.random.detune": "12.0",
        "global.voice_control.random.envs": "80%", "global.voice_control.scaling.envs": "50%",
        "global.voice_control.scaling.lfos": "500%"}},
    "FLB_DOMAIN_MAX": {"file": GUI_DIR + "/FLB_DOMAIN_MAX_global_arp_decay60__window.png", "fields": {
        "arp.playback.offset": "8", "arp.playback.repeats": "16", "arp.velocity.decay": "60.00",
        "global.oversampling": "Ultra", "global.voice_control.random.cutoff": "100%",
        "global.voice_control.random.detune": "20.0", "global.voice_control.random.envs": "100%",
        "global.voice_control.scaling.envs": "1000%", "global.voice_control.scaling.lfos": "1000%"}},
    "FLB_DOMAIN_MIN": {"file": GUI_DIR + "/FLB_DOMAIN_MIN_global_arp_decaybox__window.png", "fields": {
        "arp.playback.offset": "-8", "arp.playback.repeats": "inf", "arp.velocity.decay": "-nan(ind)",
        "global.oversampling": "Good", "global.voice_control.random.cutoff": "--",
        "global.voice_control.random.detune": "0.0", "global.voice_control.random.envs": "--",
        "global.voice_control.scaling.envs": "1000%", "global.voice_control.scaling.lfos": "1000%"}},
}
GUI_DOMAIN_READINGS.update({
    "FLB_OPEN3_A": {"file": GUI_DIR + "/FLB_OPEN3_A__curve_tooltip.png", "fields": {
        "global.portamento_curve": "-100 %", "global.swing_div": "1/2", "global.swing": "25.0%"}},
    "FLB_OPEN3_B": {"file": GUI_DIR + "/FLB_OPEN3_B__curve_tooltip.png", "fields": {
        "global.portamento_curve": "-50 %", "global.swing_div": "1/4", "global.swing": "40.0%"}},
    "FLB_OPEN3_C": {"file": GUI_DIR + "/FLB_OPEN3_C__curve_tooltip.png", "fields": {
        "global.portamento_curve": "50 %", "global.swing_div": "1/64", "global.swing": "60.0%"}},
    "FLB_OPEN3_D": {"file": GUI_DIR + "/FLB_OPEN3_D__curve_tooltip.png", "fields": {
        "global.portamento_curve": "100 %", "global.swing_div": "1/128", "global.swing": "87.5%"}},
})
# GLOBAL-page quality readout for the untouched body (screenshot not retained: it was taken through the screen, which
# the Claude window overlapped; the same value is recorded here only as a cross-check, not as a bound).
GUI_DEFAULT_OBSERVED = {"global.oversampling": "High", "global.voice_control.scaling.envs": "100%",
                        "global.voice_control.scaling.lfos": "100%"}

# Atlas canonical strings are the Atlas's own enum_values; a GUI display maps to one only by case-insensitive equality
# (distortion/reverb/delay), or, for fx.filter.type's category-level enum, only when the GUI name appears verbatim in the
# Atlas category text's own member list.
ATLAS_ENUMS = {
    "fx.distortion.type": ('Tube', 'SoftClip', 'HardClip', 'Diode 1', 'Diode 2', 'Linear Fold', 'Sin Fold',
                           'Zero-Square', 'Downsample', 'Asym', 'Rectify', 'X-Shaper', 'X-Shaper (Asym)',
                           'Sine Shaper', 'Stomp Box', 'Tape Sat.', 'Overdrive', 'Soft Sat.'),
    "fx.reverb.type": ('Plate', 'Hall', 'Vintage', 'Nitrous', 'Basin'),
    "fx.delay.mode": ('Normal', 'Ping-Pong', 'Tap->Delay'),
    "fx.filter.type": ('Normal (18 types: MG Low 6/12/18/24, Low 6/12/18/24, High 6/12/18/24, Band 12/24, '
                       'Peak 12/24, Notch 12/24)', 'Multi', 'Flanges', 'Misc', 'S2 Filters'),
}


def _normal_members(cat):
    """'MG Low 6/12/18/24, Low 6/12/18/24, ...' -> {'MG Low 6', 'MG Low 12', ..., 'Notch 24'}"""
    inner = re.search(r"\((\d+) types: (.*)\)", cat).group(2)
    out = set()
    for part in inner.split(","):
        stem, nums = part.strip().rsplit(" ", 1)
        out |= {"%s %s" % (stem, n) for n in nums.split("/")}
    return out


def atlas_canonical(aid, gui):
    vals = ATLAS_ENUMS[aid]
    if aid == "fx.filter.type":
        return vals[0] if gui in _normal_members(vals[0]) else None
    return next((v for v in vals if v.lower() == gui.lower()), None)


def main():
    plan = json.load(open(os.path.join(BUV, "finish_line_b_gui_plan.json")))
    probe = [json.loads(l) for l in open(os.path.join(BUV, "finish_line_b_probe.jsonl"))]
    host = json.load(open(os.path.join(BUV, "finish_line_b_hosttext.json")))
    sha = probe[0]["serum_sha256"]
    assert plan["serum_sha256"] == sha == host["serum_sha256"]

    enums = {}
    for p in plan["presets"]:
        if "rack_slots" not in p:
            continue
        gui = GUI_READINGS[p["preset"]]
        assert len(gui) == len(p["rack_slots"]), p["preset"]
        shots = sorted(f for f in os.listdir(os.path.join(REPO, GUI_DIR)) if f.startswith(p["preset"] + "__"))
        for s, g in zip(p["rack_slots"], gui):
            assert s["written"] == s["serum_readback"], (p["preset"], s)
            enums.setdefault(p["atlas_id"], []).append({
                "body_key": s["written"], "serum_readback": s["serum_readback"], "gui_display": g,
                "atlas_canonical": atlas_canonical(p["atlas_id"], g), "is_serum_default": s["written"] is None,
                "preset": p["preset"], "rack_slot": s["slot"], "gui_screenshots": [GUI_DIR + "/" + f for f in shots]})
    rejected_keys = {}
    for r in probe[1:]:
        if r["task"] == "enum" and not r.get("persisted_unchanged"):
            rejected_keys.setdefault(r["atlas_id"], []).append({"written": r["written"], "readback": r.get("readback")})

    domain_probe = {}
    for r in probe[1:]:
        if r["task"] == "domain":
            domain_probe.setdefault(r["atlas_id"], []).append({"written": r["written"], "readback": r.get("readback")})

    def gui(aid):
        return {k: v["fields"][aid] for k, v in GUI_DOMAIN_READINGS.items() if aid in v["fields"]}

    open3 = json.load(open(os.path.join(BUV, "finish_line_b_open3_plan.json")))
    assert open3["serum_sha256"] == sha
    for op in open3["presets"]:
        for aid, col, h in (("global.voice_amp", "kParamVoiceAmp", "Amp"), ("global.swing_div", "kParamSwingDiv", "Swing Div")):
            host["presets"].setdefault(op["preset"], {})[h] = op["host_text"][h]
    proof_path = GUI_DIR + "/voice_amp_gui_absence_proof.json"
    proof = json.load(open(os.path.join(REPO, proof_path)))
    assert proof["voice_amp_visible_in_gui"] is False
    H = {"global.swing_div": "Swing Div", "global.voice_amp": "Amp", "global.voice_control.random.cutoff": "Cutoff Rand",
         "global.voice_control.random.detune": "Osc Detune Rnd", "global.voice_control.random.envs": "Env Rand"}
    # min/max = Serum's own clamp of +/-1e6 (state re-save); a readback of None means Serum omitted the leaf because it
    # equals its default, so that side's bound is the default, established by the GUI/host reading at that preset.
    D = {
        "arp.playback.offset": (-8.0, 8.0, 0.0, "GUI_NUMERIC", "GUI -8 / 8 (EXACT_LO, MAX); state clamp -8/8"),
        "arp.playback.repeats": (0.0, 16.0, 0.0, "GUI_NUMERIC", "GUI 'inf' at raw 0 (= Serum default; 0 means infinite) / 16 at MAX; negatives omitted = default 0"),
        "arp.velocity.decay": (0.0, 60.0, 0.0, "GUI_NUMERIC", "GUI type-value box 0.00 (EXACT_LO) / 60.00 (MAX); state clamp max 60, negatives omitted = default 0"),
        "global.oversampling": (0.0, 2.0, 1.0, "GUI_NUMERIC", "GUI Quality Good/High/Ultra at raw 0/1(default)/2; state clamp 0..2"),
        "global.portamento_curve": (-100.0, 100.0, 0.0, "GUI_NUMERIC", "GUI press-and-hold tooltip 'Porta Curve : X %' reads -100 / -50 / 50 / 100 for raw -100 / -50 / 50 / 100 (OPEN3_A..D); state clamp -100..100"),
        "global.swing_div": (0.0, 6.0, 3.0, "GUI_NUMERIC", "GUI keyboard-bar division readout '1/2' (raw 0) / '1/4' (raw 1) / '1/64' (raw 5) / '1/128' (raw 6); host text '1/16' at default raw 3; state clamp 0..6 (discrete: 7 steps)"),
        "global.voice_amp": (0.0, 1.0, 0.5, "HOST_TEXT_NO_GUI_CONTROL", "NO base-value control exists on any page (see gui_absence_proof); the GUI exposes it only as the Matrix destination Global > Amp (matrix_destination_global_amp.png; its OUTPUT tooltip reads the route level 'Mod 1 Out', not Amp's value). Serum host parameter 'Amp' text 0.0000 / 0.2500 / 0.5000 (default) / 0.7500 / 1.0000 and state clamp 0..1 are the only Serum-side readings"),
        "global.voice_control.random.cutoff": (0.0, 100.0, 0.0, "GUI_NUMERIC", "GUI '--' at 0 / 40% / 100%, host text identical"),
        "global.voice_control.random.detune": (0.0, 100.0, 0.0, "GUI_NUMERIC", "GUI 0.0 / 12.0 (raw 60) / 20.0 (raw 100): display = raw/5, host text identical"),
        "global.voice_control.random.envs": (0.0, 100.0, 0.0, "GUI_NUMERIC", "GUI '--' at 0 / 80% / 100%, host text identical"),
        "global.voice_control.scaling.envs": (10.0, 1000.0, 100.0, "GUI_NUMERIC", "GUI 10% (EXACT_LO) / 50% / 100% (default) / 1000% (MAX); state clamp 10..1000"),
        "global.voice_control.scaling.lfos": (10.0, 1000.0, 100.0, "GUI_NUMERIC", "GUI 10% (EXACT_LO) / 500% / 100% (default) / 1000% (MAX); state clamp 10..1000"),
    }
    domains = {aid: {"min": mn, "max": mx, "serum_default": df, "basis": basis, "note": note,
                     "state_clamp_probe": domain_probe[aid], "gui_readings": gui(aid),
                     "gui_default_observed": GUI_DEFAULT_OBSERVED.get(aid),
                     "gui_absence_proof": proof_path if basis == "HOST_TEXT_NO_GUI_CONTROL" else None,
                     "open3_written_and_serum_readback": [
                         {"preset": op["preset"], "written": op["written"], "serum_readback": op["serum_readback"]}
                         for op in open3["presets"]] if aid in ("global.voice_amp", "global.swing_div", "global.portamento_curve") else None,
                     "host_text": {k: v[H[aid]] for k, v in host["presets"].items() if H[aid] in v} if aid in H else None}
               for aid, (mn, mx, df, basis, note) in D.items()}

    findings = [
        {"id": "FLB-F1", "controls": ["arp.velocity.decay", "global.voice_control.scaling.envs", "global.voice_control.scaling.lfos"],
         "finding": "Out-of-range write (-1e6) is clamped differently by the two real Serum load paths: DawDreamer state re-save "
                    "gives default/10.0, but the on-screen GUI (same .SerumPreset file) shows DECAY '-nan(ind)' and SCALING 1000%. "
                    "Values must be written inside the verified domain; out-of-range writes are not safely clamped.",
         "evidence": [GUI_DIR + "/FLB_DOMAIN_MIN_global_arp_decaybox__window.png"]},
        {"id": "FLB-F2", "controls": ["fx.reverb.type", "fx.distortion.type", "fx.filter.type", "fx.delay.mode"],
         "finding": "Each control's Serum default (Plate / Tube / MG Low 6 / Normal) has no persisted body key: writing kPlate/kTube/MgL6/0.0 "
                    "comes back omitted exactly like an invalid key. Selecting the default means leaving the leaf unset."},
        {"id": "FLB-F3", "controls": ["fx.reverb.type"],
         "finding": "Body keys do not match display names: kAbyss -> NITROUS, kSpace -> BASIN (kHall/kVintage match). kPlate/kNitrous/kBasin are not Serum keys."},
        {"id": "FLB-F4", "controls": ["fx.filter.type"],
         "finding": "Atlas enum is category-level (5 strings). Only 'Normal' lists members, so only its 17 keyed members + default map to an Atlas "
                    "value; the other 79 keys have verified GUI names but no Atlas category assignment (needs the GUI dropdown's category grouping). "
                    "Non-obvious names: FormantTWB->Formant-III, FormantTWO->Formant-II, Scream->French LP, ZDF_A->German LP. "
                    "The Atlas lists 'Peak 24' but none of the 96 persisted candidate keys displays as Peak 24."},
        {"id": "FLB-F5", "controls": ["global.voice_amp"],
         "finding": "Voice Amp has no on-screen base-value control: loading amp 0.0 vs 1.0 changes no pixel on any of the 5 top-level pages "
                    "(body + top bar, PrintWindow captures; MAIN knob is unchanged, so it is not Voice Amp). Its bounds come from the Serum host "
                    "parameter 'Amp' text and the state clamp only. Proof: " + proof_path + " (lower ENV/LFO/ARP/keyboard strip excluded; the only "
                    "differences there between A and D are swing/division/curve/porta and leftover ARP state). UI structure cross-checked against "
                    "'Serum 2 What's New.pdf' p4 (pages OSC/MIX/FX/MATRIX/GLOBAL; the top-right MAIN knob is 'Volume' = main volume, unaffected by "
                    "voice_amp) and p15-19. The only GUI appearance of 'Amp' is the Matrix destination list, Global submenu (Main Tuning, Amp, Porta Time, "
                    "Swing, Transpose, Envelope Scaling, LFO Scaling): " + GUI_DIR + "/matrix_destination_global_amp.png."},
        {"id": "FLB-F6", "controls": ["global.swing", "global.swing_div", "global.portamento_curve"],
         "finding": "Swing % clamps 90 -> 87.5 in Serum's own state (GUI shows 87.5%). Swing Div raw 0..6 displays 1/2, 1/4, (1/8, 1/16 default, 1/32 not read), "
                    "1/64, 1/128. Porta Curve is readable on screen by pressing and holding (no drag) the CURVE box: the tooltip shows the value in %."},
    ]
    json.dump({"serum_sha256": sha, "product_version": "2.0.23",
               "sources": ["serum2/qualification/bulk_causal/giant_verify_out/bulk_ui_verification/" + f for f in (
                   "finish_line_b_probe.jsonl", "finish_line_b_gui_plan.json", "finish_line_b_hosttext.json",
                   "finish_line_b_open3_plan.json", "mcp_exec_finish_line_b_results.jsonl")] + [GUI_DIR],
               "domains": domains, "enum_body_keys": enums, "enum_rejected_candidate_keys": rejected_keys,
               "findings": findings}, open(OUT, "w"), indent=1, default=repr)
    print(OUT)
    for aid, rows in enums.items():
        print(aid, len(rows), "slots;", sum(1 for r in rows if r["atlas_canonical"]), "map to an Atlas value")


if __name__ == "__main__":
    main()
