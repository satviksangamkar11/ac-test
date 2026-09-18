# SERUM CONTROL LAYER MATRIX

Generated: 2026-09-18T12:15:12.020826

Total semantic rows: 908  
Total normalized targets: 396

## Disposition Taxonomy

- **A** — CAUSAL_PROVEN + ADMITTED
- **B** — CAUSAL_PROVEN but blocked (no execution binding wired)
- **C** — machine/UI verified but not causally qualified (STRUCTURAL_ONLY)
- **D** — not-yet-derived
- **E** — unsupported/structural (incl. DEAD_OR_SUPERSEDED, NEGATIVE_EVIDENCE)
- **F** — unresolved/unknown (ambiguous, contradicted)
- **G** — proven-not-user-control

## Normalized Target Matrix (396 targets)

| TARGET_ID | CAPABILITY_BINDING | STATUS | MECHANISM | FIXTURE | PROVEN? | TIER | DISPOSITION |
|---|---|---|---|---|---|---|---|
| ARP.Enable | arp_field_ENABLE | — | — | — | no | NOT_YET_DERIVED | **D** |
| BUS1.Level | global_plain_param_fx_bus1_vol | — | — | — | no | NOT_YET_DERIVED | **D** |
| BUS2.Level | global_plain_param_fx_bus2_vol | — | — | — | no | NOT_YET_DERIVED | **D** |
| CLIP.SETTINGS.OFFSET | vst3_idx_522 | — | — | — | no | NOT_YET_DERIVED | **D** |
| ENV1.ATK_CURVE | vst3_idx_229 | — | — | — | no | NOT_YET_DERIVED | **D** |
| ENV1.DEC_CURVE | vst3_idx_230 | — | — | — | no | NOT_YET_DERIVED | **D** |
| ENV1.HOLD | vst3_idx_225 | — | — | — | no | NOT_YET_DERIVED | **D** |
| ENV1.REL_CURVE | vst3_idx_231 | — | — | — | no | NOT_YET_DERIVED | **D** |
| ENV2.ATK_CURVE | vst3_idx_237 | — | — | — | no | NOT_YET_DERIVED | **D** |
| ENV2.DEC_CURVE | vst3_idx_238 | — | — | — | no | NOT_YET_DERIVED | **D** |
| ENV2.HOLD | vst3_idx_233 | — | — | — | no | NOT_YET_DERIVED | **D** |
| ENV2.REL_CURVE | vst3_idx_239 | — | — | — | no | NOT_YET_DERIVED | **D** |
| ENV3.ATK_CURVE | vst3_idx_247 | — | — | — | no | NOT_YET_DERIVED | **D** |
| ENV3.DEC_CURVE | vst3_idx_248 | — | — | — | no | NOT_YET_DERIVED | **D** |
| ENV3.HOLD | vst3_idx_243 | — | — | — | no | NOT_YET_DERIVED | **D** |
| ENV3.REL_CURVE | vst3_idx_249 | — | — | — | no | NOT_YET_DERIVED | **D** |
| ENV4.ATK_CURVE | vst3_idx_257 | — | — | — | no | NOT_YET_DERIVED | **D** |
| ENV4.DEC_CURVE | vst3_idx_258 | — | — | — | no | NOT_YET_DERIVED | **D** |
| ENV4.HOLD | vst3_idx_253 | — | — | — | no | NOT_YET_DERIVED | **D** |
| ENV4.REL_CURVE | vst3_idx_259 | — | — | — | no | NOT_YET_DERIVED | **D** |
| Env1.Attack | envelope_field_attack | CAUSAL_VERIFIED | HOST_PARAMETER (DawDreamer: 'Env 1 Attack') | none (default Serum skeleton) | YES | EXECUTED_WITH_FRESH_EVIDENCE | **A** |
| Env1.Decay | envelope_field_decay | CAUSAL_VERIFIED | HOST_PARAMETER (DawDreamer: 'Env 1 Decay') | none (default Serum skeleton) | no | ADMITTED_BINDING_READY_UNTESTED | **A** |
| Env1.Release | envelope_field_release | CAUSAL_VERIFIED | HOST_PARAMETER (DawDreamer: 'Env 1 Release') | none (default Serum skeleton) | no | ADMITTED_BINDING_READY_UNTESTED | **A** |
| Env1.Sustain | envelope_field_sustain | CAUSAL_VERIFIED | HOST_PARAMETER (DawDreamer: 'Env 1 Sustain') | none (default Serum skeleton) | no | ADMITTED_BINDING_READY_UNTESTED | **A** |
| Env2.Attack | envelope2_field_attack | — | — | — | no | NOT_YET_DERIVED | **D** |
| Env2.Decay | envelope2_field_decay | — | — | — | no | NOT_YET_DERIVED | **D** |
| Env2.Release | envelope2_field_release | — | — | — | no | NOT_YET_DERIVED | **D** |
| Env2.Sustain | envelope2_field_sustain | — | — | — | no | NOT_YET_DERIVED | **D** |
| Env3.Attack | envelope3_field_attack | — | — | — | no | NOT_YET_DERIVED | **D** |
| Env3.Decay | envelope3_field_decay | — | — | — | no | NOT_YET_DERIVED | **D** |
| Env3.Release | envelope3_field_release | — | — | — | no | NOT_YET_DERIVED | **D** |
| Env3.Sustain | envelope3_field_sustain | — | — | — | no | NOT_YET_DERIVED | **D** |
| Env4.Attack | envelope4_field_attack | — | — | — | no | NOT_YET_DERIVED | **D** |
| Env4.Decay | envelope4_field_decay | — | — | — | no | NOT_YET_DERIVED | **D** |
| Env4.Release | envelope4_field_release | — | — | — | no | NOT_YET_DERIVED | **D** |
| Env4.Sustain | envelope4_field_sustain | — | — | — | no | NOT_YET_DERIVED | **D** |
| FILTER1.BUS1Send | routing_slot5_bus1_level | — | — | — | no | NOT_YET_DERIVED | **D** |
| FILTER1.BUS2Send | routing_slot5_bus2_level | — | — | — | no | NOT_YET_DERIVED | **D** |
| FILTER1.Level | voicefilter0_plain_param_level_out | — | — | — | no | NOT_YET_DERIVED | **D** |
| FILTER1.Mix | voicefilter0_plain_param_wet | — | — | — | no | NOT_YET_DERIVED | **D** |
| FILTER1.Route | routing_slot5_dest | — | — | — | no | NOT_YET_DERIVED | **D** |
| FILTER1.STEREO | vst3_idx_210 | — | — | — | no | NOT_YET_DERIVED | **D** |
| FILTER1.VAR | vst3_idx_208 | — | — | — | no | NOT_YET_DERIVED | **D** |
| FILTER2.BUS1Send | routing_slot6_bus1_level | — | — | — | no | NOT_YET_DERIVED | **D** |
| FILTER2.BUS2Send | routing_slot6_bus2_level | — | — | — | no | NOT_YET_DERIVED | **D** |
| FILTER2.Level | voicefilter1_plain_param_level_out | — | — | — | no | NOT_YET_DERIVED | **D** |
| FILTER2.Mix | voicefilter1_plain_param_wet | — | — | — | no | NOT_YET_DERIVED | **D** |
| FILTER2.Route | routing_slot6_dest | — | — | — | no | NOT_YET_DERIVED | **D** |
| FILTER2.STEREO | vst3_idx_221 | — | — | — | no | NOT_YET_DERIVED | **D** |
| FILTER2.VAR | vst3_idx_219 | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXBODE.Direction | fx_field_bode_direction | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXBODE.Frequency | fx_field_bode_frequency | DEAD_OR_SUPERSEDED | — | — | no | NONE | **E** |
| FXBODE.LevelOut | fx_field_bode_level_out | DEAD_OR_SUPERSEDED | — | — | no | NONE | **E** |
| FXBODE.Mix | fx_field_bode_mix | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXBODE.MixOrGain | fx_field_bode_mix_or_gain | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXBODE.Range | fx_field_bode_range | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXBODE.Shift | fx_field_bode_shift | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXChorus.Depth | fx_field_chorus_depth | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXChorus.Feedback | fx_field_chorus_feedback | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXChorus.Mix | fx_field_chorus_mix | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXChorus.MixOrGain | fx_field_chorus_mix_or_gain | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXChorus.Phase | fx_field_chorus_phase | DEAD_OR_SUPERSEDED | — | — | no | NONE | **E** |
| FXChorus.Rate | fx_field_chorus_rate | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXCompressor.Attack | fx_field_comp_attack | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXCompressor.Gain | fx_field_comp_gain | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXCompressor.MixOrGain | fx_field_comp_mix_or_gain | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXCompressor.Ratio | fx_field_comp_ratio | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXCompressor.Release | fx_field_comp_release | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXCompressor.Threshold | fx_field_comp_threshold | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXConvolve.Attack | fx_field_convolve_attack | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXConvolve.Damping | fx_field_convolve_damping | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXConvolve.Decay | fx_field_convolve_decay | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXConvolve.IR | fx_field_convolve_ir | DEAD_OR_SUPERSEDED | — | — | no | NONE | **E** |
| FXConvolve.IRGain | fx_field_convolve_ir_gain | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXConvolve.IRPath | fx_field_convolve_ir_path | DEAD_OR_SUPERSEDED | — | — | no | NONE | **E** |
| FXConvolve.Mix | fx_field_convolve_mix | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXConvolve.MixOrGain | fx_field_convolve_mix_or_gain | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXDelay.BW | fx_field_delay_bw | DEAD_OR_SUPERSEDED | — | — | no | NONE | **E** |
| FXDelay.Feedback | fx_field_delay_feedback | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXDelay.Mix | fx_field_delay_mix | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXDelay.MixOrGain | fx_field_delay_mix_or_gain | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXDelay.Mode | fx_field_delay_mode | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXDelay.OffsetL | fx_field_delay_offset_l | DEAD_OR_SUPERSEDED | — | — | no | NONE | **E** |
| FXDelay.OffsetR | fx_field_delay_offset_r | DEAD_OR_SUPERSEDED | — | — | no | NONE | **E** |
| FXDelay.Time | fx_field_delay_time | DEAD_OR_SUPERSEDED | — | — | no | NONE | **E** |
| FXDelay.TimeL | fx_field_delay_time_l | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXDelay.TimeR | fx_field_delay_time_r | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXDistortion.BW | fx_field_dist_bw | DEAD_OR_SUPERSEDED | — | — | no | NONE | **E** |
| FXDistortion.Drive | fx_field_dist_drive | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXDistortion.Freq | fx_field_dist_freq | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXDistortion.LPHP | fx_field_dist_lphp | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXDistortion.LevelOut | fx_field_dist_level_out | DEAD_OR_SUPERSEDED | — | — | no | NONE | **E** |
| FXDistortion.MixOrGain | fx_field_dist_mix_or_gain | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXDistortion.Mode | fx_field_dist_mode | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXDistortion.PrePost | fx_field_dist_prepost | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXDistortion.Tone | fx_field_dist_tone | DEAD_OR_SUPERSEDED | — | — | no | NONE | **E** |
| FXEQ.Freq1 | fx_field_eq_freq1 | CAUSAL_VERIFIED | BODY_STATE (pathmerge) | experiments/_corpus_cache.pkl bodies[4] (FXEQ-populated fixture) | YES | EXECUTED_WITH_FRESH_EVIDENCE | **A** |
| FXEQ.Freq2 | fx_field_eq_kParamFreq2 | CAUSAL_VERIFIED | BODY_STATE (pathmerge) | experiments/_corpus_cache.pkl bodies[4] (FXEQ-populated fixture) | YES | EXECUTED_WITH_FRESH_EVIDENCE | **A** |
| FXEQ.Gain1 | fx_field_eq_kParamGain1 | CAUSAL_VERIFIED | BODY_STATE (pathmerge) | experiments/_corpus_cache.pkl bodies[4] (FXEQ-populated fixture) | YES | EXECUTED_WITH_FRESH_EVIDENCE | **A** |
| FXEQ.Gain2 | fx_field_eq_kParamGain2 | CAUSAL_VERIFIED | BODY_STATE (pathmerge) | experiments/_corpus_cache.pkl bodies[4] (FXEQ-populated fixture) | YES | EXECUTED_WITH_FRESH_EVIDENCE | **A** |
| FXEQ.LevelOut | fx_field_eq_kParamLevelOut | DEAD_OR_SUPERSEDED | — | — | no | NONE | **E** |
| FXEQ.Reso1 | fx_field_eq_kParamReso1 | CAUSAL_VERIFIED | BODY_STATE (pathmerge) | experiments/_corpus_cache.pkl bodies[4] (FXEQ-populated fixture) | YES | EXECUTED_WITH_FRESH_EVIDENCE | **A** |
| FXEQ.Reso2 | fx_field_eq_kParamReso2 | CAUSAL_VERIFIED | BODY_STATE (pathmerge) | experiments/_corpus_cache.pkl bodies[4] (FXEQ-populated fixture) | YES | EXECUTED_WITH_FRESH_EVIDENCE | **A** |
| FXEQ.Type1 | fx_field_eq_type1 | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXEQ.Type2 | fx_field_eq_kParamType2 | CAUSAL_VERIFIED | BODY_STATE (pathmerge) | experiments/_corpus_cache.pkl bodies[4] (FXEQ-populated fixture) | YES | EXECUTED_WITH_FRESH_EVIDENCE | **A** |
| FXFilter.Cutoff | fx_field_filter_cutoff | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXFilter.Drive | fx_field_filter_drive | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXFilter.MixOrGain | fx_field_filter_mix_or_gain | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXFilter.Resonance | fx_field_filter_resonance | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXFilter.Type | fx_field_filter_type | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXFilterFX.Cutoff | fx_field_filter_fx_cutoff | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXFilterFX.Drive | fx_field_filter_fx_drive | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXFilterFX.Mix | fx_field_filter_fx_mix | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXFilterFX.Resonance | fx_field_filter_fx_resonance | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXFilterFX.Type | fx_field_filter_fx_type | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXFlanger.Depth | fx_field_flanger_depth | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXFlanger.Feedback | fx_field_flanger_feedback | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXFlanger.Mix | fx_field_flanger_mix | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXFlanger.MixOrGain | fx_field_flanger_mix_or_gain | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXFlanger.Phase | fx_field_flanger_phase | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXFlanger.Rate | fx_field_flanger_rate | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXHyper.Detune | fx_field_hyper_detune | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXHyper.Mix | fx_field_hyper_mix | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXHyper.MixOrGain | fx_field_hyper_mix_or_gain | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXHyper.Rate | fx_field_hyper_rate | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXHyper.Retrigger | fx_field_hyper_retrigger | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXHyper.Unison | fx_field_hyper_unison | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXPhaser.Feedback | fx_field_phaser_feedback | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXPhaser.Frequency | fx_field_phaser_frequency | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXPhaser.Mix | fx_field_phaser_mix | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXPhaser.MixOrGain | fx_field_phaser_mix_or_gain | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXPhaser.Phase | fx_field_phaser_phase | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXReverb.Damping | fx_field_reverb_damping | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXReverb.Mix | fx_field_reverb_mix | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXReverb.MixOrGain | fx_field_reverb_mix_or_gain | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXReverb.Size | fx_field_reverb_size | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXReverb.Time | fx_field_reverb_time | DEAD_OR_SUPERSEDED | — | — | no | NONE | **E** |
| FXSplitter.BandCount | fx_field_splitter_band_count | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXSplitter.Crossover1 | fx_field_splitter_crossover1 | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXSplitter.Crossover2 | fx_field_splitter_crossover2 | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXSplitter.Crossover3 | fx_field_splitter_crossover3 | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXUtility.Gain | fx_field_utility_gain | DEAD_OR_SUPERSEDED | — | — | no | NONE | **E** |
| FXUtility.Mix | fx_field_utility_mix | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXUtility.MixOrGain | fx_field_utility_mix_or_gain | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXUtility.Mono | fx_field_utility_mono | — | — | — | no | NOT_YET_DERIVED | **D** |
| FXUtility.Phase | fx_field_utility_phase | DEAD_OR_SUPERSEDED | — | — | no | NONE | **E** |
| Filter.Cutoff | filter_field_cutoff | CAUSAL_VERIFIED | HOST_PARAMETER (DawDreamer: 'Filter 1 Freq') | none (default Serum skeleton) | YES | EXECUTED_WITH_FRESH_EVIDENCE | **A** |
| Filter.Drive | filter_field_drive | — | — | — | no | NOT_YET_DERIVED | **D** |
| Filter.Enable | filter_field_ENABLE | — | — | — | no | NOT_YET_DERIVED | **D** |
| Filter.Q | filter_field_q | — | — | — | no | NOT_YET_DERIVED | **D** |
| Filter.Resonance | filter_field_reso | CAUSAL_VERIFIED | HOST_PARAMETER (DawDreamer: 'Filter 1 Res') | none (default Serum skeleton) | YES | EXECUTED_WITH_FRESH_EVIDENCE | **A** |
| Filter.Type | filter_field_type | CAUSAL_VERIFIED | HOST_PARAMETER (DawDreamer: 'Filter 1 Type') | none (default Serum skeleton) | no | ADMITTED_BINDING_READY_UNTESTED | **A** |
| Filter2.Cutoff | filter2_field_cutoff | — | — | — | no | AMBIGUOUS | **F** |
| Filter2.Drive | filter2_field_drive | — | — | — | no | NOT_YET_DERIVED | **D** |
| Filter2.Enable | filter2_field_ENABLE | — | — | — | no | NOT_YET_DERIVED | **D** |
| Filter2.Q | filter2_field_q | — | — | — | no | NOT_YET_DERIVED | **D** |
| Filter2.Resonance | filter2_field_reso | — | — | — | no | AMBIGUOUS | **F** |
| Filter2.Type | filter2_field_type | — | — | — | no | NOT_YET_DERIVED | **D** |
| Global.Glide | global_field_glide | — | — | — | no | NOT_YET_DERIVED | **D** |
| Global.Key | global_field_key | — | — | — | no | NOT_YET_DERIVED | **D** |
| Global.MasterVolume | global_field_mastervolume | CAUSAL_VERIFIED | HOST_PARAMETER (DawDreamer: 'Main Vol') | none (default Serum skeleton) | no | ADMITTED_BINDING_READY_UNTESTED | **A** |
| Global.Mono | global_field_mono | — | — | — | no | NOT_YET_DERIVED | **D** |
| Global.PitchTracking | global_field_pitch_tracking | — | — | — | no | NOT_YET_DERIVED | **D** |
| Global.Portamento | global_field_portamento | — | — | — | no | NOT_YET_DERIVED | **D** |
| Global.Quality | global_field_quality | — | — | — | no | NOT_YET_DERIVED | **D** |
| Global.Scale | global_field_scale | — | — | — | no | NOT_YET_DERIVED | **D** |
| Global.Swing | global_field_swing | — | — | — | no | NOT_YET_DERIVED | **D** |
| Global.Transpose | global_field_transpose | — | — | — | no | NOT_YET_DERIVED | **D** |
| Global.Tuning | global_field_tuning | — | — | — | no | NOT_YET_DERIVED | **D** |
| Global.VelocityCurve | global_field_velocity_curve | — | — | — | no | NOT_YET_DERIVED | **D** |
| Global.Voicing | global_field_voicing | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO0.Mode | lfo_field_lfo0_mode | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO0.Phase | lfo_field_lfo0_phase | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO0.Rate | lfo_field_lfo0_rate | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO0.Retrigger | lfo_field_lfo0_retrigger | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO0.Shape | lfo_field_lfo0_shape | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO1.DELAY | vst3_idx_265 | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO1.Mode | lfo_field_lfo1_mode | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO1.Phase | lfo_field_lfo1_phase | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO1.RISE | vst3_idx_264 | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO1.Rate | lfo_field_lfo1_rate | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO1.Retrigger | lfo_field_lfo1_retrigger | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO1.SMOOTH | vst3_idx_263 | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO1.Shape | lfo_field_lfo1_shape | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO2.DELAY | vst3_idx_270 | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO2.Mode | lfo_field_lfo2_mode | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO2.Phase | lfo_field_lfo2_phase | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO2.RISE | vst3_idx_269 | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO2.Rate | lfo_field_lfo2_rate | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO2.Retrigger | lfo_field_lfo2_retrigger | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO2.SMOOTH | vst3_idx_268 | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO2.Shape | lfo_field_lfo2_shape | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO3.DELAY | vst3_idx_275 | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO3.Mode | lfo_field_lfo3_mode | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO3.Phase | lfo_field_lfo3_phase | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO3.RISE | vst3_idx_274 | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO3.Rate | lfo_field_lfo3_rate | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO3.Retrigger | lfo_field_lfo3_retrigger | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO3.SMOOTH | vst3_idx_273 | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO3.Shape | lfo_field_lfo3_shape | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO4.DELAY | vst3_idx_280 | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO4.Mode | lfo_field_lfo4_mode | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO4.Phase | lfo_field_lfo4_phase | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO4.RISE | vst3_idx_279 | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO4.Rate | lfo_field_lfo4_rate | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO4.Retrigger | lfo_field_lfo4_retrigger | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO4.SMOOTH | vst3_idx_278 | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO4.Shape | lfo_field_lfo4_shape | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO5.DELAY | vst3_idx_285 | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO5.Mode | lfo_field_lfo5_mode | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO5.Phase | lfo_field_lfo5_phase | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO5.RISE | vst3_idx_284 | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO5.Rate | lfo_field_lfo5_rate | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO5.Retrigger | lfo_field_lfo5_retrigger | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO5.SMOOTH | vst3_idx_283 | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO5.Shape | lfo_field_lfo5_shape | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO6.DELAY | vst3_idx_290 | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO6.Mode | lfo_field_lfo6_mode | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO6.Phase | lfo_field_lfo6_phase | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO6.RISE | vst3_idx_289 | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO6.Rate | lfo_field_lfo6_rate | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO6.Retrigger | lfo_field_lfo6_retrigger | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO6.SMOOTH | vst3_idx_288 | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO6.Shape | lfo_field_lfo6_shape | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO7.Mode | lfo_field_lfo7_mode | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO7.Phase | lfo_field_lfo7_phase | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO7.Rate | lfo_field_lfo7_rate | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO7.Retrigger | lfo_field_lfo7_retrigger | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO7.Shape | lfo_field_lfo7_shape | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO8.Mode | lfo_field_lfo8_mode | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO8.Phase | lfo_field_lfo8_phase | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO8.Rate | lfo_field_lfo8_rate | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO8.Retrigger | lfo_field_lfo8_retrigger | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO8.Shape | lfo_field_lfo8_shape | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO9.Mode | lfo_field_lfo9_mode | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO9.Phase | lfo_field_lfo9_phase | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO9.Rate | lfo_field_lfo9_rate | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO9.Retrigger | lfo_field_lfo9_retrigger | — | — | — | no | NOT_YET_DERIVED | **D** |
| LFO9.Shape | lfo_field_lfo9_shape | — | — | — | no | NOT_YET_DERIVED | **D** |
| ModRoute.AuxSource | mod_field_route_aux_source | — | — | — | no | NOT_YET_DERIVED | **D** |
| ModRoute.Bipolar | mod_field_route_bipolar | — | — | — | no | NOT_YET_DERIVED | **D** |
| ModRoute.Bypass | mod_field_route_bypass | — | — | — | no | NOT_YET_DERIVED | **D** |
| ModRoute.Curve | mod_field_route_curve | — | — | — | no | NOT_YET_DERIVED | **D** |
| ModRoute.MacroDepth | mod_field_route_macro_depth | — | — | — | no | NOT_YET_DERIVED | **D** |
| NOISE.BUS1Send | routing_slot3_bus1_level | — | — | — | no | NOT_YET_DERIVED | **D** |
| NOISE.BUS2Send | routing_slot3_bus2_level | — | — | — | no | NOT_YET_DERIVED | **D** |
| NOISE.Fine | oscillator_field_NOISE-FINE | — | — | — | no | NOT_YET_DERIVED | **D** |
| NOISE.Level | noise_plain_param_level | — | — | — | no | NOT_YET_DERIVED | **D** |
| NOISE.Pan | noise_plain_param_pan | — | — | — | no | NOT_YET_DERIVED | **D** |
| NOISE.Route | routing_slot3_dest | — | — | — | no | NOT_YET_DERIVED | **D** |
| NOISE.Type | oscillator_field_NOISE-TYPE | — | — | — | no | NOT_YET_DERIVED | **D** |
| NOISE.Volume | oscillator_field_NOISE-VOLUME | — | — | — | no | NOT_YET_DERIVED | **D** |
| NOISE.Warp | oscillator_field_NOISE-WARP | — | — | — | no | NOT_YET_DERIVED | **D** |
| NOISE_OSC.PHASE | vst3_idx_191 | — | — | — | no | NOT_YET_DERIVED | **D** |
| NOISE_OSC.PITCH | vst3_idx_189 | — | — | — | no | NOT_YET_DERIVED | **D** |
| NOISE_OSC.PITCH_TRACK | vst3_idx_188 | — | — | — | no | NOT_YET_DERIVED | **D** |
| NOISE_OSC.RAND_PHASE | vst3_idx_192 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.BUS1Send | routing_slot0_bus1_level | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.BUS2Send | routing_slot0_bus2_level | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.COARSE_PITCH | vst3_idx_28 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.Detune | oscillator_field_OSC1-DETUNE | CAUSAL_VERIFIED | HOST_PARAMETER (DawDreamer: 'A Uni Detune') | none (default Serum skeleton) | YES | EXECUTED_WITH_FRESH_EVIDENCE | **A** |
| OSC1.END | vst3_idx_31 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.Enable | oscillator_field_OSC1-ENABLE | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.FINE | vst3_idx_25 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.LOOP_END | vst3_idx_38 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.LOOP_MODE | vst3_idx_40 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.LOOP_START | vst3_idx_37 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.LOOP_X-FADE | vst3_idx_39 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.Level | osc1_plain_param_level | CAUSAL_VERIFIED | HOST_PARAMETER (DawDreamer: 'A Level') | none (default Serum skeleton) | YES | EXECUTED_WITH_FRESH_EVIDENCE | **A** |
| OSC1.Octave | oscillator_field_OSC1-OCTAVE | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.PHASE | vst3_idx_61 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.POSITION | vst3_idx_36 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.Pan | osc1_plain_param_pan | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.RAND_PHASE | vst3_idx_62 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.Route | routing_slot0_dest | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.SCAN_BPM_RATE | vst3_idx_34 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.SCAN_RATE | vst3_idx_33 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.SEMI | vst3_idx_24 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.SINGLE_SLICE | vst3_idx_42 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.START | vst3_idx_30 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.UNISON | vst3_idx_44 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.UNI_BLEND | vst3_idx_47 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.UNI_DETUNE | vst3_idx_46 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.UNI_RAND_START | vst3_idx_50 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.UNI_SPAN | vst3_idx_49 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.UNI_STACK | vst3_idx_45 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.UNI_WARP | vst3_idx_51 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.UNI_WARP_2 | vst3_idx_52 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.UNI_WIDTH | vst3_idx_48 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.UNI_WT_POS | vst3_idx_60 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.Volume | oscillator_field_OSC1-VOLUME | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.WARP_2 | vst3_idx_56 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.WARP_2_MODE | vst3_idx_58 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.WARP_2_VAR | vst3_idx_57 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.WARP_MODE | vst3_idx_55 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.WARP_VAR | vst3_idx_54 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.WT_POS | vst3_idx_59 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.Warp | oscillator_field_OSC1-WARP | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC1.Wavetable | oscillator_field_OSC1-WAVETABLE | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.BUS1Send | routing_slot1_bus1_level | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.BUS2Send | routing_slot1_bus2_level | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.COARSE_PITCH | vst3_idx_28 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.Detune | oscillator_field_OSC2-DETUNE | DEAD_OR_SUPERSEDED | — | — | no | NONE | **E** |
| OSC2.END | vst3_idx_31 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.Enable | oscillator_field_OSC2-ENABLE | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.FINE | vst3_idx_25 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.LOOP_END | vst3_idx_38 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.LOOP_MODE | vst3_idx_40 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.LOOP_START | vst3_idx_37 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.LOOP_X-FADE | vst3_idx_39 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.Level | osc2_plain_param_level | CAUSAL_VERIFIED | HOST_PARAMETER (DawDreamer: 'B Level') | none (default Serum skeleton) | YES | EXECUTED_WITH_FRESH_EVIDENCE | **A** |
| OSC2.Octave | oscillator_field_OSC2-OCTAVE | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.PHASE | vst3_idx_61 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.POSITION | vst3_idx_36 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.Pan | osc2_plain_param_pan | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.RAND_PHASE | vst3_idx_62 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.Route | routing_slot1_dest | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.SCAN_BPM_RATE | vst3_idx_34 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.SCAN_RATE | vst3_idx_33 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.SEMI | vst3_idx_24 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.SINGLE_SLICE | vst3_idx_42 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.START | vst3_idx_30 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.UNISON | vst3_idx_44 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.UNI_BLEND | vst3_idx_47 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.UNI_DETUNE | vst3_idx_46 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.UNI_RAND_START | vst3_idx_50 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.UNI_SPAN | vst3_idx_49 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.UNI_STACK | vst3_idx_45 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.UNI_WARP | vst3_idx_51 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.UNI_WARP_2 | vst3_idx_52 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.UNI_WIDTH | vst3_idx_48 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.UNI_WT_POS | vst3_idx_60 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.Volume | oscillator_field_OSC2-VOLUME | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.WARP_2 | vst3_idx_56 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.WARP_2_MODE | vst3_idx_58 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.WARP_2_VAR | vst3_idx_57 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.WARP_MODE | vst3_idx_55 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.WARP_VAR | vst3_idx_54 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.WT_POS | vst3_idx_59 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC2.Warp | oscillator_field_OSC2-WARP | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.BUS1Send | routing_slot2_bus1_level | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.BUS2Send | routing_slot2_bus2_level | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.COARSE_PITCH | vst3_idx_28 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.Detune | oscillator_field_OSC3-DETUNE | DEAD_OR_SUPERSEDED | — | — | no | NONE | **E** |
| OSC3.END | vst3_idx_31 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.Enable | oscillator_field_OSC3-ENABLE | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.FINE | vst3_idx_25 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.LOOP_END | vst3_idx_38 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.LOOP_MODE | vst3_idx_40 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.LOOP_START | vst3_idx_37 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.LOOP_X-FADE | vst3_idx_39 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.Level | osc3_plain_param_level | CAUSAL_VERIFIED | HOST_PARAMETER (DawDreamer: 'C Level') | none (default Serum skeleton) | YES | EXECUTED_WITH_FRESH_EVIDENCE | **A** |
| OSC3.Octave | oscillator_field_OSC3-OCTAVE | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.PHASE | vst3_idx_61 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.POSITION | vst3_idx_36 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.Pan | osc3_plain_param_pan | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.RAND_PHASE | vst3_idx_62 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.Route | routing_slot2_dest | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.SCAN_BPM_RATE | vst3_idx_34 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.SCAN_RATE | vst3_idx_33 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.SEMI | vst3_idx_24 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.SINGLE_SLICE | vst3_idx_42 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.START | vst3_idx_30 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.UNISON | vst3_idx_44 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.UNI_BLEND | vst3_idx_47 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.UNI_DETUNE | vst3_idx_46 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.UNI_RAND_START | vst3_idx_50 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.UNI_SPAN | vst3_idx_49 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.UNI_STACK | vst3_idx_45 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.UNI_WARP | vst3_idx_51 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.UNI_WARP_2 | vst3_idx_52 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.UNI_WIDTH | vst3_idx_48 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.UNI_WT_POS | vst3_idx_60 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.Volume | oscillator_field_OSC3-VOLUME | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.WARP_2 | vst3_idx_56 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.WARP_2_MODE | vst3_idx_58 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.WARP_2_VAR | vst3_idx_57 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.WARP_MODE | vst3_idx_55 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.WARP_VAR | vst3_idx_54 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.WT_POS | vst3_idx_59 | — | — | — | no | NOT_YET_DERIVED | **D** |
| OSC3.Warp | oscillator_field_OSC3-WARP | — | — | — | no | NOT_YET_DERIVED | **D** |
| SUB.BUS1Send | routing_slot4_bus1_level | — | — | — | no | NOT_YET_DERIVED | **D** |
| SUB.BUS2Send | routing_slot4_bus2_level | — | — | — | no | NOT_YET_DERIVED | **D** |
| SUB.Detune | oscillator_field_SUB-DETUNE | DEAD_OR_SUPERSEDED | — | — | no | NONE | **E** |
| SUB.Enable | oscillator_field_SUB-ENABLE | — | — | — | no | NOT_YET_DERIVED | **D** |
| SUB.Level | sub_plain_param_level | — | — | — | no | NOT_YET_DERIVED | **D** |
| SUB.Octave | oscillator_field_SUB-OCTAVE | — | — | — | no | NOT_YET_DERIVED | **D** |
| SUB.Pan | sub_plain_param_pan | — | — | — | no | NOT_YET_DERIVED | **D** |
| SUB.Route | routing_slot4_dest | — | — | — | no | NOT_YET_DERIVED | **D** |
| SUB.Volume | oscillator_field_SUB-VOLUME | — | — | — | no | NOT_YET_DERIVED | **D** |
| SUB.Warp | oscillator_field_SUB-WARP | — | — | — | no | NOT_YET_DERIVED | **D** |
| SUB_OSC.COARSE_PITCH | vst3_idx_197 | — | — | — | no | NOT_YET_DERIVED | **D** |
| SUB_OSC.CONT_PHASE | vst3_idx_201 | — | — | — | no | NOT_YET_DERIVED | **D** |
| SUB_OSC.PHASE | vst3_idx_200 | — | — | — | no | NOT_YET_DERIVED | **D** |
| SUB_OSC.PITCH_TRACK | vst3_idx_198 | — | — | — | no | NOT_YET_DERIVED | **D** |
| SUB_OSC.SHAPE | vst3_idx_199 | — | — | — | no | NOT_YET_DERIVED | **D** |

## Semantic Row Matrix (908 rows) — grouped by disposition


### Disposition A — CAUSAL_PROVEN + ADMITTED (4 rows)

| SEMANTIC_ID | NORMALIZED_TARGET | FAMILY | TIER | EVIDENCE |
|---|---|---|---|---|
| ENV1.ATTACK | Env1.Attack | TARGET_BACKED_CENSUS_VERIFIED | EXECUTED_WITH_FRESH_EVIDENCE | Joined to normalized target Env1.Attack: Phase 3/4A bulk execution (baseline->mutation->observed->restored) |
| ENV1.DECAY | Env1.Decay | TARGET_BACKED_CENSUS_VERIFIED | ADMITTED_BINDING_READY_UNTESTED | Joined to normalized target Env1.Decay: CAUSAL_VERIFIED contract + execution_binding attached, no bulk-execution run yet |
| ENV1.RELEASE | Env1.Release | TARGET_BACKED_CENSUS_VERIFIED | ADMITTED_BINDING_READY_UNTESTED | Joined to normalized target Env1.Release: CAUSAL_VERIFIED contract + execution_binding attached, no bulk-execution run yet |
| ENV1.SUSTAIN | Env1.Sustain | TARGET_BACKED_CENSUS_VERIFIED | ADMITTED_BINDING_READY_UNTESTED | Joined to normalized target Env1.Sustain: CAUSAL_VERIFIED contract + execution_binding attached, no bulk-execution run yet |

### Disposition D — not-yet-derived (786 rows)

| SEMANTIC_ID | NORMALIZED_TARGET | FAMILY | TIER | EVIDENCE |
|---|---|---|---|---|
| ARP.GLOBAL.BANK | — | UNKNOWN_EXECUTION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.GLOBAL.EDIT_ALL | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.GLOBAL.LAUNCH_QUANT | — | UI_ACTION_ARP | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| ARP.MIDI_OUT | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.PATTERN.BPM_HZ | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.PATTERN.DOT | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.PATTERN.EDITOR.ADD_LANE_MENU | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.PATTERN.EDITOR.LENGTH | — | UI_ACTION_ARP | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| ARP.PATTERN.EDITOR.MODE | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.PATTERN.EDITOR.PATTERN_SELECT | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.PATTERN.EDITOR.PITCH | — | UI_ACTION_ARP | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| ARP.PATTERN.EDITOR.RANGE | — | UI_ACTION_ARP | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| ARP.PATTERN.EDITOR.STEP_GRID | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.PATTERN.EDITOR.STEP_MODE | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.PATTERN.EDITOR.TIME | — | UI_ACTION_ARP | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| ARP.PATTERN.EDITOR.VELOCITY_LANE | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.PATTERN.EDITOR.VEL_RAND_LANE | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.PATTERN.EDITOR.WRAP | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.PATTERN.EDITOR.WRAP_PHANTOM_NOTE | — | UI_ACTION_ARP | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| ARP.PATTERN.EDIT_TOGGLE | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.PATTERN.RATE | — | UI_ACTION_ARP | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| ARP.PATTERN.SHAPE | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.PATTERN.SHAPE_PATTERN_MODE | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.PATTERN.TRIP | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.PLAYBACK.CHANCE | — | UI_ACTION_ARP | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| ARP.PLAYBACK.CHANCE_PRE | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.PLAYBACK.GATE | — | UI_ACTION_ARP | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| ARP.PLAYBACK.LATCH | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.PLAYBACK.OFFSET | — | UI_ACTION_ARP | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| ARP.PLAYBACK.REPEATS | — | UI_ACTION_ARP | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| ARP.PLAYBACK.THRU | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.RETRIGGER.FIRST | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.RETRIGGER.LAUNCH | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.RETRIGGER.NOTE | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.RETRIGGER.RATE_ENABLE | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.RETRIGGER.RATE_VALUE | — | UI_ACTION_ARP | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| ARP.SLOT.CONTEXT_MENU | — | STRUCTURAL_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.SLOT.COUNT | — | STRUCTURAL_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.SLOT.MIDI_KEYBOARD_LAUNCH | — | STRUCTURAL_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.SLOT.PLAY_BUTTON | — | STRUCTURAL_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.SLOT.SUMMARY_DISPLAY | — | STRUCTURAL_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.TRANSPOSE.RANGE | — | UI_ACTION_ARP | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| ARP.TRANSPOSE.SHAPE | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.TRANSPOSE.SHIFT | — | UI_ACTION_ARP | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| ARP.VELOCITY.DECAY | — | UI_ACTION_ARP | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| ARP.VELOCITY.ENABLE | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.VELOCITY.RETRIG | — | UI_ACTION_ARP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ARP.VELOCITY.TARGET | — | UI_ACTION_ARP | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| BROWSER.CATEGORIES_TAGS.CATEGORY_LIST | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.CATEGORIES_TAGS.RATING_FILTER | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.CATEGORIES_TAGS.TAG_LIST | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.CATEGORIES_TAGS.TOGGLE | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.FOLDERS.CREATE_EXPORT_PACK | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.FOLDERS.TREE | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.MENU.AUTO_PLAY_PREVIEWS | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.MENU.DELETE_PRESETS | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.MENU.ERASE_REBUILD_DATABASE | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.MENU.HYBRIDIZE | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.MENU.HYBRIDIZE_FAVORING_SELECTED | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.MENU.LOAD_RANDOM_PRESET | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.MENU.PREVIEW_FALLBACK_CLIP | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.MENU.RENAME_MOVE_PRESET | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.MENU.RESCAN_DATABASE | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.MENU.SHOW_IN_FOLDER | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.METADATA.AUTHOR | — | RESOURCE_OPERATION | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (META_STRING V4 population: meta_key='presetAuthor' confirmed present in real .SerumPreset meta dict evid... |
| BROWSER.METADATA.CATEGORY | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.METADATA.DESCRIPTION | — | RESOURCE_OPERATION | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (META_STRING V4 population: meta_key='presetDescription' confirmed present in real .SerumPreset meta dict... |
| BROWSER.METADATA.NOTES | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.METADATA.PRESET_NAME | — | RESOURCE_OPERATION | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (META_STRING V4 population: meta_key='presetName' confirmed present in real .SerumPreset meta dict eviden... |
| BROWSER.METADATA.TAGS_PANEL | — | RESOURCE_OPERATION | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (META_STRING V4 population: meta_key='tags' confirmed present in real .SerumPreset meta dict evidence. se... |
| BROWSER.NAVIGATION.PRESET_DROPDOWN | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.NAVIGATION.PREV_NEXT | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.NAVIGATION.SAVE_ICON | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.PACKS.GET_PACKS | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.PACKS.IMPORT | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.PRESET_LIST.COLUMNS | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.PRESET_LIST.RATING_STARS | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.PRESET_LIST.ROW_CONTEXT_MENU | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.PRESET_LIST.ROW_SELECT_LOAD | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.SEARCH.CLEAR | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.SEARCH.FIELD | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| BROWSER.TOGGLE | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.EDITOR.HEAR_SELECTED | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.EDITOR.NOTE_GRID | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.EDITOR.VELOCITY_LANE | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.GLOBAL.BANK | — | UNKNOWN_EXECUTION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.GLOBAL.EDIT_ALL | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.GLOBAL.SHOW_MACROS | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.GLOBAL.TRIGGER_MODE | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.METRONOME | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.MIDI_OUT | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.PLAYER.ENABLE | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.RECORD | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.RECORD_MODE | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.SETTINGS.CLIP_SELECT | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.SETTINGS.KB_SPAN | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.SETTINGS.LAUNCH_QUANT | — | UI_ACTION_CLIP | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| CLIP.SETTINGS.LENGTH | — | UI_ACTION_CLIP | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| CLIP.SETTINGS.MODE | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.SETTINGS.NOTE_GATE | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.SETTINGS.OFFSET | CLIP.SETTINGS.OFFSET | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target CLIP.SETTINGS.OFFSET: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence ye... |
| CLIP.SETTINGS.RATE | — | UI_ACTION_CLIP | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| CLIP.SETTINGS.RATE_BPM_HZ | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.SETTINGS.RATE_DOT | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.SETTINGS.RATE_TRIP | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.SETTINGS.RETRIG | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.SETTINGS.TIME | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.SETTINGS.TRANS | — | UI_ACTION_CLIP | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| CLIP.SETTINGS.VELO_TRIG | — | UI_ACTION_CLIP | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.SLOT.CONTEXT_MENU | — | STRUCTURAL_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.SLOT.COUNT | — | STRUCTURAL_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| CLIP.SLOT.PLAY_BUTTON | — | STRUCTURAL_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ENV1.ATK_CURVE | ENV1.ATK_CURVE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target ENV1.ATK_CURVE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV1.BPM | — | UI_ACTION_ENV | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ENV1.DEC_CURVE | ENV1.DEC_CURVE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target ENV1.DEC_CURVE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV1.HOLD | ENV1.HOLD | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target ENV1.HOLD: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV1.LEGATOINVERTED | — | UI_ACTION_ENV | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ENV1.REL_CURVE | ENV1.REL_CURVE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target ENV1.REL_CURVE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV1.VOICESTEALRETRIGGERMODE | — | UI_ACTION_ENV | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ENV2.ATK_CURVE | ENV2.ATK_CURVE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target ENV2.ATK_CURVE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV2.ATTACK | Env2.Attack | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target Env2.Attack: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV2.BPM | — | UI_ACTION_ENV | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ENV2.DECAY | Env2.Decay | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target Env2.Decay: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV2.DEC_CURVE | ENV2.DEC_CURVE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target ENV2.DEC_CURVE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV2.HOLD | ENV2.HOLD | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target ENV2.HOLD: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV2.LEGATOINVERTED | — | UI_ACTION_ENV | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ENV2.RELEASE | Env2.Release | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target Env2.Release: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV2.REL_CURVE | ENV2.REL_CURVE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target ENV2.REL_CURVE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV2.SUSTAIN | Env2.Sustain | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target Env2.Sustain: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV2.VOICESTEALRETRIGGERMODE | — | UI_ACTION_ENV | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ENV3.ATK_CURVE | ENV3.ATK_CURVE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target ENV3.ATK_CURVE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV3.ATTACK | Env3.Attack | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target Env3.Attack: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV3.BPM | — | UI_ACTION_ENV | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ENV3.DECAY | Env3.Decay | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target Env3.Decay: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV3.DEC_CURVE | ENV3.DEC_CURVE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target ENV3.DEC_CURVE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV3.HOLD | ENV3.HOLD | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target ENV3.HOLD: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV3.LEGATOINVERTED | — | UI_ACTION_ENV | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ENV3.RELEASE | Env3.Release | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target Env3.Release: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV3.REL_CURVE | ENV3.REL_CURVE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target ENV3.REL_CURVE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV3.SUSTAIN | Env3.Sustain | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target Env3.Sustain: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV3.VOICESTEALRETRIGGERMODE | — | UI_ACTION_ENV | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ENV4.ATK_CURVE | ENV4.ATK_CURVE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target ENV4.ATK_CURVE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV4.ATTACK | Env4.Attack | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target Env4.Attack: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV4.BPM | — | UI_ACTION_ENV | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ENV4.DECAY | Env4.Decay | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target Env4.Decay: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV4.DEC_CURVE | ENV4.DEC_CURVE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target ENV4.DEC_CURVE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV4.HOLD | ENV4.HOLD | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target ENV4.HOLD: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV4.LEGATOINVERTED | — | UI_ACTION_ENV | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| ENV4.RELEASE | Env4.Release | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target Env4.Release: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV4.REL_CURVE | ENV4.REL_CURVE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target ENV4.REL_CURVE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV4.SUSTAIN | Env4.Sustain | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target Env4.Sustain: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| ENV4.VOICESTEALRETRIGGERMODE | — | UI_ACTION_ENV | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FILTER1.CUTOFF | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| FILTER1.DRIVE | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| FILTER1.KEYTRACK | — | UI_ACTION_FILTER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FILTER1.MUTE | — | UI_ACTION_FILTER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FILTER1.RESONANCE | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| FILTER1.ROUTENOISE | — | UI_ACTION_FILTER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FILTER1.ROUTEOSCA | — | UI_ACTION_FILTER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FILTER1.ROUTEOSCB | — | UI_ACTION_FILTER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FILTER1.ROUTEOSCC | — | UI_ACTION_FILTER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FILTER1.ROUTESUB | — | UI_ACTION_FILTER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FILTER1.STEREO | FILTER1.STEREO | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FILTER1.STEREO: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FILTER1.TYPE | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| FILTER1.TYPE_SPECIFIC.BOEUF | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER1.TYPE_SPECIFIC.COMBFREQ | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER1.TYPE_SPECIFIC.DAMP | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER1.TYPE_SPECIFIC.FAT | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER1.TYPE_SPECIFIC.FORMANT | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER1.TYPE_SPECIFIC.FREQ2 | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER1.TYPE_SPECIFIC.FREQ2COMB | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER1.TYPE_SPECIFIC.GAINDB | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER1.TYPE_SPECIFIC.HLWIDTH | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER1.TYPE_SPECIFIC.HPFREQ | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER1.TYPE_SPECIFIC.LPFREQ | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER1.TYPE_SPECIFIC.MIXALT | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER1.TYPE_SPECIFIC.MORPH | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER1.TYPE_SPECIFIC.PAIN | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER1.TYPE_SPECIFIC.SCREAMAMT | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER1.TYPE_SPECIFIC.SMOOTH | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER1.TYPE_SPECIFIC.SPREAD | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER1.TYPE_SPECIFIC.STAGES | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER1.TYPE_SPECIFIC.THRU | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER1.TYPE_SPECIFIC.WIDTH | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER1.VAR | FILTER1.VAR | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FILTER1.VAR: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FILTER2.DRIVE | Filter2.Drive | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target Filter2.Drive: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FILTER2.KEYTRACK | — | UI_ACTION_FILTER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FILTER2.MUTE | — | UI_ACTION_FILTER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FILTER2.ROUTENOISE | — | UI_ACTION_FILTER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FILTER2.ROUTEOSCA | — | UI_ACTION_FILTER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FILTER2.ROUTEOSCB | — | UI_ACTION_FILTER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FILTER2.ROUTEOSCC | — | UI_ACTION_FILTER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FILTER2.ROUTESUB | — | UI_ACTION_FILTER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FILTER2.STEREO | FILTER2.STEREO | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FILTER2.STEREO: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FILTER2.TYPE | Filter2.Type | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target Filter2.Type: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FILTER2.TYPE_SPECIFIC.BOEUF | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER2.TYPE_SPECIFIC.COMBFREQ | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER2.TYPE_SPECIFIC.DAMP | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER2.TYPE_SPECIFIC.FAT | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER2.TYPE_SPECIFIC.FORMANT | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER2.TYPE_SPECIFIC.FREQ2 | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER2.TYPE_SPECIFIC.FREQ2COMB | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER2.TYPE_SPECIFIC.GAINDB | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER2.TYPE_SPECIFIC.HLWIDTH | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER2.TYPE_SPECIFIC.HPFREQ | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER2.TYPE_SPECIFIC.LPFREQ | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER2.TYPE_SPECIFIC.MIXALT | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER2.TYPE_SPECIFIC.MORPH | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER2.TYPE_SPECIFIC.PAIN | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER2.TYPE_SPECIFIC.SCREAMAMT | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER2.TYPE_SPECIFIC.SMOOTH | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER2.TYPE_SPECIFIC.SPREAD | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER2.TYPE_SPECIFIC.STAGES | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER2.TYPE_SPECIFIC.THRU | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER2.TYPE_SPECIFIC.WIDTH | — | BODY_STATE_FIELD_FILTER | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (FILTER TYPE_SPECIFIC reconciliation pass: real-Serum-in-Ableton UI check (not guessed) across 3 distinct... |
| FILTER2.VAR | FILTER2.VAR | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FILTER2.VAR: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.BODE.BALANCE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.BODE.BLUR | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.BODE.BPM | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.BODE.DELAY | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.BODE.DIR | — | UNCLASSIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.BODE.FEED | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.BODE.MONO_INPUT | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.BODE.RANGE | FXBODE.Range | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXBODE.Range: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.BODE.SHIFT | FXBODE.Shift | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXBODE.Shift: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.BODE.SHIFT_RETRIG | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.BODE.WET | — | UNCLASSIFIED | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.BODE.WIDTH | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.CHORUS.BPM | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.CHORUS.DELAY1 | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.CHORUS.DELAY2 | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.CHORUS.DEPTH | FXChorus.Depth | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXChorus.Depth: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.CHORUS.FEEDBACK | FXChorus.Feedback | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXChorus.Feedback: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.CHORUS.FILTER_CUTOFF | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.CHORUS.FILTER_MODE | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.CHORUS.RATE | FXChorus.Rate | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXChorus.Rate: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.CHORUS.WET | — | UNCLASSIFIED | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.COMPRESSOR.ATTACK | FXCompressor.Attack | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXCompressor.Attack: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.COMPRESSOR.BAND_H | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.COMPRESSOR.BAND_L | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.COMPRESSOR.BAND_M | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.COMPRESSOR.BELOW | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.COMPRESSOR.GAIN | FXCompressor.Gain | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXCompressor.Gain: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.COMPRESSOR.MODE | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.COMPRESSOR.RATIO | FXCompressor.Ratio | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXCompressor.Ratio: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.COMPRESSOR.RELEASE | FXCompressor.Release | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXCompressor.Release: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence ye... |
| FX.COMPRESSOR.THRESH | — | UNCLASSIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.COMPRESSOR.WET | — | UNCLASSIFIED | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.COMPRESSOR.X_HIGH | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.COMPRESSOR.X_LOW | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.CONVOLVE.ATTACK | FXConvolve.Attack | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXConvolve.Attack: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.CONVOLVE.BPM | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.CONVOLVE.DAMP | — | UNCLASSIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.CONVOLVE.DECAY | FXConvolve.Decay | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXConvolve.Decay: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.CONVOLVE.IR_BROWSER | — | UNKNOWN_EXECUTION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.CONVOLVE.IR_GAIN | FXConvolve.IRGain | UNCLASSIFIED | NOT_YET_DERIVED | Joined to normalized target FXConvolve.IRGain: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.CONVOLVE.IR_NEXT_PREV | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.CONVOLVE.LOAD_IR_EXTERNAL | — | UNKNOWN_EXECUTION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.CONVOLVE.MIN_PHASE | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.CONVOLVE.PRE_DLY | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.CONVOLVE.SIZE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.CONVOLVE.TONE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.CONVOLVE.WET | — | UNCLASSIFIED | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.DELAY.BPM | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.DELAY.FEEDBACK | FXDelay.Feedback | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXDelay.Feedback: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.DELAY.FILTER_GRAPH | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.DELAY.FREQ | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.DELAY.HIGH_QUALITY | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.DELAY.LINK | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.DELAY.MODE | FXDelay.Mode | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXDelay.Mode: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.DELAY.Q | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.DELAY.TIME_L | FXDelay.TimeL | UNCLASSIFIED | NOT_YET_DERIVED | Joined to normalized target FXDelay.TimeL: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.DELAY.TIME_R | FXDelay.TimeR | UNCLASSIFIED | NOT_YET_DERIVED | Joined to normalized target FXDelay.TimeR: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.DELAY.WET | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.DIMENSION.SIZE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.DIMENSION.WET | — | UNCLASSIFIED | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.DISTORTION.DRIVE | FXDistortion.Drive | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXDistortion.Drive: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.DISTORTION.FILTER_GRAPH | — | UNCLASSIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.DISTORTION.FILTER_POSITION | — | UI_ACTION_FX | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.DISTORTION.FREQ | FXDistortion.Freq | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXDistortion.Freq: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.DISTORTION.Q | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.DISTORTION.TYPE | — | UI_ACTION_FX | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.DISTORTION.WAVEFORM_PREVIEW | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.DISTORTION.WET | — | UNCLASSIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.DISTORTION.XSHAPER_A | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.DISTORTION.XSHAPER_B | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.EQUALIZER.GRAPH | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.EQUALIZER.LEFT_FREQ | — | UNCLASSIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.EQUALIZER.LEFT_GAIN | — | UNCLASSIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.EQUALIZER.LEFT_Q | — | UNCLASSIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.EQUALIZER.LEFT_TYPE | — | UI_ACTION_FX | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.EQUALIZER.RIGHT_FREQ | — | UNCLASSIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.EQUALIZER.RIGHT_GAIN | — | UNCLASSIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.EQUALIZER.RIGHT_Q | — | UNCLASSIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.EQUALIZER.RIGHT_TYPE | — | UI_ACTION_FX | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.FILTER.CUTOFF | FXFilter.Cutoff | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXFilter.Cutoff: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.FILTER.DRIVE | FXFilter.Drive | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXFilter.Drive: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.FILTER.FAT | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.FILTER.GRAPH | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.FILTER.KEY_TRACK | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.FILTER.PAN | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.FILTER.RES | — | UNCLASSIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.FILTER.TYPE | FXFilter.Type | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXFilter.Type: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.FILTER.WET | — | UNCLASSIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.FLANGER.BPM | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.FLANGER.DEPTH | FXFlanger.Depth | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXFlanger.Depth: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.FLANGER.FEEDBACK | FXFlanger.Feedback | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXFlanger.Feedback: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.FLANGER.PHASE | FXFlanger.Phase | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXFlanger.Phase: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.FLANGER.RATE | FXFlanger.Rate | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXFlanger.Rate: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.FLANGER.WET | — | UNCLASSIFIED | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.HYPER.DETUNE | FXHyper.Detune | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXHyper.Detune: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.HYPER.RATE | FXHyper.Rate | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXHyper.Rate: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.HYPER.RETRIG | — | UI_ACTION_FX | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.HYPER.UNISON | FXHyper.Unison | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXHyper.Unison: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.HYPER.WET | — | UNCLASSIFIED | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.HYPER_DIMENSION.STRUCTURE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.PHASER.BPM | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.PHASER.DEPTH | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.PHASER.DEPTH2 | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.PHASER.FEEDBACK | FXPhaser.Feedback | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXPhaser.Feedback: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.PHASER.FREQ | — | UNCLASSIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.PHASER.PHASE | FXPhaser.Phase | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXPhaser.Phase: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.PHASER.POLES | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.PHASER.RATE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.PHASER.WET | — | UNCLASSIFIED | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.REVERB.CHORUS_MOD | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.REVERB.DAMP_PLATE | — | UNCLASSIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.REVERB.DAMP_VINTAGE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.REVERB.DECAY_HALL | — | UNCLASSIFIED | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.REVERB.DIFFUSION_NITROUS | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.REVERB.DIFF_A_VINTAGE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.REVERB.DIFF_B_VINTAGE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.REVERB.ER_SIZE_VINTAGE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.REVERB.FEEDBACK_NITROUS_BASIN | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.REVERB.HI_CUT | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.REVERB.LO_CUT | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.REVERB.MODE_NITROUS | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.REVERB.PRE_DLY | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.REVERB.SIZE | FXReverb.Size | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target FXReverb.Size: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| FX.REVERB.SPIN_HALL | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.REVERB.TYPE | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.REVERB.WET | — | UNCLASSIFIED | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.REVERB.WIDTH_PLATE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.SPLITTER_LH.HIGHS_BYPASS | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SPLITTER_LH.HIGHS_RACK | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SPLITTER_LH.HIGHS_SELECT | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SPLITTER_LH.LOWS_BYPASS | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SPLITTER_LH.LOWS_RACK | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SPLITTER_LH.LOWS_SELECT | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SPLITTER_LH.SPLIT_FREQ | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.SPLITTER_LH.STRUCTURE | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SPLITTER_LH.WET | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.SPLITTER_LMH.HIGHS_BYPASS | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SPLITTER_LMH.HIGHS_RACK | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SPLITTER_LMH.LOWS_BYPASS | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SPLITTER_LMH.LOWS_RACK | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SPLITTER_LMH.MIDS_BYPASS | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SPLITTER_LMH.MIDS_RACK | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SPLITTER_LMH.SPLIT_FREQ_LOW_MID | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.SPLITTER_LMH.SPLIT_FREQ_MID_HIGH | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.SPLITTER_LMH.STRUCTURE | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SPLITTER_LMH.WET | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.SPLITTER_MS.MID_BYPASS | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SPLITTER_MS.MID_RACK | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SPLITTER_MS.SIDE_BYPASS | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SPLITTER_MS.SIDE_RACK | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SPLITTER_MS.STRUCTURE | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SYS.ADD_FX_MENU | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SYS.MODULE_BYPASS | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SYS.MODULE_CONTEXT_MENU | — | UNKNOWN_EXECUTION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SYS.MODULE_LIST_PANEL | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SYS.MODULE_PARAM_CONTEXT_MENU | — | STRUCTURAL_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SYS.RACKS | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SYS.RACK_PRESET_BROWSER | — | UNKNOWN_EXECUTION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.SYS.REORDER | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.UTILITY.FREQ | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.UTILITY.HPF | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.UTILITY.LPF | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.UTILITY.MONO_BASS | — | UI_ACTION_FX | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| FX.UTILITY.PAN | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| FX.UTILITY.POLARITY_INV_L | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.UTILITY.POLARITY_INV_R | — | UI_ACTION_FX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.UTILITY.WET | — | UNCLASSIFIED | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| FX.UTILITY.WIDTH | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.PREFERENCES.DEFAULT_WAVEFORM_VIEW | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.PREFERENCES.DOUBLE_CLICK_PARAMS | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.PREFERENCES.HELP_TOOLTIPS | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.PREFERENCES.KEYBOARD_SHORTCUTS | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.PREFERENCES.MOUSE_WHEEL_PARAM_CONTROL | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.PREFERENCES.MPE_ENABLED_BY_DEFAULT | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.PREFERENCES.MPE_EXPR_Y_ACTS_BI_DIRECTIONAL | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.PREFERENCES.MPE_PITCH_BEND_MAPS_TO_EXPR_X | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.PREFERENCES.PARAM_VALUE_TOOLTIPS | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.QUALITY.DISABLE_SMOOTHING | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.QUALITY.OVERSAMPLING | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.QUALITY.OVERSAMPLING_LOCK | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.QUALITY.S1_COMPATIBILITY | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.TUNING.GLOBAL_TUNING | — | TARGET_BACKED_CENSUS_VERIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| GLOBAL.TUNING.LOCK | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.TUNING.TUN_FILE | — | UNKNOWN_EXECUTION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| GLOBAL.VOICE_CONTROL.OSC_SCOPE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.VOICE_CONTROL.PRESET_FIELD | — | UNKNOWN_EXECUTION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| GLOBAL.VOICE_CONTROL.RANDOM.CUTOFF | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.VOICE_CONTROL.RANDOM.DETUNE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.VOICE_CONTROL.RANDOM.ENVS | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.VOICE_CONTROL.RANDOM.PAN | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.VOICE_CONTROL.SCALING.ENVS | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.VOICE_CONTROL.SCALING.LFOS | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.VOICE_CONTROL.SCALING.LFOS_RATE_TOGGLE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.VOICE_CONTROL.SEQ.CUTOFF | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.VOICE_CONTROL.SEQ.DETUNE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.VOICE_CONTROL.SEQ.ENVS | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.VOICE_CONTROL.SEQ.MOD1 | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.VOICE_CONTROL.SEQ.MOD2 | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| GLOBAL.VOICE_CONTROL.SEQ.PAN | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| KEYBOARD.KEY | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| KEYBOARD.MAIN_KEYBOARD | — | UI_ACTION_GLOBAL_KEYBOARD | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| KEYBOARD.MOD_WHEEL | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| KEYBOARD.MOD_WHEEL.SOURCE_INDICATOR | — | UI_ACTION_GLOBAL_KEYBOARD | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| KEYBOARD.MPE.BEND_RANGE | — | UI_ACTION_GLOBAL_KEYBOARD | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| KEYBOARD.MPE.ENABLED | — | UI_ACTION_GLOBAL_KEYBOARD | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| KEYBOARD.MPE.XYZ_TO_MACROS123 | — | UI_ACTION_GLOBAL_KEYBOARD | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| KEYBOARD.MPE.YZ_TO_MACROS12 | — | UI_ACTION_GLOBAL_KEYBOARD | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| KEYBOARD.MPE.Y_TO_MODWHEEL | — | UI_ACTION_GLOBAL_KEYBOARD | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| KEYBOARD.OSC_MAPPING.ARP_ROW_FOLD | — | UI_ACTION_GLOBAL_KEYBOARD | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| KEYBOARD.OSC_MAPPING.ARP_ROW_KEY_RANGE | — | UI_ACTION_GLOBAL_KEYBOARD | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| KEYBOARD.OSC_MAPPING.ARP_ROW_WARP | — | UI_ACTION_GLOBAL_KEYBOARD | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| KEYBOARD.OSC_MAPPING.EDITOR | — | UI_ACTION_GLOBAL_KEYBOARD | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| KEYBOARD.OSC_MAPPING.RESET_ALL | — | UI_ACTION_GLOBAL_KEYBOARD | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| KEYBOARD.OSC_MAPPING.VEL_TAB | — | UI_ACTION_GLOBAL_KEYBOARD | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| KEYBOARD.PITCH_BEND | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| KEYBOARD.PITCH_BEND.BEND_DOWN | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| KEYBOARD.PITCH_BEND.BEND_UP | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| KEYBOARD.SCALE | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| KEYBOARD.SWING | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| KEYBOARD.TRANSPOSE | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| LFO1.DELAY | LFO1.DELAY | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO1.DELAY: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO1.DIRECTION | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO V4 population: body_path='LFO0.plainParams.kParamDirection' confirmed present in real .SerumPreset e... |
| LFO1.DIVISION | — | BODY_STATE_FIELD_LFO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| LFO1.DOTTED | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO reconciliation pass: real-Serum-in-Ableton manual UI toggle -> Serum-own-save -> CBOR diff (same for... |
| LFO1.PHASE | LFO1.Phase | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO1.Phase: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO1.PRESET | — | BODY_STATE_FIELD_LFO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| LFO1.RATE | LFO1.Rate | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO1.Rate: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO1.RISE | LFO1.RISE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO1.RISE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO1.SMOOTH | LFO1.SMOOTH | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO1.SMOOTH: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO1.TEMPO_SYNC | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO reconciliation pass (continued): real-Serum-in-Ableton manual UI toggle of the BPM/HZ sync-mode butt... |
| LFO1.TRIGGER_MODE | — | UI_ACTION_LFO | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| LFO1.TRIPLET | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO reconciliation pass: real-Serum-in-Ableton manual UI toggle -> Serum-own-save -> CBOR diff (same for... |
| LFO1.TYPE | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO V4 population: body_path='LFO0.plainParams.kParamType' confirmed present in real .SerumPreset eviden... |
| LFO1.WAVEFORM_GRAPH | — | BODY_STATE_FIELD_LFO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| LFO2.DELAY | LFO2.DELAY | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO2.DELAY: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO2.DIRECTION | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO V4 population: body_path='LFO1.plainParams.kParamDirection' confirmed present in real .SerumPreset e... |
| LFO2.DIVISION | — | BODY_STATE_FIELD_LFO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| LFO2.DOTTED | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO reconciliation pass: real-Serum-in-Ableton manual UI toggle -> Serum-own-save -> CBOR diff (same for... |
| LFO2.PHASE | LFO2.Phase | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO2.Phase: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO2.PRESET | — | BODY_STATE_FIELD_LFO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| LFO2.RATE | LFO2.Rate | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO2.Rate: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO2.RISE | LFO2.RISE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO2.RISE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO2.SMOOTH | LFO2.SMOOTH | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO2.SMOOTH: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO2.TEMPO_SYNC | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO reconciliation pass (continued): real-Serum-in-Ableton manual UI toggle of the BPM/HZ sync-mode butt... |
| LFO2.TRIGGER_MODE | — | UI_ACTION_LFO | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| LFO2.TRIPLET | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO reconciliation pass: real-Serum-in-Ableton manual UI toggle -> Serum-own-save -> CBOR diff (same for... |
| LFO2.TYPE | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO V4 population: body_path='LFO1.plainParams.kParamType' confirmed present in real .SerumPreset eviden... |
| LFO2.WAVEFORM_GRAPH | — | BODY_STATE_FIELD_LFO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| LFO3.DELAY | LFO3.DELAY | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO3.DELAY: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO3.DIRECTION | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO V4 population: body_path='LFO2.plainParams.kParamDirection' confirmed present in real .SerumPreset e... |
| LFO3.DIVISION | — | BODY_STATE_FIELD_LFO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| LFO3.DOTTED | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO reconciliation pass: real-Serum-in-Ableton manual UI toggle -> Serum-own-save -> CBOR diff (same for... |
| LFO3.PHASE | LFO3.Phase | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO3.Phase: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO3.PRESET | — | BODY_STATE_FIELD_LFO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| LFO3.RATE | LFO3.Rate | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO3.Rate: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO3.RISE | LFO3.RISE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO3.RISE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO3.SMOOTH | LFO3.SMOOTH | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO3.SMOOTH: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO3.TEMPO_SYNC | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO reconciliation pass (continued): real-Serum-in-Ableton manual UI toggle of the BPM/HZ sync-mode butt... |
| LFO3.TRIGGER_MODE | — | UI_ACTION_LFO | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| LFO3.TRIPLET | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO reconciliation pass: real-Serum-in-Ableton manual UI toggle -> Serum-own-save -> CBOR diff (same for... |
| LFO3.TYPE | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO V4 population: body_path='LFO2.plainParams.kParamType' confirmed present in real .SerumPreset eviden... |
| LFO3.WAVEFORM_GRAPH | — | BODY_STATE_FIELD_LFO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| LFO4.DELAY | LFO4.DELAY | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO4.DELAY: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO4.DIRECTION | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO V4 population: body_path='LFO3.plainParams.kParamDirection' confirmed present in real .SerumPreset e... |
| LFO4.DIVISION | — | BODY_STATE_FIELD_LFO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| LFO4.DOTTED | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO reconciliation pass: real-Serum-in-Ableton manual UI toggle -> Serum-own-save -> CBOR diff (same for... |
| LFO4.PHASE | LFO4.Phase | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO4.Phase: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO4.PRESET | — | BODY_STATE_FIELD_LFO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| LFO4.RATE | LFO4.Rate | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO4.Rate: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO4.RISE | LFO4.RISE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO4.RISE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO4.SMOOTH | LFO4.SMOOTH | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO4.SMOOTH: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO4.TEMPO_SYNC | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO reconciliation pass (continued): real-Serum-in-Ableton manual UI toggle of the BPM/HZ sync-mode butt... |
| LFO4.TRIGGER_MODE | — | UI_ACTION_LFO | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| LFO4.TRIPLET | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO reconciliation pass: real-Serum-in-Ableton manual UI toggle -> Serum-own-save -> CBOR diff (same for... |
| LFO4.TYPE | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO V4 population: body_path='LFO3.plainParams.kParamType' confirmed present in real .SerumPreset eviden... |
| LFO4.WAVEFORM_GRAPH | — | BODY_STATE_FIELD_LFO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| LFO5.DELAY | LFO5.DELAY | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO5.DELAY: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO5.DIRECTION | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO V4 population: body_path='LFO4.plainParams.kParamDirection' confirmed present in real .SerumPreset e... |
| LFO5.DIVISION | — | BODY_STATE_FIELD_LFO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| LFO5.DOTTED | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO reconciliation pass: real-Serum-in-Ableton manual UI toggle -> Serum-own-save -> CBOR diff (same for... |
| LFO5.PHASE | LFO5.Phase | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO5.Phase: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO5.PRESET | — | BODY_STATE_FIELD_LFO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| LFO5.RATE | LFO5.Rate | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO5.Rate: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO5.RISE | LFO5.RISE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO5.RISE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO5.SMOOTH | LFO5.SMOOTH | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO5.SMOOTH: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO5.TEMPO_SYNC | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO reconciliation pass (continued): real-Serum-in-Ableton manual UI toggle of the BPM/HZ sync-mode butt... |
| LFO5.TRIGGER_MODE | — | UI_ACTION_LFO | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| LFO5.TRIPLET | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO reconciliation pass: real-Serum-in-Ableton manual UI toggle -> Serum-own-save -> CBOR diff (same for... |
| LFO5.TYPE | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO V4 population: body_path='LFO4.plainParams.kParamType' confirmed present in real .SerumPreset eviden... |
| LFO5.WAVEFORM_GRAPH | — | BODY_STATE_FIELD_LFO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| LFO6.DELAY | LFO6.DELAY | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO6.DELAY: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO6.DIRECTION | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO V4 population: body_path='LFO5.plainParams.kParamDirection' confirmed present in real .SerumPreset e... |
| LFO6.DIVISION | — | BODY_STATE_FIELD_LFO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| LFO6.DOTTED | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO reconciliation pass: real-Serum-in-Ableton manual UI toggle -> Serum-own-save -> CBOR diff (same for... |
| LFO6.PHASE | LFO6.Phase | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO6.Phase: 2D.6J table_b: UNKNOWN disposition, no contract |
| LFO6.PRESET | — | BODY_STATE_FIELD_LFO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| LFO6.RATE | LFO6.Rate | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO6.Rate: 2D.6J table_b: UNKNOWN disposition, no contract |
| LFO6.RISE | LFO6.RISE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO6.RISE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO6.SMOOTH | LFO6.SMOOTH | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target LFO6.SMOOTH: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| LFO6.TEMPO_SYNC | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO reconciliation pass (continued): real-Serum-in-Ableton manual UI toggle of the BPM/HZ sync-mode butt... |
| LFO6.TRIGGER_MODE | — | UI_ACTION_LFO | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| LFO6.TRIPLET | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO reconciliation pass: real-Serum-in-Ableton manual UI toggle -> Serum-own-save -> CBOR diff (same for... |
| LFO6.TYPE | — | BODY_STATE_FIELD_LFO | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (LFO V4 population: body_path='LFO5.plainParams.kParamType' confirmed present in real .SerumPreset eviden... |
| LFO6.WAVEFORM_GRAPH | — | BODY_STATE_FIELD_LFO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.01.NAME | — | UI_ACTION_MACRO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.01.VALUE | — | UI_ACTION_MACRO | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MACRO.02.NAME | — | UI_ACTION_MACRO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.02.VALUE | — | UI_ACTION_MACRO | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MACRO.03.NAME | — | UI_ACTION_MACRO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.03.VALUE | — | UI_ACTION_MACRO | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MACRO.04.NAME | — | UI_ACTION_MACRO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.04.VALUE | — | UI_ACTION_MACRO | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MACRO.05.NAME | — | UI_ACTION_MACRO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.05.VALUE | — | UI_ACTION_MACRO | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MACRO.06.NAME | — | UI_ACTION_MACRO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.06.VALUE | — | UI_ACTION_MACRO | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MACRO.07.NAME | — | UI_ACTION_MACRO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.07.VALUE | — | UI_ACTION_MACRO | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MACRO.08.NAME | — | UI_ACTION_MACRO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.08.VALUE | — | UI_ACTION_MACRO | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MACRO.SYS.APPLY_AND_DELETE_MACRO | — | UI_ACTION_MACRO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.SYS.ASSIGN_DRAG | — | UI_ACTION_MACRO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.SYS.AUX_CURVE | — | MATRIX_ROUTE | MECHANISM_KNOWN_PREREQ_UNMET | Registered COMPOUND compiler 'mod_set_curve' (compiler_set_modulation_curve) writes ModSlot{N}.curve -- real, wired mechanism, not compiler_... |
| MACRO.SYS.AUX_OUTPUT | — | UI_ACTION_MACRO | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MACRO.SYS.AUX_SOURCE | — | MATRIX_ROUTE | MECHANISM_KNOWN_PREREQ_UNMET | Registered COMPOUND compiler 'mod_set_aux_source' (compiler_set_modulation_aux_source) writes ModSlot{N}.auxSource -- real, wired mechanism,... |
| MACRO.SYS.BIPOLAR_UNIPOLAR | — | MATRIX_ROUTE | MECHANISM_KNOWN_PREREQ_UNMET | Registered COMPOUND compiler 'mod_set_bipolar' (compiler_set_modulation_bipolar) writes ModSlot{N}.bipolar -- real, wired mechanism, not com... |
| MACRO.SYS.BROWSER_VIEW_ACCESS | — | UI_ACTION_MACRO | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MACRO.SYS.CENTER_TOGGLE_MODIFIER | — | UI_ACTION_MACRO | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MACRO.SYS.CLIP_VIEW_ACCESS | — | UI_ACTION_MACRO | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MACRO.SYS.COPY_PASTE | — | UI_ACTION_MACRO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.SYS.DELETE_ROUTE | — | UI_ACTION_MACRO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.SYS.INIT_MODULE | — | UI_ACTION_MACRO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.SYS.KNOB_CONTEXT_MENU | — | STRUCTURAL_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.SYS.LOCK_PARAMETER | — | UI_ACTION_MACRO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.SYS.MULTI_ASSIGN_ONE_MACRO | — | UI_ACTION_MACRO | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MACRO.SYS.MULTI_MACRO_SUMMED_DEST | — | UI_ACTION_MACRO | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MACRO.SYS.OUTPUT_MONITOR | — | UI_ACTION_MACRO | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MACRO.SYS.RANGE_DIRECTION_DRAG | — | UI_ACTION_MACRO | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MACRO.SYS.RENAME_MECHANISM | — | UI_ACTION_MACRO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.SYS.RESET_VALUE | — | UI_ACTION_MACRO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.SYS.RISE_FALL_SMOOTH | — | UI_ACTION_MACRO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.SYS.ROUTE_AMOUNT | — | UI_ACTION_MACRO | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MACRO.SYS.SOURCE_CURVE | — | UNKNOWN_EXECUTION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.SYS.TEMP_BYPASS | — | UI_ACTION_MACRO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.SYS.UNASSIGN_RIGHTCLICK | — | UI_ACTION_MACRO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MACRO.SYS.VALUE_AS_MOD_DESTINATION | — | UI_ACTION_MACRO | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MATRIX.LFO_BUS.01 | — | MATRIX_ROUTE | MECHANISM_KNOWN_PREREQ_UNMET | control_type='destination_target': a3_modulation_route._DESTINATIONS now has 5 real, corpus-evidenced per-parameter destination(s) for LFO1 ... |
| MATRIX.LFO_BUS.02 | — | MATRIX_ROUTE | MECHANISM_KNOWN_PREREQ_UNMET | control_type='destination_target': a3_modulation_route._DESTINATIONS now has 5 real, corpus-evidenced per-parameter destination(s) for LFO2 ... |
| MATRIX.LFO_BUS.03 | — | MATRIX_ROUTE | MECHANISM_KNOWN_PREREQ_UNMET | control_type='destination_target': a3_modulation_route._DESTINATIONS now has 5 real, corpus-evidenced per-parameter destination(s) for LFO3 ... |
| MATRIX.LFO_BUS.04 | — | MATRIX_ROUTE | MECHANISM_KNOWN_PREREQ_UNMET | control_type='destination_target': a3_modulation_route._DESTINATIONS now has 5 real, corpus-evidenced per-parameter destination(s) for LFO4 ... |
| MATRIX.LFO_BUS.05 | — | MATRIX_ROUTE | MECHANISM_KNOWN_PREREQ_UNMET | control_type='destination_target': a3_modulation_route._DESTINATIONS now has 1 real, corpus-evidenced per-parameter destination(s) for LFO5 ... |
| MATRIX.LFO_BUS.06 | — | MATRIX_ROUTE | MECHANISM_KNOWN_PREREQ_UNMET | control_type='destination_target': a3_modulation_route._DESTINATIONS now has 1 real, corpus-evidenced per-parameter destination(s) for LFO6 ... |
| MATRIX.LFO_BUS.07 | — | MATRIX_ROUTE | MECHANISM_KNOWN_PREREQ_UNMET | control_type='destination_target': a3_modulation_route._DESTINATIONS now has 1 real, corpus-evidenced per-parameter destination(s) for LFO7 ... |
| MATRIX.LFO_BUS.08 | — | MATRIX_ROUTE | MECHANISM_KNOWN_PREREQ_UNMET | control_type='destination_target': a3_modulation_route._DESTINATIONS now has 1 real, corpus-evidenced per-parameter destination(s) for LFO8 ... |
| MATRIX.LFO_BUS.09 | — | MATRIX_ROUTE | MECHANISM_KNOWN_PREREQ_UNMET | control_type='destination_target': a3_modulation_route._DESTINATIONS now has 2 real, corpus-evidenced per-parameter destination(s) for LFO9 ... |
| MATRIX.LFO_BUS.10 | — | MATRIX_ROUTE | MECHANISM_KNOWN_PREREQ_UNMET | control_type='destination_target': a3_modulation_route._DESTINATIONS now has 1 real, corpus-evidenced per-parameter destination(s) for LFO10... |
| MATRIX.OUT | — | MATRIX_ROUTE | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (MATRIX_ROUTE reconciliation pass (serum2/reconciliation/matrix_route_reconciliation.py): semantic defini... |
| MATRIX.SYS.APPLY_AND_DELETE_MACROS | — | UI_ACTION_MATRIX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MATRIX.SYS.CREATE_VELO_AMP_ASSIGNMENT | — | UI_ACTION_MATRIX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MATRIX.SYS.CREATE_VIBRATO | — | UNKNOWN_EXECUTION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MATRIX.SYS.DYNAMIC_VISUALIZATION | — | UNKNOWN_EXECUTION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MATRIX.SYS.EXPANDED_VIEW | — | UI_ACTION_MATRIX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MATRIX.SYS.LOCK_MATRIX | — | UI_ACTION_MATRIX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MATRIX.SYS.SORT_BY_DESTINATION | — | UI_ACTION_MATRIX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MATRIX.SYS.SORT_BY_SOURCE | — | UI_ACTION_MATRIX | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MIXER.BUS1.LEVEL | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.BUS1.ROUTING | — | UI_ACTION_MIXER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MIXER.BUS2.LEVEL | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.BUS2.ROUTING | — | UI_ACTION_MIXER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MIXER.DIRECT.LEVEL | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MIXER.FILTER1.BUS1 | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.FILTER1.BUS2 | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.FILTER1.ENABLE | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.FILTER1.ENV1_BYPASS | — | UI_ACTION_MIXER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MIXER.FILTER1.LEVEL | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.FILTER1.PAN | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MIXER.FILTER1.ROUTING | — | TARGET_BACKED_CENSUS_VERIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| MIXER.FILTER1.WET | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.FILTER2.BUS1 | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.FILTER2.BUS2 | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.FILTER2.ENABLE | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.FILTER2.ENV1_BYPASS | — | UI_ACTION_MIXER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MIXER.FILTER2.LEVEL | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.FILTER2.PAN | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MIXER.FILTER2.ROUTING | — | TARGET_BACKED_CENSUS_VERIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| MIXER.FILTER2.WET | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.MAIN.LEVEL | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.NOISE.BUS1 | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.NOISE.BUS2 | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.NOISE.ENABLE | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.NOISE.ENV1_BYPASS | — | UI_ACTION_MIXER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MIXER.NOISE.FILTER_BALANCE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MIXER.NOISE.LEVEL | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MIXER.NOISE.PAN | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MIXER.NOISE.ROUTING | — | TARGET_BACKED_CENSUS_VERIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| MIXER.OSC_A.BUS1 | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.OSC_A.BUS2 | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.OSC_A.ENABLE | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.OSC_A.ENV1_BYPASS | — | UI_ACTION_MIXER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MIXER.OSC_A.FILTER_BALANCE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MIXER.OSC_A.LEVEL | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.OSC_A.PAN | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.OSC_A.ROUTING | — | TARGET_BACKED_CENSUS_VERIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| MIXER.OSC_B.BUS1 | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.OSC_B.BUS2 | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.OSC_B.ENABLE | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.OSC_B.ENV1_BYPASS | — | UI_ACTION_MIXER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MIXER.OSC_B.FILTER_BALANCE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MIXER.OSC_B.LEVEL | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.OSC_B.PAN | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.OSC_B.ROUTING | — | TARGET_BACKED_CENSUS_VERIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| MIXER.OSC_C.BUS1 | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.OSC_C.BUS2 | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.OSC_C.ENABLE | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.OSC_C.ENV1_BYPASS | — | UI_ACTION_MIXER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MIXER.OSC_C.FILTER_BALANCE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MIXER.OSC_C.LEVEL | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.OSC_C.PAN | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.OSC_C.ROUTING | — | TARGET_BACKED_CENSUS_VERIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| MIXER.SUB.BUS1 | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.SUB.BUS2 | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.SUB.ENABLE | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| MIXER.SUB.ENV1_BYPASS | — | UI_ACTION_MIXER | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| MIXER.SUB.FILTER_BALANCE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MIXER.SUB.LEVEL | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MIXER.SUB.PAN | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| MIXER.SUB.ROUTING | — | TARGET_BACKED_CENSUS_VERIFIED | MAPPED_LINK_NOT_MACHINE_JOINED | 2D.6J table_a bulk category: MAPPED_TO_EXISTING_TARGET (mapped to a target but this pass has no machine-readable link) |
| NOISE_OSC.FINE | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| NOISE_OSC.LEVEL | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| NOISE_OSC.PAN | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| NOISE_OSC.PHASE | NOISE_OSC.PHASE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target NOISE_OSC.PHASE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| NOISE_OSC.PITCH | NOISE_OSC.PITCH | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target NOISE_OSC.PITCH: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| NOISE_OSC.PITCH_TRACK | NOISE_OSC.PITCH_TRACK | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target NOISE_OSC.PITCH_TRACK: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence y... |
| NOISE_OSC.RAND_PHASE | NOISE_OSC.RAND_PHASE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target NOISE_OSC.RAND_PHASE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence ye... |
| OSC1.COARSE_PITCH | OSC1.COARSE_PITCH | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.COARSE_PITCH: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.END | OSC1.END | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.END: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.FINE | OSC1.FINE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.FINE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.LOOP_END | OSC1.LOOP_END | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.LOOP_END: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.LOOP_MODE | OSC1.LOOP_MODE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.LOOP_MODE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.LOOP_START | OSC1.LOOP_START | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.LOOP_START: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.LOOP_X-FADE | OSC1.LOOP_X-FADE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.LOOP_X-FADE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.OCTAVE | OSC1.Octave | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.Octave: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.PHASE | OSC1.PHASE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.PHASE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.PITCH_TRACK | — | UI_ACTION_OSC | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| OSC1.POSITION | OSC1.POSITION | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.POSITION: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.RAND_PHASE | OSC1.RAND_PHASE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.RAND_PHASE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.RELATIVE_LOOP | — | UI_ACTION_OSC | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| OSC1.REVERSE | — | UI_ACTION_OSC | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| OSC1.SCAN_BPM_RATE | OSC1.SCAN_BPM_RATE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.SCAN_BPM_RATE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.SCAN_KEY_TRACK | — | UI_ACTION_OSC | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| OSC1.SCAN_RATE | OSC1.SCAN_RATE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.SCAN_RATE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.SEMI | OSC1.SEMI | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.SEMI: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.SINGLE_SLICE | OSC1.SINGLE_SLICE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.SINGLE_SLICE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.SLICE_PLAY_MODE | — | UI_ACTION_OSC | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| OSC1.START | OSC1.START | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.START: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.UNISON | OSC1.UNISON | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.UNISON: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.UNI_BLEND | OSC1.UNI_BLEND | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.UNI_BLEND: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.UNI_DETUNE | OSC1.UNI_DETUNE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.UNI_DETUNE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.UNI_RAND_START | OSC1.UNI_RAND_START | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.UNI_RAND_START: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.UNI_SPAN | OSC1.UNI_SPAN | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.UNI_SPAN: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.UNI_STACK | OSC1.UNI_STACK | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.UNI_STACK: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.UNI_WARP | OSC1.UNI_WARP | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.UNI_WARP: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.UNI_WARP_2 | OSC1.UNI_WARP_2 | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.UNI_WARP_2: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.UNI_WIDTH | OSC1.UNI_WIDTH | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.UNI_WIDTH: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.UNI_WT_POS | OSC1.UNI_WT_POS | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.UNI_WT_POS: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.WARP | OSC1.Warp | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.Warp: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.WARP_2 | OSC1.WARP_2 | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.WARP_2: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.WARP_2_MODE | OSC1.WARP_2_MODE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.WARP_2_MODE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.WARP_2_VAR | OSC1.WARP_2_VAR | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.WARP_2_VAR: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.WARP_MODE | OSC1.WARP_MODE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.WARP_MODE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.WARP_VAR | OSC1.WARP_VAR | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.WARP_VAR: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC1.WT_POS | OSC1.WT_POS | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC1.WT_POS: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.COARSE_PITCH | OSC2.COARSE_PITCH | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.COARSE_PITCH: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.END | OSC2.END | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.END: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.FINE | OSC2.FINE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.FINE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.LOOP_END | OSC2.LOOP_END | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.LOOP_END: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.LOOP_MODE | OSC2.LOOP_MODE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.LOOP_MODE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.LOOP_START | OSC2.LOOP_START | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.LOOP_START: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.LOOP_X-FADE | OSC2.LOOP_X-FADE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.LOOP_X-FADE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.OCTAVE | OSC2.Octave | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.Octave: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.PHASE | OSC2.PHASE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.PHASE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.PITCH_TRACK | — | UI_ACTION_OSC | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| OSC2.POSITION | OSC2.POSITION | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.POSITION: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.RAND_PHASE | OSC2.RAND_PHASE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.RAND_PHASE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.RELATIVE_LOOP | — | UI_ACTION_OSC | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| OSC2.REVERSE | — | UI_ACTION_OSC | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| OSC2.SCAN_BPM_RATE | OSC2.SCAN_BPM_RATE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.SCAN_BPM_RATE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.SCAN_KEY_TRACK | — | UI_ACTION_OSC | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| OSC2.SCAN_RATE | OSC2.SCAN_RATE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.SCAN_RATE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.SEMI | OSC2.SEMI | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.SEMI: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.SINGLE_SLICE | OSC2.SINGLE_SLICE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.SINGLE_SLICE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.SLICE_PLAY_MODE | — | UI_ACTION_OSC | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| OSC2.START | OSC2.START | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.START: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.UNISON | OSC2.UNISON | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.UNISON: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.UNI_BLEND | OSC2.UNI_BLEND | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.UNI_BLEND: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.UNI_DETUNE | OSC2.UNI_DETUNE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.UNI_DETUNE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.UNI_RAND_START | OSC2.UNI_RAND_START | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.UNI_RAND_START: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.UNI_SPAN | OSC2.UNI_SPAN | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.UNI_SPAN: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.UNI_STACK | OSC2.UNI_STACK | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.UNI_STACK: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.UNI_WARP | OSC2.UNI_WARP | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.UNI_WARP: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.UNI_WARP_2 | OSC2.UNI_WARP_2 | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.UNI_WARP_2: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.UNI_WIDTH | OSC2.UNI_WIDTH | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.UNI_WIDTH: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.UNI_WT_POS | OSC2.UNI_WT_POS | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.UNI_WT_POS: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.WARP | OSC2.Warp | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.Warp: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.WARP_2 | OSC2.WARP_2 | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.WARP_2: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.WARP_2_MODE | OSC2.WARP_2_MODE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.WARP_2_MODE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.WARP_2_VAR | OSC2.WARP_2_VAR | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.WARP_2_VAR: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.WARP_MODE | OSC2.WARP_MODE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.WARP_MODE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.WARP_VAR | OSC2.WARP_VAR | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.WARP_VAR: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC2.WT_POS | OSC2.WT_POS | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC2.WT_POS: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.COARSE_PITCH | OSC3.COARSE_PITCH | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.COARSE_PITCH: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.END | OSC3.END | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.END: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.FINE | OSC3.FINE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.FINE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.LOOP_END | OSC3.LOOP_END | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.LOOP_END: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.LOOP_MODE | OSC3.LOOP_MODE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.LOOP_MODE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.LOOP_START | OSC3.LOOP_START | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.LOOP_START: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.LOOP_X-FADE | OSC3.LOOP_X-FADE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.LOOP_X-FADE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.OCTAVE | OSC3.Octave | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.Octave: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.PHASE | OSC3.PHASE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.PHASE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.PITCH_TRACK | — | UI_ACTION_OSC | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| OSC3.POSITION | OSC3.POSITION | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.POSITION: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.RAND_PHASE | OSC3.RAND_PHASE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.RAND_PHASE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.RELATIVE_LOOP | — | UI_ACTION_OSC | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| OSC3.REVERSE | — | UI_ACTION_OSC | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| OSC3.SCAN_BPM_RATE | OSC3.SCAN_BPM_RATE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.SCAN_BPM_RATE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.SCAN_KEY_TRACK | — | UI_ACTION_OSC | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| OSC3.SCAN_RATE | OSC3.SCAN_RATE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.SCAN_RATE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.SEMI | OSC3.SEMI | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.SEMI: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.SINGLE_SLICE | OSC3.SINGLE_SLICE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.SINGLE_SLICE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.SLICE_PLAY_MODE | — | UI_ACTION_OSC | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| OSC3.START | OSC3.START | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.START: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.UNISON | OSC3.UNISON | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.UNISON: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.UNI_BLEND | OSC3.UNI_BLEND | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.UNI_BLEND: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.UNI_DETUNE | OSC3.UNI_DETUNE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.UNI_DETUNE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.UNI_RAND_START | OSC3.UNI_RAND_START | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.UNI_RAND_START: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.UNI_SPAN | OSC3.UNI_SPAN | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.UNI_SPAN: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.UNI_STACK | OSC3.UNI_STACK | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.UNI_STACK: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.UNI_WARP | OSC3.UNI_WARP | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.UNI_WARP: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.UNI_WARP_2 | OSC3.UNI_WARP_2 | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.UNI_WARP_2: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.UNI_WIDTH | OSC3.UNI_WIDTH | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.UNI_WIDTH: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.UNI_WT_POS | OSC3.UNI_WT_POS | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.UNI_WT_POS: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.WARP | OSC3.Warp | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.Warp: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.WARP_2 | OSC3.WARP_2 | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.WARP_2: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.WARP_2_MODE | OSC3.WARP_2_MODE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.WARP_2_MODE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.WARP_2_VAR | OSC3.WARP_2_VAR | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.WARP_2_VAR: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.WARP_MODE | OSC3.WARP_MODE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.WARP_MODE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.WARP_VAR | OSC3.WARP_VAR | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.WARP_VAR: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| OSC3.WT_POS | OSC3.WT_POS | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target OSC3.WT_POS: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| SUB_OSC.COARSE_PITCH | SUB_OSC.COARSE_PITCH | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target SUB_OSC.COARSE_PITCH: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence ye... |
| SUB_OSC.CONT_PHASE | SUB_OSC.CONT_PHASE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target SUB_OSC.CONT_PHASE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| SUB_OSC.LEVEL | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| SUB_OSC.OCTAVE | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| SUB_OSC.PAN | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| SUB_OSC.PHASE | SUB_OSC.PHASE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target SUB_OSC.PHASE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| SUB_OSC.PITCH_TRACK | SUB_OSC.PITCH_TRACK | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target SUB_OSC.PITCH_TRACK: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| SUB_OSC.SHAPE | SUB_OSC.SHAPE | TARGET_BACKED_CENSUS_VERIFIED | NOT_YET_DERIVED | Joined to normalized target SUB_OSC.SHAPE: 2D.6J table_b: OWNED (a real, named target) but no CapabilityContract / causal evidence yet |
| TOPMENU.RESOURCE.INIT_PRESET | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| TOPMENU.RESOURCE.LOAD_PRESET | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| TOPMENU.RESOURCE.LOAD_TUNING | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| TOPMENU.RESOURCE.OPEN_PRESETS_FOLDER | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| TOPMENU.RESOURCE.RESCAN_FOLDERS_ON_DISK | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| TOPMENU.RESOURCE.REVERT_TO_SAVED | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| TOPMENU.RESOURCE.SAVE_AS_DEFAULT_PRESET | — | RESOURCE_OPERATION | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| VOICE.VOICING.LEGATO | — | UI_ACTION_VOICE | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| VOICE.VOICING.MONO | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |
| VOICE.VOICING.POLY | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| VOICE.VOICING.PORTA_ALWAYS | — | UI_ACTION_VOICE | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| VOICE.VOICING.PORTA_CURVE | — | UNCLASSIFIED | NOT_YET_DERIVED | 2D.6J table_a bulk category: UNKNOWN |
| VOICE.VOICING.PORTA_SCALED | — | UI_ACTION_VOICE | MECHANISM_KNOWN_NO_TARGET | 2D.6J table_a bulk category: CONTROL_PATH_KNOWN_NO_TARGET |
| VOICE.VOICING.PORTA_TIME | — | TARGET_BACKED_CENSUS_VERIFIED | LIVE_VERIFIED_NO_TARGET_JOIN | V3 registry: LIVE_VERIFIED binding (V4 HOST_PARAMETER reconciliation pass (serum2/reconciliation/host_parameter_v4_match.py): exact match ag... |

### Disposition E — unsupported/structural (incl. DEAD_OR_SUPERSEDED, NEGATIVE_EVIDENCE) (40 rows)

| SEMANTIC_ID | NORMALIZED_TARGET | FAMILY | TIER | EVIDENCE |
|---|---|---|---|---|
| GLOBAL.RETRIGGERS.ENV_2 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='boolean': checked against the live VST3 host-parameter list this run -- no '<source> Retrig'-shaped parameter exists (only unr... |
| GLOBAL.RETRIGGERS.ENV_3 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='boolean': checked against the live VST3 host-parameter list this run -- no '<source> Retrig'-shaped parameter exists (only unr... |
| GLOBAL.RETRIGGERS.ENV_4 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='boolean': checked against the live VST3 host-parameter list this run -- no '<source> Retrig'-shaped parameter exists (only unr... |
| GLOBAL.RETRIGGERS.LFO_1 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='boolean': checked against the live VST3 host-parameter list this run -- no '<source> Retrig'-shaped parameter exists (only unr... |
| GLOBAL.RETRIGGERS.LFO_10 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='boolean': checked against the live VST3 host-parameter list this run -- no '<source> Retrig'-shaped parameter exists (only unr... |
| GLOBAL.RETRIGGERS.LFO_2 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='boolean': checked against the live VST3 host-parameter list this run -- no '<source> Retrig'-shaped parameter exists (only unr... |
| GLOBAL.RETRIGGERS.LFO_3 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='boolean': checked against the live VST3 host-parameter list this run -- no '<source> Retrig'-shaped parameter exists (only unr... |
| GLOBAL.RETRIGGERS.LFO_4 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='boolean': checked against the live VST3 host-parameter list this run -- no '<source> Retrig'-shaped parameter exists (only unr... |
| GLOBAL.RETRIGGERS.LFO_5 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='boolean': checked against the live VST3 host-parameter list this run -- no '<source> Retrig'-shaped parameter exists (only unr... |
| GLOBAL.RETRIGGERS.LFO_6 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='boolean': checked against the live VST3 host-parameter list this run -- no '<source> Retrig'-shaped parameter exists (only unr... |
| GLOBAL.RETRIGGERS.LFO_7 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='boolean': checked against the live VST3 host-parameter list this run -- no '<source> Retrig'-shaped parameter exists (only unr... |
| GLOBAL.RETRIGGERS.LFO_8 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='boolean': checked against the live VST3 host-parameter list this run -- no '<source> Retrig'-shaped parameter exists (only unr... |
| GLOBAL.RETRIGGERS.LFO_9 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='boolean': checked against the live VST3 host-parameter list this run -- no '<source> Retrig'-shaped parameter exists (only unr... |
| GLOBAL.RETRIGGERS.NOISE | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='boolean': checked against the live VST3 host-parameter list this run -- no '<source> Retrig'-shaped parameter exists (only unr... |
| GLOBAL.RETRIGGERS.NOTE | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='boolean': checked against the live VST3 host-parameter list this run -- no '<source> Retrig'-shaped parameter exists (only unr... |
| GLOBAL.RETRIGGERS.OSC_A | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='boolean': checked against the live VST3 host-parameter list this run -- no '<source> Retrig'-shaped parameter exists (only unr... |
| GLOBAL.RETRIGGERS.OSC_B | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='boolean': checked against the live VST3 host-parameter list this run -- no '<source> Retrig'-shaped parameter exists (only unr... |
| GLOBAL.RETRIGGERS.OSC_C | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='boolean': checked against the live VST3 host-parameter list this run -- no '<source> Retrig'-shaped parameter exists (only unr... |
| GLOBAL.RETRIGGERS.SUB | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='boolean': checked against the live VST3 host-parameter list this run -- no '<source> Retrig'-shaped parameter exists (only unr... |
| LFO1.SOURCE | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='continuous'/value_domain='SCALAR_UNBOUNDED' with no options and no matching field in any registered compiler or a3_modulation_... |
| LFO2.SOURCE | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='continuous'/value_domain='SCALAR_UNBOUNDED' with no options and no matching field in any registered compiler or a3_modulation_... |
| LFO3.SOURCE | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='continuous'/value_domain='SCALAR_UNBOUNDED' with no options and no matching field in any registered compiler or a3_modulation_... |
| LFO4.SOURCE | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='continuous'/value_domain='SCALAR_UNBOUNDED' with no options and no matching field in any registered compiler or a3_modulation_... |
| LFO5.SOURCE | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='continuous'/value_domain='SCALAR_UNBOUNDED' with no options and no matching field in any registered compiler or a3_modulation_... |
| LFO6.SOURCE | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='continuous'/value_domain='SCALAR_UNBOUNDED' with no options and no matching field in any registered compiler or a3_modulation_... |
| MACRO.SYS.ASSIGN_MATRIX_SOURCE | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | The general mechanism (compound_create_modulation_route's source= parameter) exists, but 'Macro 1'..'Macro 8' are not keys in a3_modulation_... |
| MACRO.SYS.AUX_INVERT | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='toggle': no registered compiler for aux-invert (checked compound_operations.py's full compiler list) and no matching live host... |
| MATRIX.LFO_BUS.11 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='destination_target': a3_modulation_route._DESTINATIONS has zero real, corpus-evidenced entries for LFO11 (moduleID=10) across ... |
| MATRIX.LFO_BUS.12 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='destination_target': a3_modulation_route._DESTINATIONS has zero real, corpus-evidenced entries for LFO12 (moduleID=11) across ... |
| MATRIX.LFO_BUS.13 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='destination_target': a3_modulation_route._DESTINATIONS has zero real, corpus-evidenced entries for LFO13 (moduleID=12) across ... |
| MATRIX.LFO_BUS.14 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='destination_target': a3_modulation_route._DESTINATIONS has zero real, corpus-evidenced entries for LFO14 (moduleID=13) across ... |
| MATRIX.LFO_BUS.15 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='destination_target': a3_modulation_route._DESTINATIONS has zero real, corpus-evidenced entries for LFO15 (moduleID=14) across ... |
| MATRIX.LFO_BUS.16 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='destination_target': a3_modulation_route._DESTINATIONS has zero real, corpus-evidenced entries for LFO16 (moduleID=15) across ... |
| MATRIX.SOURCE.FILTER_1 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='source_target', but 'MATRIX.SOURCE.FILTER_1' has no matching key in a3_modulation_route._SOURCES (['Env1', 'Env2', 'Env3', 'En... |
| MATRIX.SOURCE.FILTER_2 | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='source_target', but 'MATRIX.SOURCE.FILTER_2' has no matching key in a3_modulation_route._SOURCES (['Env1', 'Env2', 'Env3', 'En... |
| MATRIX.SOURCE.NOISE_OSC | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='source_target', but 'MATRIX.SOURCE.NOISE_OSC' has no matching key in a3_modulation_route._SOURCES (['Env1', 'Env2', 'Env3', 'E... |
| MATRIX.SOURCE.OSC_A | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='source_target', but 'MATRIX.SOURCE.OSC_A' has no matching key in a3_modulation_route._SOURCES (['Env1', 'Env2', 'Env3', 'Env4'... |
| MATRIX.SOURCE.OSC_B | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='source_target', but 'MATRIX.SOURCE.OSC_B' has no matching key in a3_modulation_route._SOURCES (['Env1', 'Env2', 'Env3', 'Env4'... |
| MATRIX.SOURCE.OSC_C | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='source_target', but 'MATRIX.SOURCE.OSC_C' has no matching key in a3_modulation_route._SOURCES (['Env1', 'Env2', 'Env3', 'Env4'... |
| MATRIX.SOURCE.SUB_OSC | — | MATRIX_ROUTE | UNSUPPORTED_NO_EVIDENCE | control_type='source_target', but 'MATRIX.SOURCE.SUB_OSC' has no matching key in a3_modulation_route._SOURCES (['Env1', 'Env2', 'Env3', 'Env... |

### Disposition F — unresolved/unknown (ambiguous, contradicted) (5 rows)

| SEMANTIC_ID | NORMALIZED_TARGET | FAMILY | TIER | EVIDENCE |
|---|---|---|---|---|
| FILTER2.CUTOFF | Filter2.Cutoff | TARGET_BACKED_CENSUS_VERIFIED | AMBIGUOUS | Joined to normalized target Filter2.Cutoff: 2D.6J table_b: MANY_TO_ONE, multiple semantic rows compete for this target, unresolved |
| FILTER2.RESONANCE | Filter2.Resonance | TARGET_BACKED_CENSUS_VERIFIED | AMBIGUOUS | Joined to normalized target Filter2.Resonance: 2D.6J table_b: MANY_TO_ONE, multiple semantic rows compete for this target, unresolved |
| MATRIX.ROUTING.SIGNAL_BALANCE | — | TARGET_BACKED_CENSUS_VERIFIED | AMBIGUOUS | 2D.6J table_a bulk category: MANY_TO_ONE |
| MIXER.FILTER1.GRAPHIC_CUTOFF_RESONANCE | — | TARGET_BACKED_CENSUS_VERIFIED | AMBIGUOUS | 2D.6J table_a bulk category: MANY_TO_ONE |
| MIXER.FILTER2.GRAPHIC_CUTOFF_RESONANCE | — | TARGET_BACKED_CENSUS_VERIFIED | AMBIGUOUS | 2D.6J table_a bulk category: MANY_TO_ONE |

### Disposition G — proven-not-user-control (73 rows)

| SEMANTIC_ID | NORMALIZED_TARGET | FAMILY | TIER | EVIDENCE |
|---|---|---|---|---|
| ARP.PATTERN.EDITOR.ACCENT_ROW | — | UNKNOWN_EXECUTION | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |
| ARP.PATTERN.EDITOR.STRUM_ROW | — | UNKNOWN_EXECUTION | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |
| ENV1.SOURCE | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | Own definition: 'drag-handle circle icon' -- a drag-gesture affordance for initiating a route, not itself a discrete value. |
| ENV2.SOURCE | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | Own definition: 'drag-handle circle icon' -- a drag-gesture affordance for initiating a route, not itself a discrete value. |
| ENV3.SOURCE | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | Own definition: 'drag-handle circle icon' -- a drag-gesture affordance for initiating a route, not itself a discrete value. |
| ENV4.SOURCE | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | Own definition: 'drag-handle circle icon' -- a drag-gesture affordance for initiating a route, not itself a discrete value. |
| FX.COMPRESSOR.BAND_GRAPHIC | — | UNKNOWN_EXECUTION | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |
| FX.DISTORTION.XSHAPER_EDIT_PENCIL | — | UNKNOWN_EXECUTION | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |
| FX.EQUALIZER.LEVEL | — | UNKNOWN_EXECUTION | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |
| FX.FLANGER.NO_SEPARATE_DELAY_KNOB | — | UNKNOWN_EXECUTION | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |
| FX.SPLITTER_MS.WET | — | UNKNOWN_EXECUTION | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |
| GLOBAL.INFO.BUILD_DATE_DISPLAY | — | UNKNOWN_EXECUTION | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |
| MACRO.SYS.ADD_REMOVE_SLOT | — | UI_ACTION_MACRO | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |
| MACRO.SYS.FX_EXPANDED_NOT_ASSIGNABLE | — | UNKNOWN_EXECUTION | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |
| MACRO.SYS.MACRO_DEPTH_RECONCILE | — | UNKNOWN_EXECUTION | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |
| MACRO.SYS.MACRO_SPECIFIC_PRESET | — | UNKNOWN_EXECUTION | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |
| MATRIX.DESTINATION.LFO_N_CONDITIONAL | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='destination_target_conditional': describes the conditional param-choice submenu shown once LFO is picked as destination module... |
| MATRIX.MOD | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | Own definition: 'hypothesized separate...control (does not exist as a discrete Matrix column)' -- proven not to exist as a real column by it... |
| MATRIX.OUT_INDICATOR | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | Own definition: 'small non-interactive indicator' -- proven non-interactive by definition. |
| MATRIX.SOURCE.ACTIVE_VOICES | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.AFTERTOUCH | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.ENV_1 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.ENV_2 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.ENV_3 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.ENV_4 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.EXPR_X_PAN | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.EXPR_Y_TIMBRE | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.EXPR_Z_PRESS | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.FIXED | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.LFO_1 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.LFO_10 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.LFO_2 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.LFO_3 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.LFO_4 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.LFO_5 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.LFO_6 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.LFO_7 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.LFO_8 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.LFO_9 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.MACRO_1 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.MACRO_2 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.MACRO_3 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.MACRO_4 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.MACRO_5 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.MACRO_6 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.MACRO_7 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.MACRO_8 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.MOD_WHEEL | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.NOTE# | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.NOTEON_ALT | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.NOTEON_ALT2 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.NOTEON_RAND1 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.NOTEON_RAND2 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.NOTEON_RAND_DISCRETE | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.PITCH_BEND | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.POLY_AFTERTCH | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.RELEASE_VELO | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.VELO | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.VOICE_INDEX | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.VOICE_MOD_1 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SOURCE.VOICE_MOD_2 | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_source_selection'/value_domain='STRUCTURAL_SELECTION': the frozen definition itself classifies this as an availabil... |
| MATRIX.SYS.DUPLICATE_ROUTE_POLICY | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='structural_policy': describes internal duplicate-route ALLOW rules, not a settable value. |
| MATRIX.SYS.MAX_ROUTES | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='system_limit': a fixed capacity constant (0-64 slots), not a mutable control. |
| MATRIX.SYS.MENU | — | MATRIX_ROUTE | PROVEN_NOT_USER_CONTROL | control_type='menu': a UI menu container of sub-actions (Sort by Source, Lock Matrix, etc.), not itself a single mutable value. |
| MIXER.BUS1.ENABLE | — | UNKNOWN_EXECUTION | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |
| MIXER.BUS2.ENABLE | — | UNKNOWN_EXECUTION | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |
| OSC1.HZ_OFFSET | — | UNKNOWN_EXECUTION | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |
| OSC1.RATIO | — | UNKNOWN_EXECUTION | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |
| OSC2.HZ_OFFSET | — | UNKNOWN_EXECUTION | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |
| OSC2.RATIO | — | UNKNOWN_EXECUTION | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |
| OSC3.HZ_OFFSET | — | UNKNOWN_EXECUTION | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |
| OSC3.RATIO | — | UNKNOWN_EXECUTION | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |
| VOICE.VOICING.VOICE_COUNT_DISPLAY | — | UNKNOWN_EXECUTION | PROVEN_NOT_USER_CONTROL | 2D.6J table_a bulk category: PROVEN_NOT_USER_CONTROL |

## Orphan CAUSAL_VERIFIED/STRUCTURAL_ONLY Contracts (outside 396 vocabulary)

These are real, evidence-backed capabilities with no reachable semantic name in the current 396-target vocabulary or producer's SEMANTIC_TARGETS registration.

| CAPABILITY_KEY | STATUS | BOUND? |
|---|---|---|
| fx_field_distortion_drive | CAUSAL_VERIFIED | no |
| fx_field_distortion_mode | CAUSAL_VERIFIED | no |
| fx_field_eq_kParamType1 | STRUCTURAL_ONLY | no |
| global_field_monotoggle | STRUCTURAL_ONLY | no |
| global_field_oversampling | STRUCTURAL_ONLY | no |
| lfo_as_modulation_source | NEGATIVE_EVIDENCE | no |
| lfo_field_LFO-MODE | STRUCTURAL_ONLY | no |
| lfo_field_LFO-RATE | STRUCTURAL_ONLY | no |
| lfo_field_LFO-SHAPE | STRUCTURAL_ONLY | no |
| lfo_rate_dependent_route | CAUSAL_VERIFIED | no |
| macro_field_name | NEGATIVE_EVIDENCE | no |
| macro_field_value | CAUSAL_VERIFIED | no |
| modulation_route_fxdelay | NEGATIVE_EVIDENCE | no |
| modulation_route_voicefilter | CAUSAL_VERIFIED | no |
| oscillator_field_OSC-ENABLE | CAUSAL_VERIFIED | yes |
| oscillator_field_OSC-OCTAVE | CAUSAL_VERIFIED | yes |
| oscillator_field_OSC-VOLUME | CAUSAL_VERIFIED | yes |
| oscillator_field_OSC-WAVETABLE | CAUSAL_VERIFIED | no |
| route_coexistence | CAUSAL_VERIFIED | no |
| voice_field_detune | STRUCTURAL_ONLY | no |
| voice_field_randompan | STRUCTURAL_ONLY | no |