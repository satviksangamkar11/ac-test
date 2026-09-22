"""Episode Context for HEEGN1Xl5o4 reference material.

Deterministic evidence-based determination of what controls should be expected.
Does NOT infer from screenshot visibility; uses transcript/procedure/module context.

Reference: Serum 2.0.21 tutorial building a synth with:
  - OSC A/B waveform selection
  - LFO1 chaos mode routing
  - Matrix modulation
  - Multiple filter/FX chains
  - Envelope and modulation setup
"""

from expected_inventory import EpisodeContextResolver


def build_heegn1xl5o4_context() -> EpisodeContextResolver:
    """Build expected inventory context for HEEGN1Xl5o4 reference episode.

    This is deterministic — based on known procedure, not screenshot visibility.
    Expects controls that SHOULD be observed, even if currently unreadable/off-screen.
    """

    # Import atlas when available; for now, use empty dict
    atlas = {}
    context = EpisodeContextResolver(reference_id="HEEGN1Xl5o4", atlas=atlas)

    # === STEP 1: OSC A Setup ===
    context.add_module_context("OSC_A", "visible in step1_01m09s")
    context.add_control_context("oscA.wavetable", {
        "transcript": "Load 'Default Shapes' wavetable",
        "procedure": "OSC A waveform setup",
        "module_context": "OSC A / Wavetable Selector",
        "reference_surface": "step1_01m09s_osc_a_sawtooth_setup.jpg",
    })
    context.add_control_context("oscA.wt_position", {
        "transcript": "Adjust wavetable position",
        "procedure": "OSC A wavetable frame selection",
        "module_context": "OSC A / Wavetable Position",
        "reference_surface": "step1_01m09s_osc_a_sawtooth_setup.jpg (visible knob)",
    })
    context.add_control_context("oscA.unison", {
        "transcript": "Set Unison to 7",
        "procedure": "OSC A thickness control",
        "module_context": "OSC A / Unison",
        "reference_surface": "step1_01m09s_osc_a_sawtooth_setup.jpg (Gate-A Test 1: LIVE_VERIFIED)",
    })
    context.add_control_context("oscA.octave", {
        "transcript": "OSC A octave setting",
        "procedure": "OSC A pitch coarse",
        "module_context": "OSC A / Octave",
        "reference_surface": "step1_01m09s_osc_a_sawtooth_setup.jpg",
    })
    context.add_control_context("voicing.legato", {
        "transcript": "Legato toggle OFF",
        "procedure": "Voicing / Legato mode",
        "module_context": "Bottom panel / Voicing Controls",
        "reference_surface": "step1_01m09s_osc_a_sawtooth_setup.jpg (Gate-A Test 5: LIVE_VERIFIED)",
    })
    context.add_control_context("voicing.mono", {
        "transcript": "Mono mode unchecked",
        "procedure": "Voicing / Monophonic mode",
        "module_context": "Bottom panel / Voicing Controls",
        "reference_surface": "step1_01m09s_osc_a_sawtooth_setup.jpg (same crop as Legato)",
    })
    context.add_control_context("voicing.poly_voices", {
        "transcript": "Poly = 8 voices",
        "procedure": "Voicing / Voice count",
        "module_context": "Bottom panel / Voicing Controls",
        "reference_surface": "step1_01m09s_osc_a_sawtooth_setup.jpg (visible as label)",
    })

    # === STEP 1b: OSC B ===
    context.add_module_context("OSC_B", "visible in step1_01m34s")
    context.add_control_context("oscB.wavetable", {
        "transcript": "OSC B sawtooth + 1 octave",
        "procedure": "OSC B setup layering",
        "module_context": "OSC B / Wavetable",
        "reference_surface": "step1_01m34s_osc_b_sawtooth_plus1_oct.jpg",
    })
    context.add_control_context("oscB.octave", {
        "transcript": "OSC B octave +1",
        "procedure": "OSC B pitch offset",
        "module_context": "OSC B / Octave",
        "reference_surface": "step1_01m34s_osc_b_sawtooth_plus1_oct.jpg",
    })

    # === STEP 1c: LFO1 Chaos Mode ===
    context.add_module_context("LFO_1", "visible in step1_01m46s and step2_02m08s")
    context.add_control_context("lfo1.shape", {
        "transcript": "Set LFO1 mode to Chaos: Lorenz",
        "procedure": "LFO1 chaos mode selection",
        "module_context": "LFO1 / Mode Selector",
        "reference_surface": "step2_02m08s_lfo1_lorenz_full_pattern.jpg (Gate-A Test 3: LIVE_VERIFIED text + curve)",
    })
    context.add_control_context("lfo1.rate", {
        "transcript": "LFO1 rate setting",
        "procedure": "LFO1 speed control",
        "module_context": "LFO1 / Rate",
        "reference_surface": "step1_01m46s_lfo1_chaos_lorenz_routing.jpg (visible control)",
    })

    # === STEP 2: FILTER 1 ===
    context.add_module_context("FILTER_1", "visible in step2_03m14s")
    context.add_control_context("filter1.mode", {
        "transcript": "Filter 1 mode MG18",
        "procedure": "Filter type selection",
        "module_context": "FILTER 1 / Mode",
        "reference_surface": "step2_03m14s_filter_mg18_setup.jpg",
    })
    context.add_control_context("filter1.frequency", {
        "transcript": "Filter 1 frequency control",
        "procedure": "Filter cutoff frequency",
        "module_context": "FILTER 1 / Frequency",
        "reference_surface": "step2_03m14s_filter_mg18_setup.jpg",
    })
    context.add_control_context("filter1.resonance", {
        "transcript": "Filter 1 resonance",
        "procedure": "Filter resonance/emphasis",
        "module_context": "FILTER 1 / Resonance",
        "reference_surface": "step2_03m14s_filter_mg18_setup.jpg",
    })

    # === STEP 2b: ENV2 Modulation ===
    context.add_module_context("ENV_2", "visible in step2_03m27s")
    context.add_control_context("env2.attack", {
        "transcript": "ENV2 attack envelope",
        "procedure": "ENV2 modulation shape",
        "module_context": "ENV2 / Attack",
        "reference_surface": "step2_03m27s_env2_to_filter_cutoff.jpg",
    })
    context.add_control_context("env2.decay", {
        "transcript": "ENV2 decay",
        "procedure": "ENV2 decay time",
        "module_context": "ENV2 / Decay",
        "reference_surface": "step2_03m47s_env2_parameters_adjust.jpg",
    })

    # === STEP 3: MATRIX Routing ===
    context.add_module_context("MATRIX", "visible in step3_04m35s")
    context.add_control_context("route:Env 2->Filter 1 Freq", {
        "transcript": "Matrix: Env 2 modulates Filter 1 cutoff",
        "procedure": "Matrix modulation row setup",
        "module_context": "MATRIX / Row 1 (Env 2)",
        "reference_surface": "step3_04m35s_matrix_mod_routes.jpg (Gate-A Test 2: SOURCE + DEST LIVE_VERIFIED, AMOUNT visual-only)",
    })
    context.add_control_context("matrix.amount[Env 2->Filter 1 Freq]", {
        "transcript": "Modulation amount slider",
        "procedure": "Matrix row amount depth",
        "module_context": "MATRIX / Row 1 / Amount Slider",
        "reference_surface": "step3_04m35s_matrix_mod_routes.jpg (slider visible, no text value; Phase 3.5 calibration)",
        "observation_status": "OBSERVABLE_VISUAL_ONLY",
    })

    # === STEP 4: FX Chain / Distortion ===
    context.add_module_context("FX_OVERDRIVE", "referenced in step5_05m51s and step5_07m04s")
    context.add_control_context("fx.overdrive.drive", {
        "transcript": "Overdrive Drive = 1.9",
        "procedure": "Distortion effect drive amount",
        "module_context": "FX Chain / Overdrive / Drive",
        "reference_surface": "step5_07m04s_main_delay_ping_pong.jpg (Gate-A Test 4: MODEL_OUTPUT, SOURCE_INSUFFICIENT)",
    })

    # === STEP 5: EQ and Dynamics ===
    context.add_module_context("EQUALIZER", "visible in step5_06m44s")
    context.add_control_context("eq.freq[1]", {
        "transcript": "EQ band 1 frequency",
        "procedure": "EQ parameter setting",
        "module_context": "EQUALIZER / Band 1",
        "reference_surface": "step5_06m44s_main_eq_chain.jpg",
    })

    # === Expected controls that may not be explicitly set but should be documented ===
    # These are important for completeness tracking even if not visibly changed
    context.add_control_context("oscC.enabled", {
        "transcript": "OSC C state (typically disabled in this setup)",
        "procedure": "Oscillator C control",
        "module_context": "OSC C / Enable",
        "reference_surface": "Not visible (expected NOT_APPLICABLE or NOT_VISIBLE)",
        "visibility_requirement": "OPTIONAL",
    })
    context.add_control_context("filter2.enabled", {
        "transcript": "FILTER 2 state (typically secondary in this setup)",
        "procedure": "Filter 2 control",
        "module_context": "FILTER 2 / Enable",
        "reference_surface": "step6_07m47s_secondary_filter_mg_low6.jpg",
        "visibility_requirement": "OPTIONAL",
    })

    # === Explicit SOURCE_INSUFFICIENT cases ===
    # These are expected but the current frame set doesn't provide readable evidence
    context.add_control_context("env1.attack", {
        "transcript": "ENV1 main amplitude envelope attack",
        "procedure": "Main envelope shaping",
        "module_context": "ENV1 / Attack",
        "reference_surface": "step2_02m49s_env1_main_amp_shape.jpg (frame visible but detail unreadable)",
        "evidence_status": "SOURCE_INSUFFICIENT",
    })

    return context


if __name__ == "__main__":
    # Test: print expected inventory summary
    ctx = build_heegn1xl5o4_context()
    expected_ids = ctx.get_expected_set()
    print(f"HEEGN1Xl5o4 Expected Inventory: {len(expected_ids)} controls")
    for cid in sorted(expected_ids):
        basis = ctx.get_expectation_basis(cid)
        print(f"  {cid}: {basis.get('procedure', '?')}")
