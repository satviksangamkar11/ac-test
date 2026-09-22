# STEP 1: E2E Integration Bundle — Implementation Status

**Deadline:** Complete before proceeding to STEP 2 (Full Test Suite)

---

## Tasks Completed

✅ **Task D — Corrected Reference State**
- Regenerated `reference_state_corrected_heegn1xl5o4.py` with v3 detector amounts
- Replaced hand-computed values (6.7, -12.0, -33.3, +1.3) with v3-detected (+2.4, +2.4, +34.4, +71.2)
- Added geometry_provenance and reference_row tracking
- All amounts from production v3 detector only (no manual injection)
- Committed: `fef799c`

---

## Tasks Remaining (CRITICAL PATH)

### Task A — ExpectedInventory Integration (30 min)
**What:** Add 4 Matrix route identities to expected set for HEEGN1Xl5o4

**File:** `expected_inventory.py` (or new `expected_inventory_heegn1xl5o4_step3.py`)

**Implementation:**
```python
# Four expected Matrix routes
expected_routes = {
    'LFO 1 → A Fine': ExpectedObservation(
        canonical_id='matrix.amount',
        row_detail='LFO 1 → A Fine',
        observation_kind='MATRIX_AMOUNT',
        strategy='slider_pixel_calibration_v3',
        visibility_requirement='VISIBLE',
        evidence_requirement='REQUIRED',
    ),
    # ... repeat for other 3 routes
}
```

**Acceptance:**
- Four route identities defined
- Each has distinct row_detail
- observation_kind='MATRIX_AMOUNT'
- strategy points to v3 calibration

---

### Task B — Reference-Rail Auto-Selection (1 hour)
**What:** Replace hardcoded `reference_row_y = 280` with deterministic algorithm

**File:** Modify `slider_geometry_detector_v3.py` or create wrapper

**Implementation approach:**
```python
def auto_detect_structural_rail(
    arr: np.ndarray,
    amount_column_x_range: Tuple[int, int] = (198, 324),
    matrix_row_candidates: Optional[List[int]] = None,
) -> Tuple[StructuralRail, ReferenceRailSelection]:
    """
    Deterministic structural-rail selection.
    
    1. Scan matrix_row_candidates (or [250-300] range)
    2. Find rows with high plateau coverage (≥70% grey pixels)
    3. Validate convergence (multiple rows detect same rail)
    4. Return structural rail + selection provenance
    """
    
    # Must return:
    #   StructuralRail(left=198, right=323, ...)
    #   ReferenceRailSelection(
    #       confidence=HIGH,
    #       source_rows=[280],
    #       selection_reason="...",
    #       convergence_error=0px
    #   )
```

**Acceptance:**
- For HEEGN1Xl5o4: algorithm independently converges on [198-323]
- No hardcoded y-coordinates in detector
- Returns explicit provenance/confidence
- Works when called without reference_row_ys parameter

---

### Task C — Real Production Extraction Path (30 min)
**What:** Verify actual wiring (don't create parallel example)

**Files involved:**
- `slider_evidence_extractor_v3.py` (extract)
- `phase4_2_verified_state_adapter.py` (add_matrix_route_observation)
- `test_e2e_reference_pipeline_heegn1xl5o4.py` (ALREADY COMPLETE)

**Verification:**
```
ExtractionRequest
  → SliderEvidenceExtractorV3.extract()
  → ExtractionResult
  → VerifiedStateBuilder.add_matrix_route_observation()
  → VerifiedMatrixRoute (agreement=False initially)
```

**Acceptance:**
- No bypass of SliderEvidenceExtractorV3
- No hardcoded amounts
- agreement=False until audit

---

### Task E — E2E Integration Test (30 min)
**What:** Single focused test for REAL production path

**File:** `test_phase4_2_1_e2e_heegn1xl5o4_production.py`

**Must verify:**
1. Load actual image
2. Create 4 extraction requests
3. Auto-detect structural rail (no hardcoded y=280)
4. Extract via SliderEvidenceExtractorV3
5. Calibrate via GenericSliderCalibration
6. Add via VerifiedStateBuilder.add_matrix_route_observation()
7. All 4 routes created with agreement=False
8. ExpectedInventory accounts for all 4
9. Gate blocked before audit
10. No hardcoded amounts anywhere

**Acceptance:**
- Test passes
- All 4 routes extracted
- Amounts canonical [-100,+100]%
- No bypasses detected

---

### Task F — Regression Protection (15 min)
**What:** Minimal tests to protect key invariants

**Tests needed:**
```python
test_reference_rail_not_hardcoded()
  # Verify y=280 comes from auto-detection, not constant

test_rail_geometry_is_structural_not_fill()
  # Verify different rows use same rail

test_no_amount_hardcoding_bypass()
  # Verify all amounts from v3 extraction

test_route_identities_preserved()
  # Verify row_detail preserved exactly
```

**Acceptance:**
- 4 tests added
- All pass
- No regressions in Phase 3-4 existing tests

---

## Final Report (After All Tasks Complete)

**Must include:**
1. ✅ Files changed (reference_state + new tests)
2. ✅ Production path now used (no parallel examples)
3. ✅ ExpectedInventory status (4 routes defined)
4. ✅ Reference-rail selection algorithm (no hardcoding)
5. ✅ Four extracted routes + amounts (+2.4, +2.4, +34.4, +71.2)
6. ✅ No hardcoded amounts (all from v3)
7. ✅ Test results (all passing)
8. ✅ Any remaining blockers (none = STEP 1 COMPLETE)

---

## Current Status

```
✅ Task D (reference state regenerated)
⏳ Task A (ExpectedInventory) — ~30 min
⏳ Task B (reference-rail auto-selection) — ~1 hour
⏳ Task C (production path verification) — ~30 min (mostly review)
⏳ Task E (E2E integration test) — ~30 min
⏳ Task F (regression protection) — ~15 min
```

**Estimated total remaining: 2.5 hours**

---

## Gate Passes When

1. All 4 routes expected in ExpectedInventory
2. Reference-rail auto-detection working (no y=280 hardcoding)
3. E2E test passes (all 4 routes extracted, amounts canonical)
4. No regression in existing tests
5. All 4 amounts match v3 detector (+2.4, +2.4, +34.4, +71.2)

**THEN: Proceed to STEP 2 (Full Test Suite)**

---

## Do NOT

❌ Create another example/parallel extraction path
❌ Manually inject amount values
❌ Hardcode y=280 in production detector
❌ Weaken the completeness gate
❌ Skip ExpectedInventory integration
❌ Proceed to STEP 2 before all 6 tasks complete
