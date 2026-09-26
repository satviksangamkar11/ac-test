# CAL_04 / CAL_05 / CAL_06 / CAL_07 — exact instructions, 4 loads

Closes the 4 open display curves: compressor gain, distortion frequency, filter cutoff, warp amount (Sync
mode). Each preset holds 8 (or 3) units of ONE control; only that column varies. Load each one exactly the
way you loaded CAL_03: Serum dropdown → User → BULKCAUSAL_VERIFY → click the preset name, one click at a
time, screenshot between clicks, confirm no `*` before reading anything.

There is no "expected" value here — the whole point is to learn the curve, so just record the exact
number/text shown. Read each unit's header row directly (no clicking, hover only where needed), same as
CAL_01/CAL_03.

## 1. CAL_04_COMPRESSOR_GAIN (8 compressor units)

Every unit has ratio=4, thresh=0.5, attack=50, release=200 (all safe, non-Limit values) so the header
should show real numbers on every column, not "Limit". Only GAIN differs per unit.

Read the GAIN column of all 8 units, top to bottom (use the left FX list to pick each unit, never scroll
the mouse wheel over a knob):

| Unit | raw gain | record the GAIN reading here |
|---|---|---|
| 1 | 1.0 | |
| 2 | 4.0 | |
| 3 | 7.0 | |
| 4 | 11.0 | |
| 5 | 15.0 | |
| 6 | 18.0 | |
| 7 | 23.0 | |
| 8 | 30.0 | |

## 2. CAL_05_DISTORTION_FREQ (8 distortion units)

Read the FREQ knob of all 8 units (hover for the tooltip; the header may already show it directly like the
compressor did):

| Unit | raw freq | record the FREQ reading here |
|---|---|---|
| 1 | 0.05 | |
| 2 | 0.15 | |
| 3 | 0.28 | |
| 4 | 0.40 | |
| 5 | 0.52 | |
| 6 | 0.64 | |
| 7 | 0.76 | |
| 8 | 0.90 | |

## 3. CAL_06_FILTER_CUTOFF (8 filter units)

Same as above, but the FX FILTER unit's cutoff/freq knob:

| Unit | raw freq | record the FREQ reading here |
|---|---|---|
| 1 | 0.05 | |
| 2 | 0.15 | |
| 3 | 0.28 | |
| 4 | 0.40 | |
| 5 | 0.52 | |
| 6 | 0.64 | |
| 7 | 0.76 | |
| 8 | 0.90 | |

## 4. CAL_07_WARP_SYNC (OSC page, oscillators A/B/C)

All three oscillators are in WAVETABLE mode with warp mode = **Sync**. Only the WARP AMOUNT knob (the
first warp knob, not warp 2) differs per oscillator. Hover it on A, B and C:

| Osc | raw warp amount | record the WARP reading here |
|---|---|---|
| A | 0.20 | |
| B | 0.65 | |
| C | 0.90 | |

## Output

Write one line per row above to `CLOSURE_PASS_4_results.json`:

```json
{"part": "C4", "preset": "CAL_04", "unit": 1, "raw": 1.0, "screen": "<exact text you saw>"}
{"part": "C4", "preset": "CAL_05", "unit": 3, "raw": 0.28, "screen": "<exact text you saw>"}
{"part": "C4", "preset": "CAL_07", "unit": "A", "raw": 0.20, "screen": "<exact text you saw>"}
```

If any single knob gives no tooltip after one attempt, write `"screen": "UNREADABLE"` for that row only and
move on — do not retry, do not stop.

Commit `CLOSURE_PASS_4_results.json` and push to `claude/direct-ui-rescan-2026-09-26`.
