# Finding: causal state-readback does not prove native-file/GUI truth for some raw writes

## CORRECTION (after further isolation testing)
The original version of this document claimed `lfo1.mode` shared the same root cause as the compressor and
sustain findings ("raw write bypasses `apply_spec`'s encoder"). **That claim was wrong and is retracted below,
in section 1.** A methodology error (reading Serum's LFO *shape* dropdown, not the *mode* buttons -- they sit
directly above/below each other in the same panel) produced the original "S&H" / "Normal" readings entirely.
Once corrected to read the actual `FREE`/`RETRIG`/`ENVELOPE` toggle buttons, two escalating isolation tests
(a single-field write, and a structural-merge-only write) both show the raw write working CORRECTLY --
`ENVELOPE` lights up as expected. Only the full 299-candidate giant preset shows `FREE` instead. This means
`lfo1.mode`'s failure mode is real but is NOT the same "raw write is fundamentally unreliable for this field"
story as the other 3 findings -- it's an unresolved interaction with something else among the other 298
candidates, not yet bisected. See section 1 below for the full, corrected trail.

Per c27645b/82d86f5 remaining untouched as historical checkpoints: this correction is a NEW addition on top
of the prior commit (f0cfb2e), not a rewrite of it. The prior commit's claim about `lfo1.mode` was incorrect;
this document says so plainly rather than quietly editing the record.

## Summary
Investigated all 4 open findings from the DIRECT_UI screen scan. 2 (`fx.compressor.ratio`/`.release`) are
confirmed genuine, isolated, reproducible mismatches with a common root cause (serum-mcp's schema domain for
these parameters does not match Serum's actual on-disk encoding). The 3rd (`env*.sustain`) resolves to a smaller
but still real version of the same root cause, not a display-unit red herring. The 4th (`lfo1.mode`) is a
confirmed real mismatch but with a DIFFERENT, not-yet-identified root cause -- see the correction above and
section 1 below.

## Root cause
The causal engine (`bulk_engine.py`) has exactly one write mechanism: `body_set()` writes a raw Python value
directly into the packed `.SerumPreset` dict at a `raw_path`. It never goes through `serum_mcp`'s structured
`apply_spec()` / `FxUnitSpec` / `PresetSpec` encoder -- the path real preset *generation* uses.

**CRITICAL CORRECTION**: The encoder does NOT bypass these values. The `apply_spec()` encoder passes values
through unchanged (verified by `encoder_diff.py`: for all 302 comparable controls, `apply_spec` and raw write
produce identical bodies). The problem is **serum-mcp's own schema domains are wrong** for these specific
parameters. The domain metadata (`min`/`max`/`kind`/enum vocabulary) was taken from schema metadata written
for the *structured* generation path (`"mechanism": "DIRECT_RAW"`/`"ENUM_RAW"`, etc.) -- but this metadata
describes constraints/transformations that apply during generation, not the actual on-disk encoding that
Serum's native loader reads. When the causal engine writes what the schema says should be valid directly into
the raw slot, Serum interprets that same byte/value differently because Serum's interpretation of the raw
encoding does not match what serum-mcp's schema claims it should be.

Examples:
- `fx.compressor.ratio`: schema domain says `kind: "log"` min 1.0 max 1,000,000. But Serum's native file
  loader interprets that raw slot differently, producing `1.0` and `30.4` for targets `31622.78` / `100.0`.
- `env*.sustain`: schema domain says `kind: continuous [0,1]` linear. Written `0.5`, Serum displays `-12.0dB` /
  `25%` (~0.251). The stored-value -> display curve is NOT yet known (dB, squared, or other); unverified.

For most candidates this is fine: the raw dict slot genuinely holds the value Serum reads. But for a subset,
there is a genuine mismatch between what the schema claims the encoding is and what Serum's native preset
loader actually does with it. When the causal engine writes that number/string directly into the raw slot,
two different things can happen:

1. **DawDreamer's live session** (`backend.load(body)` + `backend.observe()` -> `save_state()`/`decode()`)
   echoes the value back unchanged. This is what the campaign recorded as `state_value`, and it is what
   `closure_ledger_v2`'s `STATE_QUALIFIED_UI_PENDING` status is built on.
2. **Real Serum's native `.SerumPreset` file loader** (what a human opening the file in the actual GUI sees)
   can interpret the same raw slot differently -- silently falling back to a default, clamping through an
   unrelated curve, or reading a different byte/type than the causal engine wrote.

The campaign's own state-readback is therefore **not sufficient evidence** that a `DIRECT_RAW`/`ENUM_RAW`-
mechanism candidate's write is GUI-true. This is exactly the gap the DIRECT_UI screen-scan stage exists to
catch -- these 4 are the first confirmed instances, not a reason to distrust the whole campaign, but a
concrete reason the exhaustive scan must continue rather than stopping at "state matches."

## The 4 findings, resolved

### 1. `lfo1.mode` -- CONFIRMED MISMATCH, root cause NOT YET IDENTIFIED (corrected)
- Declared domain (schema-verified against `serum_mcp`'s `LfoSpec.mode` / `schema.py` LFO_MODE enum):
  exactly `Free`, `Retrig`, `Envelope`. Target written: `"Envelope"` (valid per this vocabulary).
- Serum's LFO1 panel has TWO adjacent controls that are easy to conflate: a `shape` dropdown (kParamType,
  e.g. "S&H", "Normal") directly above a `FREE`/`RETRIG`/`ENVELOPE` three-way toggle (kParamMode, the real
  mode). The first pass of this investigation read the shape dropdown and mistook it for the mode control --
  its "S&H" (giant preset) and "Normal" (isolated test) readings were `lfo1.shape`'s values, not `lfo1.mode`'s.
  (Fittingly, `lfo1.shape`'s own target is `"RandomSH"`, and "S&H" is very plausibly its display label --
  likely a MATCH, not investigated further here since it wasn't one of the 4 open findings.)
- **Corrected re-test, isolated single-field write** (pure init body, only `kParamMode='Envelope'` touched):
  `ENVELOPE` button correctly highlighted. MATCH.
- **Corrected re-test, structural-merge-only** (12-FX-slot + OSC_SAMPLE merge, THEN only `kParamMode` written,
  none of the other 298 candidates applied): `ENVELOPE` correctly highlighted. MATCH.
- **Corrected re-test, full giant preset** (all 299 candidates applied, including `lfo1.mode='Envelope'`):
  `FREE` highlighted, not `ENVELOPE`. Ruled out a stale-UI redraw (switched to the LFO2 tab and back --
  still shows `FREE`). The packed file itself was independently double-checked (both the builder's own
  assertion and the separate fresh-`unpack_file` readback test) and both confirm `kParamMode == 'Envelope'`
  in the actual file bytes.
- **Net**: the raw string write method itself is proven reliable for this field (both isolation tests pass).
  The giant preset's failure is a real, reproduced mismatch between file content and Serum's native rendering,
  but the trigger is an unidentified interaction with one or more of the other 298 candidates (possibly the
  other 5 LFOs also being set to `Envelope` simultaneously, possibly something else) -- not yet bisected.
  Retracts the original claim that this shares the compressor/sustain "encoder-bypass" root cause.

### 2 & 3. `fx.compressor.ratio` / `fx.compressor.release` -- CONFIRMED MISMATCH
- Both `mechanism: DIRECT_RAW`, domain `kind: "log"` sourced from `schema.FX_PARAMS ParamDef` (generation
  metadata, not necessarily the raw wire encoding).
- Campaign causal readback: full log-sweep (1.0 -> 31.6 -> 1000 -> 31622.8 -> 1,000,000) retained cleanly,
  clamped correctly beyond bounds -- looked like a fully clean, well-behaved control.
- **Giant preset, real Serum GUI**: `RATIO 1.0`, `RELEASE 30.4` for targets `31622.78` / `100.0`.
- **Isolated single-field test** (pure FXComp unit, only ratio+release touched): `RATIO 0.9`, `RELEASE 0.0` --
  DIFFERENT wrong values than the giant preset produced for the SAME targets.
- `fx.compressor.attack` (also DIRECT_RAW, same FX unit) matched exactly (`100.0`) in both tests -- proves
  this isn't a wholesale "compressor panel is broken" issue, it's specific to `ratio`/`release`'s raw
  encoding not matching what the causal engine assumes.

### 4. `env1-4.sustain` -- CONFIRMED MISMATCH (smaller than it first looked)
- Target `0.5` (all four envelopes, `mechanism: DIRECT_RAW`, `kind: continuous [0,1]`).
- `env1` displays `SUS -12.0dB`; `env2/3/4` display `SUS 25%` -- different UI unit choices per envelope panel.
- These two readings ARE mutually consistent: `10**(-12/20) = 0.2512 ~= 25.1%`. So it is not a display-unit
  red herring -- both units agree on one underlying stored value.
- But that agreed-upon value (~0.251) is NOT the target (0.5). The raw write landed somewhere other than
  intended, consistently across all four envelopes, just consistently-not-the-target rather than
  inconsistently wrong like the compressor case.

## What this does NOT mean
- It does not mean the giant-preset construction script has a bug -- the isolated, single-field, minimal-body
  tests reproduce the same class of divergence independent of the giant preset entirely.
- It does not mean every `DIRECT_RAW`/`ENUM_RAW` candidate is wrong -- the vast majority of this scan's ~40
  confirmed MATCHes (including `fx.compressor.attack`, itself DIRECT_RAW) are also raw writes that landed
  correctly. The gap is real but not universal, and only the screen can tell which candidates fall on which
  side.
- **IMPORTANT**: It DOES mean that presets generated through serum-mcp's `apply_spec()` for these same
  parameters (`fx.compressor.ratio`, `fx.compressor.release`, `env*.sustain`) will be equally wrong when loaded
  in the native Serum GUI, because the schema domain is wrong for ALL paths, not just the raw-write causal path.
  The encoder is not the problem; the schema specification itself is the problem. Fixing the write path fixes
  nothing. The schema domains must be corrected.
- No enum was expanded, no domain was widened, and no schema/Atlas file was touched to "fix" this -- per
  instruction, these are reported as open findings for the closure ledger to carry forward, not resolved by
  guessing a corrected encoding.

## Candidate count reconciliation (299 giant-preset vs 330 total MCP candidates)
No silent exclusion. Every one of the 330 MCP candidates (`campaign_accounting_v1.json`) has exactly one
terminal status in `giant_verification_plan.json`:

| status                        | count | why |
|---|---|---|
| `APPLIED_TO_GIANT_PRESET`     | 299   | has a campaign-retained target value, no path conflict |
| `APPLIED_TO_SECONDARY_PRESET` | 3     | `oscA/B/C.warp_amount2` -- genuine structural conflict: same oscillator slots as `OSC_SAMPLE` (chosen for the giant preset, 9 vs 3 candidates) but a different, mutually exclusive engine mode |
| `NO_USABLE_TARGET_VALUE`      | 26    | no retained non-probe value in the GUI campaign for this candidate (stricter than `closure_ledger`'s `observable()`, which also counts probes) |
| `NOT_DERIVED`                 | 2     | `arp.transpose.shape`, `global.voice_priority` -- vocabulary unknown, no manifest entry at all, never had a derivation mechanism |
| **total**                     | **330** | = `campaign_accounting_v1.json`'s `total_candidates` |

299 + 3 + 26 + 2 = 330. Enforced by an `assert` in `build_giant_verification_preset.py`'s `main()`.

## Next step
Continue the exhaustive page-by-page scan. Every candidate that turns out to match this same class of
divergence (state-true, GUI-false) should be logged as `MISMATCH` in the DIRECT_UI evidence, not silently
reclassified -- that is precisely the signal `closure_ledger_v3` needs to keep `STATE_QUALIFIED_UI_PENDING`
candidates from being promoted on causal evidence alone.
