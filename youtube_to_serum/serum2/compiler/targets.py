"""16.5.4: Semantic target resolution.

SemanticTargetRef is a dumb alias only: name -> capability_key.
No structural knowledge, no RequiredContext, no admission decision.

RequiredContext derivation is entirely delegated to context.py via
extract_required_context(). This module does not reimplement it.

Resolution chain:
  "FXEQ.Freq1"
    -> SemanticTargetRef   (SEMANTIC_TARGETS lookup)
    -> CapabilityContract  (contracts lookup by c.target == capability_key)
    -> RequiredContext      (context.extract_required_context on contract's path)
    -> concrete path       (RequiredContext.resolve_index(body))

SEMANTIC_TARGETS carries no index knowledge. An index here would be a layering
violation: list positions are body-state details, never vocabulary.
"""
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from . import context as ctx_mod

CONTEXT_NOT_SATISFIED = "CONTEXT_NOT_SATISFIED"
UNKNOWN_SEMANTIC_TARGET = "UNKNOWN_SEMANTIC_TARGET"
CAPABILITY_NOT_FOUND = "CAPABILITY_NOT_FOUND"


@dataclass(frozen=True)
class SemanticTargetRef:
    name: str
    capability_key: str


@dataclass(frozen=True)
class ResolvedTarget:
    ref: SemanticTargetRef
    contract: Any  # CapabilityContract -- Any avoids a circular import


@dataclass(frozen=True)
class TargetRefusal:
    reason: str
    detail: str


# Vocabulary only. No index, no path, no structural knowledge.
SEMANTIC_TARGETS: Dict[str, SemanticTargetRef] = {
    "FXEQ.Freq1":        SemanticTargetRef("FXEQ.Freq1",        "fx_field_eq_freq1"),
    "FXEQ.Freq2":        SemanticTargetRef("FXEQ.Freq2",        "fx_field_eq_freq2"),
    "FXEQ.Reso1":        SemanticTargetRef("FXEQ.Reso1",        "fx_field_eq_kParamReso1"),
    "FXEQ.Reso2":        SemanticTargetRef("FXEQ.Reso2",        "fx_field_eq_kParamReso2"),
    "FXEQ.Gain1":        SemanticTargetRef("FXEQ.Gain1",        "fx_field_eq_kParamGain1"),
    "FXEQ.Gain2":        SemanticTargetRef("FXEQ.Gain2",        "fx_field_eq_kParamGain2"),
    "FXEQ.LevelOut":     SemanticTargetRef("FXEQ.LevelOut",     "fx_field_eq_level_out"),
    "FXDistortion.Drive": SemanticTargetRef("FXDistortion.Drive", "fx_field_dist_drive"),
    # Oscillator (OSC1/OSC2/OSC3 + SUB)
    "SUB.Enable":         SemanticTargetRef("SUB.Enable",         "oscillator_field_SUB-ENABLE"),
    "SUB.Octave":         SemanticTargetRef("SUB.Octave",         "oscillator_field_SUB-OCTAVE"),
    "SUB.Volume":         SemanticTargetRef("SUB.Volume",         "oscillator_field_SUB-VOLUME"),
    "SUB.Level":          SemanticTargetRef("SUB.Level",          "sub_plain_param_level"),
    "SUB.Pan":            SemanticTargetRef("SUB.Pan",            "sub_plain_param_pan"),
    "SUB.BUS1Send":       SemanticTargetRef("SUB.BUS1Send",       "routing_slot4_bus1_level"),
    "SUB.BUS2Send":       SemanticTargetRef("SUB.BUS2Send",       "routing_slot4_bus2_level"),
    "SUB.Route":          SemanticTargetRef("SUB.Route",          "routing_slot4_dest"),
    "SUB.Detune":         SemanticTargetRef("SUB.Detune",         "oscillator_field_SUB-DETUNE"),
    "SUB.Warp":           SemanticTargetRef("SUB.Warp",           "oscillator_field_SUB-WARP"),

    "OSC1.Enable":        SemanticTargetRef("OSC1.Enable",        "oscillator_field_OSC1-ENABLE"),
    "OSC1.Octave":        SemanticTargetRef("OSC1.Octave",        "oscillator_field_OSC1-OCTAVE"),
    "OSC1.Volume":        SemanticTargetRef("OSC1.Volume",        "oscillator_field_OSC1-VOLUME"),
    "OSC1.Level":         SemanticTargetRef("OSC1.Level",         "osc1_plain_param_level"),
    "OSC1.Pan":           SemanticTargetRef("OSC1.Pan",           "osc1_plain_param_pan"),
    "OSC1.BUS1Send":      SemanticTargetRef("OSC1.BUS1Send",      "routing_slot0_bus1_level"),
    "OSC1.BUS2Send":      SemanticTargetRef("OSC1.BUS2Send",      "routing_slot0_bus2_level"),
    "OSC1.Route":         SemanticTargetRef("OSC1.Route",         "routing_slot0_dest"),
    "OSC1.Detune":        SemanticTargetRef("OSC1.Detune",        "oscillator_field_OSC1-DETUNE"),
    "OSC1.Wavetable":     SemanticTargetRef("OSC1.Wavetable",     "oscillator_field_OSC1-WAVETABLE"),
    "OSC1.Warp":          SemanticTargetRef("OSC1.Warp",          "oscillator_field_OSC1-WARP"),

    "OSC2.Octave":        SemanticTargetRef("OSC2.Octave",        "oscillator_field_OSC2-OCTAVE"),
    "OSC2.Volume":        SemanticTargetRef("OSC2.Volume",        "oscillator_field_OSC2-VOLUME"),
    "OSC2.Level":         SemanticTargetRef("OSC2.Level",         "osc2_plain_param_level"),
    "OSC2.Pan":           SemanticTargetRef("OSC2.Pan",           "osc2_plain_param_pan"),
    "OSC2.BUS1Send":      SemanticTargetRef("OSC2.BUS1Send",      "routing_slot1_bus1_level"),
    "OSC2.BUS2Send":      SemanticTargetRef("OSC2.BUS2Send",      "routing_slot1_bus2_level"),
    "OSC2.Route":         SemanticTargetRef("OSC2.Route",         "routing_slot1_dest"),
    "OSC2.Detune":        SemanticTargetRef("OSC2.Detune",        "oscillator_field_OSC2-DETUNE"),
    "OSC2.Warp":          SemanticTargetRef("OSC2.Warp",          "oscillator_field_OSC2-WARP"),

    "OSC3.Octave":        SemanticTargetRef("OSC3.Octave",        "oscillator_field_OSC3-OCTAVE"),
    "OSC3.Volume":        SemanticTargetRef("OSC3.Volume",        "oscillator_field_OSC3-VOLUME"),
    "OSC3.Level":         SemanticTargetRef("OSC3.Level",         "osc3_plain_param_level"),
    "OSC3.Pan":           SemanticTargetRef("OSC3.Pan",           "osc3_plain_param_pan"),
    "OSC3.BUS1Send":      SemanticTargetRef("OSC3.BUS1Send",      "routing_slot2_bus1_level"),
    "OSC3.BUS2Send":      SemanticTargetRef("OSC3.BUS2Send",      "routing_slot2_bus2_level"),
    "OSC3.Route":         SemanticTargetRef("OSC3.Route",         "routing_slot2_dest"),
    "OSC3.Detune":        SemanticTargetRef("OSC3.Detune",        "oscillator_field_OSC3-DETUNE"),
    "OSC3.Warp":          SemanticTargetRef("OSC3.Warp",          "oscillator_field_OSC3-WARP"),

    "NOISE.Volume":       SemanticTargetRef("NOISE.Volume",       "oscillator_field_NOISE-VOLUME"),
    "NOISE.Level":        SemanticTargetRef("NOISE.Level",        "noise_plain_param_level"),
    "NOISE.Pan":          SemanticTargetRef("NOISE.Pan",          "noise_plain_param_pan"),
    "NOISE.BUS1Send":     SemanticTargetRef("NOISE.BUS1Send",     "routing_slot3_bus1_level"),
    "NOISE.BUS2Send":     SemanticTargetRef("NOISE.BUS2Send",     "routing_slot3_bus2_level"),
    "NOISE.Route":        SemanticTargetRef("NOISE.Route",        "routing_slot3_dest"),
    "NOISE.Warp":         SemanticTargetRef("NOISE.Warp",         "oscillator_field_NOISE-WARP"),
    "NOISE.Type":         SemanticTargetRef("NOISE.Type",         "oscillator_field_NOISE-TYPE"),
    # Filter
    "Filter.Resonance":   SemanticTargetRef("Filter.Resonance",   "filter_field_reso"),
    "Filter.Type":        SemanticTargetRef("Filter.Type",        "filter_field_type"),
    "FILTER1.BUS1Send":   SemanticTargetRef("FILTER1.BUS1Send",   "routing_slot5_bus1_level"),
    "FILTER1.BUS2Send":   SemanticTargetRef("FILTER1.BUS2Send",   "routing_slot5_bus2_level"),
    "FILTER1.Route":      SemanticTargetRef("FILTER1.Route",      "routing_slot5_dest"),
    "FILTER2.BUS1Send":   SemanticTargetRef("FILTER2.BUS1Send",   "routing_slot6_bus1_level"),
    "FILTER2.BUS2Send":   SemanticTargetRef("FILTER2.BUS2Send",   "routing_slot6_bus2_level"),
    "FILTER2.Route":      SemanticTargetRef("FILTER2.Route",      "routing_slot6_dest"),
    # STEP 20B PART 4: Filter Level/Mix (VoiceFilter, distinct from Oscillator.plainParams)
    "FILTER1.Level":      SemanticTargetRef("FILTER1.Level",      "voicefilter0_plain_param_level_out"),
    "FILTER1.Mix":        SemanticTargetRef("FILTER1.Mix",        "voicefilter0_plain_param_wet"),
    "FILTER2.Level":      SemanticTargetRef("FILTER2.Level",      "voicefilter1_plain_param_level_out"),
    "FILTER2.Mix":        SemanticTargetRef("FILTER2.Mix",        "voicefilter1_plain_param_wet"),
    # BUS master volumes (Global0) — the bus channel's own overall level, distinct from per-source sends
    "BUS1.Level":         SemanticTargetRef("BUS1.Level",         "global_plain_param_fx_bus1_vol"),
    "BUS2.Level":         SemanticTargetRef("BUS2.Level",         "global_plain_param_fx_bus2_vol"),
    # Envelope
    "Env1.Attack":        SemanticTargetRef("Env1.Attack",        "envelope_field_attack"),
    "Env1.Decay":         SemanticTargetRef("Env1.Decay",         "envelope_field_decay"),
    "Env1.Release":       SemanticTargetRef("Env1.Release",       "envelope_field_release"),
    "Env1.Sustain":       SemanticTargetRef("Env1.Sustain",       "envelope_field_sustain"),
    # Filter (extended)
    "Filter.Cutoff":       SemanticTargetRef("Filter.Cutoff",       "filter_field_cutoff"),
    "Filter.Drive":        SemanticTargetRef("Filter.Drive",        "filter_field_drive"),
    "Filter.Q":            SemanticTargetRef("Filter.Q",            "filter_field_q"),
    "Filter2.Cutoff":      SemanticTargetRef("Filter2.Cutoff",      "filter2_field_cutoff"),
    "Filter2.Resonance":   SemanticTargetRef("Filter2.Resonance",   "filter2_field_reso"),
    "Filter2.Type":        SemanticTargetRef("Filter2.Type",        "filter2_field_type"),
    "Filter2.Drive":       SemanticTargetRef("Filter2.Drive",       "filter2_field_drive"),
    "Filter2.Q":           SemanticTargetRef("Filter2.Q",           "filter2_field_q"),
    # Envelope (extended)
    "Env2.Attack":         SemanticTargetRef("Env2.Attack",         "envelope2_field_attack"),
    "Env2.Decay":          SemanticTargetRef("Env2.Decay",          "envelope2_field_decay"),
    "Env2.Sustain":        SemanticTargetRef("Env2.Sustain",        "envelope2_field_sustain"),
    "Env2.Release":        SemanticTargetRef("Env2.Release",        "envelope2_field_release"),
    "Env3.Attack":         SemanticTargetRef("Env3.Attack",         "envelope3_field_attack"),
    "Env3.Decay":          SemanticTargetRef("Env3.Decay",          "envelope3_field_decay"),
    "Env3.Sustain":        SemanticTargetRef("Env3.Sustain",        "envelope3_field_sustain"),
    "Env3.Release":        SemanticTargetRef("Env3.Release",        "envelope3_field_release"),
    "Env4.Attack":         SemanticTargetRef("Env4.Attack",         "envelope4_field_attack"),
    "Env4.Decay":          SemanticTargetRef("Env4.Decay",          "envelope4_field_decay"),
    "Env4.Sustain":        SemanticTargetRef("Env4.Sustain",        "envelope4_field_sustain"),
    "Env4.Release":        SemanticTargetRef("Env4.Release",        "envelope4_field_release"),
    # Global (extended)
    "Global.MasterVolume": SemanticTargetRef("Global.MasterVolume", "global_field_mastervolume"),
    "Global.Transpose":    SemanticTargetRef("Global.Transpose",    "global_field_transpose"),
    "Global.Tuning":       SemanticTargetRef("Global.Tuning",       "global_field_tuning"),
    "Global.Quality":      SemanticTargetRef("Global.Quality",      "global_field_quality"),
    "Global.Swing":        SemanticTargetRef("Global.Swing",        "global_field_swing"),
    "Global.Scale":        SemanticTargetRef("Global.Scale",        "global_field_scale"),
    "Global.Key":          SemanticTargetRef("Global.Key",          "global_field_key"),
    "Global.Portamento":   SemanticTargetRef("Global.Portamento",   "global_field_portamento"),
    "Global.Glide":        SemanticTargetRef("Global.Glide",        "global_field_glide"),
    "Global.Mono":         SemanticTargetRef("Global.Mono",         "global_field_mono"),
    "Global.Voicing":      SemanticTargetRef("Global.Voicing",      "global_field_voicing"),
    "Global.VelocityCurve": SemanticTargetRef("Global.VelocityCurve", "global_field_velocity_curve"),
    # LFO 0-9 (Phase 8D expansion)
    "LFO0.Rate":           SemanticTargetRef("LFO0.Rate",           "lfo_field_lfo0_rate"),
    "LFO0.Shape":          SemanticTargetRef("LFO0.Shape",          "lfo_field_lfo0_shape"),
    "LFO0.Mode":           SemanticTargetRef("LFO0.Mode",           "lfo_field_lfo0_mode"),
    "LFO0.Phase":          SemanticTargetRef("LFO0.Phase",          "lfo_field_lfo0_phase"),
    "LFO0.Retrigger":      SemanticTargetRef("LFO0.Retrigger",      "lfo_field_lfo0_retrigger"),
    "LFO1.Rate":           SemanticTargetRef("LFO1.Rate",           "lfo_field_lfo1_rate"),
    "LFO1.Shape":          SemanticTargetRef("LFO1.Shape",          "lfo_field_lfo1_shape"),
    "LFO1.Mode":           SemanticTargetRef("LFO1.Mode",           "lfo_field_lfo1_mode"),
    "LFO1.Phase":          SemanticTargetRef("LFO1.Phase",          "lfo_field_lfo1_phase"),
    "LFO1.Retrigger":      SemanticTargetRef("LFO1.Retrigger",      "lfo_field_lfo1_retrigger"),
    "LFO2.Rate":           SemanticTargetRef("LFO2.Rate",           "lfo_field_lfo2_rate"),
    "LFO2.Shape":          SemanticTargetRef("LFO2.Shape",          "lfo_field_lfo2_shape"),
    "LFO2.Mode":           SemanticTargetRef("LFO2.Mode",           "lfo_field_lfo2_mode"),
    "LFO2.Phase":          SemanticTargetRef("LFO2.Phase",          "lfo_field_lfo2_phase"),
    "LFO2.Retrigger":      SemanticTargetRef("LFO2.Retrigger",      "lfo_field_lfo2_retrigger"),
    "LFO3.Rate":           SemanticTargetRef("LFO3.Rate",           "lfo_field_lfo3_rate"),
    "LFO3.Shape":          SemanticTargetRef("LFO3.Shape",          "lfo_field_lfo3_shape"),
    "LFO3.Mode":           SemanticTargetRef("LFO3.Mode",           "lfo_field_lfo3_mode"),
    "LFO3.Phase":          SemanticTargetRef("LFO3.Phase",          "lfo_field_lfo3_phase"),
    "LFO3.Retrigger":      SemanticTargetRef("LFO3.Retrigger",      "lfo_field_lfo3_retrigger"),
    "LFO4.Rate":           SemanticTargetRef("LFO4.Rate",           "lfo_field_lfo4_rate"),
    "LFO4.Shape":          SemanticTargetRef("LFO4.Shape",          "lfo_field_lfo4_shape"),
    "LFO4.Mode":           SemanticTargetRef("LFO4.Mode",           "lfo_field_lfo4_mode"),
    "LFO4.Phase":          SemanticTargetRef("LFO4.Phase",          "lfo_field_lfo4_phase"),
    "LFO4.Retrigger":      SemanticTargetRef("LFO4.Retrigger",      "lfo_field_lfo4_retrigger"),
    "LFO5.Rate":           SemanticTargetRef("LFO5.Rate",           "lfo_field_lfo5_rate"),
    "LFO5.Shape":          SemanticTargetRef("LFO5.Shape",          "lfo_field_lfo5_shape"),
    "LFO5.Mode":           SemanticTargetRef("LFO5.Mode",           "lfo_field_lfo5_mode"),
    "LFO5.Phase":          SemanticTargetRef("LFO5.Phase",          "lfo_field_lfo5_phase"),
    "LFO5.Retrigger":      SemanticTargetRef("LFO5.Retrigger",      "lfo_field_lfo5_retrigger"),
    "LFO6.Rate":           SemanticTargetRef("LFO6.Rate",           "lfo_field_lfo6_rate"),
    "LFO6.Shape":          SemanticTargetRef("LFO6.Shape",          "lfo_field_lfo6_shape"),
    "LFO6.Mode":           SemanticTargetRef("LFO6.Mode",           "lfo_field_lfo6_mode"),
    "LFO6.Phase":          SemanticTargetRef("LFO6.Phase",          "lfo_field_lfo6_phase"),
    "LFO6.Retrigger":      SemanticTargetRef("LFO6.Retrigger",      "lfo_field_lfo6_retrigger"),
    "LFO7.Rate":           SemanticTargetRef("LFO7.Rate",           "lfo_field_lfo7_rate"),
    "LFO7.Shape":          SemanticTargetRef("LFO7.Shape",          "lfo_field_lfo7_shape"),
    "LFO7.Mode":           SemanticTargetRef("LFO7.Mode",           "lfo_field_lfo7_mode"),
    "LFO7.Phase":          SemanticTargetRef("LFO7.Phase",          "lfo_field_lfo7_phase"),
    "LFO7.Retrigger":      SemanticTargetRef("LFO7.Retrigger",      "lfo_field_lfo7_retrigger"),
    "LFO8.Rate":           SemanticTargetRef("LFO8.Rate",           "lfo_field_lfo8_rate"),
    "LFO8.Shape":          SemanticTargetRef("LFO8.Shape",          "lfo_field_lfo8_shape"),
    "LFO8.Mode":           SemanticTargetRef("LFO8.Mode",           "lfo_field_lfo8_mode"),
    "LFO8.Phase":          SemanticTargetRef("LFO8.Phase",          "lfo_field_lfo8_phase"),
    "LFO8.Retrigger":      SemanticTargetRef("LFO8.Retrigger",      "lfo_field_lfo8_retrigger"),
    "LFO9.Rate":           SemanticTargetRef("LFO9.Rate",           "lfo_field_lfo9_rate"),
    "LFO9.Shape":          SemanticTargetRef("LFO9.Shape",          "lfo_field_lfo9_shape"),
    "LFO9.Mode":           SemanticTargetRef("LFO9.Mode",           "lfo_field_lfo9_mode"),
    "LFO9.Phase":          SemanticTargetRef("LFO9.Phase",          "lfo_field_lfo9_phase"),
    "LFO9.Retrigger":      SemanticTargetRef("LFO9.Retrigger",      "lfo_field_lfo9_retrigger"),
    # Additional FX effects (Phase 8A expansion)
    "FXDistortion.Tone":   SemanticTargetRef("FXDistortion.Tone",   "fx_field_dist_tone"),
    "FXDistortion.LevelOut": SemanticTargetRef("FXDistortion.LevelOut", "fx_field_dist_level_out"),
    "FXDelay.Time":        SemanticTargetRef("FXDelay.Time",        "fx_field_delay_time"),
    "FXDelay.Feedback":    SemanticTargetRef("FXDelay.Feedback",    "fx_field_delay_feedback"),
    "FXDelay.Mix":         SemanticTargetRef("FXDelay.Mix",         "fx_field_delay_mix"),
    "FXReverb.Time":       SemanticTargetRef("FXReverb.Time",       "fx_field_reverb_time"),
    "FXReverb.Damping":    SemanticTargetRef("FXReverb.Damping",    "fx_field_reverb_damping"),
    "FXReverb.Mix":        SemanticTargetRef("FXReverb.Mix",        "fx_field_reverb_mix"),
    "FXCompressor.Threshold": SemanticTargetRef("FXCompressor.Threshold", "fx_field_comp_threshold"),
    "FXCompressor.Ratio":  SemanticTargetRef("FXCompressor.Ratio",  "fx_field_comp_ratio"),
    "FXCompressor.Attack": SemanticTargetRef("FXCompressor.Attack", "fx_field_comp_attack"),
    "FXCompressor.Release": SemanticTargetRef("FXCompressor.Release", "fx_field_comp_release"),
    "FXChorus.Rate":       SemanticTargetRef("FXChorus.Rate",       "fx_field_chorus_rate"),
    "FXChorus.Depth":      SemanticTargetRef("FXChorus.Depth",      "fx_field_chorus_depth"),
    "FXChorus.Mix":        SemanticTargetRef("FXChorus.Mix",        "fx_field_chorus_mix"),
    # Additional FX (BODE, FLANGER, PHASER, UTILITY, etc.)
    "FXBODE.Frequency":    SemanticTargetRef("FXBODE.Frequency",    "fx_field_bode_frequency"),
    "FXBODE.Range":        SemanticTargetRef("FXBODE.Range",        "fx_field_bode_range"),
    "FXBODE.Direction":    SemanticTargetRef("FXBODE.Direction",    "fx_field_bode_direction"),
    "FXBODE.Mix":          SemanticTargetRef("FXBODE.Mix",          "fx_field_bode_mix"),
    "FXFlanger.Rate":      SemanticTargetRef("FXFlanger.Rate",      "fx_field_flanger_rate"),
    "FXFlanger.Depth":     SemanticTargetRef("FXFlanger.Depth",     "fx_field_flanger_depth"),
    "FXFlanger.Feedback":  SemanticTargetRef("FXFlanger.Feedback",  "fx_field_flanger_feedback"),
    "FXFlanger.Phase":     SemanticTargetRef("FXFlanger.Phase",     "fx_field_flanger_phase"),
    "FXFlanger.Mix":       SemanticTargetRef("FXFlanger.Mix",       "fx_field_flanger_mix"),
    "FXPhaser.Frequency":  SemanticTargetRef("FXPhaser.Frequency",  "fx_field_phaser_frequency"),
    "FXPhaser.Feedback":   SemanticTargetRef("FXPhaser.Feedback",   "fx_field_phaser_feedback"),
    "FXPhaser.Phase":      SemanticTargetRef("FXPhaser.Phase",      "fx_field_phaser_phase"),
    "FXPhaser.Mix":        SemanticTargetRef("FXPhaser.Mix",        "fx_field_phaser_mix"),
    "FXUtility.Gain":      SemanticTargetRef("FXUtility.Gain",      "fx_field_utility_gain"),
    "FXUtility.Phase":     SemanticTargetRef("FXUtility.Phase",     "fx_field_utility_phase"),
    "FXUtility.Mono":      SemanticTargetRef("FXUtility.Mono",      "fx_field_utility_mono"),
    "FXUtility.Mix":       SemanticTargetRef("FXUtility.Mix",       "fx_field_utility_mix"),
    "FXConvolve.IR":       SemanticTargetRef("FXConvolve.IR",       "fx_field_convolve_ir"),
    "FXConvolve.IRGain":   SemanticTargetRef("FXConvolve.IRGain",   "fx_field_convolve_ir_gain"),
    "FXConvolve.Attack":   SemanticTargetRef("FXConvolve.Attack",   "fx_field_convolve_attack"),
    "FXConvolve.Decay":    SemanticTargetRef("FXConvolve.Decay",    "fx_field_convolve_decay"),
    "FXConvolve.Damping":  SemanticTargetRef("FXConvolve.Damping",  "fx_field_convolve_damping"),
    "FXConvolve.Mix":      SemanticTargetRef("FXConvolve.Mix",      "fx_field_convolve_mix"),
    "FXHyper.Rate":        SemanticTargetRef("FXHyper.Rate",        "fx_field_hyper_rate"),
    "FXHyper.Unison":      SemanticTargetRef("FXHyper.Unison",      "fx_field_hyper_unison"),
    "FXHyper.Detune":      SemanticTargetRef("FXHyper.Detune",      "fx_field_hyper_detune"),
    "FXHyper.Mix":         SemanticTargetRef("FXHyper.Mix",         "fx_field_hyper_mix"),
    "FXFilterFX.Type":     SemanticTargetRef("FXFilterFX.Type",     "fx_field_filter_fx_type"),
    "FXFilterFX.Cutoff":   SemanticTargetRef("FXFilterFX.Cutoff",   "fx_field_filter_fx_cutoff"),
    "FXFilterFX.Resonance": SemanticTargetRef("FXFilterFX.Resonance", "fx_field_filter_fx_resonance"),
    "FXFilterFX.Drive":    SemanticTargetRef("FXFilterFX.Drive",    "fx_field_filter_fx_drive"),
    "FXFilterFX.Mix":      SemanticTargetRef("FXFilterFX.Mix",      "fx_field_filter_fx_mix"),
    # Matrix operations (Phase 8B — represented via semantic names; actual operations are compound)
    "ModRoute.Curve":      SemanticTargetRef("ModRoute.Curve",      "mod_field_route_curve"),
    "ModRoute.Bipolar":    SemanticTargetRef("ModRoute.Bipolar",    "mod_field_route_bipolar"),
    "ModRoute.AuxSource":  SemanticTargetRef("ModRoute.AuxSource",  "mod_field_route_aux_source"),
    "ModRoute.Bypass":     SemanticTargetRef("ModRoute.Bypass",     "mod_field_route_bypass"),
    "ModRoute.MacroDepth": SemanticTargetRef("ModRoute.MacroDepth", "mod_field_route_macro_depth"),
    # Phase 9B: Module activation controls
    "OSC2.Enable":         SemanticTargetRef("OSC2.Enable",         "oscillator_field_OSC2-ENABLE"),
    "OSC3.Enable":         SemanticTargetRef("OSC3.Enable",         "oscillator_field_OSC3-ENABLE"),
    "Filter.Enable":       SemanticTargetRef("Filter.Enable",       "filter_field_ENABLE"),
    "Filter2.Enable":      SemanticTargetRef("Filter2.Enable",      "filter2_field_ENABLE"),
    # Phase 9B: Global controls
    "Global.PitchTracking": SemanticTargetRef("Global.PitchTracking", "global_field_pitch_tracking"),
    # Phase 9B: Oscillator-specific (NOISE fine tuning)
    "NOISE.Fine":          SemanticTargetRef("NOISE.Fine",          "oscillator_field_NOISE-FINE"),
    # Phase 9B: ARP control
    "ARP.Enable":          SemanticTargetRef("ARP.Enable",          "arp_field_ENABLE"),

    # =========================================================================
    # PHASE FX-FULL: Complete FX parameter coverage (14 effect types)
    # =========================================================================

    # BODE (Frequency Shifter)
    "FXBODE.Shift":        SemanticTargetRef("FXBODE.Shift",        "fx_field_bode_shift"),
    "FXBODE.Range":        SemanticTargetRef("FXBODE.Range",        "fx_field_bode_range"),
    "FXBODE.Direction":    SemanticTargetRef("FXBODE.Direction",    "fx_field_bode_direction"),
    "FXBODE.LevelOut":     SemanticTargetRef("FXBODE.LevelOut",     "fx_field_bode_level_out"),
    "FXBODE.MixOrGain":    SemanticTargetRef("FXBODE.MixOrGain",    "fx_field_bode_mix_or_gain"),

    # CHORUS
    "FXChorus.Rate":       SemanticTargetRef("FXChorus.Rate",       "fx_field_chorus_rate"),
    "FXChorus.Depth":      SemanticTargetRef("FXChorus.Depth",      "fx_field_chorus_depth"),
    "FXChorus.Feedback":   SemanticTargetRef("FXChorus.Feedback",   "fx_field_chorus_feedback"),
    "FXChorus.Phase":      SemanticTargetRef("FXChorus.Phase",      "fx_field_chorus_phase"),
    "FXChorus.MixOrGain":  SemanticTargetRef("FXChorus.MixOrGain",  "fx_field_chorus_mix_or_gain"),

    # COMPRESSOR
    "FXCompressor.Threshold": SemanticTargetRef("FXCompressor.Threshold", "fx_field_comp_threshold"),
    "FXCompressor.Ratio":  SemanticTargetRef("FXCompressor.Ratio",  "fx_field_comp_ratio"),
    "FXCompressor.Attack": SemanticTargetRef("FXCompressor.Attack", "fx_field_comp_attack"),
    "FXCompressor.Release": SemanticTargetRef("FXCompressor.Release", "fx_field_comp_release"),
    "FXCompressor.Gain":   SemanticTargetRef("FXCompressor.Gain",   "fx_field_comp_gain"),
    "FXCompressor.MixOrGain": SemanticTargetRef("FXCompressor.MixOrGain", "fx_field_comp_mix_or_gain"),

    # CONVOLVE (Convolution Reverb)
    "FXConvolve.IRGain":   SemanticTargetRef("FXConvolve.IRGain",   "fx_field_convolve_ir_gain"),
    "FXConvolve.Attack":   SemanticTargetRef("FXConvolve.Attack",   "fx_field_convolve_attack"),
    "FXConvolve.Decay":    SemanticTargetRef("FXConvolve.Decay",    "fx_field_convolve_decay"),
    "FXConvolve.Damping":  SemanticTargetRef("FXConvolve.Damping",  "fx_field_convolve_damping"),
    "FXConvolve.MixOrGain": SemanticTargetRef("FXConvolve.MixOrGain", "fx_field_convolve_mix_or_gain"),
    "FXConvolve.IRPath":   SemanticTargetRef("FXConvolve.IRPath",   "fx_field_convolve_ir_path"),

    # DELAY
    "FXDelay.Mode":        SemanticTargetRef("FXDelay.Mode",        "fx_field_delay_mode"),
    "FXDelay.TimeL":       SemanticTargetRef("FXDelay.TimeL",       "fx_field_delay_time_l"),
    "FXDelay.TimeR":       SemanticTargetRef("FXDelay.TimeR",       "fx_field_delay_time_r"),
    "FXDelay.OffsetL":     SemanticTargetRef("FXDelay.OffsetL",     "fx_field_delay_offset_l"),
    "FXDelay.OffsetR":     SemanticTargetRef("FXDelay.OffsetR",     "fx_field_delay_offset_r"),
    "FXDelay.Feedback":    SemanticTargetRef("FXDelay.Feedback",    "fx_field_delay_feedback"),
    "FXDelay.MixOrGain":   SemanticTargetRef("FXDelay.MixOrGain",   "fx_field_delay_mix_or_gain"),
    "FXDelay.BW":          SemanticTargetRef("FXDelay.BW",          "fx_field_delay_bw"),

    # DISTORTION (extended)
    "FXDistortion.Mode":   SemanticTargetRef("FXDistortion.Mode",   "fx_field_dist_mode"),
    "FXDistortion.Drive":  SemanticTargetRef("FXDistortion.Drive",  "fx_field_dist_drive"),
    "FXDistortion.Freq":   SemanticTargetRef("FXDistortion.Freq",   "fx_field_dist_freq"),
    "FXDistortion.LPHP":   SemanticTargetRef("FXDistortion.LPHP",   "fx_field_dist_lphp"),
    "FXDistortion.PrePost": SemanticTargetRef("FXDistortion.PrePost", "fx_field_dist_prepost"),
    "FXDistortion.MixOrGain": SemanticTargetRef("FXDistortion.MixOrGain", "fx_field_dist_mix_or_gain"),
    "FXDistortion.BW":     SemanticTargetRef("FXDistortion.BW",     "fx_field_dist_bw"),

    # EQUALIZER (extended with type controls)
    "FXEQ.Type1":          SemanticTargetRef("FXEQ.Type1",          "fx_field_eq_type1"),
    "FXEQ.Freq1":          SemanticTargetRef("FXEQ.Freq1",          "fx_field_eq_freq1"),
    "FXEQ.Reso1":          SemanticTargetRef("FXEQ.Reso1",          "fx_field_eq_kParamReso1"),
    "FXEQ.Gain1":          SemanticTargetRef("FXEQ.Gain1",          "fx_field_eq_kParamGain1"),
    "FXEQ.Type2":          SemanticTargetRef("FXEQ.Type2",          "fx_field_eq_kParamType2"),
    "FXEQ.Freq2":          SemanticTargetRef("FXEQ.Freq2",          "fx_field_eq_kParamFreq2"),
    "FXEQ.LevelOut":       SemanticTargetRef("FXEQ.LevelOut",       "fx_field_eq_kParamLevelOut"),

    # FILTER (as FX module)
    "FXFilter.Type":       SemanticTargetRef("FXFilter.Type",       "fx_field_filter_type"),
    "FXFilter.Cutoff":     SemanticTargetRef("FXFilter.Cutoff",     "fx_field_filter_cutoff"),
    "FXFilter.Resonance":  SemanticTargetRef("FXFilter.Resonance",  "fx_field_filter_resonance"),
    "FXFilter.Drive":      SemanticTargetRef("FXFilter.Drive",      "fx_field_filter_drive"),
    "FXFilter.MixOrGain":  SemanticTargetRef("FXFilter.MixOrGain",  "fx_field_filter_mix_or_gain"),

    # FLANGER (extended)
    "FXFlanger.Rate":      SemanticTargetRef("FXFlanger.Rate",      "fx_field_flanger_rate"),
    "FXFlanger.Depth":     SemanticTargetRef("FXFlanger.Depth",     "fx_field_flanger_depth"),
    "FXFlanger.Feedback":  SemanticTargetRef("FXFlanger.Feedback",  "fx_field_flanger_feedback"),
    "FXFlanger.Phase":     SemanticTargetRef("FXFlanger.Phase",     "fx_field_flanger_phase"),
    "FXFlanger.MixOrGain": SemanticTargetRef("FXFlanger.MixOrGain", "fx_field_flanger_mix_or_gain"),

    # HYPER/DIMENSION (extended with retrigger)
    "FXHyper.Rate":        SemanticTargetRef("FXHyper.Rate",        "fx_field_hyper_rate"),
    "FXHyper.Unison":      SemanticTargetRef("FXHyper.Unison",      "fx_field_hyper_unison"),
    "FXHyper.Detune":      SemanticTargetRef("FXHyper.Detune",      "fx_field_hyper_detune"),
    "FXHyper.MixOrGain":   SemanticTargetRef("FXHyper.MixOrGain",   "fx_field_hyper_mix_or_gain"),
    "FXHyper.Retrigger":   SemanticTargetRef("FXHyper.Retrigger",   "fx_field_hyper_retrigger"),

    # PHASER (extended)
    "FXPhaser.Frequency":  SemanticTargetRef("FXPhaser.Frequency",  "fx_field_phaser_frequency"),
    "FXPhaser.Feedback":   SemanticTargetRef("FXPhaser.Feedback",   "fx_field_phaser_feedback"),
    "FXPhaser.Phase":      SemanticTargetRef("FXPhaser.Phase",      "fx_field_phaser_phase"),
    "FXPhaser.MixOrGain":  SemanticTargetRef("FXPhaser.MixOrGain",  "fx_field_phaser_mix_or_gain"),

    # REVERB (extended)
    "FXReverb.Size":       SemanticTargetRef("FXReverb.Size",       "fx_field_reverb_size"),
    "FXReverb.Damping":    SemanticTargetRef("FXReverb.Damping",    "fx_field_reverb_damping"),
    "FXReverb.MixOrGain":  SemanticTargetRef("FXReverb.MixOrGain",  "fx_field_reverb_mix_or_gain"),

    # SPLITTER (Frequency Splitter)
    "FXSplitter.BandCount": SemanticTargetRef("FXSplitter.BandCount", "fx_field_splitter_band_count"),
    "FXSplitter.Crossover1": SemanticTargetRef("FXSplitter.Crossover1", "fx_field_splitter_crossover1"),
    "FXSplitter.Crossover2": SemanticTargetRef("FXSplitter.Crossover2", "fx_field_splitter_crossover2"),
    "FXSplitter.Crossover3": SemanticTargetRef("FXSplitter.Crossover3", "fx_field_splitter_crossover3"),

    # UTILITY (extended)
    "FXUtility.Gain":      SemanticTargetRef("FXUtility.Gain",      "fx_field_utility_gain"),
    "FXUtility.Phase":     SemanticTargetRef("FXUtility.Phase",     "fx_field_utility_phase"),
    "FXUtility.Mono":      SemanticTargetRef("FXUtility.Mono",      "fx_field_utility_mono"),
    "FXUtility.MixOrGain": SemanticTargetRef("FXUtility.MixOrGain", "fx_field_utility_mix_or_gain"),

    # FX Structural Operations (3 buses)
    # PROVEN: clear_rack, remove, add, replace
    # UNRESOLVED: enable/disable/bypass (flex field mechanism unknown, see memory/fx_bypass_mechanism_unknown.md)
}


def resolve_semantic_target(
    name: str,
    contracts: Dict[Tuple[str, str], Any],
) -> "ResolvedTarget | TargetRefusal":
    """Resolve a semantic name to a (ref, contract) pair.

    Does NOT grant admission. Does NOT check whether the contract is usable.
    The caller is responsible for running admission.admit() independently.

    Invariants:
    - Returns TargetRefusal if the name is not in SEMANTIC_TARGETS
    - Returns TargetRefusal if no contract exists for the capability_key
    - Prefers CAUSAL_VERIFIED contract when multiple exist for the same key
    - Never contains a literal list index
    """
    ref = SEMANTIC_TARGETS.get(name)
    if ref is None:
        return TargetRefusal(
            UNKNOWN_SEMANTIC_TARGET,
            "no semantic target named %r -- not in SEMANTIC_TARGETS vocabulary" % name,
        )
    matches = [c for c in contracts.values() if c.target == ref.capability_key]
    if not matches:
        return TargetRefusal(
            CAPABILITY_NOT_FOUND,
            "no CapabilityContract for capability_key %r -- "
            "no evidence has been collected for this target" % ref.capability_key,
        )
    # Preference only -- admission still required before any execution.
    from ..evidence.capability_contract import CAUSAL_VERIFIED
    contract = next((c for c in matches if c.status == CAUSAL_VERIFIED), matches[0])
    return ResolvedTarget(ref=ref, contract=contract)


def resolve_path(resolved_target: ResolvedTarget, body: Dict[str, Any]) -> Optional[str]:
    """Resolve the concrete mutation path for this target in the given body.

    Uses context.extract_required_context() -- the sole RequiredContext
    derivation mechanism -- to find where the target lives in body regardless
    of which list index the witness experiment happened to use.

    Returns:
        str   -- concrete path where the target lives in body
        None  -- body does not satisfy the required structural context
                 (e.g. no FXEQ element in FXRack0.FX)
    """
    mutation_path = resolved_target.contract.scope.get("mutation_target_path")
    if mutation_path is None:
        return None
    ctx = ctx_mod.extract_required_context(mutation_path)
    if ctx is None:
        # No list traversal required -- path addresses a dict field directly.
        return mutation_path
    if not ctx.satisfied_by(body):
        return None
    return ctx.resolve_path(mutation_path, body)
