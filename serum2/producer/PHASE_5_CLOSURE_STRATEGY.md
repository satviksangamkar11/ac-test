# PHASE 5 CLOSURE STRATEGY — 7-STEP OPTIMIZED PATH

**Status:** Planning (Pre-execution)

Date: September 23, 2026  
Scope: 908 semantic records → Production 100%  
Architecture: Coverage-ledger-first, group-by-capability-gap, proven Phase 4.2.1 gate

---

## Strategic Overview

**Core Principle:** Build the **coverage ledger first**, then fix by **capability gap grouping**, not parameter-by-parameter.

**Expected Outcome:** Every required Serum state classified, represented, observable, executable, and readback-verified. Explicitly classified unsupported states remain out-of-scope.

---

## 7-Step Closure Plan

### Step 1 — Freeze the Coverage Universe ✅ *START HERE*

**What:** Build one machine-readable ledger from:
- 908 semantic records (from prior phases)
- Atlas schema (controls, enums, defaults)
- Serum 2.0.23 capabilities
- serum-mcp operations

**Deliverable:** `parameter_coverage_matrix.json`

**Columns:**
```
record_id
canonical_id
source (Atlas | Observation | Inference)
observation_status (OBSERVED | NOT_VISIBLE | INSUFFICIENT_EVIDENCE)
representation_status (FULL | ROUNDTRIP_ONLY | OBSERVE_ONLY | MISSING | UNRESOLVED)
execution_status (FULL | PARTIAL | MISSING | OUT_OF_SCOPE)
readback_status (VERIFIED | UNTESTED | UNSUPPORTED)
classification (FULL | OBSERVE_ONLY | ROUNDTRIP_ONLY | OUT_OF_SCOPE | UNRESOLVED)
notes
```

**Closure Condition:** 0 unclassified items. Every record has a terminal classification.

**Why First:** Immediately reveals:
- What's already closed
- What gaps are actually blocking
- Which gaps affect multiple records (group-by opportunity)
- What should remain explicitly OUT_OF_SCOPE

**Output Summary Example:**
```
908 total

FULL                  ~750  ✅
OBSERVE_ONLY           ~80  (observation complete, no roundtrip needed)
ROUNDTRIP_ONLY         ~40  (execute/readback OK, but not visually modifiable)
MISSING REPRESENTATION ~20  (no canonical model exists)
MISSING EXECUTION      ~10  (model exists, no serum-mcp operation)
MISSING READBACK        ~5  (can execute, can't verify the result)
UNRESOLVED              ~3  (uncertain)
OUT_OF_SCOPE            ~0  (explicitly excluded)
```

---

### Step 2 — Close Representation Gaps

**What:** For every "MISSING REPRESENTATION" record, build the minimal canonical model.

**Examples of Groups to Fix Together:**
- All LFO curves (LFO 1-6 curve state)
- All Filter enums (Filter 1-2 type, mode, switches)
- All Oscillator mode-specific state (OSC A/B/C wavetable, phase, unison mode)
- All FX parameters (routing, state, curves)
- Special states (ARP/CLIP, Matrix curves, Global/MPE, Noise/Sub modes)

**Methodology:**
1. Read the Serum manual / serum-mcp schema for each group
2. Define canonical representation (no existing representation = new definition)
3. Add to `canonical_state.yaml`
4. Retest against Phase 3-4 calibration validators

**Closure Condition:** Every in-scope UI state has a canonical representation.

---

### Step 3 — Close Observation

**What:** Make universal V3 extraction + ExpectedInventory capable of producing a terminal outcome for every expected item.

**Reuse:** The proven generic extraction/calibration methodology from Phase 4.2.1.

**For each record:**
- If OBSERVED → mark observation status complete
- If NOT_VISIBLE_IN_FRAME → explicit terminal outcome
- If INSUFFICIENT_EVIDENCE → document what evidence would be needed
- If UNRESOLVABLE → explicit terminal reason

**Closure Condition:** `EXPECTED_SET == TERMINAL_SET`. Zero silent drops.

---

### Step 4 — Close Compilation & Execution

**What:** Generate a coverage report through:
```
PresetSpec → AuthorizedPresetCompiler → admission → serum-mcp
```

For every required/in-scope item:
- Check AuthorizedPresetCompiler has an operation
- Check serum-mcp can execute it
- Check admission rules don't block it
- Fix only actual gaps: `NO_CAPABILITY`, `NO_OPERATION`, or mapping errors

**Closure Condition:** Every required executable item has a verified execution path.

---

### Step 5 — Close Readback

**What:** For every executable control/route, perform **Serum live-UI readback** and verify against intended state.

**Reuse:** Phase 4.2.1 blind verification gate (fresh auditor, system manifest hidden).

**Process:**
1. Write state via serum-mcp
2. Read UI screenshot
3. Compare against expected (±tolerance)
4. Mark VERIFIED or document mismatch

**Closure Condition:** `write → UI readback == expected` for all in-scope items.

---

### Step 6 — Close Special-State Cases

**What:** Finish the difficult non-scalar states (last 5-10% of work, 50% of complexity):
- Matrix curves and auxiliary routing
- LFO curves and point editing
- Envelope graph state and segment parameters
- Oscillator mode-specific state (FM, Spectral, etc.)
- FX curves and complex routing state
- ARP/CLIP state and condition parameters

**Approach:** Use Phase 4.2.1 extraction + readback methodology per item group.

**Closure Condition:** No hidden opaque state remains for anything declared in-scope.

---

### Step 7 — Run Universal Proof Gate

**What:** Execute arbitrary/reference fixtures through the complete chain and generate one final coverage certificate.

**Pipeline:**
```
Reference Fixture → ExpectedInventory → Extraction → Representation
  → AuthorizedPresetCompiler → serum-mcp → Serum Live
  → UI Readback → Blind Verification → Certificate
```

**Output:** `PHASE_5_COVERAGE_CERTIFICATE.json`

```json
{
  "date": "2026-09-23",
  "fixtures_tested": 5,
  "total_items_expected": 908,
  "items_verified": 890,
  "unresolved_required": 0,
  "conflicts": 0,
  "unsupported_required": 0,
  "compiler_gaps": 0,
  "readback_mismatches": 0,
  "status": "PRODUCTION READY"
}
```

**Closure Condition:** 
```
unresolved_required == 0
conflicts == 0
unsupported_required == 0
compiler_gaps == 0
readback_mismatches == 0
```

---

## Key Optimization: Group-by-Capability-Gap

**Do NOT fix one parameter at a time.**

Instead:

```text
908 records
    ↓
COVERAGE LEDGER
    ↓
find actual gaps
    ↓
GROUP gaps by missing capability
    ↓
fix capability once
    ↓
all affected parameters close together
```

**Example: LFO Curves**

❌ BAD:
```
LFO 1 curve representation
LFO 2 curve representation
LFO 3 curve representation
LFO 4 curve representation
LFO 5 curve representation
LFO 6 curve representation
```

✅ GOOD:
```
Generic LFO curve representation (once)
  ↓ applies to LFO 1-6
Generic LFO curve extraction (once)
  ↓ applies to LFO 1-6
Generic LFO curve compiler operation (once)
  ↓ applies to LFO 1-6
Validate all LFO instances (once, together)
```

**Efficiency:** 1 fix → 6 items closed (vs. 6 separate fixes).

---

## Two Definitions of "100%"

### Semantic 100%
```
Every relevant Serum UI state is known,
identified, represented, and observable.
```

### Production 100%
```
Every in-scope state can:
  observe → represent → compile → execute → readback → verify
```

**Phase 5 Gate:** Production 100% (includes semantic 100% as prerequisite).

---

## Out-of-Scope Design

**Do NOT force unsupported Serum state into execution just to reach 100%.**

Instead:

```
If something genuinely cannot be authored through 
the verified backend, classify it explicitly as 
OUT_OF_SCOPE rather than invent it.
```

Example:
- Some FX parameter curves are read-only in Serum → `OBSERVE_ONLY`
- Some Matrix aux state cannot be set via API → `OUT_OF_SCOPE + documented reason`
- Some global MPE state requires live Serum UI → `ROUNDTRIP_ONLY`

This keeps the final certificate honest and prevents false 100% claims.

---

## Implementation Sequence

1. **Step 1 (Coverage Ledger)** — Generate in one pass, no implementation yet
2. **Step 2 (Representation Gaps)** — Canonical models only (no extraction/compilation changes)
3. **Step 3 (Observation)** — Use proven V3 + ExpectedInventory methodology
4. **Step 4 (Compilation)** — Wire serum-mcp operations to canonical models
5. **Step 5 (Readback)** — Live Serum verification (Phase 4.2.1 gate methodology)
6. **Step 6 (Special Cases)** — Remaining complex state (curves, modes, routing)
7. **Step 7 (Proof Gate)** — Final universal verification + certificate

---

## Expected Outcomes

### By Step 1
```
coverage_matrix.json: every record classified
blockers identified
work estimate: based on actual gaps, not speculation
```

### By Step 3
```
every expected item has a terminal observation outcome
zero silent drops
observation complete for all in-scope items
```

### By Step 4
```
every executable item has a compiler operation
serum-mcp execution path exists for all in-scope items
no execution surprises remaining
```

### By Step 5
```
every roundtrip item verified live in Serum
readback matches expected within tolerance
no hidden state remains
```

### By Step 7
```
PHASE_5_COVERAGE_CERTIFICATE.json
Production 100% achieved
Phase 6 entry approved
```

---

## Success Criteria

Phase 5 is CLOSED when:

```
1. coverage_matrix.json exists (Step 1)
   └─ 908/908 records classified

2. Every MISSING_REPRESENTATION gap closed (Step 2)
   └─ canonical models exist for all in-scope items

3. Every EXPECTED item has terminal observation (Step 3)
   └─ EXPECTED_SET == TERMINAL_SET

4. Every MISSING_EXECUTION gap closed (Step 4)
   └─ serum-mcp operations exist for all executable items

5. Every MISSING_READBACK gap closed (Step 5)
   └─ Live Serum verification complete

6. Every special-state case resolved (Step 6)
   └─ Curves, modes, routing, ARP/CLIP all verified

7. Universal proof gate passes (Step 7)
   ├─ unresolved_required == 0
   ├─ conflicts == 0
   ├─ unsupported_required == 0
   ├─ compiler_gaps == 0
   └─ readback_mismatches == 0

PHASE_5_COVERAGE_CERTIFICATE.json: PRODUCTION READY
```

---

## Next Action

**Before implementing anything in Steps 2-7:**

Build `parameter_coverage_matrix.json` (Step 1).

This immediately shows:
- Actual vs. speculative gaps
- Which fixes have highest leverage (affect many records)
- Whether we're already closer to 100% than we think

The matrix becomes the workplan. No surprises.

---

**Recommendation:** Start Phase 5 execution with Step 1 only. Once the ledger exists, the remaining six steps become deterministic (clear blockers, clear sequences, clear verification gates).
