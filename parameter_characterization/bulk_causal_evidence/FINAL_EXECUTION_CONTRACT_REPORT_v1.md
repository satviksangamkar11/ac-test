# Final MCP Execution Contract v1 — Report

Built entirely from committed evidence; no Serum rerun, no GUI exploration, no new controls.
Live v3 sweep outcome is the execution authority and is copied verbatim.

- Serum version: `2.0.23`
- Serum binary SHA256: `9293eb90fc9fc890fd2505272abd6172cee5bd32b1fb20be22531810702bf9b3`
- Contract: `final_execution_contract_v1.json`

## Counts

| metric | value |
|---|---|
| total controls | 330 |
| conforming / executable | 310 |
| conformance exceptions | 20 |
| host-confirmed | 183 |
| raw-only | 127 |
| execution failures | 0 |
| noop suspects | 0 |
| restoration verified | 330/330 |
| v3 vs v2 | identical |

Only the 183 host-confirmed rows carry live VST3 host-parameter evidence. The 127 raw-only rows (and the 20 exceptions) execute as raw-field edits; the 330 controls are **not** all native host parameters.

Of the 183 host-confirmed rows, 182 have a single named host parameter; `global.global_tuning` is host-confirmed by the live run but changed several host parameters, so no single host identity is asserted for it.

## Classification rules

- `MCP_EXEC_HOST_CONFIRMED` — live MCP execution succeeded and the expected named host parameter behavior was confirmed (a named VST3 host parameter's text changed in the live run)
- `MCP_EXEC_RAW_ONLY` — live MCP execution succeeded and the raw state persisted and restored correctly, but no reliable named host confirmation exists; the control is executed as a raw-field edit, NOT as a native host parameter
- `MCP_EXEC_CONFORMANCE_EXCEPTION` — execution occurred but a known, documented Serum/schema/UI divergence remains; never counted as success
- final_classification is the LIVE v3 `outcome`, copied verbatim; it is never reinterpreted or upgraded
- an exception is never converted into success
- host identity is reported only from the live run's observed named host change, never from a raw path
- not all 330 controls are native VST3 host parameters; only HOST_CONFIRMED rows carry live host identity

## The 20 conformance exceptions

| atlas_id | reference conclusion | reason / live oracle |
|---|---|---|
| `arp.transpose.range` | UI_SCHEMA_MISMATCH | DIVERGENT: written 16 displayed as 8; Serum's usable range is narrower than declared |
| `fx.compressor.attack` | UI_SCHEMA_MISMATCH | DIVERGENT: displays raw ms with a numeric ratio, raw/100 ms only when ratio shows 'Limit' (control-map v8) |
| `fx.compressor.ratio` | UI_SCHEMA_MISMATCH | DIVERGENT: raw==display for 1-8; 20 shows '32:1'; >=100 (and every value the campaign used, 210/430/31622) shows 'Limit' |
| `fx.compressor.release` | UI_SCHEMA_MISMATCH | DIVERGENT: displays raw ms directly; the declared minimum 0.1 shows 1000 (schema minimum invalid) |
| `global.fx_bus1_destination` | UI_SCHEMA_MISMATCH | DIVERGENT: schema word 'master' (raw 1.0) displays DIRECT |
| `global.fx_bus2_destination` | UI_SCHEMA_MISMATCH | DIVERGENT: schema word 'direct' (raw 2.0) displays BUS 1 |
| `global.use_ultra_on_render` | RESIDUAL_NOT_STORED | EXPECT NO DIFF: confirmed by direct toggle+save+diff test not persisted into any preset |
| `global.voice_priority` | UI_UNOBSERVABLE | EXCEPTION: serum-mcp accepts any string for voice_priority, Serum silently drops unknown words (smoke run: 'MCP_TEST' not persisted); re-tested with 'Low' |
| `macro1.name` | UI_MISMATCH | DIVERGENT: Serum shows 'Macro 1', never the written name |
| `macro2.name` | UI_MISMATCH | DIVERGENT: Serum shows 'Macro 2', never the written name |
| `macro3.name` | UI_MISMATCH | DIVERGENT: Serum shows 'Macro 3', never the written name |
| `macro4.name` | UI_MISMATCH | DIVERGENT: Serum shows 'Macro 4', never the written name |
| `macro5.name` | UI_MISMATCH | DIVERGENT: Serum shows 'Macro 5', never the written name |
| `macro6.name` | UI_MISMATCH | DIVERGENT: Serum shows 'Macro 6', never the written name |
| `macro7.name` | UI_MISMATCH | DIVERGENT: Serum shows 'Macro 7', never the written name |
| `macro8.name` | UI_MISMATCH | DIVERGENT: Serum shows 'Macro 8', never the written name |
| `mixer.noise.pan` | UI_MISMATCH | DIVERGENT: display is written+1 toward zero (e.g. -20 -> '-19 L') |
| `mixer.sub.pan` | UI_MISMATCH | DIVERGENT: display is written+1 toward zero (e.g. -4 -> '-3 L') |
| `oscA.warp_amount` | UI_CURVE_UNRESOLVED_FINAL | EXPECT MONOTONIC, NO EXACT VALUE: Sync-mode display likely quantized, no smooth curve fits 8 points |
| `oscNoise.pan` | UI_MISMATCH | DIVERGENT: alias of mixer.noise.pan, same off-by-one |

## Producer lookup

`atlas_id -> MCP operation -> expected raw path=value -> verification -> exception policy`. The same index is in the JSON under `producer_lookup`.

| atlas_id | MCP operation | expected raw | verification | class | exception policy |
|---|---|---|---|---|---|
| `arp.pattern.rate` | `{"kind":"singleton_field","field":"rate","attr":"arp"}` | `ArpClip0.plainParams.kParamRate`=0.25 | FULL_SCAN | RAW_ONLY | NONE |
| `arp.pattern.shape` | `{"kind":"singleton_field","field":"shape","attr":"arp"}` | `ArpClip0.plainParams.kParamShape`="Chord" | FULL_SCAN | RAW_ONLY | NONE |
| `arp.playback.chance` | `{"kind":"singleton_field","field":"chance","attr":"arp"}` | `ArpClip0.plainParams.kParamChance`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `arp.playback.gate` | `{"kind":"singleton_field","field":"gate","attr":"arp"}` | `ArpClip0.plainParams.kParamGate`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `arp.playback.offset` | `{"kind":"singleton_field","field":"offset","attr":"arp"}` | `ArpClip0.plainParams.kParamOffset`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `arp.playback.repeats` | `{"kind":"singleton_field","field":"repeats","attr":"arp"}` | `ArpClip0.plainParams.kParamRepeats`=10.0 | FULL_SCAN | RAW_ONLY | NONE |
| `arp.playback.thru` | `{"kind":"singleton_field","field":"thru","attr":"arp"}` | `ArpClip0.plainParams.kParamThru`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `arp.retrigger.first` | `{"kind":"singleton_field","field":"first_note_retrig","attr":"arp"}` | `ArpClip0.plainParams.kParamFirstNoteRetrig`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `arp.retrigger.launch` | `{"kind":"singleton_field","field":"launch_retrig","attr":"arp"}` | `ArpClip0.plainParams.kParamLaunchRetrig`=0.0 | FULL_SCAN | RAW_ONLY | NONE |
| `arp.retrigger.note` | `{"kind":"singleton_field","field":"note_retrig","attr":"arp"}` | `ArpClip0.plainParams.kParamNoteRetrig`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `arp.transpose.range` | `{"kind":"singleton_field","field":"transpose_range","attr":"arp"}` | `ArpClip0.plainParams.kParamTransposeRange`=16.0 | ORACLE | CONFORMANCE_EXCEPTION | KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS |
| `arp.transpose.shape` | `{"kind":"singleton_field","field":"transpose_shape","attr":"arp"}` | `ArpClip0.plainParams.kParamTransposeShape`="Down" | FULL_SCAN | RAW_ONLY | NONE |
| `arp.transpose.shift` | `{"kind":"singleton_field","field":"transpose_shift","attr":"arp"}` | `ArpClip0.plainParams.kParamTransposeShift`=-12.0 | FULL_SCAN | RAW_ONLY | NONE |
| `arp.velocity.decay` | `{"kind":"singleton_field","field":"velo_decay","attr":"arp"}` | `ArpClip0.plainParams.kParamVeloDecay`=0.9999999999999998 | FULL_SCAN | RAW_ONLY | NONE |
| `arp.velocity.enable` | `{"kind":"singleton_field","field":"velo_enabled","attr":"arp"}` | `ArpClip0.plainParams.kParamVeloEnabled`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `arp.velocity.retrig` | `{"kind":"singleton_field","field":"velo_retrig","attr":"arp"}` | `ArpClip0.plainParams.kParamVeloRetrig`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `arp.velocity.target` | `{"kind":"singleton_field","field":"velo_target","attr":"arp"}` | `ArpClip0.plainParams.kParamVeloTarget`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `env1.attack` | `{"kind":"field","field":"attack","list":"envelopes","index":0}` | `Env0.plainParams.kParamAttack`=5.000000000000001 | NAMED -> Env 1 Attack | HOST_CONFIRMED | NONE |
| `env1.attack_curve` | `{"kind":"field","field":"attack_curve","list":"envelopes","index":0}` | `Env0.plainParams.kParamCurve1`=90.0 | NAMED -> Env 1 Atk Curve | HOST_CONFIRMED | NONE |
| `env1.decay` | `{"kind":"field","field":"decay","list":"envelopes","index":0}` | `Env0.plainParams.kParamDecay`=15.999999999999998 | NAMED -> Env 1 Decay | HOST_CONFIRMED | NONE |
| `env1.decay_curve` | `{"kind":"field","field":"decay_curve","list":"envelopes","index":0}` | `Env0.plainParams.kParamCurve2`=50.0 | NAMED -> Env 1 Dec Curve | HOST_CONFIRMED | NONE |
| `env1.hold` | `{"kind":"field","field":"hold","list":"envelopes","index":0}` | `Env0.plainParams.kParamHold`=2.599999999999999 | NAMED -> Env 1 Hold | HOST_CONFIRMED | NONE |
| `env1.release` | `{"kind":"field","field":"release","list":"envelopes","index":0}` | `Env0.plainParams.kParamRelease`=15.999999999999998 | NAMED -> Env 1 Release | HOST_CONFIRMED | NONE |
| `env1.release_curve` | `{"kind":"field","field":"release_curve","list":"envelopes","index":0}` | `Env0.plainParams.kParamCurve3`=50.0 | NAMED -> Env 1 Rel Curve | HOST_CONFIRMED | NONE |
| `env1.sustain` | `{"kind":"field","field":"sustain","list":"envelopes","index":0}` | `Env0.plainParams.kParamSustain`=0.5 | NAMED -> Env 1 Sustain | HOST_CONFIRMED | NONE |
| `env2.attack` | `{"kind":"field","field":"attack","list":"envelopes","index":1}` | `Env1.plainParams.kParamAttack`=5.000000000000001 | NAMED -> Env 2 Attack | HOST_CONFIRMED | NONE |
| `env2.attack_curve` | `{"kind":"field","field":"attack_curve","list":"envelopes","index":1}` | `Env1.plainParams.kParamCurve1`=90.0 | NAMED -> Env 2 Atk Curve | HOST_CONFIRMED | NONE |
| `env2.decay` | `{"kind":"field","field":"decay","list":"envelopes","index":1}` | `Env1.plainParams.kParamDecay`=15.999999999999998 | NAMED -> Env 2 Decay | HOST_CONFIRMED | NONE |
| `env2.decay_curve` | `{"kind":"field","field":"decay_curve","list":"envelopes","index":1}` | `Env1.plainParams.kParamCurve2`=50.0 | NAMED -> Env 2 Dec Curve | HOST_CONFIRMED | NONE |
| `env2.hold` | `{"kind":"field","field":"hold","list":"envelopes","index":1}` | `Env1.plainParams.kParamHold`=2.599999999999999 | NAMED -> Env 2 Hold | HOST_CONFIRMED | NONE |
| `env2.release` | `{"kind":"field","field":"release","list":"envelopes","index":1}` | `Env1.plainParams.kParamRelease`=15.999999999999998 | NAMED -> Env 2 Release | HOST_CONFIRMED | NONE |
| `env2.release_curve` | `{"kind":"field","field":"release_curve","list":"envelopes","index":1}` | `Env1.plainParams.kParamCurve3`=50.0 | NAMED -> Env 2 Rel Curve | HOST_CONFIRMED | NONE |
| `env2.sustain` | `{"kind":"field","field":"sustain","list":"envelopes","index":1}` | `Env1.plainParams.kParamSustain`=0.5 | NAMED -> Env 2 Sustain | HOST_CONFIRMED | NONE |
| `env3.attack` | `{"kind":"field","field":"attack","list":"envelopes","index":2}` | `Env2.plainParams.kParamAttack`=5.000000000000001 | NAMED -> Env 3 Attack | HOST_CONFIRMED | NONE |
| `env3.attack_curve` | `{"kind":"field","field":"attack_curve","list":"envelopes","index":2}` | `Env2.plainParams.kParamCurve1`=90.0 | NAMED -> Env 3 Atk Curve | HOST_CONFIRMED | NONE |
| `env3.decay` | `{"kind":"field","field":"decay","list":"envelopes","index":2}` | `Env2.plainParams.kParamDecay`=15.999999999999998 | NAMED -> Env 3 Decay | HOST_CONFIRMED | NONE |
| `env3.decay_curve` | `{"kind":"field","field":"decay_curve","list":"envelopes","index":2}` | `Env2.plainParams.kParamCurve2`=50.0 | NAMED -> Env 3 Dec Curve | HOST_CONFIRMED | NONE |
| `env3.hold` | `{"kind":"field","field":"hold","list":"envelopes","index":2}` | `Env2.plainParams.kParamHold`=2.599999999999999 | NAMED -> Env 3 Hold | HOST_CONFIRMED | NONE |
| `env3.release` | `{"kind":"field","field":"release","list":"envelopes","index":2}` | `Env2.plainParams.kParamRelease`=15.999999999999998 | NAMED -> Env 3 Release | HOST_CONFIRMED | NONE |
| `env3.release_curve` | `{"kind":"field","field":"release_curve","list":"envelopes","index":2}` | `Env2.plainParams.kParamCurve3`=50.0 | NAMED -> Env 3 Rel Curve | HOST_CONFIRMED | NONE |
| `env3.sustain` | `{"kind":"field","field":"sustain","list":"envelopes","index":2}` | `Env2.plainParams.kParamSustain`=0.5 | NAMED -> Env 3 Sustain | HOST_CONFIRMED | NONE |
| `env4.attack` | `{"kind":"field","field":"attack","list":"envelopes","index":3}` | `Env3.plainParams.kParamAttack`=5.000000000000001 | NAMED -> Env 4 Attack | HOST_CONFIRMED | NONE |
| `env4.attack_curve` | `{"kind":"field","field":"attack_curve","list":"envelopes","index":3}` | `Env3.plainParams.kParamCurve1`=90.0 | NAMED -> Env 4 Atk Curve | HOST_CONFIRMED | NONE |
| `env4.decay` | `{"kind":"field","field":"decay","list":"envelopes","index":3}` | `Env3.plainParams.kParamDecay`=15.999999999999998 | NAMED -> Env 4 Decay | HOST_CONFIRMED | NONE |
| `env4.decay_curve` | `{"kind":"field","field":"decay_curve","list":"envelopes","index":3}` | `Env3.plainParams.kParamCurve2`=50.0 | NAMED -> Env 4 Dec Curve | HOST_CONFIRMED | NONE |
| `env4.hold` | `{"kind":"field","field":"hold","list":"envelopes","index":3}` | `Env3.plainParams.kParamHold`=2.599999999999999 | NAMED -> Env 4 Hold | HOST_CONFIRMED | NONE |
| `env4.release` | `{"kind":"field","field":"release","list":"envelopes","index":3}` | `Env3.plainParams.kParamRelease`=15.999999999999998 | NAMED -> Env 4 Release | HOST_CONFIRMED | NONE |
| `env4.release_curve` | `{"kind":"field","field":"release_curve","list":"envelopes","index":3}` | `Env3.plainParams.kParamCurve3`=50.0 | NAMED -> Env 4 Rel Curve | HOST_CONFIRMED | NONE |
| `env4.sustain` | `{"kind":"field","field":"sustain","list":"envelopes","index":3}` | `Env3.plainParams.kParamSustain`=0.5 | NAMED -> Env 4 Sustain | HOST_CONFIRMED | NONE |
| `filter1.cutoff` | `{"kind":"field","field":"cutoff","list":"filters","index":0}` | `VoiceFilter0.plainParams.kParamFreq`=0.25 | NAMED -> Filter 1 Freq | HOST_CONFIRMED | NONE |
| `filter1.drive` | `{"kind":"field","field":"drive","list":"filters","index":0}` | `VoiceFilter0.plainParams.kParamDrive`=50.0 | NAMED -> Filter 1 Drive | HOST_CONFIRMED | NONE |
| `filter1.enabled` | `{"kind":"field","field":"enabled","list":"filters","index":0}` | `VoiceFilter0.plainParams.kParamEnable`=1.0 | NAMED -> Filter 1 On | HOST_CONFIRMED | NONE |
| `filter1.key_track` | `{"kind":"field","field":"key_track","list":"filters","index":0}` | `VoiceFilter0.plainParams.kParamKeyTrack`=1.0 | NAMED -> Filter 1 Freq | HOST_CONFIRMED | NONE |
| `filter1.level_out` | `{"kind":"field","field":"level_out","list":"filters","index":0}` | `VoiceFilter0.plainParams.kParamLevelOut`=0.25 | NAMED -> Filter 1 Level | HOST_CONFIRMED | NONE |
| `filter1.resonance` | `{"kind":"field","field":"resonance","list":"filters","index":0}` | `VoiceFilter0.plainParams.kParamReso`=50.0 | NAMED -> Filter 1 Res | HOST_CONFIRMED | NONE |
| `filter1.stereo` | `{"kind":"field","field":"stereo","list":"filters","index":0}` | `VoiceFilter0.plainParams.kParamStereo`=25.0 | NAMED -> Filter 1 Stereo | HOST_CONFIRMED | NONE |
| `filter1.type` | `{"kind":"field","field":"type","list":"filters","index":0}` | `VoiceFilter0.plainParams.kParamType`="L12" | NAMED -> Filter 1 Type | HOST_CONFIRMED | NONE |
| `filter1.var` | `{"kind":"field","field":"var","list":"filters","index":0}` | `VoiceFilter0.plainParams.kParamVar`=50.0 | NAMED -> Filter 1 Var | HOST_CONFIRMED | NONE |
| `filter1.wet` | `{"kind":"field","field":"wet","list":"filters","index":0}` | `VoiceFilter0.plainParams.kParamWet`=50.0 | NAMED -> Filter 1 Wet | HOST_CONFIRMED | NONE |
| `filter2.cutoff` | `{"kind":"field","field":"cutoff","list":"filters","index":1}` | `VoiceFilter1.plainParams.kParamFreq`=0.25 | NAMED -> Filter 2 Freq | HOST_CONFIRMED | NONE |
| `filter2.drive` | `{"kind":"field","field":"drive","list":"filters","index":1}` | `VoiceFilter1.plainParams.kParamDrive`=50.0 | NAMED -> Filter 2 Drive | HOST_CONFIRMED | NONE |
| `filter2.enabled` | `{"kind":"field","field":"enabled","list":"filters","index":1}` | `VoiceFilter1.plainParams.kParamEnable`=1.0 | NAMED -> Filter 2 On | HOST_CONFIRMED | NONE |
| `filter2.key_track` | `{"kind":"field","field":"key_track","list":"filters","index":1}` | `VoiceFilter1.plainParams.kParamKeyTrack`=1.0 | NAMED -> Filter 2 Freq | HOST_CONFIRMED | NONE |
| `filter2.level_out` | `{"kind":"field","field":"level_out","list":"filters","index":1}` | `VoiceFilter1.plainParams.kParamLevelOut`=0.25 | NAMED -> Filter 2 Level | HOST_CONFIRMED | NONE |
| `filter2.resonance` | `{"kind":"field","field":"resonance","list":"filters","index":1}` | `VoiceFilter1.plainParams.kParamReso`=50.0 | NAMED -> Filter 2 Res | HOST_CONFIRMED | NONE |
| `filter2.stereo` | `{"kind":"field","field":"stereo","list":"filters","index":1}` | `VoiceFilter1.plainParams.kParamStereo`=25.0 | NAMED -> Filter 2 Stereo | HOST_CONFIRMED | NONE |
| `filter2.type` | `{"kind":"field","field":"type","list":"filters","index":1}` | `VoiceFilter1.plainParams.kParamType`="L12" | NAMED -> Filter 2 Type | HOST_CONFIRMED | NONE |
| `filter2.var` | `{"kind":"field","field":"var","list":"filters","index":1}` | `VoiceFilter1.plainParams.kParamVar`=50.0 | NAMED -> Filter 2 Var | HOST_CONFIRMED | NONE |
| `filter2.wet` | `{"kind":"field","field":"wet","list":"filters","index":1}` | `VoiceFilter1.plainParams.kParamWet`=50.0 | NAMED -> Filter 2 Wet | HOST_CONFIRMED | NONE |
| `fx.bode.blur` | `{"kind":"fx","fx_type":"FXBode","param":"kParamBlur"}` | `FXRack0.FX.0.FXBode.plainParams.kParamBlur`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.bode.range` | `{"kind":"fx","fx_type":"FXBode","param":"kParamRange"}` | `FXRack0.FX.0.FXBode.plainParams.kParamRange`=3043.1999999999975 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.bode.shift` | `{"kind":"fx","fx_type":"FXBode","param":"kParamShift"}` | `FXRack0.FX.0.FXBode.plainParams.kParamShift`=-9.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.bode.wet` | `{"kind":"fx","fx_type":"FXBode","param":"kParamWet"}` | `FXRack0.FX.0.FXBode.plainParams.kParamWet`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.chorus.depth` | `{"kind":"fx","fx_type":"FXChorus","param":"kParamDepth"}` | `FXRack0.FX.0.FXChorus.plainParams.kParamDepth`=13.000000000000004 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.chorus.feedback` | `{"kind":"fx","fx_type":"FXChorus","param":"kParamFeedback"}` | `FXRack0.FX.0.FXChorus.plainParams.kParamFeedback`=37.5 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.chorus.rate` | `{"kind":"fx","fx_type":"FXChorus","param":"kParamRate"}` | `FXRack0.FX.0.FXChorus.plainParams.kParamRate`=9.999999999999998 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.chorus.wet` | `{"kind":"fx","fx_type":"FXChorus","param":"kParamWet"}` | `FXRack0.FX.0.FXChorus.plainParams.kParamWet`=25.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.compressor.attack` | `{"kind":"fx","fx_type":"FXComp","param":"kParamAttack"}` | `FXRack0.FX.0.FXComp.plainParams.kParamAttack`=100.00000000000001 | ORACLE | CONFORMANCE_EXCEPTION | KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS |
| `fx.compressor.gain` | `{"kind":"fx","fx_type":"FXComp","param":"kParamMakeup"}` | `FXRack0.FX.0.FXComp.plainParams.kParamMakeup`=16.500000000000007 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.compressor.ratio` | `{"kind":"fx","fx_type":"FXComp","param":"kParamRatio"}` | `FXRack0.FX.0.FXComp.plainParams.kParamRatio`=100.0 | ORACLE | CONFORMANCE_EXCEPTION | KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS |
| `fx.compressor.release` | `{"kind":"fx","fx_type":"FXComp","param":"kParamRelease"}` | `FXRack0.FX.0.FXComp.plainParams.kParamRelease`=0.1 | ORACLE | CONFORMANCE_EXCEPTION | KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS |
| `fx.compressor.thresh` | `{"kind":"fx","fx_type":"FXComp","param":"kParamThresh"}` | `FXRack0.FX.0.FXComp.plainParams.kParamThresh`=0.25 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.compressor.wet` | `{"kind":"fx","fx_type":"FXComp","param":"kParamWet"}` | `FXRack0.FX.0.FXComp.plainParams.kParamWet`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.convolve.decay` | `{"kind":"fx","fx_type":"FXConv","param":"kParamDecay"}` | `FXRack0.FX.0.FXConv.plainParams.kParamDecay`=19.999999999999996 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.convolve.size` | `{"kind":"fx","fx_type":"FXConv","param":"kParamSize"}` | `FXRack0.FX.0.FXConv.plainParams.kParamSize`=505.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.convolve.tone` | `{"kind":"fx","fx_type":"FXConv","param":"kParamTone"}` | `FXRack0.FX.0.FXConv.plainParams.kParamTone`=-7.5 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.convolve.wet` | `{"kind":"fx","fx_type":"FXConv","param":"kParamWet"}` | `FXRack0.FX.0.FXConv.plainParams.kParamWet`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.delay.bpm` | `{"kind":"fx","fx_type":"FXDelay","param":"kParamBeatSync"}` | `FXRack0.FX.0.FXDelay.plainParams.kParamBeatSync`=0.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.delay.feedback` | `{"kind":"fx","fx_type":"FXDelay","param":"kParamFeedback"}` | `FXRack0.FX.0.FXDelay.plainParams.kParamFeedback`=45.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.delay.freq` | `{"kind":"fx","fx_type":"FXDelay","param":"kParamFreq"}` | `FXRack0.FX.0.FXDelay.plainParams.kParamFreq`=9015.249999999995 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.delay.link` | `{"kind":"fx","fx_type":"FXDelay","param":"kParamLink"}` | `FXRack0.FX.0.FXDelay.plainParams.kParamLink`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.delay.mode` | `{"kind":"fx","fx_type":"FXDelay","param":"kParamMode"}` | `FXRack0.FX.0.FXDelay.plainParams.kParamMode`=2.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.delay.time_l` | `{"kind":"fx","fx_type":"FXDelay","param":"kParamTimeL"}` | `FXRack0.FX.0.FXDelay.plainParams.kParamTimeL`=0.1705 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.delay.time_r` | `{"kind":"fx","fx_type":"FXDelay","param":"kParamTimeR"}` | `FXRack0.FX.0.FXDelay.plainParams.kParamTimeR`=0.1605 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.delay.wet` | `{"kind":"fx","fx_type":"FXDelay","param":"kParamWet"}` | `FXRack0.FX.0.FXDelay.plainParams.kParamWet`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.dimension.size` | `{"kind":"fx","fx_type":"FXHyperD","param":"kParamDimESize"}` | `FXRack0.FX.0.FXHyperD.plainParams.kParamDimESize`=25.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.dimension.wet` | `{"kind":"fx","fx_type":"FXHyperD","param":"kParamDimEWet"}` | `FXRack0.FX.0.FXHyperD.plainParams.kParamDimEWet`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.distortion.drive` | `{"kind":"fx","fx_type":"FXDistortion","param":"kParamDrive"}` | `FXRack0.FX.0.FXDistortion.plainParams.kParamDrive`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.distortion.freq` | `{"kind":"fx","fx_type":"FXDistortion","param":"kParamFreq"}` | `FXRack0.FX.0.FXDistortion.plainParams.kParamFreq`=0.25 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.distortion.type` | `{"kind":"fx","fx_type":"FXDistortion","param":"kParamMode"}` | `FXRack0.FX.0.FXDistortion.plainParams.kParamMode`="kAsym" | FULL_SCAN | RAW_ONLY | NONE |
| `fx.distortion.wet` | `{"kind":"fx","fx_type":"FXDistortion","param":"kParamWet"}` | `FXRack0.FX.0.FXDistortion.plainParams.kParamWet`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.equalizer.left_freq` | `{"kind":"fx","fx_type":"FXEQ","param":"kParamFreq1"}` | `FXRack0.FX.0.FXEQ.plainParams.kParamFreq1`=5010.750000000001 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.equalizer.left_gain` | `{"kind":"fx","fx_type":"FXEQ","param":"kParamGain1"}` | `FXRack0.FX.0.FXEQ.plainParams.kParamGain1`=-12.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.equalizer.left_q` | `{"kind":"fx","fx_type":"FXEQ","param":"kParamReso1"}` | `FXRack0.FX.0.FXEQ.plainParams.kParamReso1`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.equalizer.right_freq` | `{"kind":"fx","fx_type":"FXEQ","param":"kParamFreq2"}` | `FXRack0.FX.0.FXEQ.plainParams.kParamFreq2`=10010.750000000002 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.equalizer.right_gain` | `{"kind":"fx","fx_type":"FXEQ","param":"kParamGain2"}` | `FXRack0.FX.0.FXEQ.plainParams.kParamGain2`=-12.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.equalizer.right_q` | `{"kind":"fx","fx_type":"FXEQ","param":"kParamReso2"}` | `FXRack0.FX.0.FXEQ.plainParams.kParamReso2`=47.5 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.filter.cutoff` | `{"kind":"fx","fx_type":"FXFilter","param":"kParamFreq"}` | `FXRack0.FX.0.FXFilter.plainParams.kParamFreq`=0.25 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.filter.drive` | `{"kind":"fx","fx_type":"FXFilter","param":"kParamDrive"}` | `FXRack0.FX.0.FXFilter.plainParams.kParamDrive`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.filter.res` | `{"kind":"fx","fx_type":"FXFilter","param":"kParamReso"}` | `FXRack0.FX.0.FXFilter.plainParams.kParamReso`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.filter.type` | `{"kind":"fx","fx_type":"FXFilter","param":"kParamType"}` | `FXRack0.FX.0.FXFilter.plainParams.kParamType`="L6" | FULL_SCAN | RAW_ONLY | NONE |
| `fx.filter.wet` | `{"kind":"fx","fx_type":"FXFilter","param":"kParamWet"}` | `FXRack0.FX.0.FXFilter.plainParams.kParamWet`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.flanger.depth` | `{"kind":"fx","fx_type":"FXFlanger","param":"kParamDepth"}` | `FXRack0.FX.0.FXFlanger.plainParams.kParamDepth`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.flanger.feedback` | `{"kind":"fx","fx_type":"FXFlanger","param":"kParamFeedback"}` | `FXRack0.FX.0.FXFlanger.plainParams.kParamFeedback`=25.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.flanger.rate` | `{"kind":"fx","fx_type":"FXFlanger","param":"kParamRate"}` | `FXRack0.FX.0.FXFlanger.plainParams.kParamRate`=5.000000000000001 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.flanger.wet` | `{"kind":"fx","fx_type":"FXFlanger","param":"kParamWet"}` | `FXRack0.FX.0.FXFlanger.plainParams.kParamWet`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.hyper.detune` | `{"kind":"fx","fx_type":"FXHyperD","param":"kParamDetune"}` | `FXRack0.FX.0.FXHyperD.plainParams.kParamDetune`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.hyper.rate` | `{"kind":"fx","fx_type":"FXHyperD","param":"kParamRate"}` | `FXRack0.FX.0.FXHyperD.plainParams.kParamRate`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.hyper.unison` | `{"kind":"fx","fx_type":"FXHyperD","param":"kParamUnison"}` | `FXRack0.FX.0.FXHyperD.plainParams.kParamUnison`=3.5 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.hyper.wet` | `{"kind":"fx","fx_type":"FXHyperD","param":"kParamWet"}` | `FXRack0.FX.0.FXHyperD.plainParams.kParamWet`=25.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.phaser.depth` | `{"kind":"fx","fx_type":"FXPhaser","param":"kParamDepth"}` | `FXRack0.FX.0.FXPhaser.plainParams.kParamDepth`=25.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.phaser.feedback` | `{"kind":"fx","fx_type":"FXPhaser","param":"kParamFeedback"}` | `FXRack0.FX.0.FXPhaser.plainParams.kParamFeedback`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.phaser.freq` | `{"kind":"fx","fx_type":"FXPhaser","param":"kParamFreq"}` | `FXRack0.FX.0.FXPhaser.plainParams.kParamFreq`=3556.5588200778457 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.phaser.rate` | `{"kind":"fx","fx_type":"FXPhaser","param":"kParamRate"}` | `FXRack0.FX.0.FXPhaser.plainParams.kParamRate`=9.999999999999998 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.phaser.wet` | `{"kind":"fx","fx_type":"FXPhaser","param":"kParamWet"}` | `FXRack0.FX.0.FXPhaser.plainParams.kParamWet`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.reverb.size` | `{"kind":"fx","fx_type":"FXReverb","param":"kParamSize"}` | `FXRack0.FX.0.FXReverb.plainParams.kParamSize`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `fx.reverb.type` | `{"kind":"fx","fx_type":"FXReverb","param":"kParamType"}` | `FXRack0.FX.0.FXReverb.plainParams.kParamType`="kAbyss" | FULL_SCAN | RAW_ONLY | NONE |
| `fx.reverb.wet` | `{"kind":"fx","fx_type":"FXReverb","param":"kParamWet"}` | `FXRack0.FX.0.FXReverb.plainParams.kParamWet`=50.0 | FULL_SCAN | RAW_ONLY | NONE |
| `global.bend_range_down` | `{"kind":"singleton_field","field":"bend_range_down","attr":"global_"}` | `Global0.plainParams.kParamBendRangeDn`=-12.0 | NAMED -> Bend Down | HOST_CONFIRMED | NONE |
| `global.bend_range_up` | `{"kind":"singleton_field","field":"bend_range_up","attr":"global_"}` | `Global0.plainParams.kParamBendRangeUp`=12.0 | NAMED -> Bend Up | HOST_CONFIRMED | NONE |
| `global.direct_volume` | `{"kind":"singleton_field","field":"direct_volume","attr":"global_"}` | `Global0.plainParams.kParamDirectVol`=0.09999999999999999 | FULL_SCAN -> Direct Vol | HOST_CONFIRMED | NONE |
| `global.fx_bus1_destination` | `{"kind":"singleton_field","field":"fx_bus1_destination","attr":"global_"}` | `Global0.plainParams.kParamFXBus1Dest`=1.0 | ORACLE | CONFORMANCE_EXCEPTION | KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS |
| `global.fx_bus1_volume` | `{"kind":"singleton_field","field":"fx_bus1_volume","attr":"global_"}` | `Global0.plainParams.kParamFXBus1Vol`=0.09999999999999999 | FULL_SCAN -> Bus 1 Vol | HOST_CONFIRMED | NONE |
| `global.fx_bus2_destination` | `{"kind":"singleton_field","field":"fx_bus2_destination","attr":"global_"}` | `Global0.plainParams.kParamFXBus2Dest`=2.0 | ORACLE | CONFORMANCE_EXCEPTION | KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS |
| `global.fx_bus2_volume` | `{"kind":"singleton_field","field":"fx_bus2_volume","attr":"global_"}` | `Global0.plainParams.kParamFXBus2Vol`=0.09999999999999999 | FULL_SCAN -> Bus 2 Vol | HOST_CONFIRMED | NONE |
| `global.global_tuning` | `{"kind":"singleton_field","field":"global_tuning","attr":"global_"}` | `Global0.plainParams.kParamGlobalTuning`=450.0 | FULL_SCAN | HOST_CONFIRMED | NONE |
| `global.legato` | `{"kind":"singleton_field","field":"legato","attr":"global_"}` | `Global0.plainParams.kParamLegato`=1.0 | NAMED -> Legato | HOST_CONFIRMED | NONE |
| `global.limit_same_note_polyphony` | `{"kind":"singleton_field","field":"limit_same_note_polyphony","attr":"global_"}` | `Global0.plainParams.kParamLimitSameNotePolyphony`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `global.master_volume` | `{"kind":"singleton_field","field":"master_volume","attr":"global_"}` | `Global0.plainParams.kParamMasterVolume`=0.9 | NAMED -> Main Vol | HOST_CONFIRMED | NONE |
| `global.mono` | `{"kind":"singleton_field","field":"mono","attr":"global_"}` | `Global0.plainParams.kParamMonoToggle`=1.0 | NAMED -> Mono Toggle | HOST_CONFIRMED | NONE |
| `global.note_latch` | `{"kind":"singleton_field","field":"note_latch","attr":"global_"}` | `Global0.plainParams.kParamNoteLatch`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `global.oversampling` | `{"kind":"singleton_field","field":"oversampling","attr":"global_"}` | `Global0.plainParams.kParamOversampling`=2.0 | FULL_SCAN | RAW_ONLY | NONE |
| `global.poly_count` | `{"kind":"singleton_field","field":"poly_count","attr":"global_"}` | `Global0.plainParams.kParamPolyCount`=17.0 | FULL_SCAN | RAW_ONLY | NONE |
| `global.porta_always` | `{"kind":"singleton_field","field":"porta_always","attr":"global_"}` | `Global0.plainParams.kParamPortaAlways`=1.0 | NAMED -> Porta Always | HOST_CONFIRMED | NONE |
| `global.porta_scaled` | `{"kind":"singleton_field","field":"porta_scaled","attr":"global_"}` | `Global0.plainParams.kParamPortaScaled`=1.0 | NAMED -> Porta Scaled | HOST_CONFIRMED | NONE |
| `global.portamento_curve` | `{"kind":"singleton_field","field":"portamento_curve","attr":"global_"}` | `Global0.plainParams.kParamPortamentoCurve`=0.0010000000000047748 | FULL_SCAN | RAW_ONLY | NONE |
| `global.portamento_time` | `{"kind":"singleton_field","field":"portamento_time","attr":"global_"}` | `Global0.plainParams.kParamPortamentoTime`=1.5000000000000002 | NAMED -> Porta Time | HOST_CONFIRMED | NONE |
| `global.s1_compatibility` | `{"kind":"singleton_field","field":"s1_compatibility","attr":"global_"}` | `Global0.plainParams.kParamS1Compatibility`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `global.swing` | `{"kind":"singleton_field","field":"swing","attr":"global_"}` | `Global0.plainParams.kParamSwing`=25.0 | NAMED -> Swing | HOST_CONFIRMED | NONE |
| `global.swing_div` | `{"kind":"singleton_field","field":"swing_div","attr":"global_"}` | `Global0.plainParams.kParamSwingDiv`=6.0 | FULL_SCAN -> Swing Div | HOST_CONFIRMED | NONE |
| `global.transpose` | `{"kind":"singleton_field","field":"transpose","attr":"global_"}` | `Global0.plainParams.kParamTranspose`=-24.0 | NAMED -> Transpose | HOST_CONFIRMED | NONE |
| `global.use_ultra_on_render` | `{"kind":"singleton_field","field":"use_ultra_on_render","attr":"global_"}` | `Global0.plainParams.kParamUseUltraOnRender`=1.0 | ORACLE | CONFORMANCE_EXCEPTION | KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS |
| `global.voice_amp` | `{"kind":"singleton_field","field":"voice_amp","attr":"global_"}` | `Global0.plainParams.kParamVoiceAmp`=0.1 | FULL_SCAN -> Amp | HOST_CONFIRMED | NONE |
| `global.voice_control.random.cutoff` | `{"kind":"singleton_field","field":"random_filter_cutoff","attr":"voice_unison"}` | `VoicePanel0.plainParams.kParamGlobalRandomFilterCutoff`=1.0 | FULL_SCAN -> Cutoff Rand | HOST_CONFIRMED | NONE |
| `global.voice_control.random.detune` | `{"kind":"singleton_field","field":"random_detune","attr":"voice_unison"}` | `VoicePanel0.plainParams.kParamGlobalRandomOscDetune`=1.0 | FULL_SCAN -> Osc Detune Rnd | HOST_CONFIRMED | NONE |
| `global.voice_control.random.envs` | `{"kind":"singleton_field","field":"random_env_time","attr":"voice_unison"}` | `VoicePanel0.plainParams.kParamGlobalRandomEnvTime`=1.0 | FULL_SCAN -> Env Rand | HOST_CONFIRMED | NONE |
| `global.voice_control.random.pan` | `{"kind":"singleton_field","field":"random_pan","attr":"voice_unison"}` | `VoicePanel0.plainParams.kParamGlobalRandomOscPan`=50.0 | NAMED -> Osc Pan Rand | HOST_CONFIRMED | NONE |
| `global.voice_control.scaling.envs` | `{"kind":"singleton_field","field":"scaling_env_time","attr":"voice_unison"}` | `VoicePanel0.plainParams.kParamGlobalScalingEnvTime`=1000.0 | FULL_SCAN | RAW_ONLY | NONE |
| `global.voice_control.scaling.lfos` | `{"kind":"singleton_field","field":"scaling_lfo_time","attr":"voice_unison"}` | `VoicePanel0.plainParams.kParamGlobalScalingLfoTime`=1000.0 | FULL_SCAN | RAW_ONLY | NONE |
| `global.voice_priority` | `{"kind":"singleton_field","field":"voice_priority","attr":"global_"}` | `Global0.plainParams.kParamVoicePriority`="Low" | ORACLE | CONFORMANCE_EXCEPTION | KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS |
| `lfo1.beat_sync` | `{"kind":"field","field":"beat_sync","list":"lfos","index":0}` | `LFO0.plainParams.kParamBeatSync`=0.0 | NAMED -> LFO 1 Delay | HOST_CONFIRMED | NONE |
| `lfo1.delay` | `{"kind":"field","field":"delay","list":"lfos","index":0}` | `LFO0.plainParams.kParamDelay`=1.8 | NAMED -> LFO 1 Delay | HOST_CONFIRMED | NONE |
| `lfo1.dotted` | `{"kind":"field","field":"dotted","list":"lfos","index":0}` | `LFO0.plainParams.kParamDotted`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo1.mode` | `{"kind":"field","field":"mode","list":"lfos","index":0}` | `LFO0.plainParams.kParamMode`="Envelope" | FULL_SCAN | RAW_ONLY | NONE |
| `lfo1.mono` | `{"kind":"field","field":"mono","list":"lfos","index":0}` | `LFO0.plainParams.kParamMono`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo1.rate` | `{"kind":"field","field":"rate","list":"lfos","index":0}` | `LFO0.plainParams.kParamRate`=49.999999999999986 | NAMED -> LFO 1 Rate | HOST_CONFIRMED | NONE |
| `lfo1.rate_10x` | `{"kind":"field","field":"rate10x","list":"lfos","index":0}` | `LFO0.plainParams.kParamRate10x`=1.0 | NAMED_THEN_FULL_SCAN | RAW_ONLY | NONE |
| `lfo1.rise` | `{"kind":"field","field":"rise","list":"lfos","index":0}` | `LFO0.plainParams.kParamRise`=2.5 | NAMED -> LFO 1 Rise | HOST_CONFIRMED | NONE |
| `lfo1.shape` | `{"kind":"field","field":"shape","list":"lfos","index":0}` | `LFO0.plainParams.kParamType`="RandomSH" | FULL_SCAN | RAW_ONLY | NONE |
| `lfo1.smooth` | `{"kind":"field","field":"smooth","list":"lfos","index":0}` | `LFO0.plainParams.kParamSmooth`=50.0 | NAMED -> LFO 1 Smooth | HOST_CONFIRMED | NONE |
| `lfo1.swing` | `{"kind":"field","field":"swing","list":"lfos","index":0}` | `LFO0.plainParams.kParamSwing`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo1.triplets` | `{"kind":"field","field":"triplets","list":"lfos","index":0}` | `LFO0.plainParams.kParamTriplets`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo2.beat_sync` | `{"kind":"field","field":"beat_sync","list":"lfos","index":1}` | `LFO1.plainParams.kParamBeatSync`=0.0 | NAMED -> LFO 2 Delay | HOST_CONFIRMED | NONE |
| `lfo2.delay` | `{"kind":"field","field":"delay","list":"lfos","index":1}` | `LFO1.plainParams.kParamDelay`=1.8 | NAMED -> LFO 2 Delay | HOST_CONFIRMED | NONE |
| `lfo2.dotted` | `{"kind":"field","field":"dotted","list":"lfos","index":1}` | `LFO1.plainParams.kParamDotted`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo2.mode` | `{"kind":"field","field":"mode","list":"lfos","index":1}` | `LFO1.plainParams.kParamMode`="Envelope" | FULL_SCAN | RAW_ONLY | NONE |
| `lfo2.mono` | `{"kind":"field","field":"mono","list":"lfos","index":1}` | `LFO1.plainParams.kParamMono`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo2.rate` | `{"kind":"field","field":"rate","list":"lfos","index":1}` | `LFO1.plainParams.kParamRate`=49.999999999999986 | NAMED -> LFO 2 Rate | HOST_CONFIRMED | NONE |
| `lfo2.rate_10x` | `{"kind":"field","field":"rate10x","list":"lfos","index":1}` | `LFO1.plainParams.kParamRate10x`=1.0 | NAMED_THEN_FULL_SCAN | RAW_ONLY | NONE |
| `lfo2.rise` | `{"kind":"field","field":"rise","list":"lfos","index":1}` | `LFO1.plainParams.kParamRise`=2.5 | NAMED -> LFO 2 Rise | HOST_CONFIRMED | NONE |
| `lfo2.shape` | `{"kind":"field","field":"shape","list":"lfos","index":1}` | `LFO1.plainParams.kParamType`="RandomSH" | FULL_SCAN | RAW_ONLY | NONE |
| `lfo2.smooth` | `{"kind":"field","field":"smooth","list":"lfos","index":1}` | `LFO1.plainParams.kParamSmooth`=50.0 | NAMED -> LFO 2 Smooth | HOST_CONFIRMED | NONE |
| `lfo2.swing` | `{"kind":"field","field":"swing","list":"lfos","index":1}` | `LFO1.plainParams.kParamSwing`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo2.triplets` | `{"kind":"field","field":"triplets","list":"lfos","index":1}` | `LFO1.plainParams.kParamTriplets`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo3.beat_sync` | `{"kind":"field","field":"beat_sync","list":"lfos","index":2}` | `LFO2.plainParams.kParamBeatSync`=0.0 | NAMED -> LFO 3 Delay | HOST_CONFIRMED | NONE |
| `lfo3.delay` | `{"kind":"field","field":"delay","list":"lfos","index":2}` | `LFO2.plainParams.kParamDelay`=1.8 | NAMED -> LFO 3 Delay | HOST_CONFIRMED | NONE |
| `lfo3.dotted` | `{"kind":"field","field":"dotted","list":"lfos","index":2}` | `LFO2.plainParams.kParamDotted`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo3.mode` | `{"kind":"field","field":"mode","list":"lfos","index":2}` | `LFO2.plainParams.kParamMode`="Envelope" | FULL_SCAN | RAW_ONLY | NONE |
| `lfo3.mono` | `{"kind":"field","field":"mono","list":"lfos","index":2}` | `LFO2.plainParams.kParamMono`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo3.rate` | `{"kind":"field","field":"rate","list":"lfos","index":2}` | `LFO2.plainParams.kParamRate`=49.999999999999986 | NAMED -> LFO 3 Rate | HOST_CONFIRMED | NONE |
| `lfo3.rate_10x` | `{"kind":"field","field":"rate10x","list":"lfos","index":2}` | `LFO2.plainParams.kParamRate10x`=1.0 | NAMED_THEN_FULL_SCAN | RAW_ONLY | NONE |
| `lfo3.rise` | `{"kind":"field","field":"rise","list":"lfos","index":2}` | `LFO2.plainParams.kParamRise`=2.5 | NAMED -> LFO 3 Rise | HOST_CONFIRMED | NONE |
| `lfo3.shape` | `{"kind":"field","field":"shape","list":"lfos","index":2}` | `LFO2.plainParams.kParamType`="RandomSH" | FULL_SCAN | RAW_ONLY | NONE |
| `lfo3.smooth` | `{"kind":"field","field":"smooth","list":"lfos","index":2}` | `LFO2.plainParams.kParamSmooth`=50.0 | NAMED -> LFO 3 Smooth | HOST_CONFIRMED | NONE |
| `lfo3.swing` | `{"kind":"field","field":"swing","list":"lfos","index":2}` | `LFO2.plainParams.kParamSwing`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo3.triplets` | `{"kind":"field","field":"triplets","list":"lfos","index":2}` | `LFO2.plainParams.kParamTriplets`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo4.beat_sync` | `{"kind":"field","field":"beat_sync","list":"lfos","index":3}` | `LFO3.plainParams.kParamBeatSync`=0.0 | NAMED -> LFO 4 Delay | HOST_CONFIRMED | NONE |
| `lfo4.delay` | `{"kind":"field","field":"delay","list":"lfos","index":3}` | `LFO3.plainParams.kParamDelay`=1.8 | NAMED -> LFO 4 Delay | HOST_CONFIRMED | NONE |
| `lfo4.dotted` | `{"kind":"field","field":"dotted","list":"lfos","index":3}` | `LFO3.plainParams.kParamDotted`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo4.mode` | `{"kind":"field","field":"mode","list":"lfos","index":3}` | `LFO3.plainParams.kParamMode`="Envelope" | FULL_SCAN | RAW_ONLY | NONE |
| `lfo4.mono` | `{"kind":"field","field":"mono","list":"lfos","index":3}` | `LFO3.plainParams.kParamMono`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo4.rate` | `{"kind":"field","field":"rate","list":"lfos","index":3}` | `LFO3.plainParams.kParamRate`=49.999999999999986 | NAMED -> LFO 4 Rate | HOST_CONFIRMED | NONE |
| `lfo4.rate_10x` | `{"kind":"field","field":"rate10x","list":"lfos","index":3}` | `LFO3.plainParams.kParamRate10x`=1.0 | NAMED_THEN_FULL_SCAN | RAW_ONLY | NONE |
| `lfo4.rise` | `{"kind":"field","field":"rise","list":"lfos","index":3}` | `LFO3.plainParams.kParamRise`=2.5 | NAMED -> LFO 4 Rise | HOST_CONFIRMED | NONE |
| `lfo4.shape` | `{"kind":"field","field":"shape","list":"lfos","index":3}` | `LFO3.plainParams.kParamType`="RandomSH" | FULL_SCAN | RAW_ONLY | NONE |
| `lfo4.smooth` | `{"kind":"field","field":"smooth","list":"lfos","index":3}` | `LFO3.plainParams.kParamSmooth`=50.0 | NAMED -> LFO 4 Smooth | HOST_CONFIRMED | NONE |
| `lfo4.swing` | `{"kind":"field","field":"swing","list":"lfos","index":3}` | `LFO3.plainParams.kParamSwing`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo4.triplets` | `{"kind":"field","field":"triplets","list":"lfos","index":3}` | `LFO3.plainParams.kParamTriplets`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo5.beat_sync` | `{"kind":"field","field":"beat_sync","list":"lfos","index":4}` | `LFO4.plainParams.kParamBeatSync`=0.0 | NAMED -> LFO 5 Delay | HOST_CONFIRMED | NONE |
| `lfo5.delay` | `{"kind":"field","field":"delay","list":"lfos","index":4}` | `LFO4.plainParams.kParamDelay`=1.8 | NAMED -> LFO 5 Delay | HOST_CONFIRMED | NONE |
| `lfo5.dotted` | `{"kind":"field","field":"dotted","list":"lfos","index":4}` | `LFO4.plainParams.kParamDotted`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo5.mode` | `{"kind":"field","field":"mode","list":"lfos","index":4}` | `LFO4.plainParams.kParamMode`="Envelope" | FULL_SCAN | RAW_ONLY | NONE |
| `lfo5.mono` | `{"kind":"field","field":"mono","list":"lfos","index":4}` | `LFO4.plainParams.kParamMono`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo5.rate` | `{"kind":"field","field":"rate","list":"lfos","index":4}` | `LFO4.plainParams.kParamRate`=49.999999999999986 | NAMED -> LFO 5 Rate | HOST_CONFIRMED | NONE |
| `lfo5.rate_10x` | `{"kind":"field","field":"rate10x","list":"lfos","index":4}` | `LFO4.plainParams.kParamRate10x`=1.0 | NAMED_THEN_FULL_SCAN | RAW_ONLY | NONE |
| `lfo5.rise` | `{"kind":"field","field":"rise","list":"lfos","index":4}` | `LFO4.plainParams.kParamRise`=2.5 | NAMED -> LFO 5 Rise | HOST_CONFIRMED | NONE |
| `lfo5.shape` | `{"kind":"field","field":"shape","list":"lfos","index":4}` | `LFO4.plainParams.kParamType`="RandomSH" | FULL_SCAN | RAW_ONLY | NONE |
| `lfo5.smooth` | `{"kind":"field","field":"smooth","list":"lfos","index":4}` | `LFO4.plainParams.kParamSmooth`=50.0 | NAMED -> LFO 5 Smooth | HOST_CONFIRMED | NONE |
| `lfo5.swing` | `{"kind":"field","field":"swing","list":"lfos","index":4}` | `LFO4.plainParams.kParamSwing`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo5.triplets` | `{"kind":"field","field":"triplets","list":"lfos","index":4}` | `LFO4.plainParams.kParamTriplets`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo6.beat_sync` | `{"kind":"field","field":"beat_sync","list":"lfos","index":5}` | `LFO5.plainParams.kParamBeatSync`=0.0 | NAMED -> LFO 6 Delay | HOST_CONFIRMED | NONE |
| `lfo6.delay` | `{"kind":"field","field":"delay","list":"lfos","index":5}` | `LFO5.plainParams.kParamDelay`=1.8 | NAMED -> LFO 6 Delay | HOST_CONFIRMED | NONE |
| `lfo6.dotted` | `{"kind":"field","field":"dotted","list":"lfos","index":5}` | `LFO5.plainParams.kParamDotted`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo6.mode` | `{"kind":"field","field":"mode","list":"lfos","index":5}` | `LFO5.plainParams.kParamMode`="Envelope" | FULL_SCAN | RAW_ONLY | NONE |
| `lfo6.mono` | `{"kind":"field","field":"mono","list":"lfos","index":5}` | `LFO5.plainParams.kParamMono`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo6.rate` | `{"kind":"field","field":"rate","list":"lfos","index":5}` | `LFO5.plainParams.kParamRate`=49.999999999999986 | NAMED -> LFO 6 Rate | HOST_CONFIRMED | NONE |
| `lfo6.rate_10x` | `{"kind":"field","field":"rate10x","list":"lfos","index":5}` | `LFO5.plainParams.kParamRate10x`=1.0 | NAMED_THEN_FULL_SCAN | RAW_ONLY | NONE |
| `lfo6.rise` | `{"kind":"field","field":"rise","list":"lfos","index":5}` | `LFO5.plainParams.kParamRise`=2.5 | NAMED -> LFO 6 Rise | HOST_CONFIRMED | NONE |
| `lfo6.shape` | `{"kind":"field","field":"shape","list":"lfos","index":5}` | `LFO5.plainParams.kParamType`="RandomSH" | FULL_SCAN | RAW_ONLY | NONE |
| `lfo6.smooth` | `{"kind":"field","field":"smooth","list":"lfos","index":5}` | `LFO5.plainParams.kParamSmooth`=50.0 | NAMED -> LFO 6 Smooth | HOST_CONFIRMED | NONE |
| `lfo6.swing` | `{"kind":"field","field":"swing","list":"lfos","index":5}` | `LFO5.plainParams.kParamSwing`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `lfo6.triplets` | `{"kind":"field","field":"triplets","list":"lfos","index":5}` | `LFO5.plainParams.kParamTriplets`=1.0 | FULL_SCAN | RAW_ONLY | NONE |
| `macro1.name` | `{"kind":"field","field":"name","list":"macros","index":0}` | `Macro0.name`="MCP_TEST" | ORACLE | CONFORMANCE_EXCEPTION | KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS |
| `macro1.value` | `{"kind":"field","field":"value","list":"macros","index":0}` | `Macro0.plainParams.kParamValue`=50.0 | NAMED -> Macro 1 | HOST_CONFIRMED | NONE |
| `macro2.name` | `{"kind":"field","field":"name","list":"macros","index":1}` | `Macro1.name`="MCP_TEST" | ORACLE | CONFORMANCE_EXCEPTION | KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS |
| `macro2.value` | `{"kind":"field","field":"value","list":"macros","index":1}` | `Macro1.plainParams.kParamValue`=50.0 | NAMED -> Macro 2 | HOST_CONFIRMED | NONE |
| `macro3.name` | `{"kind":"field","field":"name","list":"macros","index":2}` | `Macro2.name`="MCP_TEST" | ORACLE | CONFORMANCE_EXCEPTION | KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS |
| `macro3.value` | `{"kind":"field","field":"value","list":"macros","index":2}` | `Macro2.plainParams.kParamValue`=50.0 | NAMED -> Macro 3 | HOST_CONFIRMED | NONE |
| `macro4.name` | `{"kind":"field","field":"name","list":"macros","index":3}` | `Macro3.name`="MCP_TEST" | ORACLE | CONFORMANCE_EXCEPTION | KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS |
| `macro4.value` | `{"kind":"field","field":"value","list":"macros","index":3}` | `Macro3.plainParams.kParamValue`=50.0 | NAMED -> Macro 4 | HOST_CONFIRMED | NONE |
| `macro5.name` | `{"kind":"field","field":"name","list":"macros","index":4}` | `Macro4.name`="MCP_TEST" | ORACLE | CONFORMANCE_EXCEPTION | KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS |
| `macro5.value` | `{"kind":"field","field":"value","list":"macros","index":4}` | `Macro4.plainParams.kParamValue`=50.0 | NAMED -> Macro 5 | HOST_CONFIRMED | NONE |
| `macro6.name` | `{"kind":"field","field":"name","list":"macros","index":5}` | `Macro5.name`="MCP_TEST" | ORACLE | CONFORMANCE_EXCEPTION | KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS |
| `macro6.value` | `{"kind":"field","field":"value","list":"macros","index":5}` | `Macro5.plainParams.kParamValue`=50.0 | NAMED -> Macro 6 | HOST_CONFIRMED | NONE |
| `macro7.name` | `{"kind":"field","field":"name","list":"macros","index":6}` | `Macro6.name`="MCP_TEST" | ORACLE | CONFORMANCE_EXCEPTION | KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS |
| `macro7.value` | `{"kind":"field","field":"value","list":"macros","index":6}` | `Macro6.plainParams.kParamValue`=50.0 | NAMED -> Macro 7 | HOST_CONFIRMED | NONE |
| `macro8.name` | `{"kind":"field","field":"name","list":"macros","index":7}` | `Macro7.name`="MCP_TEST" | ORACLE | CONFORMANCE_EXCEPTION | KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS |
| `macro8.value` | `{"kind":"field","field":"value","list":"macros","index":7}` | `Macro7.plainParams.kParamValue`=50.0 | NAMED -> Macro 8 | HOST_CONFIRMED | NONE |
| `mixer.filter1.bus1` | `{"kind":"field","field":"fx_bus1_send","list":"filters","index":0}` | `RoutingSlot5.plainParams.kParamFXBus1Level`=50.0 | NAMED -> Filter 1>BUS1 | HOST_CONFIRMED | NONE |
| `mixer.filter1.bus2` | `{"kind":"field","field":"fx_bus2_send","list":"filters","index":0}` | `RoutingSlot5.plainParams.kParamFXBus2Level`=50.0 | NAMED -> Filter 1>BUS2 | HOST_CONFIRMED | NONE |
| `mixer.filter1.enable` | `{"kind":"field","field":"enabled","list":"filters","index":0}` | `VoiceFilter0.plainParams.kParamEnable`=1.0 | NAMED -> Filter 1 On | HOST_CONFIRMED | NONE |
| `mixer.filter1.wet` | `{"kind":"field","field":"wet","list":"filters","index":0}` | `VoiceFilter0.plainParams.kParamWet`=50.0 | NAMED -> Filter 1 Wet | HOST_CONFIRMED | NONE |
| `mixer.filter2.bus1` | `{"kind":"field","field":"fx_bus1_send","list":"filters","index":1}` | `RoutingSlot6.plainParams.kParamFXBus1Level`=50.0 | NAMED -> Filter 2>BUS1 | HOST_CONFIRMED | NONE |
| `mixer.filter2.bus2` | `{"kind":"field","field":"fx_bus2_send","list":"filters","index":1}` | `RoutingSlot6.plainParams.kParamFXBus2Level`=50.0 | NAMED -> Filter 2>BUS2 | HOST_CONFIRMED | NONE |
| `mixer.filter2.enable` | `{"kind":"field","field":"enabled","list":"filters","index":1}` | `VoiceFilter1.plainParams.kParamEnable`=1.0 | NAMED -> Filter 2 On | HOST_CONFIRMED | NONE |
| `mixer.filter2.wet` | `{"kind":"field","field":"wet","list":"filters","index":1}` | `VoiceFilter1.plainParams.kParamWet`=50.0 | NAMED -> Filter 2 Wet | HOST_CONFIRMED | NONE |
| `mixer.noise.bus1` | `{"kind":"field","field":"fx_bus1_send","list":"oscillators","index":3}` | `RoutingSlot3.plainParams.kParamFXBus1Level`=50.0 | NAMED -> Noise>BUS1 | HOST_CONFIRMED | NONE |
| `mixer.noise.bus2` | `{"kind":"field","field":"fx_bus2_send","list":"oscillators","index":3}` | `RoutingSlot3.plainParams.kParamFXBus2Level`=50.0 | NAMED -> Noise>BUS2 | HOST_CONFIRMED | NONE |
| `mixer.noise.enable` | `{"kind":"field","field":"enabled","list":"oscillators","index":3}` | `Oscillator3.plainParams.kParamEnable`=1.0 | NAMED -> Noise Enable | HOST_CONFIRMED | NONE |
| `mixer.noise.filter_balance` | `{"kind":"field","field":"filter_balance","list":"oscillators","index":3}` | `RoutingSlot3.plainParams.kParamFilterBalance`=50.0 | NAMED -> Noise>Filter Balance | HOST_CONFIRMED | NONE |
| `mixer.noise.pan` | `{"kind":"field","field":"pan","list":"oscillators","index":3}` | `Oscillator3.plainParams.kParamPan`=-20.0 | ORACLE | CONFORMANCE_EXCEPTION | KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS |
| `mixer.osc_a.bus1` | `{"kind":"field","field":"fx_bus1_send","list":"oscillators","index":0}` | `RoutingSlot0.plainParams.kParamFXBus1Level`=50.0 | NAMED -> A>BUS1 | HOST_CONFIRMED | NONE |
| `mixer.osc_a.bus2` | `{"kind":"field","field":"fx_bus2_send","list":"oscillators","index":0}` | `RoutingSlot0.plainParams.kParamFXBus2Level`=50.0 | NAMED -> A>BUS2 | HOST_CONFIRMED | NONE |
| `mixer.osc_a.filter_balance` | `{"kind":"field","field":"filter_balance","list":"oscillators","index":0}` | `RoutingSlot0.plainParams.kParamFilterBalance`=50.0 | NAMED -> A>Filter Balance | HOST_CONFIRMED | NONE |
| `mixer.osc_b.bus1` | `{"kind":"field","field":"fx_bus1_send","list":"oscillators","index":1}` | `RoutingSlot1.plainParams.kParamFXBus1Level`=50.0 | NAMED -> B>BUS1 | HOST_CONFIRMED | NONE |
| `mixer.osc_b.bus2` | `{"kind":"field","field":"fx_bus2_send","list":"oscillators","index":1}` | `RoutingSlot1.plainParams.kParamFXBus2Level`=50.0 | NAMED -> B>BUS2 | HOST_CONFIRMED | NONE |
| `mixer.osc_b.filter_balance` | `{"kind":"field","field":"filter_balance","list":"oscillators","index":1}` | `RoutingSlot1.plainParams.kParamFilterBalance`=50.0 | NAMED -> B>Filter Balance | HOST_CONFIRMED | NONE |
| `mixer.osc_c.bus1` | `{"kind":"field","field":"fx_bus1_send","list":"oscillators","index":2}` | `RoutingSlot2.plainParams.kParamFXBus1Level`=50.0 | NAMED -> C>BUS1 | HOST_CONFIRMED | NONE |
| `mixer.osc_c.bus2` | `{"kind":"field","field":"fx_bus2_send","list":"oscillators","index":2}` | `RoutingSlot2.plainParams.kParamFXBus2Level`=50.0 | NAMED -> C>BUS2 | HOST_CONFIRMED | NONE |
| `mixer.osc_c.filter_balance` | `{"kind":"field","field":"filter_balance","list":"oscillators","index":2}` | `RoutingSlot2.plainParams.kParamFilterBalance`=50.0 | NAMED -> C>Filter Balance | HOST_CONFIRMED | NONE |
| `mixer.sub.bus1` | `{"kind":"field","field":"fx_bus1_send","list":"oscillators","index":4}` | `RoutingSlot4.plainParams.kParamFXBus1Level`=50.0 | NAMED -> Sub Osc>BUS1 | HOST_CONFIRMED | NONE |
| `mixer.sub.bus2` | `{"kind":"field","field":"fx_bus2_send","list":"oscillators","index":4}` | `RoutingSlot4.plainParams.kParamFXBus2Level`=50.0 | NAMED -> Sub Osc>BUS2 | HOST_CONFIRMED | NONE |
| `mixer.sub.enable` | `{"kind":"field","field":"enabled","list":"oscillators","index":4}` | `Oscillator4.plainParams.kParamEnable`=1.0 | NAMED -> Sub Enable | HOST_CONFIRMED | NONE |
| `mixer.sub.filter_balance` | `{"kind":"field","field":"filter_balance","list":"oscillators","index":4}` | `RoutingSlot4.plainParams.kParamFilterBalance`=50.0 | NAMED -> Sub Osc>Filter Balance | HOST_CONFIRMED | NONE |
| `mixer.sub.pan` | `{"kind":"field","field":"pan","list":"oscillators","index":4}` | `Oscillator4.plainParams.kParamPan`=-4.0 | ORACLE | CONFORMANCE_EXCEPTION | KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS |
| `oscA.detune` | `{"kind":"field","field":"detune","list":"oscillators","index":0}` | `Oscillator0.plainParams.kParamDetune`=0.5000000000000001 | NAMED -> A Uni Detune | HOST_CONFIRMED | NONE |
| `oscA.enabled` | `{"kind":"field","field":"enabled","list":"oscillators","index":0}` | `Oscillator0.plainParams.kParamEnable`=0.0 | NAMED -> A Enable | HOST_CONFIRMED | NONE |
| `oscA.fine` | `{"kind":"field","field":"fine","list":"oscillators","index":0}` | `Oscillator0.plainParams.kParamFine`=-40.0 | NAMED -> A Fine | HOST_CONFIRMED | NONE |
| `oscA.octave` | `{"kind":"field","field":"octave","list":"oscillators","index":0}` | `Oscillator0.plainParams.kParamOctave`=-2.0 | NAMED -> A Octave | HOST_CONFIRMED | NONE |
| `oscA.pan` | `{"kind":"field","field":"pan","list":"oscillators","index":0}` | `Oscillator0.plainParams.kParamPan`=-25.0 | NAMED -> A Pan | HOST_CONFIRMED | NONE |
| `oscA.sample_loop_crossfade` | `{"kind":"field","field":"sample_loop_crossfade","list":"oscillators","index":0}` | `Oscillator0.plainParams.kParamLoopCrossfade`=50.0 | NAMED -> A Loop X-Fade | HOST_CONFIRMED | NONE |
| `oscA.sample_loop_end` | `{"kind":"field","field":"sample_loop_end","list":"oscillators","index":0}` | `Oscillator0.plainParams.kParamLoopEnd`=50.0 | NAMED -> A Loop End | HOST_CONFIRMED | NONE |
| `oscA.sample_loop_start` | `{"kind":"field","field":"sample_loop_start","list":"oscillators","index":0}` | `Oscillator0.plainParams.kParamLoopStart`=50.0 | NAMED -> A Loop Start | HOST_CONFIRMED | NONE |
| `oscA.semitone` | `{"kind":"field","field":"semitone","list":"oscillators","index":0}` | `Oscillator0.plainParams.kParamPitch`=-6.0 | NAMED -> A Semi | HOST_CONFIRMED | NONE |
| `oscA.unison` | `{"kind":"field","field":"unison","list":"oscillators","index":0}` | `Oscillator0.plainParams.kParamUnison`=9.0 | NAMED -> A Unison | HOST_CONFIRMED | NONE |
| `oscA.warp_amount` | `{"kind":"field","field":"warp_amount","list":"oscillators","index":0}` | `Oscillator0.WTOsc0.plainParams.kParamWarp`=0.5 | ORACLE | CONFORMANCE_EXCEPTION | KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS |
| `oscA.warp_amount2` | `{"kind":"field","field":"warp_amount2","list":"oscillators","index":0}` | `Oscillator0.WTOsc0.plainParams.kParamWarp2`=0.5 | NAMED -> A Warp 2 | HOST_CONFIRMED | NONE |
| `oscA.warp_mode` | `{"kind":"field","field":"warp_mode","list":"oscillators","index":0}` | `Oscillator0.WTOsc0.plainParams.kParamWarpMenu`="kAM_OSC" | NAMED -> A Warp Mode | HOST_CONFIRMED | NONE |
| `oscA.warp_mode2` | `{"kind":"field","field":"warp_mode2","list":"oscillators","index":0}` | `Oscillator0.WTOsc0.plainParams.kParamXfadeMode`=1.0<br>`Oscillator0.WTOsc0.plainParams.kParamWarp2`=0.0<br>`Oscillator0.WTOsc0.plainParams.kParamWarpMenu2`="kFM_OSC" | NAMED -> A Warp 2 Mode | HOST_CONFIRMED | NONE |
| `oscA.warp_var2` | `{"kind":"field","field":"warp_var2","list":"oscillators","index":0}` | `Oscillator0.WTOsc0.plainParams.kParamWarpVar2`=0.5 | NAMED -> A Warp 2 Var | HOST_CONFIRMED | NONE |
| `oscA.wavetable` | `{"kind":"field","field":"wavetable","list":"oscillators","index":0}` | `Oscillator0.WTOsc0.numFrames`=14336<br>`Oscillator0.WTOsc0.relativePathToWT`="Analog/Basic Shapes.wav" | FULL_SCAN | RAW_ONLY | NONE |
| `oscB.detune` | `{"kind":"field","field":"detune","list":"oscillators","index":1}` | `Oscillator1.plainParams.kParamDetune`=0.5000000000000001 | NAMED -> B Uni Detune | HOST_CONFIRMED | NONE |
| `oscB.enabled` | `{"kind":"field","field":"enabled","list":"oscillators","index":1}` | `Oscillator1.plainParams.kParamEnable`=1.0 | NAMED -> B Enable | HOST_CONFIRMED | NONE |
| `oscB.fine` | `{"kind":"field","field":"fine","list":"oscillators","index":1}` | `Oscillator1.plainParams.kParamFine`=-40.0 | NAMED -> B Fine | HOST_CONFIRMED | NONE |
| `oscB.octave` | `{"kind":"field","field":"octave","list":"oscillators","index":1}` | `Oscillator1.plainParams.kParamOctave`=-2.0 | NAMED -> B Octave | HOST_CONFIRMED | NONE |
| `oscB.pan` | `{"kind":"field","field":"pan","list":"oscillators","index":1}` | `Oscillator1.plainParams.kParamPan`=-25.0 | NAMED -> B Pan | HOST_CONFIRMED | NONE |
| `oscB.sample_loop_crossfade` | `{"kind":"field","field":"sample_loop_crossfade","list":"oscillators","index":1}` | `Oscillator1.plainParams.kParamLoopCrossfade`=50.0 | NAMED -> B Loop X-Fade | HOST_CONFIRMED | NONE |
| `oscB.sample_loop_end` | `{"kind":"field","field":"sample_loop_end","list":"oscillators","index":1}` | `Oscillator1.plainParams.kParamLoopEnd`=50.0 | NAMED -> B Loop End | HOST_CONFIRMED | NONE |
| `oscB.sample_loop_start` | `{"kind":"field","field":"sample_loop_start","list":"oscillators","index":1}` | `Oscillator1.plainParams.kParamLoopStart`=50.0 | NAMED -> B Loop Start | HOST_CONFIRMED | NONE |
| `oscB.semitone` | `{"kind":"field","field":"semitone","list":"oscillators","index":1}` | `Oscillator1.plainParams.kParamPitch`=-6.0 | NAMED -> B Semi | HOST_CONFIRMED | NONE |
| `oscB.unison` | `{"kind":"field","field":"unison","list":"oscillators","index":1}` | `Oscillator1.plainParams.kParamUnison`=9.0 | NAMED -> B Unison | HOST_CONFIRMED | NONE |
| `oscB.warp_amount` | `{"kind":"field","field":"warp_amount","list":"oscillators","index":1}` | `Oscillator1.WTOsc1.plainParams.kParamWarp`=0.5 | NAMED -> B Warp | HOST_CONFIRMED | NONE |
| `oscB.warp_amount2` | `{"kind":"field","field":"warp_amount2","list":"oscillators","index":1}` | `Oscillator1.WTOsc1.plainParams.kParamWarp2`=0.5 | NAMED -> B Warp 2 | HOST_CONFIRMED | NONE |
| `oscB.warp_mode` | `{"kind":"field","field":"warp_mode","list":"oscillators","index":1}` | `Oscillator1.WTOsc1.plainParams.kParamWarpMenu`="kAM_OSC" | NAMED -> B Warp Mode | HOST_CONFIRMED | NONE |
| `oscB.warp_mode2` | `{"kind":"field","field":"warp_mode2","list":"oscillators","index":1}` | `Oscillator1.WTOsc1.plainParams.kParamXfadeMode`=1.0<br>`Oscillator1.WTOsc1.plainParams.kParamWarp2`=0.0<br>`Oscillator1.WTOsc1.plainParams.kParamWarpMenu2`="kFM_OSC" | NAMED -> B Warp 2 Mode | HOST_CONFIRMED | NONE |
| `oscB.warp_var2` | `{"kind":"field","field":"warp_var2","list":"oscillators","index":1}` | `Oscillator1.WTOsc1.plainParams.kParamWarpVar2`=0.5 | NAMED -> B Warp 2 Var | HOST_CONFIRMED | NONE |
| `oscB.wavetable` | `{"kind":"field","field":"wavetable","list":"oscillators","index":1}` | `Oscillator1.WTOsc1.numFrames`=14336<br>`Oscillator1.WTOsc1.relativePathToWT`="Analog/Basic Shapes.wav" | FULL_SCAN | RAW_ONLY | NONE |
| `oscC.detune` | `{"kind":"field","field":"detune","list":"oscillators","index":2}` | `Oscillator2.plainParams.kParamDetune`=0.5000000000000001 | NAMED -> C Uni Detune | HOST_CONFIRMED | NONE |
| `oscC.enabled` | `{"kind":"field","field":"enabled","list":"oscillators","index":2}` | `Oscillator2.plainParams.kParamEnable`=1.0 | NAMED -> C Enable | HOST_CONFIRMED | NONE |
| `oscC.fine` | `{"kind":"field","field":"fine","list":"oscillators","index":2}` | `Oscillator2.plainParams.kParamFine`=-40.0 | NAMED -> C Fine | HOST_CONFIRMED | NONE |
| `oscC.octave` | `{"kind":"field","field":"octave","list":"oscillators","index":2}` | `Oscillator2.plainParams.kParamOctave`=-2.0 | NAMED -> C Octave | HOST_CONFIRMED | NONE |
| `oscC.pan` | `{"kind":"field","field":"pan","list":"oscillators","index":2}` | `Oscillator2.plainParams.kParamPan`=-25.0 | NAMED -> C Pan | HOST_CONFIRMED | NONE |
| `oscC.sample_loop_crossfade` | `{"kind":"field","field":"sample_loop_crossfade","list":"oscillators","index":2}` | `Oscillator2.plainParams.kParamLoopCrossfade`=50.0 | NAMED -> C Loop X-Fade | HOST_CONFIRMED | NONE |
| `oscC.sample_loop_end` | `{"kind":"field","field":"sample_loop_end","list":"oscillators","index":2}` | `Oscillator2.plainParams.kParamLoopEnd`=50.0 | NAMED -> C Loop End | HOST_CONFIRMED | NONE |
| `oscC.sample_loop_start` | `{"kind":"field","field":"sample_loop_start","list":"oscillators","index":2}` | `Oscillator2.plainParams.kParamLoopStart`=50.0 | NAMED -> C Loop Start | HOST_CONFIRMED | NONE |
| `oscC.semitone` | `{"kind":"field","field":"semitone","list":"oscillators","index":2}` | `Oscillator2.plainParams.kParamPitch`=-6.0 | NAMED -> C Semi | HOST_CONFIRMED | NONE |
| `oscC.unison` | `{"kind":"field","field":"unison","list":"oscillators","index":2}` | `Oscillator2.plainParams.kParamUnison`=9.0 | NAMED -> C Unison | HOST_CONFIRMED | NONE |
| `oscC.warp_amount` | `{"kind":"field","field":"warp_amount","list":"oscillators","index":2}` | `Oscillator2.WTOsc2.plainParams.kParamWarp`=0.5 | NAMED -> C Warp | HOST_CONFIRMED | NONE |
| `oscC.warp_amount2` | `{"kind":"field","field":"warp_amount2","list":"oscillators","index":2}` | `Oscillator2.WTOsc2.plainParams.kParamWarp2`=0.5 | NAMED -> C Warp 2 | HOST_CONFIRMED | NONE |
| `oscC.warp_mode` | `{"kind":"field","field":"warp_mode","list":"oscillators","index":2}` | `Oscillator2.WTOsc2.plainParams.kParamWarpMenu`="kAM_OSC" | NAMED -> C Warp Mode | HOST_CONFIRMED | NONE |
| `oscC.warp_mode2` | `{"kind":"field","field":"warp_mode2","list":"oscillators","index":2}` | `Oscillator2.WTOsc2.plainParams.kParamXfadeMode`=1.0<br>`Oscillator2.WTOsc2.plainParams.kParamWarp2`=0.0<br>`Oscillator2.WTOsc2.plainParams.kParamWarpMenu2`="kFM_OSC" | NAMED -> C Warp 2 Mode | HOST_CONFIRMED | NONE |
| `oscC.warp_var2` | `{"kind":"field","field":"warp_var2","list":"oscillators","index":2}` | `Oscillator2.WTOsc2.plainParams.kParamWarpVar2`=0.5 | NAMED -> C Warp 2 Var | HOST_CONFIRMED | NONE |
| `oscC.wavetable` | `{"kind":"field","field":"wavetable","list":"oscillators","index":2}` | `Oscillator2.WTOsc2.numFrames`=14336<br>`Oscillator2.WTOsc2.relativePathToWT`="Analog/Basic Shapes.wav" | FULL_SCAN | RAW_ONLY | NONE |
| `oscNoise.fine` | `{"kind":"field","field":"fine","list":"oscillators","index":3}` | `Oscillator3.plainParams.kParamFine`=-40.0 | NAMED_THEN_FULL_SCAN | RAW_ONLY | NONE |
| `oscNoise.noise_type` | `{"kind":"field","field":"noise_type","list":"oscillators","index":3}` | `Oscillator3.NoiseOsc3.plainParams.kParamNoiseType`="Pink" | FULL_SCAN | RAW_ONLY | NONE |
| `oscNoise.pan` | `{"kind":"field","field":"pan","list":"oscillators","index":3}` | `Oscillator3.plainParams.kParamPan`=-20.0 | ORACLE | CONFORMANCE_EXCEPTION | KNOWN_EXCEPTION_DO_NOT_TREAT_AS_SUCCESS |
| `voice.voicing.legato` | `{"kind":"singleton_field","field":"legato","attr":"global_"}` | `Global0.plainParams.kParamLegato`=1.0 | NAMED -> Legato | HOST_CONFIRMED | NONE |
| `voice.voicing.mono` | `{"kind":"singleton_field","field":"mono","attr":"global_"}` | `Global0.plainParams.kParamMonoToggle`=1.0 | NAMED -> Mono Toggle | HOST_CONFIRMED | NONE |
| `voice.voicing.porta_always` | `{"kind":"singleton_field","field":"porta_always","attr":"global_"}` | `Global0.plainParams.kParamPortaAlways`=1.0 | NAMED -> Porta Always | HOST_CONFIRMED | NONE |
| `voice.voicing.porta_scaled` | `{"kind":"singleton_field","field":"porta_scaled","attr":"global_"}` | `Global0.plainParams.kParamPortaScaled`=1.0 | NAMED -> Porta Scaled | HOST_CONFIRMED | NONE |

## Validation

Enforced by the builder and by `test_final_execution_contract_v1.py`: 330 unique atlas_ids identical across v3, v2, contract v1 and map v8; counts 183/127/20; 0 failures; 0 noop suspects; 330/330 restoration verified; every row's test value, raw paths and reference conclusion cross-checked against contract v1 and map v8; v3 == v2 per row; raw-only rows carry no host identity.
