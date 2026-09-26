# Closure pass checklist

Two parts, both on presets you already have. Record each line as: screen text, or UNREADABLE (on screen, no exact value), or ABSENT (not in the UI).

## Part A: class representatives (44 reads validate 123 host-text controls)

Pass condition: the screen shows exactly the host text. If one disagrees, that whole class needs a full read.

| # | preset | view | control | written | screen must show | class size |
|---|---|---|---|---|---|---|
| 1 | BULK_01 | BOTTOM/MACROS | `macro2.value` | 73.0 | `73` | 6 |
| 2 | BULK_01 | GLOBAL/GLOBAL | `global.bend_range_down` | -8.0 | `-8` | 1 |
| 3 | BULK_01 | GLOBAL/GLOBAL | `global.bend_range_up` | 9.0 | `9` | 1 |
| 4 | BULK_01 | GLOBAL/GLOBAL | `global.legato` | 1.0 | `On` | 2 |
| 5 | BULK_01 | GLOBAL/GLOBAL | `global.master_volume` | 0.82 | `91% [1.3 dB]` | 1 |
| 6 | BULK_01 | GLOBAL/GLOBAL | `global.mono` | 1.0 | `On` | 2 |
| 7 | BULK_01 | GLOBAL/GLOBAL | `global.porta_always` | 1.0 | `On` | 2 |
| 8 | BULK_01 | GLOBAL/GLOBAL | `global.porta_scaled` | 1.0 | `On` | 2 |
| 9 | BULK_01 | GLOBAL/GLOBAL | `global.portamento_time` | 1.9 | `1.90 s` | 1 |
| 10 | BULK_01 | GLOBAL/GLOBAL | `global.swing` | 35.0 | `35.0%` | 1 |
| 11 | BULK_01 | MIX/MIX | `mixer.filter1.bus1` | 25.0 | `25%` | 14 |
| 12 | BULK_01 | MIX/MIX | `mixer.noise.enable` | 1.0 | `On` | 2 |
| 13 | BULK_01 | MIX/MIX | `mixer.noise.filter_balance` | 44.0 | `44` | 5 |
| 14 | BULK_01 | OSC/ENV1 | `env1.attack_curve` | 80.0 | `80` | 12 |
| 15 | BULK_01 | OSC/ENV2 | `env2.sustain` | 0.55 | `30%` | 1 |
| 16 | BULK_01 | OSC/ENV3 | `env3.sustain` | 0.56 | `31%` | 1 |
| 17 | BULK_01 | OSC/ENV4 | `env4.sustain` | 0.45 | `20%` | 1 |
| 18 | BULK_01 | OSC/FILTER1 | `filter1.cutoff` | 0.19 | `172` | 2 |
| 19 | BULK_01 | OSC/FILTER1 | `filter1.drive` | 83.0 | `83` | 8 |
| 20 | BULK_01 | OSC/FILTER1 | `filter1.enabled` | 1.0 | `On` | 2 |
| 21 | BULK_01 | OSC/FILTER1 | `filter1.key_track` | 1.0 | `172` | 2 |
| 22 | BULK_01 | OSC/FILTER1 | `filter1.level_out` | 0.73 | `6.5 dB` | 2 |
| 23 | BULK_01 | OSC/FILTER1 | `filter1.type` | 'L12' | `Low 12` | 1 |
| 24 | BULK_01 | OSC/FILTER1 | `filter1.wet` | 13.0 | `13` | 2 |
| 25 | BULK_01 | OSC/FILTER2 | `filter2.enabled` | 1.0 | `On` | 2 |
| 26 | BULK_01 | OSC/FILTER2 | `filter2.wet` | 90.0 | `90` | 2 |
| 27 | BULK_01 | OSC/LFO1 | `lfo1.rate` | 5.0 | `1/2 t` | 11 |
| 28 | BULK_01 | OSC/LFO1 | `lfo1.smooth` | 91.0 | `91` | 6 |
| 29 | BULK_01 | OSC/LFO2 | `lfo2.beat_sync` | 1.0 | `1/2` | 1 |
| 30 | BULK_01 | OSC/LFO3 | `lfo3.beat_sync` | 1.0 | `4 bar t` | 4 |
| 31 | BULK_01 | OSC/LFO3 | `lfo3.delay` | 2.98 | `4 bar t` | 5 |
| 32 | BULK_01 | OSC/OSC_A | `oscA.enabled` | 0.0 | `Off` | 3 |
| 33 | BULK_01 | OSC/OSC_A | `oscA.fine` | -26.0 | `-26` | 1 |
| 34 | BULK_01 | OSC/OSC_A | `oscA.octave` | -2.0 | `-2` | 1 |
| 35 | BULK_01 | OSC/OSC_A | `oscA.semitone` | -5.0 | `-5` | 1 |
| 36 | BULK_01 | OSC/OSC_A | `oscA.warp_var2` | 0.79 | `0.7900` | 1 |
| 37 | BULK_01 | OSC/OSC_B | `oscB.detune` | 0.53 | `0.53` | 2 |
| 38 | BULK_01 | OSC/OSC_B | `oscB.pan` | -24.0 | `-24 L` | 1 |
| 39 | BULK_01 | OSC/OSC_B | `oscB.warp_amount` | 0.42 | `58` | 1 |
| 40 | BULK_01 | OSC/OSC_B | `oscB.warp_var2` | 0.22 | `0.2200` | 1 |
| 41 | BULK_01 | OSC/OSC_C | `oscC.pan` | -11.0 | `-11 L` | 1 |
| 42 | BULK_01 | OSC/OSC_C | `oscC.warp_amount` | 0.18 | `18` | 1 |
| 43 | BULK_01 | OSC/OSC_C | `oscC.warp_var2` | 0.35 | `0.3500` | 1 |
| 44 | BULK_02 | OSC/OSC_A | `oscA.sample_loop_crossfade` | 83.0 | `83` | 3 |

## Part B: controls with no host text (115), BULK_01/02 page by page

**BULK_01 / ARP/ARP** (16)

- [ ] `arp.pattern.rate` written 0.4
- [ ] `arp.pattern.shape` written 'Chord'
- [ ] `arp.playback.chance` written 50.0
- [ ] `arp.playback.gate` written 47.0
- [ ] `arp.playback.offset` written 0.0
- [ ] `arp.playback.repeats` written 10.0
- [ ] `arp.playback.thru` written 1.0
- [ ] `arp.retrigger.first` written 1.0
- [ ] `arp.retrigger.launch` written 1.0
- [ ] `arp.retrigger.note` written 1.0
- [ ] `arp.transpose.range` written 16.0
- [ ] `arp.transpose.shift` written 3.0
- [ ] `arp.velocity.decay` written 0.9999999999999998
- [ ] `arp.velocity.enable` written 1.0
- [ ] `arp.velocity.retrig` written 1.0
- [ ] `arp.velocity.target` written 30.0 (scan note: no tooltip (visual only))

**BULK_01 / BOTTOM/MACROS** (8)

- [ ] `macro1.name` written 'FP_MACRO1_NAME'
- [ ] `macro2.name` written 'FP_MACRO2_NAME'
- [ ] `macro3.name` written 'FP_MACRO3_NAME'
- [ ] `macro4.name` written 'FP_MACRO4_NAME'
- [ ] `macro5.name` written 'FP_MACRO5_NAME'
- [ ] `macro6.name` written 'FP_MACRO6_NAME'
- [ ] `macro7.name` written 'FP_MACRO7_NAME'
- [ ] `macro8.name` written 'FP_MACRO8_NAME'

**BULK_01 / FX/FX_bode** (2)

- [ ] `fx.bode.blur` written 52.0
- [ ] `fx.bode.wet` written 26.0

**BULK_01 / FX/FX_chorus** (3)

- [ ] `fx.chorus.depth` written 18.0
- [ ] `fx.chorus.feedback` written 32.0
- [ ] `fx.chorus.wet` written 15.0

**BULK_01 / FX/FX_compressor** (1)

- [ ] `fx.compressor.wet` written 65.0

**BULK_01 / FX/FX_convolve** (3)

- [ ] `fx.convolve.decay` written 33.0
- [ ] `fx.convolve.tone` written 1.0
- [ ] `fx.convolve.wet` written 28.0

**BULK_01 / FX/FX_delay** (5)

- [ ] `fx.delay.bpm` written 1.0
- [ ] `fx.delay.freq` written 12843.0
- [ ] `fx.delay.link` written 1.0
- [ ] `fx.delay.mode` written 2.0
- [ ] `fx.delay.wet` written 45.0

**BULK_01 / FX/FX_dimension** (2)

- [ ] `fx.dimension.size` written 61.0 (scan note: no tooltip (visual knob estimate only))
- [ ] `fx.dimension.wet` written 34.0

**BULK_01 / FX/FX_distortion** (3)

- [ ] `fx.distortion.drive` written 78.0
- [ ] `fx.distortion.freq` written 0.51
- [ ] `fx.distortion.wet` written 24.0

**BULK_01 / FX/FX_filter** (5)

- [ ] `fx.filter.cutoff` written 0.67
- [ ] `fx.filter.drive` written 41.0
- [ ] `fx.filter.res` written 84.0
- [ ] `fx.filter.type` written 'L6'
- [ ] `fx.filter.wet` written 57.0

**BULK_01 / FX/FX_flanger** (4)

- [ ] `fx.flanger.depth` written 74.0
- [ ] `fx.flanger.feedback` written 20.0
- [ ] `fx.flanger.rate` written 6.4
- [ ] `fx.flanger.wet` written 37.0

**BULK_01 / FX/FX_hyper** (2)

- [ ] `fx.hyper.unison` written 6.0
- [ ] `fx.hyper.wet` written 53.0

**BULK_01 / FX/FX_phaser** (5)

- [ ] `fx.phaser.depth` written 27.0
- [ ] `fx.phaser.feedback` written 70.0
- [ ] `fx.phaser.freq` written 390.0
- [ ] `fx.phaser.rate` written 3.3
- [ ] `fx.phaser.wet` written 60.0

**BULK_01 / FX/FX_reverb** (2)

- [ ] `fx.reverb.size` written 76.0
- [ ] `fx.reverb.wet` written 23.0

**BULK_01 / GLOBAL/GLOBAL** (15)

- [ ] `global.direct_volume` written 0.09999999999999999
- [ ] `global.fx_bus1_volume` written 1.0000000000000002
- [ ] `global.fx_bus2_volume` written 0.001
- [ ] `global.global_tuning` written 450.0
- [ ] `global.limit_same_note_polyphony` written 1.0
- [ ] `global.note_latch` written 1.0
- [ ] `global.poly_count` written 7.0
- [ ] `global.portamento_curve` written -0.0010000000000047748
- [ ] `global.swing_div` written 1.0
- [ ] `global.voice_amp` written 0.0
- [ ] `global.voice_control.random.cutoff` written 0.1
- [ ] `global.voice_control.random.detune` written 0.01
- [ ] `global.voice_control.random.envs` written 100.0
- [ ] `global.voice_control.scaling.envs` written 1000.0
- [ ] `global.voice_control.scaling.lfos` written 10.0

**BULK_01 / MIX/MIX** (3)

- [ ] `mixer.noise.pan` written -20.0
- [ ] `mixer.sub.pan` written -4.0
- [ ] `oscNoise.pan` written -20.0

**BULK_01 / OSC/LFO1** (6)

- [ ] `lfo1.beat_sync` written 1.0
- [ ] `lfo1.dotted` written 1.0
- [ ] `lfo1.mono` written 1.0
- [ ] `lfo1.rate_10x` written 1.0
- [ ] `lfo1.swing` written 0.54
- [ ] `lfo1.triplets` written 1.0

**BULK_01 / OSC/LFO2** (5)

- [ ] `lfo2.dotted` written 1.0
- [ ] `lfo2.mono` written 1.0
- [ ] `lfo2.rate_10x` written 1.0
- [ ] `lfo2.swing` written 0.23
- [ ] `lfo2.triplets` written 1.0

**BULK_01 / OSC/LFO3** (5)

- [ ] `lfo3.dotted` written 1.0
- [ ] `lfo3.mono` written 1.0
- [ ] `lfo3.rate_10x` written 1.0
- [ ] `lfo3.swing` written 0.74
- [ ] `lfo3.triplets` written 1.0

**BULK_01 / OSC/LFO4** (5)

- [ ] `lfo4.dotted` written 1.0
- [ ] `lfo4.mono` written 1.0
- [ ] `lfo4.rate_10x` written 1.0
- [ ] `lfo4.swing` written 0.28
- [ ] `lfo4.triplets` written 1.0

**BULK_01 / OSC/LFO5** (5)

- [ ] `lfo5.dotted` written 1.0
- [ ] `lfo5.mono` written 1.0
- [ ] `lfo5.rate_10x` written 1.0
- [ ] `lfo5.swing` written 0.36
- [ ] `lfo5.triplets` written 1.0

**BULK_01 / OSC/LFO6** (5)

- [ ] `lfo6.dotted` written 1.0
- [ ] `lfo6.mono` written 1.0
- [ ] `lfo6.rate_10x` written 1.0
- [ ] `lfo6.swing` written 0.44
- [ ] `lfo6.triplets` written 1.0

**BULK_01 / OSC/NOISE** (2)

- [ ] `oscNoise.fine` written -53.0
- [ ] `oscNoise.noise_type` written 'Pink'

**BULK_01 / OSC/OSC_A** (1)

- [ ] `oscA.wavetable` written 'analog_basic'

**BULK_01 / OSC/OSC_B** (1)

- [ ] `oscB.wavetable` written 'analog_warm'

**BULK_01 / OSC/OSC_C** (1)

- [ ] `oscC.wavetable` written 'analog_mini'

## Part C: residuals (unchanged)

- `arp.transpose.shape`: set each of the 18 labels, save, read the file back.
- `global.voice_priority`: list the menu labels, then save/read back per label.
- `global.use_ultra_on_render`: toggle once, save, read the file.
- filter balance: locate the control for the 5 mixer strips.
