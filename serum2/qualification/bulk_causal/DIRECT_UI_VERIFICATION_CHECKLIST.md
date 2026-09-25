# DIRECT_UI Verification Checklist (giant-preset stage)

Tracks screen-scan progress against `giant_verify_out/giant_verification_plan.json`
(299 candidates in `VERIFY_REFERENCE_FULL.SerumPreset`, 3 in `VERIFY_SECONDARY_OSC_WARP2.SerumPreset`).
Evidence goes in `parameter_characterization/bulk_causal_evidence/direct_ui_evidence_v2.json` as it's collected.

## Setup
- [x] Build giant preset (299 applied, 3 secondary, 26 no-usable-target, 2 not-derived = 330 accounted)
- [x] Fresh file-readback verification (0 mismatches, both presets)
- [x] Copy into Serum User presets (`BULKCAUSAL_VERIFY/`)
- [x] Load `VERIFY_REFERENCE_FULL` into a real, on-screen Serum 2 window (Ableton, temp track `QUAL_UI_VERIFY_TEMP`)
- [ ] Load `VERIFY_SECONDARY_OSC_WARP2` and scan its 3 candidates (oscA/B/C.warp_amount2)

## Screen scan by Serum page (OSC page is the default/first view)
- [x] OSC page, partial: oscA/B/C octave/semitone/fine, oscA/B/C sample_loop_start/end, unison, detune (hover), pan (hover) -- all MATCH
- [ ] OSC page, remaining: sample_loop_crossfade x3, blend/scan/level knobs, warp params, noise pan/stereo, sub
- [x] MIX page, partial: confirmed OSC A/B/C/Noise + Filter1/2 all enabled (green/blue dots); bus routing panel seen
- [ ] MIX page, remaining: per-channel pan/mix numeric values (need hover), bus1/bus2 sends
- [x] FX page, structural: **confirmed all 12 FX types present simultaneously as distinct rack slots** (Bode, Chorus,
      Compressor, Convolve, Delay, Hyper/Dimension, Distortion, Equalizer visible; Filter/Flanger/Phaser/Reverb below
      the fold) -- the core architecture claim is now visually proven, not just asserted
- [x] FX page, partial numeric: fx.compressor.attack MATCH (100.0); fx.compressor.ratio and .release MISMATCH (open finding)
- [ ] FX page, remaining: Bode/Chorus/Convolve/Delay/Hyper/Distortion/Equalizer/Filter/Flanger/Phaser/Reverb's other ~45 numeric params (need hover per knob)
- [x] MATRIX page: confirmed empty (no mod-route candidates in the manifest) -- nothing to check
- [x] GLOBAL page, partial: `global.voice_control.random.pan` (50%, MATCH), `global.s1_compatibility` (checked, MATCH)
- [ ] GLOBAL page, remaining: bend_range_up/down, fx_bus1/2_destination, note_latch, oversampling, tuning fields
- [x] Bottom bar, partial: global TRANSPOSE (-24, MATCH), VOICING MONO/POLY/LEGATO visible (not field-compared)
- [ ] ARP page/panel (dedicated: transpose.shift, chance, gate, retrigger.*, velocity.*, pattern.*) -- **do not click the
      ARP toggle to get there** (accidentally toggled ARP on/off once already, caught via the "*" modified-title
      indicator and fixed by reloading the preset fresh); find the real ARP detail page or use hover-only
- [x] ENV1-4 panels, attack/hold/decay/release: **all 16 fields MATCH** (5.00s / 2.60s / 16.0s / 16.0s, identical
      across all four envelopes as expected since all four share the same campaign targets)
- [ ] ENV1-4 sustain: open finding, see below (not yet resolved)
- [ ] LFO1-6 panels (rate, mode, shape, delay, rise, smooth, sync) -- LFO1 mode already checked (see open finding below); rate/delay/etc not yet checked
- [ ] FILTER1/FILTER2 panels (cutoff, resonance, drive, key_track) -- type already checked (filter2 NORMALIZED_MATCH); numeric knobs need hover (no tooltip appeared on first attempt at this panel's collapsed view, worth retrying on the full panel)
- [ ] MACRO panel (8 macro values)
- [ ] Secondary preset `VERIFY_SECONDARY_OSC_WARP2` (3 candidates) not yet loaded/scanned

## Open findings requiring targeted investigation (not yet resolved as MATCH/MISMATCH)
- [ ] **`lfo1.mode`**: plan target = `"Envelope"` (declared enum_str domain `["Retrig","Envelope"]`), screen shows **`S&H`** --
      `S&H` isn't even in the declared 2-value domain. Causal engine's own state-readback claimed "Envelope" was
      retained (state_value='Envelope' in campaign_run_gui_v1.json), with NO host-text corroboration either
      direction (host_text_display empty). Two possibilities: (a) writing a literal string into `kParamMode`
      doesn't match Serum's actual backing representation, or (b) the Atlas's declared enum is materially
      incomplete (Serum's real LFO mode list is longer than 2 values). Needs a targeted single-value live check.
- [ ] **`fx.compressor.ratio`**: target is a very large raw value (~31623, likely meant as near-infinite/limiting
      ratio); screen shows `RATIO 1.0` (no compression). Needs the raw-to-display curve checked before ruling.
- [ ] **`fx.compressor.release`**: target 100.0, screen shows `30.4`. Needs the raw-to-display curve checked
      (possibly a nonlinear ms mapping, same family of question as ratio above).
- [ ] **`env1/2/3/4.sustain`**: all four share raw target 0.5, but ENV1 displays `-12.0dB` while ENV2/3/4 display
      `25%` for the identical target -- a per-envelope display-unit toggle, not obviously a value bug, but neither
      reading is the naive linear 0.5 -> 50% one might expect. Needs the sustain curve/unit checked before ruling.

## Not applicable to this pass (accounted for separately)
- 26 `NO_USABLE_TARGET_VALUE` -- no retained non-probe value in the GUI campaign; not in either preset
- 2 `NOT_DERIVED` (`arp.transpose.shape`, `global.voice_priority`) -- vocabulary unknown, never had a mechanism
- 3 `APPLIED_TO_SECONDARY_PRESET` -- see secondary preset scan above

## Next ledger step (after scan complete)
- [ ] Build `closure_ledger_v3` from `direct_ui_evidence_v2.json`, keeping `DIRECT_UI` strictly separate from
      `host_text_evidence` (per closure_ledger_v2's enforced separation)
- [ ] Only then prepare batched authority-delta review (binding table / Atlas / registry / contracts / admission
      remain untouched through this entire evidence pass)
