# Phase 4.2.1 Closure Roadmap

**Compressed execution:** 4 steps remaining.

## Current State

```
✅ v3 detector (validated)
✅ SliderEvidenceExtractorV3 (production-wired, 4/4 tests)
✅ VerifiedStateAdapter (integration complete, 2-phase flow)
✅ E2E reference pipeline (HEEGN1Xl5o4 tested, gate passes)
```

## 4 Steps to Closure

### STEP 1: Full Phase 3-4 Test Suite
**Acceptance:** 0 failures

```
ALL existing tests
+
v3 detector unit tests
+
VerifiedStateAdapter integration tests
+
E2E reference pipeline test
```

Target:
- No skips caused by v3 work
- No regressions in Phase 3-4
- Only fix actual issues, no refactoring

### STEP 2: Real Blind E2E Gate (Production Path)
**Acceptance:** Gate passes through actual production pipeline

```
actual HEEGN1Xl5o4 image
  ↓
production extractor (SliderEvidenceExtractorV3)
  ↓
v3 geometry (auto-detect reference rows)
  ↓
GenericSliderCalibration (canonical amounts)
  ↓
VerifiedStateBuilder (add_matrix_route_observation)
  ↓
blind auditor manifest (independent measurement)
  ↓
hardened gate (all ±5pp + provenance + agreement)
```

Required:
- 4/4 routes extracted
- All amounts within ±5pp of blind
- No Claude-only items
- No missing required
- Valid audit provenance
- **Gate = PASS**

### STEP 3: One Second-Episode Generalization Check
**Acceptance:** v3 detector works on different Matrix screenshot

```
second reference episode
  ↓
structural rail detection (auto-detect)
  ↓
handle detection × N routes
  ↓
canonical amount conversion
```

Target:
- PASS → Phase 4.2.1 CLOSED
- FAIL → fix only generalized detector issue (isolated to detector, not adapter)

### STEP 4: Phase 4.2.1 Closure
**Criteria all met:**
- Full suite passes
- Real blind gate passes
- Generalization validated
- No outstanding issues

---

## What NOT to Do

```
❌ more standalone helper modules
❌ more artificial fixture tests
❌ another calibration redesign
❌ rewrite the architecture
❌ validate every Serum section now
❌ build Phase 4.3 before gate closes
```

## Key Constraints

**Reference-row selection is NOT universal:**
- `y=280` is HEEGN1Xl5o4-specific evidence
- Structural-rail inference IS universal principle
- Keep them separate

**No hardcoded amounts:**
- All values from v3 extraction only
- Anti-bypass check: amount_source field

**Two-phase verification:**
- Extraction: agreement=False
- Audit: agreement=True (when confirmed)
- Gate blocks until all agreement=True

**Production path only:**
- One extraction flow
- One adapter integration
- One blind gate
- One closure condition

---

## Timeline

1. **STEP 1** (full suite): 1-2 hours
   - Run all tests
   - Fix regressions only

2. **STEP 2** (blind gate): 30 min
   - One test run through production path
   - Gate either passes or identifies specific issue

3. **STEP 3** (second episode): 30 min
   - One minimal validation
   - Either passes or reveals detector edge case

4. **STEP 4** (closure): 15 min
   - Mark Phase 4.2.1 closed
   - Begin Phase 4.3 (Compiler)

**Total: ~2.5 hours to closure**

---

## Success Criteria

When all 4 steps complete:

```
Phase 4.2.1: Slider Geometry Solution
  ✅ v3 detector (structural rail architecture)
  ✅ Production extraction pipeline (v3 + adapter)
  ✅ VerifiedStateAdapter integration (2-phase flow)
  ✅ Blind audit gate (production path)
  ✅ Full test suite (0 failures)
  ✅ Generalization validated
  ✅ NO regressions in Phase 3-4
  ✅ CLOSED
```

Then: Proceed to Phase 4.3 (Authorized Preset Compiler)

---

## Current Status

- [x] Architecture validated
- [x] Extraction-layer integration
- [x] Adapter integration
- [x] E2E pipeline test
- [ ] Full suite passing
- [ ] Real blind gate
- [ ] Second-episode check
- [ ] Closed
