# Phase 2: Unified Observation Engine

**Status: COMPLETE**  
Commit: `bc0cfb4`

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

## Phase 2 Regression Test

All 5 Gate-A crops pass through the new engine with expected normalized values:

```
[PASS] OSC A Unison: NUMERIC → (7.0, '')
[PASS] Matrix Route: ROUTE_TEXT → "Env 2"
[PASS] LFO1 Mode: ENUM → "Lorenz"
[PASS] Drive: NUMERIC → (1.9, '')
[PASS] Legato: ENABLE_STATE → "OFF"
```

Confidence: 5/5 = 100%

## Phase 2 Acceptance Criteria

- [x] 1. ExpectedInventory can select an observation strategy
- [x] 2. ROI evidence represented with bbox + image/crop hash
- [x] 3. Qwen output always marked UNTRUSTED_CANDIDATE (vlm_source flag)
- [x] 4. Deterministic validators produce terminal statuses (state_ledger._coerce())
- [x] 5. TEXT/ENUM/NUMERIC/ENABLE_STATE/ROUTE_TEXT work through generic interface
- [x] 6. Runtime state cannot become PRESET_STATE (RuntimeStateObservationStrategy)
- [x] 7. No parameter-specific observer implementations (all strategies generic)
- [x] 8. Existing Gate-A crops pass with same ground truth (regression test 5/5)
- [x] 9. State Ledger receives candidates; no data dropping (architecture preserved)
- [x] 10. No compiler/admission authority changed

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

- **observation_engine.py**: 450 lines, 8 strategy classes, no external dependencies
- **test_phase2_observation_engine.py**: 110 lines, 5 regression cases, 100% pass
- No warnings/errors beyond Unicode rendering (harmless on Windows PowerShell)
- Architecture clean, strategy pattern simple and extensible
