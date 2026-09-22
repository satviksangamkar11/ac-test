# Phase 3: Frozen Epoch Manifest

**Locked at:** 2026-09-22 (commit 9ab32e4)

## Authoritative Versions

```
Serum Version:           2.0.21
Serum Schema Snapshot:   serum_2_0_21_schema_snapshot.json
Ableton Live Version:    12
UI Atlas Version:        v0.2 (frozen for Phase 3)
Binding Table Epoch:     phase-3-canonical
ObservationEngine:       v0.3 (commit 9ab32e4, 465 lines, 8 strategies)
```

## Locked Artifacts

```
Gate-A Benchmark:        five_roi_test_results.json
                         (5 tests, Qwen 2.5-VL-3B-Instruct, 4-bit BNF quantized)

Gate-B Audit:            gate_b_manifest.json
                         (5 source images, ROI bboxes, SHA256 pairs)

Gate-A Provenance:       
  - Test 1: Unison 7           → LIVE_VERIFIED (step1_01m09s crop)
  - Test 2: Env2→Filter1 Freq  → LIVE_VERIFIED (repaired crop)
  - Test 3: Chaos: Lorenz      → LIVE_VERIFIED (step2_02m08s)
  - Test 4: Drive 1.9          → MODEL_OUTPUT ONLY (source insufficient)
  - Test 5: Legato OFF         → LIVE_VERIFIED (step1_01m09s crop)
```

## ObservationEngine Behavior (Frozen)

**8 Strategies (all generic, no parameter-specific hardcoding):**

```
TEXT                → literal transcription
ENUM                → canonical vocabulary resolution
NUMERIC             → syntactic parsing + unit (semantic validation deferred to ledger)
ENABLE_STATE        → checkbox/toggle visual classification
ROUTE_TEXT          → modulation source/dest (raw preserved for ledger)
GRAPH_DERIVED       → non-independent visual evidence (outcome=NOT_APPLICABLE)
RUNTIME_STATE       → transient UI state (outcome=NOT_APPLICABLE)
SLIDER_PIXEL        → placeholder; Phase 3 implements generic calibration
```

**Prefix Format Handling:**
```
VALUE=7           → extract 7
DRIVE=1.9         → extract 1.9
STATE=OFF         → extract OFF
Chaos: Lorenz     → extract Lorenz
SOURCE=...\nDEST= → preserve raw for ledger parsing
```

**Outcome Types (Explicit):**
```
OUTCOME_CANDIDATE              → ready for state_ledger.derive()
OUTCOME_NOT_APPLICABLE         → runtime/transient; cannot be preset observation
OUTCOME_UNSUPPORTED_MODALITY   → modality exists; not yet implemented (SLIDER_PIXEL)
OUTCOME_IDENTITY_UNRESOLVED    → metadata insufficient; refuses silent defaults
```

## State Ledger Authority (Unchanged)

```
Validation authority:  state_ledger._coerce()
- Unit conversion
- Range clamping
- Semantic validation
- Route parsing (SOURCE/DESTINATION extraction)

Do NOT duplicate this logic in ObservationEngine.
```

## Phase 3 Contract

**No changes to these components:**
```
serum-mcp (direct call, not bridge)
state_ledger validation authority
admission system
AuthorizedPresetCompiler
Reference Reproduction hardening (reused from existing branch)
```

**New Phase 3 implementations:**
```
ExpectedInventory            (core missing piece)
Terminal observation outcomes (explicit classification)
Completeness invariant       (ExpectedIDs == TerminalIDs)
Matrix Amount calibration    (generic slider geometry)
ObservationEngine integration (Stage-A → Inventory → Engine → Ledger)
```

## Stop Condition for 3.1

This manifest locked. Commit immutability verified. No inference, no schema changes, no version bumps until Phase 3 exit gate.

**Next:** 3.2 — ExpectedInventory implementation
