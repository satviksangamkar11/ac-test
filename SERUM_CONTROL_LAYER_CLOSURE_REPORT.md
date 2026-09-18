# SERUM CONTROL LAYER CLOSURE REPORT

**Date:** 2026-09-18T12:15:12.020826  
**Phase:** 4A — Serum Control Layer Closure

## Summary Counts

### Normalized Targets (396)

| Disposition | Count | Meaning |
|---|---|---|
| A | 19 | CAUSAL_PROVEN + ADMITTED |
| B | 0 | CAUSAL_PROVEN but blocked (no execution binding wired) |
| C | 0 | machine/UI verified but not causally qualified (STRUCTURAL_ONLY) |
| D | 356 | not-yet-derived |
| E | 19 | unsupported/structural (incl. DEAD_OR_SUPERSEDED, NEGATIVE_EVIDENCE) |
| F | 2 | unresolved/unknown (ambiguous, contradicted) |
| G | 0 | proven-not-user-control |
| **TOTAL** | **396** | |

### Semantic Rows (908)

| Disposition | Count | Meaning |
|---|---|---|
| A | 4 | CAUSAL_PROVEN + ADMITTED |
| B | 0 | CAUSAL_PROVEN but blocked (no execution binding wired) |
| C | 0 | machine/UI verified but not causally qualified (STRUCTURAL_ONLY) |
| D | 786 | not-yet-derived |
| E | 40 | unsupported/structural (incl. DEAD_OR_SUPERSEDED, NEGATIVE_EVIDENCE) |
| F | 5 | unresolved/unknown (ambiguous, contradicted) |
| G | 73 | proven-not-user-control |
| **TOTAL** | **908** | |

## Category Breakdown (user-requested terms)

- **TOTAL SEMANTIC ROWS:** 908
- **TOTAL NORMALIZED TARGETS:** 396
- **VERIFIED EXECUTABLE (A):** 19 targets / 4 semantic rows
- **BLOCKED (B):** 0 targets / 0 semantic rows
- **STRUCTURAL/UI-VERIFIED, NOT CAUSAL (C):** 0 targets / 0 semantic rows
- **NOT_YET_DERIVED (D):** 356 targets / 786 semantic rows
- **UNSUPPORTED/STRUCTURAL (E):** 19 targets / 40 semantic rows
- **UNKNOWN/UNRESOLVED (F):** 2 targets / 5 semantic rows
- **PROVEN_NOT_USER_CONTROL (G):** 0 targets / 73 semantic rows

## Execution Closure Performed This Phase

4 additional FXEQ targets moved from B (CAUSAL_PROVEN but blocked) to A (CAUSAL_PROVEN + ADMITTED + EXECUTED) by reusing the exact Phase-3-established mechanism (BODY_STATE via pathmerge + `experiments/_corpus_cache.pkl` bodies[4] fixture). No new mechanism invented, no contract modified:

- FXEQ.Freq2, FXEQ.Gain1, FXEQ.Reso1, FXEQ.Type2 — see `experiments/phase4a_fxeq_closure_execution.json`

This brings the actively-executed-with-fresh-evidence set to 15 targets total (11 from Phase 3 + 4 from this closure pass).

## Gaps Requiring Explicit Attention

### 1. Orphan CAUSAL_VERIFIED/STRUCTURAL_ONLY contracts (21)

These contracts hold real evidence but are not reachable by any semantic name in the 396-target vocabulary or the producer's SEMANTIC_TARGETS registration. Fixing this means registering new targets — explicitly out of scope for Phase 4A (Step 6: 'do not expand the producer brain yet'). Listed in full in SERUM_CONTROL_LAYER_MATRIX.md.

### 2. Ambiguous targets (F, 2)

MANY_TO_ONE targets where multiple semantic rows compete for one normalized target, unresolved by the 2D.6J reconciliation. Needs disambiguation before admission.

### 3. Dead/superseded targets folded into E

Targets the 2D.6I/2D.6J reconciliation already determined are dead or superseded (e.g. FXEQ.LevelOut — confirmed in this phase: the field does not exist in the FXEQ-populated fixture body, consistent with the prior finding).

## Closure Gate Verification (Step 7)

- [x] 908/908 semantic rows have explicit disposition
- [x] 396/396 normalized targets have explicit disposition
- [x] No target has undocumented execution status
- [x] Every executable (A) target has an authoritative mechanism
- [x] Every previously admitted Phase-3 target remains executable
- [x] Blocked/unsupported/unknown targets preserved as such (not silently promoted)
- [x] No frozen registry changed
- [x] Evidence provenance complete (every row cites a source)
- [x] Single canonical Serum control matrix exists

## Not Modified

- 908 semantic inventory (SERUM2_EXECUTION_FAMILY_REGISTRY_EXACT_908.json)
- 396 normalized targets (SERUM2_TARGET_NORMALIZED_V4.json)
- V3 execution coverage registry (read-only in this pass)
- Capability contracts / causal ledger (experiments/_capability_contracts.pkl)
- admission.py, V4 registry, Phase 1-3 evidence

Only modified: `serum2/qualification/body_state_mapping.json` (4 new entries, reusing the established mechanism — a producer-config file, not a frozen artifact).
