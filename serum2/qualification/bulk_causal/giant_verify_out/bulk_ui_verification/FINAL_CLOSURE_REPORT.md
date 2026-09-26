# Final closure report (control map v4)

330 controls, each with exactly one conclusion. Terminal: 265. Open: 65.

| conclusion | controls |
|---|---|
| DIRECT_UI_CONFIRMED | 172 |
| HOST_TEXT_VALIDATED | 40 |
| UI_OBSERVABLE_BUT_UNREADABLE | 36 |
| HOST_TEXT_UNVALIDATED (open) | 32 |
| NEEDS_CONTEXT (open) | 17 |
| UI_MISMATCH | 11 |
| NEEDS_REREAD (open) | 9 |
| UI_SCHEMA_MISMATCH | 6 |
| UI_LANDED_CURVE_OPEN (open) | 4 |
| RESIDUAL_NOT_DERIVED (open) | 2 |
| RESIDUAL_NOT_STORED (open) | 1 |

## Open work, exactly

**NEEDS_CONTEXT (17)**: `lfo1.rate_10x`, `lfo1.swing`, `lfo2.rate_10x`, `lfo2.swing`, `lfo3.rate_10x`, `lfo3.swing`, `lfo4.rate_10x`, `lfo4.swing`, `lfo5.rate_10x`, `lfo5.swing`, `lfo6.rate_10x`, `lfo6.swing`, `mixer.noise.filter_balance`, `mixer.osc_a.filter_balance`, `mixer.osc_b.filter_balance`, `mixer.osc_c.filter_balance`, `mixer.sub.filter_balance`

**NEEDS_REREAD (9)**: `global.portamento_curve`, `global.voice_control.random.cutoff`, `global.voice_control.random.detune`, `lfo4.beat_sync`, `lfo5.beat_sync`, `lfo6.beat_sync`, `oscA.warp_var2`, `oscB.warp_var2`, `oscC.warp_var2`

**HOST_TEXT_UNVALIDATED (32)**: `env1.decay_curve`, `env1.release_curve`, `env2.attack_curve`, `env2.decay_curve`, `env2.release_curve`, `env3.attack_curve`, `env3.decay_curve`, `env3.release_curve`, `env4.attack_curve`, `env4.decay_curve`, `env4.release_curve`, `filter1.resonance`, `filter1.stereo`, `filter1.var`, `filter2.cutoff`, `filter2.drive`, `filter2.key_track`, `filter2.level_out`, `filter2.resonance`, `filter2.stereo`, `filter2.var`, `lfo2.smooth`, `lfo3.smooth`, `lfo4.delay`, `lfo4.smooth`, `lfo5.delay`, `lfo5.smooth`, `lfo6.delay`, `lfo6.rise`, `lfo6.smooth`, `mixer.filter1.wet`, `mixer.filter2.wet`

**UI_LANDED_CURVE_OPEN (4)**: `fx.compressor.gain`, `fx.distortion.freq`, `fx.filter.cutoff`, `oscA.warp_amount`

**RESIDUAL_NOT_DERIVED (2)**: `arp.transpose.shape`, `global.voice_priority`

**RESIDUAL_NOT_STORED (1)**: `global.use_ultra_on_render`

## Vendor documentation (D tier, never a screen read)

- p14 'LFO 7 to LFO 10 appear after you assign LFO 6': LFO 7 IS viewable once LFO 6 has a mod route; the earlier 'no UI tab' conclusion is withdrawn (the conflict itself is proven on LFO1, CAL_01)
- p11 '13 powerful effects': the 330 candidates cover 12 FX types; the new Utility effect has none
- p11 'Multiple instances of a single effect': supports CAL_01's 8-compressor rack

## Mismatches found (terminal, reported not fixed)

- `arp.transpose.range` (UI_SCHEMA_MISMATCH): written 16, screen 8: Serum's range appears to stop at 8; declared domain too wide
- `fx.compressor.attack` (UI_SCHEMA_MISMATCH): carried from control map v3 (UI_SCHEMA_MISMATCH)
- `fx.compressor.ratio` (UI_SCHEMA_MISMATCH): carried from control map v3 (UI_SCHEMA_MISMATCH)
- `fx.compressor.release` (UI_SCHEMA_MISMATCH): carried from control map v3 (UI_SCHEMA_MISMATCH)
- `global.fx_bus1_destination` (UI_SCHEMA_MISMATCH): carried from control map v3 (UI_SCHEMA_MISMATCH)
- `global.fx_bus2_destination` (UI_SCHEMA_MISMATCH): carried from control map v3 (UI_SCHEMA_MISMATCH)
- `macro1.name` (UI_MISMATCH): Serum shows 'Macro 1', not the written name: macro names are normally shown in the UI, so the raw write ['Macro0','name'] likely does not take effect
- `macro2.name` (UI_MISMATCH): Serum shows 'Macro 2', not the written name: macro names are normally shown in the UI, so the raw write ['Macro1','name'] likely does not take effect
- `macro3.name` (UI_MISMATCH): Serum shows 'Macro 3', not the written name: macro names are normally shown in the UI, so the raw write ['Macro2','name'] likely does not take effect
- `macro4.name` (UI_MISMATCH): Serum shows 'Macro 4', not the written name: macro names are normally shown in the UI, so the raw write ['Macro3','name'] likely does not take effect
- `macro5.name` (UI_MISMATCH): Serum shows 'Macro 5', not the written name: macro names are normally shown in the UI, so the raw write ['Macro4','name'] likely does not take effect
- `macro6.name` (UI_MISMATCH): Serum shows 'Macro 6', not the written name: macro names are normally shown in the UI, so the raw write ['Macro5','name'] likely does not take effect
- `macro7.name` (UI_MISMATCH): Serum shows 'Macro 7', not the written name: macro names are normally shown in the UI, so the raw write ['Macro6','name'] likely does not take effect
- `macro8.name` (UI_MISMATCH): Serum shows 'Macro 8', not the written name: macro names are normally shown in the UI, so the raw write ['Macro7','name'] likely does not take effect
- `mixer.noise.pan` (UI_MISMATCH): written -20, screen -19 L (host text agrees): pan display off by one
- `mixer.sub.pan` (UI_MISMATCH): written -4, screen -3 L (host text agrees): pan display off by one
- `oscNoise.pan` (UI_MISMATCH): alias of mixer.noise.pan: written -20, screen -19 L
