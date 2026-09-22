# Phase 4.2.1 Integration Checklist

## Ordered Implementation Path

The following sequence must be completed in order. Each step depends on prior steps.

---

## 1. VerifiedStateAdapter Integration

**Goal:** Wire `SliderEvidenceExtractorV3` into real verified-state builder.

**Current state:**
- `SliderEvidenceExtractorV3` exists (production-wired, tested)
- `phase4_2_verified_state_adapter.py` exists (stub)
- `example_phase4_2_integration.py` shows how they should connect (but is example-only)

**What to implement:**
```
VerifiedStateBuilder (new or extended class)
  ├─ add_slider_observation(
  │    ExtractionRequest,
  │    SliderEvidenceExtractorV3
  │  )
  │    ├─ Call extractor.extract()
  │    ├─ Convert ExtractionResult → CalibrationObservation
  │    ├─ Create VerifiedMatrixRoute with explicit unit/domain/source
  │    └─ Add to VerifiedReferenceState
  │
  └─ pass_completeness_gate()
       ├─ Check all routes have agreement=True
       ├─ Check audit_provenance (direct visual inspection)
       └─ Return boolean (gates Phase 4.2.1)
```

**Test:** `test_verified_state_adapter_with_v3_extractor.py`
- Create VerifiedStateBuilder
- Add four slider observations via v3 extractor
- Verify VerifiedMatrixRoute has correct fields
- Verify pass_completeness_gate() returns True

**Files to modify:**
- `phase4_2_verified_state_adapter.py` — Add VerifiedStateBuilder class

**Files to create:**
- `test_verified_state_adapter_with_v3_extractor.py` — Integration test

**Acceptance:** Test passes; VerifiedStateBuilder can consume v3-extracted observations.

---

## 2. ExpectedInventory Matrix Routes

**Goal:** Make ExpectedInventory aware of the four route identities for this episode.

**Current state:**
- ExpectedInventory exists (Phase 3.2)
- Matrix routes schema exists
- No test case for four-route Matrix observation

**What to implement:**
```
ExpectedInventory for HEEGN1Xl5o4 step 3
  ├─ matrix.route[LFO 1 → A Fine]
  ├─ matrix.route[LFO 1 → B Fine]
  ├─ matrix.route[Env 3 → Noise Level]
  └─ matrix.route[Env 2 → Filter 1 Freq]

Schema (canonical representation):
  ├─ source (LFO 1, Env 3, Env 2)
  ├─ destination (Osc A Fine, Osc B Fine, Noise Level, Filter 1 Freq)
  ├─ modality (SLIDER_MODULATION)
  └─ expected_unit (%)
```

**Test:** `test_expected_inventory_matrix_routes_heegn1xl5o4.py`
- Create ExpectedInventory with four route identities
- Verify VerifiedStateBuilder reconciles expectations
- Verify no "unresolved_required" or "claude_only_items" after adding all four

**Files to create:**
- `expected_inventory_heegn1xl5o4_step3.py` — Episode-specific inventory
- `test_expected_inventory_matrix_routes_heegn1xl5o4.py` — Test integration

**Acceptance:** Inventory aware of four routes; no reconciliation errors.

---

## 3. Reference Row Auto-Selection

**Goal:** Replace hardcoded `y=280` with deterministic structural-selection algorithm.

**Current state:**
- `slider_geometry_detector_v3.py` — Uses hardcoded reference_row_ys
- Strategy documented in REFERENCE_ROW_SELECTION_STRATEGY.md
- No auto-detection implementation

**What to implement:**
```
def auto_detect_reference_rows(
    arr: np.ndarray,
    amount_column_x_range: Tuple[int, int],
    matrix_grid_row_ys: Optional[List[int]] = None,
) -> Tuple[StructuralRail, ReferenceRailCandidate]:
    """
    1. Find candidate reference rows (empty, high plateau coverage)
    2. Validate convergence (multiple rows agree on rail)
    3. Return rail + metadata (confidence, source_rows, selection_reason)
    """

Result: ReferenceRailCandidate(
    left_pixel=198,
    right_pixel=323,
    confidence=1.0,  # Two rows converged
    source_rows=[280, 300],
    selection_reason="Converged from 2 empty rows",
    convergence_error=0.0,
    plateau_coverage=0.90,
)
```

**Test:** `test_reference_row_auto_detection.py`
- Call auto_detect_reference_rows() on HEEGN1Xl5o4 image
- Verify it independently selects rows [280, 300]
- Verify convergence on [198, 323]
- Verify confidence and provenance fields

**Files to modify:**
- `slider_geometry_detector_v3.py` — Add auto-detection function

**Files to create:**
- `reference_rail_candidate.py` — ReferenceRailCandidate dataclass
- `test_reference_row_auto_detection.py` — Auto-detection tests

**Acceptance:** Auto-detection produces same rail as manual selection; provenance clear.

**Critical boundary:** Row selection is episode-specific evidence (y=280). Rail inference is universal principle. Keep them separate.

---

## 4. Regenerate Corrected Reference State

**Goal:** Commit final amounts with explicit v3 provenance.

**Current state:**
- `reference_state_corrected_heegn1xl5o4.py` exists (placeholder)
- Final amounts known: +2.4%, +2.4%, +34.4%, +71.2%
- Provenance must be explicit: amount_source=SLIDER_PIXEL_CALIBRATION

**What to implement:**
```python
# reference_state_corrected_heegn1xl5o4.py

state = VerifiedReferenceState(
    episode_id="HEEGN1Xl5o4",
    source_description="step3_04m35s_matrix_mod_routes.jpg",
    serum_version="2.0.21",
)

# Four routes with explicit amounts and provenance
routes = [
    VerifiedMatrixRoute(
        route_id="LFO 1 → A Fine",
        source="LFO 1",
        destination="Osc A Fine",
        amount=2.4,
        amount_unit="%",
        amount_domain=(-100.0, 100.0),
        amount_source="SLIDER_PIXEL_CALIBRATION",
    ),
    # ... three more routes
]

for route in routes:
    state.add_verified_route(route)

# Audit provenance (direct visual inspection)
state.audit_provenance = BlindAuditProvenance(
    observer="Claude",
    audit_mode=AuditMode.DIRECT_VISUAL_INSPECTION,
    system_manifest_hidden=True,
    model_checkpoint="claude-haiku-4-5-20251001",
)
```

**Test:** `test_reference_state_heegn1xl5o4.py`
- Load corrected reference state
- Verify four routes present
- Verify amounts match v3 calibration
- Verify amount_source and unit explicitly declared
- Verify pass_completeness_gate() returns True

**Files to modify:**
- `reference_state_corrected_heegn1xl5o4.py` — Replace placeholder with final state

**Acceptance:** Reference state generated; all fields explicit; gate passes.

---

## 5. Full Phase 3-4 Test Suite

**Goal:** Run complete test suite; ensure no regressions.

**Current state:**
- Phase 3 tests: existing suite
- Phase 4.1 tests: existing suite
- Phase 4.2 tests: new v3 tests (6 tests, all passing)
- Phase 4.2.1 tests: new integration tests (need to add)

**What to run:**
```
pytest serum2/producer/test_phase3_*.py        # Phase 3 baseline
pytest serum2/producer/test_phase4_*.py        # Phase 4 existing
pytest serum2/producer/test_detector_v3.py     # v3 unit
pytest serum2/producer/test_slider_calibration_pipeline.py
pytest serum2/producer/test_slider_evidence_extractor_v3.py
pytest serum2/producer/test_verified_state_adapter_with_v3_extractor.py
pytest serum2/producer/test_reference_row_auto_detection.py
pytest serum2/producer/test_reference_state_heegn1xl5o4.py

# Should all pass with 0 failures
```

**Acceptance:** All tests pass; 0 failures.

---

## 6. Blind Audit Through Production Path

**Goal:** Run end-to-end gate using real production pipeline (not example).

**Flow:**
```
HEEGN1Xl5o4 step3_04m35s_matrix_mod_routes.jpg
    ↓
VerifiedStateBuilder
    ├─ auto_detect_reference_rows() → ReferenceRailCandidate
    ├─ SliderEvidenceExtractorV3.extract() × 4 → ExtractionResult
    ├─ Create VerifiedMatrixRoute × 4
    └─ VerifiedReferenceState
    ↓
Blind audit gate
    ├─ Compare system amounts vs blind amounts
    ├─ Verify all within ±5pp
    ├─ Check all completeness conditions
    └─ Gate passes? → Phase 4.2.1 ready
```

**Test:** `test_blind_audit_production_path.py`
- Load reference state from real pipeline (not example)
- Compare amounts against blind auditor's manifest
- Verify gate passes
- Verify no manually-injected values

**Acceptance:** Gate passes through production path; no manual overrides.

---

## 7. Second Episode Validation

**Goal:** Prove structural-rail approach generalizes beyond HEEGN1Xl5o4.

**Current state:**
- Only tested on HEEGN1Xl5o4 step 3
- Unknown: Does it work on other episodes? Other Matrix layouts?

**What to do:**
1. Select second reference episode (Matrix modulation from different timestamp)
2. Run auto_detect_reference_rows() → verify convergence
3. Extract four routes (or however many are populated)
4. Compare against blind auditor's measurements
5. Verify amounts within ±5pp

**Example candidates:**
- HEEGN1Xl5o4 step 5 (if Matrix routes shown)
- Different episode entirely (if available)

**Test:** `test_v3_generalization_second_episode.py`

**Acceptance:** Second episode produces similar geometry; no special cases needed.

---

## 8. Phase 4.2.1 Closure

**Goal:** All conditions met; phase ready to close.

**Closure conditions:**
- [x] v3 detector validated
- [x] Extraction-layer integration complete
- [ ] VerifiedStateAdapter integration complete
- [ ] ExpectedInventory matrix routes defined
- [ ] Reference row auto-selection formalized
- [ ] Corrected reference state regenerated
- [ ] Full test suite passing
- [ ] Blind audit gate passes (production path)
- [ ] Generalization validated (second episode)

**When all checked:** Phase 4.2.1 = CLOSED

**Next phase:** Phase 4.3 (Authorized Preset Compiler)

---

## Commits to Make

In order:

1. `VerifiedStateAdapter integration + tests`
2. `ExpectedInventory matrix routes for HEEGN1Xl5o4`
3. `Reference row auto-detection implementation`
4. `Regenerated corrected reference state`
5. `All Phase 3-4 tests passing`
6. `Production blind audit gate`
7. `Second episode validation`
8. `Phase 4.2.1 closure commit`

Each commit should have:
- Clear commit message naming what's integrated
- Test results (all passing)
- Verification that gate conditions advance

---

## Key Principles (Do Not Violate)

1. **No parallel paths** — Only one production path; no authoritative "example" extractor
2. **No hardcoded y-coordinates** — Must come from auto-detection algorithm with provenance
3. **Explicit representation** — Every amount must declare unit/domain/source
4. **Universal vs. episode-specific** — Structural-rail inference is universal; reference-row selection is evidence-backed but not a rule
5. **No manual injection** — Blind audit gate must pass from image alone; no pre-filled amounts

---

**Current status:** Ready to start integration task #1 (VerifiedStateAdapter).
