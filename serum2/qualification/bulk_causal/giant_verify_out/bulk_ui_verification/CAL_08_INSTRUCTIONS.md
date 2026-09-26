# CAL_08_WARP_SYNC_2 — last step to close the 330-control map

This is the only thing left. Everything else in the map is done.

## What it is

3 more Sync-mode warp readings, on the same control you already read twice (`A Warp`, on OSC A/B/C, warp
mode = Sync). This time the raw values are chosen to bracket the ones you've already read — one near 0,
one in the middle gap, one near 1 — so a curve can be fitted with 8 points instead of 5.

## Steps

1. Copy `CAL_08_WARP_SYNC_2.SerumPreset` into `BULKCAUSAL_VERIFY/` (same as every CAL_0N preset).
2. Load it in Serum, the same way you loaded CAL_07 last time (browser rescan if it doesn't show up).
3. Confirm the title bar has no `*`.
4. Open the OSC page. Hover the WARP AMOUNT knob (the first warp knob, not warp 2) on A, B, and C:

| Osc | raw warp amount | record the reading here |
|---|---|---|
| A | 0.05 | |
| B | 0.55 | |
| C | 0.97 | |

## Output

Append to (or create, if it doesn't exist) `CLOSURE_PASS_5_results.json`:

```json
{"part": "C5", "preset": "CAL_08", "unit": "A", "raw": 0.05, "screen": "<exact text you saw>"}
{"part": "C5", "preset": "CAL_08", "unit": "B", "raw": 0.55, "screen": "<exact text you saw>"}
{"part": "C5", "preset": "CAL_08", "unit": "C", "raw": 0.97, "screen": "<exact text you saw>"}
```

If a knob gives no tooltip after one attempt, write `"screen": "UNREADABLE"` and move on.

Commit `CLOSURE_PASS_5_results.json` and push to `claude/direct-ui-rescan-2026-09-26`. That's the last
thing needed — once these 3 numbers are in, the map closes at 330/330.
