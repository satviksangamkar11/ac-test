# Finding: causal state-readback does not prove native-file/GUI truth for some raw writes

## Summary
Investigated all 4 open findings from the DIRECT_UI screen scan. 3 are confirmed genuine, isolated,
reproducible mismatches with a common root cause. The 4th (env sustain) resolves to a smaller but still
real version of the same root cause, not a display-unit red herring.

## Root cause
The causal engine (`bulk_engine.py`) has exactly one write mechanism: `body_set()` writes a raw Python value
directly into the packed `.SerumPreset` dict at a `raw_path`. It never goes through `serum_mcp`'s structured
`apply_spec()` / `FxUnitSpec` / `PresetSpec` encoder -- the path real preset *generation* uses.

For most candidates this is fine: the raw dict slot genuinely holds the value Serum reads. But for a subset,
the domain used to drive the sweep (`min`/`max`/`kind`/enum vocabulary) was taken from schema metadata
written for the *structured* generation path (`"mechanism": "DIRECT_RAW"`/`"ENUM_RAW"`, `"derivation":
"differential of upstream apply_spec..."` or `"domain from schema.FX_PARAMS ParamDef"`) -- metadata that
describes what `apply_spec()` accepts as *input*, not necessarily the raw on-disk encoding. When the causal
engine writes that same number/string directly into the raw slot, two different things can happen:

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

### 1. `lfo1.mode` -- CONFIRMED MISMATCH
- Declared domain (schema-verified against `serum_mcp`'s `LfoSpec.mode` / `schema.py` LFO_MODE enum):
  exactly `Free`, `Retrig`, `Envelope`. Target written: `"Envelope"` (valid per this vocabulary).
- Campaign's causal state-readback: `state_value == "Envelope"` (looked retained).
- **Giant preset, real Serum GUI**: displays `S&H` -- not even in the declared 3-word vocabulary.
- **Isolated single-field test** (pure init body, only `kParamMode` touched, nothing else): displays
  `Normal` -- a THIRD different value, also not in the vocabulary.
- Three loads, three different outcomes (`Envelope` claimed / `S&H` / `Normal`), none matching each other.
  Proves the raw string write is not reliably interpreted by Serum's native loader for this field, regardless
  of what else is in the preset. Mechanism: `ENUM_RAW`.

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
