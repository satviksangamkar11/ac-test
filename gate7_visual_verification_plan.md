# Gate 7: Visual Verification Plan

## Objective
Load the generated Prague Lead .SerumPreset into Serum 2.0.21 UI and verify the visible state matches the authorized execution record.

## Sections to Verify (in order)
1. **Oscillators**: OSC A (saw, vol 0.85), OSC B (saw, vol 0.0), OSC C, Noise
2. **Filter**: MG18 type, cutoff ~1800Hz (0.375 normalized), resonance 0.75
3. **Envelopes**: ENV 2 (pluck ADSR: 0.01/0.1/0.1/0.5), ENV 3, ENV 4
4. **LFO**: LFO 1 (rate 0.5 Hz, free mode)
5. **Matrix**: Routing connections (if visible)
6. **FX Chain** (PRIMARY): Distortion → Hyper → EQ → Delay → Compressor
   - Distortion: overdrive, drive 60%, wet 40%
   - Hyper: 7 voices, dimension 50%
   - EQ: +6dB @ 1kHz
   - Delay: 250ms, feedback 60%, beat sync OFF
   - Compressor: 4:1 ratio, threshold 0.6
7. **Global**: Master volume 0.5, poly count 8

## Screenshot Naming Convention
gate7_serum_{section}_{timestamp}.png

Examples:
- gate7_serum_osc_a_20260920_153731.png
- gate7_serum_fx_chain_20260920_153745.png

## Verification Record Format
```json
{
  "section": "OSC A",
  "expected": "saw, volume 0.85, enabled",
  "observed": "...",
  "match": true/false,
  "screenshot": "path"
}
```

## Gate 7 Success Criteria
✅ All major sections match expected state
✅ FX chain displays all 5 units in correct order
✅ FX parameters visible and match authorized values
✅ No silent drops or missing sections
✅ Fresh screenshots from current preset load
