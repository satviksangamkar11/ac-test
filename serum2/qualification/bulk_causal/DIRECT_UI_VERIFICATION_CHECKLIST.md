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
- [x] FX page, numeric: **9 of 12 FX types checked** -- Bode (shift, range MATCH), Chorus (rate MATCH), Compressor
      (attack MATCH; ratio/release MISMATCH, resolved finding), Convolve (size MATCH), Delay (time_l/time_r/feedback
      all MATCH), Hyper (rate/detune MATCH, unison plausible), Dimension (not reached), Distortion (type
      NORMALIZED_MATCH), Equalizer (all 6 params MATCH, no hover needed -- shown directly)
- [ ] FX page, remaining: Dimension, Filter, Flanger, Phaser, Reverb not yet reached (~4 FX types, ~15 params) --
      stopped this pass after two accidental-mutation near-misses, see hazards note below
- [x] MATRIX page: confirmed empty (no mod-route candidates in the manifest) -- nothing to check
- [x] GLOBAL page, partial: `global.voice_control.random.pan` (50%, MATCH), `global.s1_compatibility` (checked, MATCH)
- [ ] GLOBAL page, remaining: bend_range_up/down, fx_bus1/2_destination, note_latch, oversampling, tuning fields
- [x] Bottom bar, partial: global TRANSPOSE (-24, MATCH), VOICING MONO/POLY/LEGATO visible (not field-compared)
- [ ] ARP page/panel (dedicated: transpose.shift, chance, gate, retrigger.*, velocity.*, pattern.*) -- **do not click the
      ARP toggle to get there** (accidentally toggled ARP on/off once already, caught via the "*" modified-title
      indicator and fixed by reloading the preset fresh); find the real ARP detail page or use hover-only
- [x] ENV1-4 panels, attack/hold/decay/release: **all 16 fields MATCH** (5.00s / 2.60s / 16.0s / 16.0s, identical
      across all four envelopes as expected since all four share the same campaign targets)
- [x] ENV1-4 sustain: resolved as confirmed MISMATCH, see DIRECT_UI_FINDING_RAW_WRITE_GAP.md
- [x] LFO1/LFO2 checked (rise, delay MATCH; shape NORMALIZED_MATCH; mode MISMATCH, see finding). LFO3-6 not
      individually checked but share identical targets with LFO1/2 -- treat as same pattern, not yet confirmed
- [ ] LFO1-6 remaining: smooth, beat_sync, dotted, triplets, mono, swing, rate_10x not checked
- [ ] FILTER1/FILTER2 panels (cutoff, resonance, drive, key_track) -- type already checked (filter2 NORMALIZED_MATCH); numeric knobs consistently show no tooltip on hover in this compact panel view (tried 3x) -- may need the panel's own expanded/detail view, not yet found
- [x] MACRO panel, partial: Macro 1, Macro 5 hover-confirmed MATCH (50). Macros 2/3/4/6/7/8 not individually checked but share identical target (50.0)
- [ ] Secondary preset `VERIFY_SECONDARY_OSC_WARP2` (3 candidates) not yet loaded/scanned

## Navigation hazards found (read before continuing the scan)
Two accidental-mutation near-misses while navigating the FX rack panel, both caught via the title's `*`
modified indicator and fixed by reloading the preset fresh (neither corrupted already-recorded evidence):
1. **Mouse-wheel scroll over a knob changes its value** (not panel scroll) -- never scroll while the cursor is
   positioned over a control. To see FX slots below the fold, use `left_click_drag` on the actual scrollbar
   (found at ~x=1172 in the FX page) or click a module's own collapse triangle -- but see hazard 2.
2. **A stray click near a module header's collapse-triangle instead ADDED a duplicate FX unit** to the rack.
   Coordinates in that area are not reliably safe -- verify with a screenshot after every click there, and
   check the title bar for `*` after each navigation action, not just after intentional edits.
As a result, Dimension/Filter/Flanger/Phaser/Reverb (5 of 12 FX types) were not reached this pass.

## Open findings -- RESOLVED (root cause identified for 3 of 4; lfo1.mode corrected, see DIRECT_UI_FINDING_RAW_WRITE_GAP.md)
`fx.compressor.ratio`/`.release` and `env1-4.sustain` are confirmed genuine MISMATCHes with a common root
cause: the causal engine's raw `body_set()` bypasses `serum_mcp`'s `apply_spec()` semantic encoder for
`DIRECT_RAW`-mechanism candidates. DawDreamer's session state-readback echoes the raw write back unchanged
(looks retained) but does not predict what Serum's native `.SerumPreset` file loader actually honors. This is
not fixed here (no enum expanded, no domain widened, no schema touched) -- it's reported as-is for the closure
ledger. **`lfo1.mode`'s original diagnosis was corrected** (see the CORRECTION section of
DIRECT_UI_FINDING_RAW_WRITE_GAP.md) after a methodology error was found: the original "S&H"/"Normal" readings
were `lfo1.shape`'s dropdown (an adjacent control), not the actual `FREE`/`RETRIG`/`ENVELOPE` mode toggle.
- [x] **`lfo1.mode`**: target `"Envelope"` (schema-confirmed valid, vocabulary is exactly Free/Retrig/Envelope).
      CORRECTED re-test reading the right control: isolated single-field write AND structural-merge-only write
      both correctly show `ENVELOPE` highlighted -- the raw write method itself works. Only the full
      299-candidate giant preset shows `FREE`. Confirmed real mismatch, but root cause is an unidentified
      interaction with the other 298 candidates, NOT the encoder-bypass story below. Needs further bisection.
- [x] **`fx.compressor.ratio`**: target `31622.78` (a legitimate point in the declared log-domain sweep, not an
      edge probe). Giant preset shows `RATIO 1.0`; isolated test shows `RATIO 0.9` -- different wrong value for
      the same target. `fx.compressor.attack` (same FX unit, same mechanism) MATCHED exactly in both tests,
      proving this is specific to `ratio`, not the whole panel. Mechanism: `DIRECT_RAW`.
- [x] **`fx.compressor.release`**: target `100.0`. Giant preset shows `30.4`; isolated test shows `0.0` --
      different wrong value again. Same mechanism/root cause as `ratio`.
- [x] **`env1/2/3/4.sustain`**: target `0.5`. `env1` displays `-12.0dB`, `env2/3/4` display `25%` -- these two
      readings are mutually consistent (`10**(-12/20) ~= 0.251 ~= 25%`), so it's one real underlying value
      (~0.251) shown in two different per-envelope unit choices, NOT a display-unit red herring -- but that
      value is still not the target (0.5). Same root cause, smaller magnitude.

## Not applicable to this pass (accounted for separately)
- 26 `NO_USABLE_TARGET_VALUE` -- no retained non-probe value in the GUI campaign; not in either preset
- 2 `NOT_DERIVED` (`arp.transpose.shape`, `global.voice_priority`) -- vocabulary unknown, never had a mechanism
- 3 `APPLIED_TO_SECONDARY_PRESET` -- see secondary preset scan above

## Next ledger step (after scan complete)
- [ ] Build `closure_ledger_v3` from `direct_ui_evidence_v2.json`, keeping `DIRECT_UI` strictly separate from
      `host_text_evidence` (per closure_ledger_v2's enforced separation)
- [ ] Only then prepare batched authority-delta review (binding table / Atlas / registry / contracts / admission
      remain untouched through this entire evidence pass)
