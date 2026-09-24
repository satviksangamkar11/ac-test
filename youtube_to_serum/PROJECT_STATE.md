# PROJECT STATE

## Latest update: 2026-09-24 — Phase A.2-A.4 trial rerun after boolean fix (VERIFICATION_BLOCKED)

## Hardened core status
- Repository: satviksangamkar11/ac-test
- Fix branch: fix/boolean-operand-kind-classification
- Base branch: generic-binding-contracts (76528dc)
- Test suite: 1013 passed, 2 skipped (5 pre-existing, unrelated failures in test_step1_complete_integration.py deselected — a VerifiedStateBuilder.add_matrix_route_observation signature mismatch, untouched by this branch's diff)
- Boolean/toggle-specific tests: 18/18 passed both before and after this trial's additional fix

## Boolean operand_kind fix — CONFIRMED (both parts required)
Two generic, non-parameter-specific fixes were needed, not one:
1. `serum2/producer/contract_scope.py`: `op_operand()` — TOGGLE_ON/TOGGLE_OFF now map to "boolean" (commit 3533365, prior session).
2. `serum2/evidence/capability_contract.py` + `contract_scope.py` (this session): `_mutation_value_kind()` classified every Python `bool` evidence value as `MUTATE_ENUM`, so contracts proven from boolean evidence were typed "enum", still mismatching the (already-fixed) "boolean" operation side. Added `MUTATE_BOOLEAN` constant and `"mutate_boolean_value": "boolean"` mapping. Fix #1 alone was necessary but not sufficient — the contract-side classification was the second half of the same generic gap.

Both fixes are keyed only on the operation family (TOGGLE_ON/OFF) and the evidence value's Python type (`bool`) respectively — no control-name branches.

## Trial `qUNIEASFZSs_trial2_boolfix` — result: VERIFICATION_BLOCKED
Location: `D:/ableton claude final best/serum2/data/runs/qUNIEASFZSs_trial2_boolfix/`
(The prior verified trial `qUNIEASFZSs/` was NOT touched or overwritten.)

- admission: ADMITTED 15, INCOMPATIBLE_OPERATION 2, NO_CAPABILITY 10, EPOCH_MISMATCH 6
- compiled: 15/15
- file readback: 10 exact, 5 normalized, 0 mismatches
- **live Serum UI readback (real — preset loaded into the running Serum 2 plugin in Ableton, read via computer-use screenshot of the actual plugin GUI, not describe_preset)**: 10 exact, 4 normalized, **1 MISMATCH** (`env2.sustain`: authorized 60% vs live-observed 36%)
- proof_level: **UI_READBACK_FAILED_OR_INCOMPLETE**
- coverage_status: **FAILED**
- reference_verified: **false**

### Boolean boundary result (this trial's actual objective) — FIXED AND LIVE-UI-VERIFIED
- `oscA.enabled`: TOGGLE_ON → ADMITTED → compiled → file VERIFIED_EXACT → **live UI VERIFIED_EXACT** (Serum GUI shows OSC A lit ON)
- `filter1.enabled`: TOGGLE_ON → ADMITTED → compiled → file VERIFIED_EXACT → **live UI VERIFIED_EXACT** (Serum GUI shows Filter 1 lit ON)
- Both fully traced through the canonical chain with no admission/compiler weakening.

### New finding this trial (not a regression, not silently patched)
`oscB.enabled` / `oscC.enabled` are now INCOMPATIBLE_OPERATION. Their contracts come from legacy Pass-1 pickled EvidenceRecords storing the mutation value as a raw float `1.0` with no declared `value_domain` — never proven boolean. Before the fix they were admitted only by coincidence (both operation and contract said "numeric"). The system now correctly refuses this false-positive match. This is a genuine pre-existing evidence gap, tracked as unresolved (see below), not papered over.

### Non-admitted (pre-existing, unrelated to boolean fix)
- NO_CAPABILITY (10): oscA.semitone, lfo1-4.mode, oscNoise.noise_type, fx.reverb.type, fx.compressor.ratio/attack/release
- EPOCH_MISMATCH (6): fx.equalizer.* — contracts qualified on Serum 2.0.21, this run's epoch is 2.0.23

### Unresolved
1. `env2.sustain`: authorized/reference value 60% (operand 0.6) compiled into the preset, but the live Serum GUI displays 36% for the same field — a genuine compiler/UI percentage-encoding mismatch, uninvestigated (out of this trial's scope). This is the row that blocks proof_level from reaching LIVE_UI_VERIFIED.
2. `oscB.enabled`/`oscC.enabled` need re-qualification through the generic binding-evidence loader (like oscA.enabled/filter1.enabled) instead of the legacy Pass-1 records.

## Forensic report
`serum2/data/runs/qUNIEASFZSs_trial2_boolfix/final_report/FORENSIC_REPORT.md` — full source/observation/execution/verification/provenance breakdown, generated from the actual run artifact (`reference_reproduction_run.json`), not hand-authored.

## Historical (superseded by this trial's real counts — kept for reference only)
- Original `qUNIEASFZSs` trial (frozen, unmodified): 15 compiled, file readback 10 exact/5 normalized, UI comparison used a FABRICATED placeholder (`serum_ui/ui_readback.json` had literal `"preset_sha256": "trial-preset-sha256"` — not real evidence, discovered and NOT reused this session).

## Next exact action
Root-cause the `env2.sustain` compiler/UI %-encoding mismatch (trace `EnvelopeSpec.sustain` through the generic compiler's percent→raw conversion vs. Serum's own ENV sustain % display curve) — this is the one row blocking LIVE_UI_VERIFIED / COMPLETE closure of Phase A.

## Persistent rule
After every meaningful project prompt, update this state with verified facts, exact test/run identifiers, and the next action. Do not replace verified facts with assumptions.
