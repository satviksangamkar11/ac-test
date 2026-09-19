# B1 Freeze and Measurement Protocol

**Date:** 2026-09-19  
**Commit:** `88bd7af` (B1 Canonical Foundation completion)  
**Status:** B1 FROZEN — no further component changes until measurement complete

---

## B1 Success Criterion (NOT "Makes Tutorial Executable")

**CORRECT:**
> Did B1 correctly transform previously unresolvable evidence into canonical, auditable intent wherever the existing reference/evidence/logic actually supports that interpretation, without inventing anything?

**INCORRECT:**
> Did B1 make the tutorial executable? (This conflates Brain reasoning with execution authority.)

---

## Measurement Protocol

### Phase 1: Establish B1 Baseline Measurement (This Turn)

**Input:** Frozen 2c0h3z41K58 artifacts (do NOT re-acquire)
- `serum2/data/runs/2c0h3z41K58/stage_a_observation.json`
- Snapshots, timeline, fusion, 9 ProductionEvents (unchanged)

**Process:** Run exact 9 events through B1 derivation engine only

```
ProductionEvent
    ↓
extract semantic changes (no metadata)
    ↓
for each change:
    ├─ ConceptDerivationEngine.derive(canonical_target)
    ├─ OperationInterpreter.interpret(direction_phrase)
    ├─ ContextExtractor.extract(event_intent)
    ├─ IntentFormationEngine.form_intent(…)
    └─ record: (canonical_target, provenance, confidence, derivation_chain)
```

**Output:** B1 baseline report

```
Event | Control | Before→After | B1 Concept Provenance | B1 Confidence | Status
------|---------|--------------|----------------------|---------------|--------
1     | oscA.warp_mode | OFF→REMAP 2 | MISSING | 0.0 | REFUSED_NO_BRAIN_CONCEPT
2     | env2.decay | 1.00s→1.77s | CONTRACT | 0.95 | B1_READY (downstream: CAPABILITY)
...
```

**Success Metric (B1 Specific):**
- For every B1-resolvable concept: provenance is derivable (not invented)
- For every derivation: audit chain is complete and traceable
- For every operation: interpretation is canonical (no tutorial-specific mapping)
- No target substitution (Decay ≠ Release; warp_mode ≠ unison)

### Phase 2: Audit Newly Resolved Concepts

For every event that moves from **REFUSED_NO_BRAIN_CONCEPT** to **B1_READY**:

```
Event #N: control X
    before: REFUSED_NO_BRAIN_CONCEPT (no concept in Brain)
    after:  B1_READY (concept derivable)
    
    verify:
    ├─ Atlas entry: [canonical_id resolved]
    ├─ Derivation chain:
    │  ├─ contract lookup: [CONTRACT | LEGACY_SEMANTIC | MCP | GENERIC | MISSING]
    │  ├─ semantic target: [found | not found]
    │  └─ provenance: [never invented]
    ├─ Operation interpretation: [direction | value | enum | toggle]
    └─ Resulting intent: [valid | invalid]
    
    RED FLAG: if operation_type == "substitute_different_control"
```

### Phase 3: Integration Test (B1 → Frozen Pipeline)

**Setup:** Wire B1 into existing Producer Brain

```python
# serum2/producer/producer_brain.py (existing)

def _resolve_concept(self, request):
    # OLD PATH: hand-written tables + heuristics
    # NEW PATH: B1 derivation engine
    
    b1_intent = self._b1_engine.form_intent(
        canonical_target=resolve_atlas(request),
        representation=self._b1_engine.derive(…),
        operation=self._operation_interp.interpret(…),
        context=self._context_extractor.extract(…),
        input_request=request,
    )
    
    return b1_intent  # feeds to Capability Resolution (unchanged)
```

**Test:** Run ProductionBrain.execute() on 9 events

```
Stage-A observation
    ↓ (unchanged)
snapshots
    ↓ (unchanged)
timeline
    ↓ (unchanged)
ProductionEvent (9 total)
    ↓
Producer Brain
    ├─ B1 derivation (NEW)
    └─ Capability Resolution (UNCHANGED)
        └─ Admission (UNCHANGED)
```

**Measure:**
- Do all 9 events flow through without crash?
- Does B1 output match standalone B1 test results?
- Does Capability Resolution receive valid UniversalProductionIntent?
- No MCP invocation from B1 layer? (all MCP calls downstream of Admission)

### Phase 4: Regression Test Suite

Run existing tests to verify B1 does not break frozen pipeline:

```bash
pytest serum2/producer/test_ordered_resolution.py -v
pytest serum2/producer/test_evidence_fusion.py -v
pytest serum2/producer/test_timeline.py -v
```

Verify:
- ✅ Frozen refusal taxonomy unchanged (4 codes)
- ✅ Capability Resolution logic untouched
- ✅ Admission gate unchanged
- ✅ MCP routing unchanged

---

## Success Criteria (B1 Frozen)

### Correctness (No Invention)

For every derived concept:
```
✅ Provenance ∈ {CONTRACT, LEGACY_SEMANTIC, MCP, GENERIC}
❌ Provenance ∉ {INVENTED, HAND_CODED, TUTORIAL_SPECIFIC}

✅ Derivation chain is complete and traceable
✅ No target substitution (Decay ≠ Release)
✅ No implicit mappings hidden in operation interpretation
```

### Architecture Compliance

```
✅ B1 feeds UniversalProductionIntent to Capability Resolution
✅ B1 does not invoke MCP or Admission
✅ B1 does not create new authority layer
✅ B1 does not modify frozen pipeline
✅ Admission gate is sole execution authority
✅ Memory remains advisory only
✅ GUI observation remains evidence only
```

### Measurement Clarity

```
9 events baseline (before B1):
├─ EXECUTABLE: 0
├─ REFUSED_NO_CAPABILITY: 3
├─ REFUSED_NO_BRAIN_CONCEPT: 2
└─ NO_SEMANTIC_INTENT: 4

After B1 integration:
├─ [B1 resolved X Brain-blocked → B1_READY → downstream CAPABILITY]
├─ [B1 resolved 0 capability-blocked → no change]
└─ [B1 resolved 0 no-intent → no change]

Explicitly stated: which events moved and why.
```

---

## Measurement Checkpoints

| Checkpoint | Metric | Target | Status |
|-----------|--------|--------|--------|
| B1 Baseline | 9 events through B1 derivation | All complete, no crashes | TBD |
| Concept Audit | Every newly resolved → verify provenance | No invented concepts | TBD |
| Integration | B1 wired into Producer Brain | All tests pass | TBD |
| Regression | Existing test suite | 0 failures | TBD |
| Refusal Count | Compare before/after Brain layer | Clear measurement | TBD |
| Authority Check | No unauthorized execution | B1 → Capability Resolution only | TBD |

---

## DO NOT (While B1 is Frozen)

❌ Add new Brain concepts to make tutorial more executable  
❌ Add hand-written concept tables  
❌ Invent derivation paths for underivable controls  
❌ Bypass Admission gate  
❌ Use GUI as authority  
❌ Use Memory as decision maker  
❌ Begin B2 before B1 measurement complete  
❌ Modify existing frozen pipeline to accommodate B1  

---

## THEN Begin B2

Once B1 measurement is complete and audit passed:

```
B1 VERIFIED
      ↓
B2 SKILL LIBRARY (P3)
├─ Skill schema (purpose, prerequisites, outcomes, provenance)
├─ Extraction from verified episodes
├─ Dependency-aware retrieval
└─ All inside frozen boundaries
```

B2 will be built using the same discipline:
- Verify no invention
- Audit derivation chains
- Measure baseline impact
- No speculative capability expansion

---

## Files for Measurement

**Frozen Artifacts (DO NOT REACQUIRE):**
- `serum2/data/runs/2c0h3z41K58/stage_a_observation.json`
- `serum2/data/runs/2c0h3z41K58/run_timeline.py` (reusable)

**Measurement Scripts:**
- `serum2/producer/test_b1_baseline_2c0h3z41K58.py` (standalone B1 test)
- New: `serum2/producer/test_b1_integration.py` (B1 wired into full pipeline)

**Report Artifacts (to generate):**
- `B1_BASELINE_BEFORE.json` (existing refusal distribution)
- `B1_BASELINE_AFTER.json` (B1-derived refusal distribution)
- `B1_AUDIT_REPORT.md` (concept provenance verification)
- `B1_REGRESSION_RESULTS.txt` (existing test suite passes)

---

## Commit/Tag Protocol

**Current state:** `88bd7af` (B1 implementation complete)

**After measurement:**
- Tag: `vlp1-b1-verified` (if all checkpoints pass)
- Branch: remains `vlp1-producer-brain-b1-canonical`
- Commit: record measurement results as new commit

**Before B2:**
- Update BRAIN_B1_PLAN.md with measurement results
- Record in memory: B1 verified (link to tag)
- Begin B2 PLAN based on actual B1 behavior, not speculation

---

## The Correct Measure of Success

B1 is successful if:

1. **Every concept derivation is auditable** — complete chain from atlas → derivation → intent
2. **No concepts are invented** — MISSING is returned rather than guessing
3. **No targets are substituted** — Decay stays Decay; warp_mode stays warp_mode
4. **Frozen pipeline is unchanged** — B1 feeds intent; Capability/Admission unchanged
5. **Measurement is clear** — before/after counts explicit; per-event audit complete

NOT: "Does it make the tutorial execute?" (That conflates reasoning with authority.)

---

## Next Session Plan

**Goal:** Complete B1 measurement without changing B1 code

1. Extract 2c0h3z41K58 events (already captured)
2. Run through B1 standalone tests
3. Audit each derived concept (provenance verification)
4. Wire B1 into full pipeline
5. Run integration tests
6. Run regression suite
7. Generate B1_BASELINE_BEFORE/AFTER report
8. Tag `vlp1-b1-verified` (if all pass)
9. Begin B2 planning based on actual B1 behavior

No speculation. No hand-coded workarounds. Only measurement and audit.
