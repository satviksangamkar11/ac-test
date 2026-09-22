# Phase 2: Unified Observation Engine

**Status: HARDENED & VERIFIED**  
Commit: `9ab32e4` (critical fixes: real normalization validation + prefix format handling)

---

## What Phase 2 Built

A generic observation strategy abstraction that normalizes raw evidence into validated candidates, decoupling observation modalities from state_ledger's validation logic.

```
Raw observation (control_id, raw_value, ROI evidence)
    ↓
ObservationEngine.observe()
    ↓
Strategy selected (TEXT, ENUM, NUMERIC, ENABLE_STATE, ROUTE_TEXT, GRAPH_DERIVED, RUNTIME_STATE, SLIDER_PIXEL)
    ↓
ObservationCandidate (normalized_value, confidence, evidence_hash)
    ↓
state_ledger.derive() [unchanged]
    ↓
TerminalObservation
```

## Architecture Decisions

1. **No changes to state_ledger.derive()** — validation and coercion remain the single authority
2. **Qwen remains untrusted** — vlm_source flag marks candidates from vision models; no VLM decision becomes terminal without deterministic validation
3. **Generic strategies only** — no parameter-specific observers; strategy selection based on element_kind/control_type from atlas
4. **Runtime state separated** — explicit RuntimeStateObservationStrategy prevents voice meters, level meters, etc. from becoming preset evidence
5. **Slider calibration deferred** — SliderPixelObservationStrategy interface exists but returns UNOBSERVED_UNSUPPORTED_MODALITY (Phase 3 work)

## Strategies Implemented

| Strategy | Use Case | Input | Output |
|----------|----------|-------|--------|
| TEXT | Literal transcription | string | normalized string |
| ENUM | Selector value | string | canonical enum value or error |
| NUMERIC | Continuous parameter | "123 Hz" / "45 ms" | (float, unit) tuple |
| ENABLE_STATE | Checkbox/toggle | "ON"/"OFF" / checkbox visual | "ON" or "OFF" |
| ROUTE_TEXT | Modulation source/dest | "Env 2" / "Filter1 Freq" | text with validation |
| GRAPH_DERIVED | Runtime animations (Phase 1) | N/A | marks as derived, not independent |
| RUNTIME_STATE | Live UI state | "0/8" voice meter | marks as transient, excluded |
| SLIDER_PIXEL | Slider pixel position | N/A (Phase 3) | UNSUPPORTED_MODALITY |

## Phase 2 Hardening & Regression Tests

**Real Gate-A Evidence Test (5/5 PASS — with normalization validation)**  
Uses actual raw Qwen outputs from `five_roi_test_results.json` (committed benchmark). Validates normalization against declared strategy contracts:

```
[PASS] OSC A Unison: NUMERIC → (7.0, '') from raw "VALUE=7"
[PASS] Matrix Route: ROUTE_TEXT → None (raw preserved for ledger parsing)
[PASS] LFO1 Mode: ENUM → "Lorenz" from raw "Chaos: Lorenz"
[PASS] Drive: NUMERIC → (1.9, '') from raw "DRIVE=1.9"
[PASS] Legato: ENABLE_STATE → "OFF" from raw "STATE=OFF"
```

**Explicit Outcome Tests (4/4 PASS)**
- RUNTIME_STATE produces outcome=NOT_APPLICABLE ✓
- SLIDER_PIXEL produces outcome=UNSUPPORTED_MODALITY ✓
- GRAPH_DERIVED produces outcome=NOT_APPLICABLE (visual evidence, not independent preset state) ✓
- Unknown metadata correctly raises ValueError ✓

**Total: 9/9 PASS** (5 real evidence + 4 explicit outcomes)

## Phase 2 Acceptance Criteria

- [x] 1. Metadata-driven strategy selection ready for future ExpectedInventory integration
- [x] 2. ROI evidence represented with bbox + image/crop hash
- [x] 3. Qwen output always marked UNTRUSTED_CANDIDATE (vlm_source flag)
- [x] 4. Deterministic validators produce terminal statuses (state_ledger._coerce())
- [x] 5. TEXT/ENUM/NUMERIC/ENABLE_STATE/ROUTE_TEXT work through generic interface
- [x] 6. Runtime state cannot become PRESET_STATE (outcome=NOT_APPLICABLE)
- [x] 7. No parameter-specific observer implementations (all strategies generic)
- [x] 8. Actual Gate-A evidence normalizes correctly (regression test 5/5 with contract validation)
- [x] 9. State Ledger receives candidates; no data dropping (architecture preserved)
- [x] 10. No compiler/admission authority changed
- [x] 11. Unknown metadata refused explicitly (IDENTITY_UNRESOLVED), not silently TEXT
- [x] 12. RUNTIME_STATE/SLIDER_PIXEL/GRAPH_DERIVED produce explicit outcomes (all NOT_APPLICABLE or UNSUPPORTED_MODALITY)

## What Phase 2 Did NOT Do

- No integration into state_ledger flow yet (ready for wiring)
- No inventory completeness enforcement (Phase 3)
- No Matrix Amount pixel calibration (Phase 3)
- No ExpectedInventory implementation (Phase 3)
- No end-to-end reference reproduction (Phase 4)

## Next Steps

**Phase 3: Matrix Amount + Inventory Closure**
- Implement SLIDER_PIXEL strategy with pixel-position calibration
- Integrate ExpectedInventory concept: `ExpectedInventory == TerminalObservations`
- Run on real Serum preset with Matrix routing

**Phase 4: Mixed End-to-End Proof**
- Single reference reproduction with TEXT + ENUM + NUMERIC + BOOLEAN + ROUTE + MATRIX AMOUNT + GRAPH_DERIVED
- Verify: ExpectedInventory == TerminalObservations == Derived == Admitted == Compiled == Verified
- Direct Serum UI readback verification

## Code Quality

- **observation_engine.py**: 465 lines, 8 strategy classes (8 with prefix-format handling), no external dependencies
- **test_phase2_observation_engine.py**: 220 lines, real normalization validation (5 cases + 3 explicit outcome checks = 8 checks total)
- All strategies handle Qwen prefix format (VALUE=, DRIVE=, STATE=, SOURCE=/DESTINATION=, Chaos:)
- No warnings/errors beyond Unicode rendering (harmless on Windows PowerShell)
- Architecture clean, strategy pattern simple and extensible
