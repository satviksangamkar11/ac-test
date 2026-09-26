# CAL_03_FILTER_BALANCE — exact instructions, no exploration needed

This closes the last 4 open controls. All 5 oscillator/noise/sub channels are enabled AND routed to the
filters, so every balance knob is lit (not dimmed). Do not build or try anything else — this is the only
preset needed.

## 1. Load

The file is already copied into `BULKCAUSAL_VERIFY/CAL_03_FILTER_BALANCE.SerumPreset` (same folder as
BULK_01/02 and CAL_01/02). Load it exactly the way you loaded CAL_02: Serum preset dropdown → User →
BULKCAUSAL_VERIFY → CAL_03_FILTER_BALANCE. Do not use the next/previous preset arrow — go through the
dropdown, one click at a time, screenshotting between clicks. Confirm the title bar shows
`CAL_03_FILTER_BALANCE` with no `*` before continuing.

## 2. Where to look

Open the **MIX** page (top tab bar, next to OSC/FX/MATRIX/GLOBAL). All five channel strips — labelled
**A**, **B**, **C**, **NOISE**, **SUB** — should now show a green/lit "F" or "FILTER" routing indicator
(not dimmed), because every one of them is both enabled and routed to the filters in this preset.

Each channel strip has a small knob or icon in the row where the routing indicator sits — the one that
gave a tooltip called **"Filter Balance"** the last time you found it (on channel A in CAL_02, it read
"A> Filter Balance (15)"). It is the SAME control on each strip, just under a different channel letter.

## 3. What to read (hover only, one tooltip each)

Hover that control on each of the 5 strips and record the exact tooltip text. Expected tooltip name and
value for each:

| Strip | Expected tooltip | Atlas ID |
|---|---|---|
| A | `A> Filter Balance (12)` | `mixer.osc_a.filter_balance` |
| B | `B> Filter Balance (34)` | `mixer.osc_b.filter_balance` |
| C | `C> Filter Balance (56)` | `mixer.osc_c.filter_balance` |
| NOISE | `Noise> Filter Balance (78)` | `mixer.noise.filter_balance` |
| SUB | `Sub Osc> Filter Balance (90)` | `mixer.sub.filter_balance` |

If a tooltip's number matches the expected value, that control is done — record `READ` with the exact
tooltip text. If a strip is still dimmed or gives no tooltip after ONE hover attempt, record `UNREADABLE`
and move on immediately — do not retry, do not go looking for another control.

## 4. What NOT to do

- Do not click any knob. Hover only.
- Do not use the mouse wheel anywhere near Serum.
- Do not scroll the MIX page.
- Do not try to fix a dimmed strip yourself (no clicking enable buttons, no re-routing). If it's dimmed,
  record `UNREADABLE` and stop on that control — that itself is useful information for us.
- After reading all 5, check the title bar for `*`. If it appears, don't reload — just note it in your
  result file; nothing here should have been clickable enough to change state.

## 5. Output

Write to `giant_verify_out/bulk_ui_verification/CLOSURE_PASS_3_results.json`, one line per control,
same format as before:

```json
{"part": "C3", "atlas_id": "mixer.osc_a.filter_balance", "screen": "A> Filter Balance (12)", "result": "READ"}
{"part": "C3", "atlas_id": "mixer.osc_b.filter_balance", "screen": "B> Filter Balance (34)", "result": "READ"}
{"part": "C3", "atlas_id": "mixer.osc_c.filter_balance", "screen": "C> Filter Balance (56)", "result": "READ"}
{"part": "C3", "atlas_id": "mixer.noise.filter_balance", "screen": "Noise> Filter Balance (78)", "result": "READ"}
{"part": "C3", "atlas_id": "mixer.sub.filter_balance", "screen": "Sub Osc> Filter Balance (90)", "result": "READ"}
```

Then commit and push to `claude/direct-ui-rescan-2026-09-26`. That is the entire task — 5 hovers, 5 lines,
done. No further presets, no further exploration.
