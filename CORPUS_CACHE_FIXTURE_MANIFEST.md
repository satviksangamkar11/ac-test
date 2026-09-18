# CORPUS_CACHE_FIXTURE_MANIFEST

## Status: FROZEN / IMMUTABLE

This fixture is load-bearing and must not be modified without explicit authorization.

**File:** experiments/_corpus_cache.pkl  
**Size:** 252,960,453 bytes (252 MB)  
**SHA256:** 69f0278838fcb978a8bebc2a5046044eb001e202c07861bb53e12a3c4d0477c8  
**Last modified:** 2026-09-03 05:43 UTC  
**Age:** 15 days (stable, unchanged)

## Usage

**Primary use:** FXEQ baseline fixture for Phase 3/4A body-state mutation tests  
**Access:** `bodies[4]` from unpickled dictionary  
**Referenced by:** ~40 scripts across experiments/, serum2/, tests/

## Content

Serum 2.0.21 state snapshot with pre-populated FXEQ structure:
- FXRack0.FX[1].FXEQ.plainParams structure
- Baseline parameter values (e.g., kParamFreq1=639.84 Hz)
- Used as execution fixture for Phase 3 FXEQ.Freq1 mutation baseline
- Provides context-safe FXEQ structure for Phase 4A closure mutations

## Regeneration Status

**NO REGENERATION SCRIPT FOUND** in current repository.

Possible sources:
1. Phase 1 experiment output (unknown script/method)
2. Manual Serum state export (unknown procedure)
3. DawDreamer snapshot (unknown export method)

**Action:** Do not attempt to regenerate without explicit authorization.
Regenerated fixtures may have different baseline values, which would:
- Invalidate Phase 3 execution evidence (baseline mismatch)
- Block Phase 4A FXEQ closure mutations
- Require new causal qualification experiments

## CI/CD Handling

**Current status:** NOT INTEGRATED

For fresh clone compatibility, one of:
1. Git LFS tracking (requires LFS infrastructure setup)
2. CDN download on-demand (requires CI integration + URL management)
3. Skip fixture-dependent tests (pytest markers + CI configuration)
4. Package in releases (binary distribution, not git source)

**Recommended path:** Option 2 (CDN) or Option 3 (skip with clear messaging)

## Integrity Verification

To verify fixture integrity and detect corruption:

```bash
sha256sum experiments/_corpus_cache.pkl
# Expected: 69f0278838fcb978a8bebc2a5046044eb001e202c07861bb53e12a3c4d0477c8

# If hash doesn't match:
#   Fixture may be corrupted. Do not use.
#   Contact team for restore from backup.
```

## Dependency Chain

**Phase 3 execution evidence** (experiments/phase3_evidence_fxeq_freq1.json) depends on:
- This fixture's baseline value (639.84 Hz for kParamFreq1)
- FXEQ structure pre-populated in bodies[4]

**If fixture is modified:**
- Phase 3 baseline evidence becomes invalid
- Phase 3 admission gate will fail (baseline mismatch)
- Must re-run Phase 3 FXEQ qualification experiments

**Consequence:** Treat as immutable once Phase 3 evidence is locked.

## Ownership & Lock Status

**Locked by:** Phase 3 execution verification (b2a8f5d)  
**Date locked:** 2026-09-18 02:15  
**Reason:** Evidence fingerprint dependency  
**Modification:** FORBIDDEN without evidence audit

---

## Tracking

- Backup: experiments/_capability_contracts.pkl.backup.1789716070 (2026-09-18 12:51)
- Corruption incident: Sep 18 04:25–04:43 (recovered, same morning)
- Current state: Stable, unchanged for 15 days
- Audit: REPO_FORENSIC_AUDIT.md, EXECUTION_GAP_MATRIX.md

See NEXT_IMPLEMENTATION_PLAN.md Phase 3 (Tier 2 reproducibility) for future distribution strategy.
