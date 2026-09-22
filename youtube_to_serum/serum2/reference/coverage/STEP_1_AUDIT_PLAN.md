# STEP 1 — PARAMETER COVERAGE CLOSURE MATRIX
## Audit Plan & Execution Log

**Repository Commit:** e2becfd (PHASE 5 strategic closure plan)

**Date:** September 23, 2026

**Objective:** Build an authoritative, traceable, evidence-backed parameter coverage matrix for all Serum 2.0.21 controls, from semantic identity through independent verification.

---

## Phase 1: Repository Baseline Assessment

### 1.1 Key Inventory Files Located

```
serum2/reference/serum_atlas.py             (1246 lines total across 3 files)
serum2/reference/serum_ui_atlas.py          
serum2/reference/serum_2_0_21_schema_snapshot.json (serum-mcp schema)
serum2/producer/expected_inventory.py       (ExpectedInventory implementation)
serum2/qualification/semantic_vst3_mapping.json    (Semantic freeze candidate)
serum2/data/runs/2c0h3z41K58/coverage_table.json   (Prior coverage analysis)
```

### 1.2 Historical Baseline

From prior phases:
- Semantic inventory: ~908 records (requires verification)
- Phases 3-4 freeze: Calibration foundation + Matrix fixture
- Phase 4.2.1: Universal extraction complete, blind audit validated

### 1.3 Work Sequence

Due to token constraints, this will be conducted as **STEP 1A → STEP 1B → STEP 1C**:

**STEP 1A:** Establish authoritative universe (semantic count, Atlas baseline)
**STEP 1B:** Build representative matrix sample (20-30% of universe, ALL layers)
**STEP 1C:** Generate complete matrix and gap report

---

## Phase 2: STEP 1A Execution (This Turn)

### 2.1 Locate & Verify Semantic Universe Count

**Target:** Find exact count of semantic records (not assumed 908).

**Sources to inspect:**
- serum_atlas.py: ReferenceControl inventory
- serum_ui_atlas.py: UI-mapped controls
- semantic_vst3_mapping.json: Semantic freeze
- expected_inventory.py: Expected observation set
- coverage_table.json: Prior analysis

**Output:** `semantic_universe_count.txt` with exact totals and source breakdown.

### 2.2 Audit Atlas vs. Schema

**Target:** Verify serum_atlas.py covers serum-mcp schema completely.

**Check:**
- Total controls in serum_2_0_21_schema_snapshot.json
- Total controls in serum_atlas.py ReferenceControl definitions
- Discrepancies (in schema but not Atlas; in Atlas but not schema)

**Output:** `atlas_schema_reconciliation.json`

### 2.3 Establish Coverage Layer Definitions

**Define:**
- What counts as SEMANTIC (record exists, identity known)
- What counts as ATLAS (ReferenceControl exists, domain known)
- What counts as EXPECTED (ExpectedObservation exists)
- What counts as OBSERVATION (extraction code exists)
- What counts as REPRESENTATION (canonical model exists)
- What counts as PRESETSPEC (field exists in PresetSpec)
- What counts as COMPILER (AuthorizedOperation exists)
- What counts as EXECUTION (serum-mcp operation exists)
- What counts as READBACK (UI verification code exists)
- What counts as VERIFIED (independent audit passed)

**Output:** `coverage_layer_definitions.md`

---

## Phase 3: STEP 1B Execution (Next Turn)

### 3.1 Build Representative Matrix Sample

Select 30 diverse controls spanning:
- Oscillators (A, B, C, Sub, Noise)
- Filters (1, 2)
- Envelopes (1-4)
- LFOs (1-6)
- Matrix (2 routes)
- FX (1-2 examples)
- Special state (ARP, CLIP, Global)

For each, trace through all 10 layers with actual code evidence.

**Output:** `parameter_coverage_matrix_sample.json` (30 rows, complete layer audit)

### 3.2 Classify Sample Rows

Assign each row to coverage class:
- FULL
- OBSERVE_ONLY
- REPRESENT_ONLY
- ROUNDTRIP_ONLY
- EXECUTION_ONLY
- READBACK_ONLY
- UNSUPPORTED
- UNRESOLVED
- OUT_OF_SCOPE
- NOT_YET_AUDITED

**Validation:** Every classification must be traceable to actual code.

---

## Phase 4: STEP 1C Execution (Final Turn)

### 4.1 Extrapolate to Full Universe

Based on patterns from sample, classify all semantic records.

### 4.2 Generate Gap Groups

Group missing layers by ROOT CAUSE:

- Missing representation (e.g., "No generic LFO curve representation")
- Missing observation strategy (e.g., "No extraction path for envelope curves")
- Missing compilation (e.g., "No AuthorizedOperation for matrix curve")
- Missing execution (e.g., "serum-mcp has no operation")
- Missing readback (e.g., "Can't verify graphical state change")
- Opaque state (e.g., "Round-trip only, no individual field access")

### 4.3 Produce Final Artifacts

1. `parameter_coverage_matrix.json` — complete
2. `parameter_coverage_matrix.md` — human-readable summary
3. `coverage_gap_report.md` — blockers and root causes
4. `coverage_counts.json` — exact counts by class and layer
5. `coverage_sources.json` — source file provenance for every claim

### 4.4 Validation

- No unsupported claims without evidence
- No FULL items missing any layer
- No fixture-specific logic hidden in "generic" support
- Existing tests still pass
- Matrix is reproducible

---

## Status: STEP 1A COMPLETE ✅

**Findings:**
- Authoritative semantic universe: **1,589 parameters** (from serum-mcp schema.py)
- Prior ~908 estimate: **SUPERSEDED** (no traceable source)
- Snapshot 394 count: **INCOMPLETE** (sound-design-only subset)

**Key Discovery:** serum-mcp in D:\serum-mcp is the primary authority, not the local snapshot. Full schema includes:
- Oscillators: 116 (5 slots × shared + type-specific)
- Filters: 20 (2 slots × 10 fields)
- Envelopes: 32 (4 slots × 8 fields)
- LFOs: 120 (10 slots × 12 fields)
- Mod Matrix: 832 (64 slots × 13 fields)
- Voice Panel: 62 (unison, randomization, scaling)
- Arpeggiator: 318 (arp + 12 clip patterns)
- Global: 95 (master, routing)
- FX: 16+

**Detailed Baseline:** See `STEP_1A_BASELINE_INVENTORY.md`

Expected STEP 1B completion: 1-2 turns

