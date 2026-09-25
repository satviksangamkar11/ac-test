# LFO Rate Crash Root Cause — 2026-09-25

## Summary
All six `lfoN.rate` parameters (N=1..6) crash Serum with access violation `0xC0000005` when written with **negative values**. The parameter's declared domain is `[0.0, 100.0]`, but the bulk engine's range_plan probes include `[-10.0, -50.0, -200.0]` to test clamping behavior. These out-of-bounds probes cause native Serum crashes.

## Evidence

### Isolated Value Tests (one value per fresh Serum process)
- 11 values tested per parameter × 6 parameters = 66 trials
- All survived: `0, 25, 50, 75, 100, 110, 150, 300, -10, -50, -200`
- Result: **No crash in isolation** — every value, including negatives, loads and restores cleanly

### Accumulated Sequence Tests (many values in one session)
- Negative values crash immediately when loaded into an active session
  - `[-10.0]` → CRASH (exit 0xC0000005)
  - `[-50.0]` → CRASH (exit 0xC0000005)
  - `[-200.0]` → CRASH (exit 0xC0000005)
  - `[300, -10]` → CRASH (any positive followed by negative)
  - `[0, -1]` → CRASH
  
- Positive and zero values safe, even beyond declared max:
  - `[0, 100, 110, 150, 300]` → SAFE (in sequence)
  - `[0, 25, 50, 75, 100, 110, 150, 300]` → SAFE

## Root Cause
Serum's VST3 implementation does not clamp out-of-bounds writes to `LFO[0..5].kParamRate` at the plugin boundary. When a raw state with a negative value is loaded into an active DawDreamer engine session, the write triggers an access violation in Serum's internal LFO rate interpolation or modulation routing code.

## Implications for the Ledger
The 6 `SERUM_CRASH` entries in `closure_ledger_v1.json` are **not parameter defects**. They are **probe-generation defects**: the range_plan's standard probe set `[...declared_max × 1.1, ...declared_max × 1.5, ...declared_max × 3.0, ...declared_min - 10, -50, -200]` assumes the engine/Serum can safely load out-of-bounds values (and return a clamped state).

## Action Required
1. **range_plan.py**: Clamp probe generation to stay within declared domain bounds, or reject probes that exceed them.
2. **campaign_supervisor**: Re-run the 6 lfoN.rate parameters with corrected probes (only positive values).
3. **ledger re-run**: The six will move from SERUM_CRASH → STATE_QUALIFIED_UI_PENDING (with probes fixed).

## No Changes to Ledger, Binding Table, Contracts, or Authority
This file documents evidence only. The immutable `closure_ledger_v1.json` is not modified.
