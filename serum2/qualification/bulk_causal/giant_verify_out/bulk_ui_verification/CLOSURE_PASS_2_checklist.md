# Closure pass 2 checklist

Same rules as pass 1: hover only, no mouse wheel over knobs, check the title for `*` after each page.
Record each line in `CLOSURE_PASS_2_results.json`, one JSON object per line:
`{"part": "C2", "atlas_id": "...", "screen": "...", "result": "READ|UNREADABLE|ABSENT"}`

## Part 1: load `CAL_02_CONTEXTS` (35 lines)

- [ ] `lfo1.beat_sync`: expect Hz shown (BPM off)
- [ ] `lfo1.rate_10x`: expect 10x on
- [ ] `lfo1.swing`: expect swing / follow-swing on
- [ ] `lfo2.beat_sync`: expect Hz shown (BPM off)
- [ ] `lfo2.rate_10x`: expect 10x on
- [ ] `lfo2.swing`: expect swing / follow-swing on
- [ ] `lfo3.beat_sync`: expect Hz shown (BPM off)
- [ ] `lfo3.rate_10x`: expect 10x on
- [ ] `lfo3.swing`: expect swing / follow-swing on
- [ ] `lfo4.beat_sync`: expect Hz shown (BPM off)
- [ ] `lfo4.rate_10x`: expect 10x on
- [ ] `lfo4.swing`: expect swing / follow-swing on
- [ ] `lfo5.beat_sync`: expect Hz shown (BPM off)
- [ ] `lfo5.rate_10x`: expect 10x on
- [ ] `lfo5.swing`: expect swing / follow-swing on
- [ ] `lfo6.beat_sync`: expect Hz shown (BPM off)
- [ ] `lfo6.rate_10x`: expect 10x on
- [ ] `lfo6.swing`: expect swing / follow-swing on
- [ ] `context: RoutingSlot0 -> Filter`: expect FILTER
- [ ] `mixer.osc_a.filter_balance`: expect 15 (balance)
- [ ] `context: RoutingSlot1 -> Filter`: expect FILTER
- [ ] `mixer.osc_b.filter_balance`: expect 30 (balance)
- [ ] `context: RoutingSlot2 -> Filter`: expect FILTER
- [ ] `mixer.osc_c.filter_balance`: expect 45 (balance)
- [ ] `context: RoutingSlot3 -> Filter`: expect FILTER
- [ ] `mixer.noise.filter_balance`: expect 70 (balance)
- [ ] `context: RoutingSlot4 -> Filter`: expect FILTER
- [ ] `mixer.sub.filter_balance`: expect 85 (balance)
- [ ] `context: filter1 on`: expect on
- [ ] `context: filter2 on`: expect on
- [ ] `reference: LFO 7 shape`: expect S&H
- [ ] `reference: LFO 7 mode`: expect ENVELOPE greyed, FREE lit
- [ ] `global.voice_control.random.cutoff`: expect 37%
- [ ] `global.voice_control.random.detune`: expect 4.6
- [ ] `global.portamento_curve`: expect -37

## Part 2: load `BULK_01_WAVETABLE_MAIN`: re-reads

- [ ] `lfo4.beat_sync` on OSC/LFO4, written 1.0 (the LFO's BPM toggle)
- [ ] `lfo5.beat_sync` on OSC/LFO5, written 1.0 (the LFO's BPM toggle)
- [ ] `lfo6.beat_sync` on OSC/LFO6, written 1.0 (the LFO's BPM toggle)
- [ ] `oscA.warp_var2` on OSC/OSC_A, written 0.79 (the warp 2 **VAR** control, not the warp 2 amount knob)
- [ ] `oscB.warp_var2` on OSC/OSC_B, written 0.22 (the warp 2 **VAR** control, not the warp 2 amount knob)
- [ ] `oscC.warp_var2` on OSC/OSC_C, written 0.35 (the warp 2 **VAR** control, not the warp 2 amount knob)

## Part 3: BULK_01/02, one hover attempt each (class representative was unreadable)

- [ ] `env1.decay_curve` on BULK_01 / OSC/ENV1, written 69.0
- [ ] `env1.release_curve` on BULK_01 / OSC/ENV1, written 43.0
- [ ] `env2.attack_curve` on BULK_01 / OSC/ENV2, written 59.0
- [ ] `env2.decay_curve` on BULK_01 / OSC/ENV2, written 49.0
- [ ] `env2.release_curve` on BULK_01 / OSC/ENV2, written 39.0
- [ ] `env3.attack_curve` on BULK_01 / OSC/ENV3, written 72.0
- [ ] `env3.decay_curve` on BULK_01 / OSC/ENV3, written 51.0
- [ ] `env3.release_curve` on BULK_01 / OSC/ENV3, written 66.0
- [ ] `env4.attack_curve` on BULK_01 / OSC/ENV4, written 29.0
- [ ] `env4.decay_curve` on BULK_01 / OSC/ENV4, written 62.0
- [ ] `env4.release_curve` on BULK_01 / OSC/ENV4, written 82.0
- [ ] `filter1.resonance` on BULK_01 / OSC/FILTER1, written 86.0
- [ ] `filter1.stereo` on BULK_01 / OSC/FILTER1, written 87.0
- [ ] `filter1.var` on BULK_01 / OSC/FILTER1, written 14.0
- [ ] `filter2.cutoff` on BULK_01 / OSC/FILTER2, written 0.41
- [ ] `filter2.drive` on BULK_01 / OSC/FILTER2, written 12.0
- [ ] `filter2.key_track` on BULK_01 / OSC/FILTER2, written 1.0
- [ ] `filter2.level_out` on BULK_01 / OSC/FILTER2, written 0.47
- [ ] `filter2.resonance` on BULK_01 / OSC/FILTER2, written 8.0
- [ ] `filter2.stereo` on BULK_01 / OSC/FILTER2, written 88.0
- [ ] `filter2.var` on BULK_01 / OSC/FILTER2, written 89.0
- [ ] `lfo2.smooth` on BULK_01 / OSC/LFO2, written 92.0
- [ ] `lfo3.smooth` on BULK_01 / OSC/LFO3, written 93.0
- [ ] `lfo4.delay` on BULK_01 / OSC/LFO4, written 2.64
- [ ] `lfo4.smooth` on BULK_01 / OSC/LFO4, written 94.0
- [ ] `lfo5.delay` on BULK_01 / OSC/LFO5, written 3.08
- [ ] `lfo5.smooth` on BULK_01 / OSC/LFO5, written 95.0
- [ ] `lfo6.delay` on BULK_01 / OSC/LFO6, written 3.23
- [ ] `lfo6.rise` on BULK_01 / OSC/LFO6, written 2.7
- [ ] `lfo6.smooth` on BULK_01 / OSC/LFO6, written 96.0
- [ ] `mixer.filter1.wet` on BULK_01 / OSC/FILTER1, written 13.0
- [ ] `mixer.filter2.wet` on BULK_01 / OSC/FILTER2, written 90.0

Global re-reads (random cutoff/detune, portamento curve) are in Part 1.

Commit `CLOSURE_PASS_2_results.json` and push to `claude/direct-ui-rescan-2026-09-26`.
