# Phase 4.2.1: 5 Real Closure Gates

**Honest assessment:** 5 gates, not 4. Implementation + acceptance + formal closure.

---

## What's Already Complete

```
✅ V3 geometry concept (structural rail architecture)
✅ V3 extraction layer (production-wired)
✅ VerifiedStateAdapter (two-phase behavior proven)
✅ Representation hardening (amount_unit/domain/source)
✅ Blind-method discovery (audit provenance pattern)
```

**Public state:** `phase-3-5-matrix-calibration` at commit `161afca` (before v3 work)
**Local state:** All v3/integration code committed locally; not yet pushed

---

## 5 Remaining Gates

### GATE 1: E2E Integration Bundle (Implementation)
**Combine into ONE coherent step:**

```
ExpectedInventory
  ├─ Define 4 route identities for HEEGN1Xl5o4 step 3
  │
+
Reference-Rail Auto-Selection
  ├─ Detect reference rows (empty Matrix rows)
  ├─ Validate convergence
  ├─ Return structural rail + confidence
  │
+
Corrected Reference State
  ├─ Regenerate with 4 v3-detected amounts
  ├─ Explicit provenance (amount_source=SLIDER_PIXEL_CALIBRATION)
  │
+
VerifiedStateAdapter Wiring
  ├─ add_matrix_route_observation() consumes v3 output
  ├─ Creates unverified routes (agreement=False)
```

**Acceptance:**
```
4 expected routes
= 4 extracted via v3
= 4 route identities in VerifiedReferenceState
0 manually injected amounts
```

**If this fails:** Local integration issue only. Detector is sound.

---

### GATE 2: Full Regression Suite (Validation)
**Run everything together:**

```
Phase 3 existing tests
+
Phase 4 existing tests  
+
v3 detector tests (17 passing)
+
VerifiedStateAdapter integration tests (3 passing)
+
E2E reference pipeline test (1 passing)
```

**Acceptance:**
```
0 failures
0 skips caused by v3 work
all pass
```

**If this fails:** Identify regression, fix only that issue. No architecture redesign.

---

### GATE 3: Real Production Blind Gate (Decisive Test)
**The actual Phase 4.2.1 closure test:**

```
actual HEEGN1Xl5o4 image
  ↓
SliderEvidenceExtractorV3 (production)
  ├─ auto-detect reference rows
  ├─ extract 4 routes
  ├─ v3 geometry
  ├─ GenericSliderCalibration
  │
  ↓
VerifiedStateBuilder (production)
  ├─ add_matrix_route_observation × 4
  ├─ routes created with agreement=False
  │
  ↓
Independent Claude manifest (blind)
  ├─ Claude verifies 4 amounts independently
  ├─ Sets agreement=True for all
  │
  ↓
Hardened completeness gate
  ├─ unresolved_required == 0
  ├─ verification_conflicts == 0
  ├─ claude_only_items == 0
  ├─ required_not_visible == 0
  ├─ audit_provenance valid
  ├─ all routes agreement == True
  │
  ↓
Result
```

**Acceptance:**
```
4/4 routes extracted
amount diff ≤ 5 pp (all routes)
no Claude-only items
no missing required
valid audit provenance
gate = PASS
```

**If this fails:** Specific issue identified. Fix only that issue.
- If geometry: tune v3 detector
- If representation: check amount_unit/domain/source
- If audit: fix provenance tracking
- If gate logic: update completeness conditions

**Do NOT redesign architecture if failure is in specific layer.**

---

### GATE 4: Generalization Check (Required Acceptance)
**Prove universality (minimum viable check):**

```
Select one additional Matrix screenshot/episode
(different timestamp, different routes, same Serum 2.0.21)

Run through v3 detector only:
  ├─ structural-rail auto-detection
  ├─ handle detection × N routes
  ├─ canonical amount conversion
```

**Acceptance:**
```
rail detected (independent of which rows are empty)
handles detected consistently
amounts in canonical [-100, +100] %
no special cases needed
```

**If this passes:** Generalization validated. Proceed to closure.

**If this fails:** Issue is detector-specific, not adapter-specific.
- Rail detection logic issue → fix auto-selection algorithm
- Handle detection issue → fix v3 handle-detection logic
- Amount conversion issue → check GenericSliderCalibration

**Do NOT redesign the entire system. Fix the specific detector issue.**

---

### GATE 5: Formal Closure (Decision)
**Only after all 4 gates pass:**

```
Phase 4.2.1: Slider Geometry Solution
  ✅ E2E integration bundle complete
  ✅ Full regression suite (0 failures)
  ✅ Real production blind gate (PASS)
  ✅ Generalization validated
  → CLOSED
```

**Mark:**
- [ ] GATE 1: E2E integration bundle
- [ ] GATE 2: Full regression suite  
- [ ] GATE 3: Real production blind gate
- [ ] GATE 4: Generalization check
- [ ] GATE 5: Formal closure

---

## Critical Mindset

**Do NOT:**
- Redesign v3 unless gate 3 or 4 specifically fails on detection
- Create more "helper" tests unless a gate specifically fails
- Refactor Phase 3-4 code unless gate 2 shows regression
- Build Phase 4.3 until gate 5 is marked complete

**DO:**
- Execute each gate in order
- When a gate fails, identify the specific layer that failed
- Fix only that layer; do not redesign the entire architecture
- Once all 5 gates pass, move forward with confidence

---

## Current Status

```
COMPLETE:
  ✅ v3 concept + extraction layer
  ✅ VerifiedStateAdapter integration
  ✅ E2E pipeline test
  
PENDING (5 gates):
  [ ] 1. E2E integration bundle (ExpectedInventory + reference + state)
  [ ] 2. Full regression suite (Phase 3-4 + v3 + adapter tests)
  [ ] 3. Real production blind gate (decisive closure test)
  [ ] 4. One generalization check (second episode)
  [ ] 5. Formal closure decision

ESTIMATED:
  Gate 1: ~1 hour (bundle integration work)
  Gate 2: ~30 min (run suite, fix regressions if any)
  Gate 3: ~30 min (production path test)
  Gate 4: ~30 min (second episode)
  Gate 5: ~5 min (mark closed)
  ─────
  Total: ~2.5 hours
```

---

## Public vs. Local

**Public branch:** `phase-3-5-matrix-calibration` at `161afca`
- Before v3 work
- No visibility of local v3/integration commits

**Local:** All v3/adapter/integration work committed
- Ready for gates 1-5
- Gate results will clarify what needs pushes upstream

**Do not push to public until gate 5 passes.**
