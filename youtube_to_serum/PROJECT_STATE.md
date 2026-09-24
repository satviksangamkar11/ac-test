# PROJECT STATE

## Latest update: 2026-09-24 — Generic percent display-curve gate CLOSED; trial3 LIVE_UI_VERIFIED (coverage PARTIAL)

## Hardened core status
- Repository: satviksangamkar11/ac-test
- Branch: fix/boolean-operand-kind-classification (base: generic-binding-contracts 76528dc)
- Test suite (local only — no CI runs exist for this branch): 1056 passed, 2 skipped, 5 failed. The 5 failures are the same pre-existing `serum2/producer/test_step1_complete_integration.py` failures present before both gates (VerifiedStateBuilder.add_matrix_route_observation signature mismatch); no new failures.
- Boolean tests 18/18; display-curve tests 43/43 (`serum2/producer/test_display_curve.py`)

## Gate status
| Gate | Status |
|---|---|
| A.1 Boolean operand typing | CLOSED |
| A.2 Trial rerun | COMPLETE |
| A.3 File + live UI verification | COMPLETE — LIVE_UI_VERIFIED for all 15 compiled ops |
| A.4 Trial/replay state | RECORDED |
| Percent display-curve correction | CLOSED |
| Overall Phase A (reference_verified) | NOT CLOSED — coverage PARTIAL |

## Percent display-curve fix
- Root cause: `state_ledger._to_target_unit()` converted every `%` observation into a 0..1 raw field linearly (`raw = pct/100`). Serum displays ENV sustain as `raw² × 100`, so reference 60% compiled to raw 0.60 and Serum showed 36%.
- Evidence: SUSTAIN_CURVE_TEST preset in live Serum — raw 0.25/0.50/0.81 displayed 6%/25%/66%. Supporting evidence only, not an authority artifact.
- Metadata source: no existing Atlas/schema field encoded a display curve (checked serum_ui_atlas.py, serum-mcp ParamDef, EnvelopeSpec). Minimal extension: structured pydantic field metadata `json_schema_extra={"display_curve": {"kind": "power", "exponent": N}}` on the authoritative spec field. Currently declared only on `EnvelopeSpec.sustain` (exponent 2) — the only field with measured evidence.
- Generic rule: `raw = (percent/100) ** (1/exponent)`. Exponent is data; linear is exponent 1. No control-name, field-name or envelope-index branching; no hardcoded values.
- Undeclared/invalid curve on a `%` → 0..1 conversion is refused with an explicit reason (not guessed). The FX-catalog path already refused `%` into normalized fields.

## Current trial: `qUNIEASFZSs_trial3_sustain_curve`
Location: `serum2/data/runs/qUNIEASFZSs_trial3_sustain_curve/` (gitignored run artifacts)
- ledger 139 rows, 33 OPERATION_DERIVED
- admission: ADMITTED 15, INCOMPATIBLE_OPERATION 2, NO_CAPABILITY 10, EPOCH_MISMATCH 6
- compiled 15/15
- file readback: 10 exact, 5 normalized, 0 mismatch
- live Serum UI: 10 exact, 5 normalized, 0 mismatch, 0 not observed
- env2.sustain: reference 60% → raw 0.7745966692414834 → file 0.77 → Serum UI 60%
- oscA.enabled / filter1.enabled: UI VERIFIED_EXACT
- proof_level = LIVE_UI_VERIFIED, coverage_status = PARTIAL, reference_verified = false
- preset sha256 f094a75b29eaf5933480040a2e3fe30ab99f738a0c660053063714c8b5155eb4
- forensic report: `final_report/FORENSIC_REPORT.md`

## Remaining blockers to reference_verified
1. oscB.enabled / oscC.enabled — INCOMPATIBLE_OPERATION: legacy Pass-1 evidence stores raw float 1.0 with no boolean value_domain; needs re-qualification through the generic binding-evidence loader.
2. NO_CAPABILITY (10): oscA.semitone, lfo1-4.mode, oscNoise.noise_type, fx.reverb.type, fx.compressor.ratio/attack/release.
3. EPOCH_MISMATCH (6): fx.equalizer.* contracts qualified on Serum 2.0.21.
4. 106 non-derived ledger rows (38 unreadable, 30 unbound, 17 unresolved, 16 unsupported, ...).

## Next exact action
Re-qualify oscB.enabled and oscC.enabled through the generic binding-evidence loader (candidate_binding_qualifier → binding_evidence JSON with value_domain.kind "bool"), the same path that already covers oscA.enabled/filter1.enabled.

## Historical
- `qUNIEASFZSs/` (frozen, untouched): 15 compiled; its `serum_ui/ui_readback.json` used placeholder hashes ("trial-preset-sha256") — not real UI evidence.
- `qUNIEASFZSs_trial2_boolfix/`: Boolean fix verified live; UI 10 exact / 4 normalized / 1 mismatch (env2.sustain 60% → 36%); proof UI_READBACK_FAILED_OR_INCOMPLETE.

## Persistent rule
After every meaningful project prompt, update this state with verified facts, exact test/run identifiers, and the next action. Do not replace verified facts with assumptions.
