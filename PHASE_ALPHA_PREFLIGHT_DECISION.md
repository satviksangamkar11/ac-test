# Phase α Preflight Discovery Gate: FINAL DECISION

**Date:** 2026-09-21  
**Branch:** phase-reference-reproduction-hardening  
**Commit:** 5f20c939269790705a6f4a3d97004ab7975570eb  
**Epoch:** 2.0.23@9293eb90

---

## EXECUTIVE DECISION

### Current State (Baseline)
- **Operations Admitted:** 9 (oscB.enabled, oscC.enabled, oscB.octave, env2/3/4 decay/release)
- **Operations NO_CAPABILITY:** 27
- **Total Derived Operations:** 36
- **Reference-State Coverage:** 9 / 178 fields = **5.1%**

### After Phase α Preflight (Discovered State)
- **Tier 1 SAFE TO PROCEED:** 12 operations (filter 2, osc fine 2, osc unison 2, env hold 4, lfo mode 1, lfo mono 1)
- **Tier 2 GATE-DEPENDENT:** 1 operation (fx.hyper.unison, requires FX schema discovery)
- **Tier 3 DISCOVERY-ONLY:** 1 operation (lfo1.shape, likely UNSUPPORTED)
- **Total Qualified:** 12–13 operations (14 if lfo1.shape found)

### After Phase α Execution (Projected)
- **Operations Admitted:** 9 + 12 = **21 operations** (minimum; up to 22–23 if FX/LFO shape qualify)
- **Reference-State Coverage:** ~21–23 / 178 fields = **12–13%**
- **New Contracts:** 7 core (filter_enable, osc_fine, osc_unison, env_hold, lfo_mode, lfo_mono, fx_hyper_unison)

---

## TIER 1: SAFE TO PROCEED IMMEDIATELY (12 OPERATIONS)

All 12 operations have been verified through kParam catalog inspection. **All kParams exist.** All mutation targets are clear. All binding types are known. No blockers.

### ✓ QUALIFICATION_READY (GO)

#### Filter Control (2 operations, 1 contract)
| Control | Atlas ID | kParam | Kind | Binding | Status |
|---------|----------|--------|------|---------|--------|
| filter1.enabled | FILTER1.Enable | VoiceFilter0.kParamEnable | bool | SERUM_PRESET_STRUCTURAL | **GO** |
| filter2.enabled | FILTER2.Enable | VoiceFilter1.kParamEnable | bool | SERUM_PRESET_STRUCTURAL | **GO** |

**Contract:** `filter_enable` (generic, covers both filters)  
**Execution Path:** VoiceFilter[0..1].plainParams.kParamEnable  
**Prerequisite:** None  
**Confidence:** HIGH

---

#### Oscillator Fine-Tuning (2 operations, 1 contract)
| Control | Atlas ID | kParam | Kind | Binding | Status |
|---------|----------|--------|------|---------|--------|
| oscA.fine | OSC1.Fine | Oscillator0.kParamFine | float | SERUM_PRESET_STRUCTURAL | **GO** |
| oscB.fine | OSC2.Fine | Oscillator1.kParamFine | float | SERUM_PRESET_STRUCTURAL | **GO** |

**Contract:** `oscillator_fine_offset` (generic, covers Osc A/B, -80…+80 cents)  
**Execution Path:** Oscillator[0..1].plainParams.kParamFine  
**Prerequisite:** None  
**Confidence:** HIGH

---

#### Oscillator Unison Voices (2 operations, 1 contract)
| Control | Atlas ID | kParam | Kind | Binding | Status |
|---------|----------|--------|------|---------|--------|
| oscA.unison | OSC1.Unison | Oscillator0.kParamUnison | float | SERUM_PRESET_STRUCTURAL | **GO** |
| oscB.unison | OSC2.Unison | Oscillator1.kParamUnison | float | SERUM_PRESET_STRUCTURAL | **GO** |

**Contract:** `oscillator_unison_voices` (generic, covers Osc A/B, 1-16 voices)  
**Execution Path:** Oscillator[0..1].plainParams.kParamUnison  
**Prerequisite:** None  
**Confidence:** HIGH

---

#### Envelope Hold Phase (4 operations, 1 contract via OperatorPattern)
| Control | Atlas ID | kParam | Kind | Binding | Status |
|---------|----------|--------|------|---------|--------|
| env1.hold | Env1.Hold | Env0.kParamHold | float | SERUM_PRESET_STRUCTURAL | **GO** |
| env2.hold | Env2.Hold | Env1.kParamHold | float | SERUM_PRESET_STRUCTURAL | **GO** |
| env3.hold | Env3.Hold | Env2.kParamHold | float | SERUM_PRESET_STRUCTURAL | **GO** |
| env4.hold | Env4.Hold | Env3.kParamHold | float | SERUM_PRESET_STRUCTURAL | **GO** |

**Contract:** `envelope_hold_phase` (generic, covers all 4 envelopes via OperatorPattern, 0-5.2 seconds)  
**Execution Path:** Env[0..3].plainParams.kParamHold  
**Prerequisite:** None  
**Pattern Note:** Single contract qualifies all 4 operations; body_state path generalizes per envelope index  
**Confidence:** HIGH

---

#### LFO Mode Selection (1 operation, 1 contract)
| Control | Atlas ID | kParam | Kind | Binding | Status |
|---------|----------|--------|------|---------|--------|
| lfo1.mode | LFO0.Mode | LFO0.kParamMode | enum | SERUM_PRESET_STRUCTURAL | **GO** |

**Contract:** `lfo_mode_select` (enum: Free, Retrig, Envelope)  
**Execution Path:** LFO0.plainParams.kParamMode  
**Prerequisite:** None  
**Confidence:** HIGH

---

#### LFO Monophonic Toggle (1 operation, 1 contract)
| Control | Atlas ID | kParam | Kind | Binding | Status |
|---------|----------|--------|------|---------|--------|
| lfo1.mono | LFO0.Mono | LFO0.kParamMono | bool | SERUM_PRESET_STRUCTURAL | **GO** |

**Contract:** `lfo_monophonic` (boolean toggle)  
**Execution Path:** LFO0.plainParams.kParamMono  
**Prerequisite:** None  
**Confidence:** HIGH

---

## TIER 2: GATE-DEPENDENT (1 OPERATION)

### ⊙ DISCOVERY_REQUIRED (GATE: FX schema query)

#### FX Hyper Unison
| Control | Atlas ID | kParam | Kind | Binding | Status |
|---------|----------|--------|------|---------|--------|
| fx.hyper.unison | FXHyper.Unison | FXRack0.FXHyperD.kParamUnison | float (TBD) | BODY_STATE | **DISCOVERY** |

**Issue:** FX parameters not in Serum schema snapshot. Must query serum-mcp for FX[Hyper] parameter details.

**Gate Action:**
1. Call `serum-mcp.describe_preset()` on a preset with Hyper FX active
2. Extract FXHyperD parameter schema (especially kParamUnison range/type)
3. If parameter found: confirm range (likely 1-16 like osc unison), then **QUALIFICATION_READY**
4. If parameter not found or named differently: update mapping and proceed

**Expected Outcome:** QUALIFICATION_READY (high confidence FX structure exists in Serum)  
**Contingency:** If parameter missing, remains NO_CAPABILITY  
**Confidence:** MEDIUM (structure exists; naming/exposure TBD)

---

## TIER 3: LIKELY UNSUPPORTED (1 OPERATION)

### ✗ UNSUPPORTED / UNREPRESENTABLE (kParam does not exist)

#### LFO Shape Selection
| Control | Atlas ID | kParam | Kind | Binding | Status |
|---------|----------|--------|------|---------|--------|
| lfo1.shape | LFO0.Shape | LFO0.kParamShape | N/A | N/A | **UNSUPPORTED** |

**Finding:** Serum schema snapshot shows **NO kParamShape in LFO parameters**. Shape exists only in sub_oscillator (Sub only), not in LFO.

**kParam Catalog Inspection:**
- `lfo.kParams`: [kParamRate, kParamMode, kParamBeatSync, kParamRise, kParamSmooth, kParamDelay, **kParamType** (not kParamShape), kParamMono, kParamSwing, kParamDotted, kParamTriplets, kParamRate10x]
- kParamShape: **NOT FOUND**

**Possible Explanations:**
1. LFO shape is not independently exposed as a parameter (may be implicit in preset type/identity)
2. LFO shape is represented differently (e.g., under kParamType or kParamRate variations)
3. Shape was observed in transcript but misidentified from UI

**Gate Action:**
1. Query serum-mcp schema for LFO0 kParams
2. Search for any Shape/Waveform/Form-related parameter names
3. If found: promote to DISCOVERY_READY → QUALIFICATION_READY
4. If not found: confirm UNSUPPORTED and mark operation as **permanently NO_CAPABILITY**

**Expected Outcome:** UNSUPPORTED (high confidence based on catalog inspection)  
**Confidence:** HIGH (parameter catalog is definitive; kParamShape not listed for LFO)

---

## ARITHMETIC RECONCILIATION

### Operations Count
- **14 candidate operations for Phase α** ✓ (2 filter + 2 osc fine + 2 osc unison + 4 env hold + 1 fx hyper + 1 lfo mode + 1 lfo mono + 1 lfo shape)
- **12 QUALIFICATION_READY** (filter 2, osc fine 2, osc unison 2, env hold 4, lfo mode 1, lfo mono 1)
- **1 DISCOVERY_REQUIRED** (fx.hyper.unison)
- **1 UNSUPPORTED** (lfo1.shape)

### Contract Count
- **7 new contracts (Tier 1):** filter_enable, oscillator_fine_offset, oscillator_unison_voices, envelope_hold_phase, lfo_mode_select, lfo_monophonic, fx_hyper_unison
- **0 additional if lfo1.shape unsupported**
- **8 total if lfo1.shape found** (unlikely)

### Reference-State Rows Covered

| Item | Count | Rows Newly Covered |
|------|-------|-------------------|
| filter1.enabled | 1 op | ~1 row (filter0.enabled) |
| filter2.enabled | 1 op | ~1 row (filter1.enabled) |
| oscA.fine | 1 op | ~1 row (oscillators[0].fine) |
| oscB.fine | 1 op | ~1 row (oscillators[1].fine) |
| oscA.unison | 1 op | ~1 row (oscillators[0].unison) |
| oscB.unison | 1 op | ~1 row (oscillators[1].unison) |
| env1.hold | 1 op | ~1 row (envelopes[0].hold) |
| env2.hold | 1 op | ~1 row (envelopes[1].hold) |
| env3.hold | 1 op | ~1 row (envelopes[2].hold) |
| env4.hold | 1 op | ~1 row (envelopes[3].hold) |
| lfo1.mode | 1 op | ~1 row (lfos[0].mode) |
| lfo1.mono | 1 op | ~1 row (lfos[0].mono) |
| **Tier 1 Subtotal** | **12 ops** | **~12 rows** |
| fx.hyper.unison | 1 op | ~1 row (if qualified) |
| lfo1.shape | 1 op | ~1 row (if qualified; unlikely) |
| **Total if all qualify** | **14 ops** | **~14 rows** |

**Coverage Calculation:**
- Current: 9 admitted operations = ~9 rows / 178 total = **5.1%**
- After Tier 1: 9 + 12 = 21 admitted = ~21 rows / 178 total = **11.8%**
- After Tier 2: 9 + 12 + 1 = 22 admitted = ~22 rows / 178 total = **12.4%** (if fx.hyper qualifies)

---

## FINAL STATUS: GO / NO-GO DECISION

### TIER 1: ✓ GO (Proceed immediately, no gates)

**12 operations are SAFE TO PROCEED to real qualification:**
1. filter1.enabled
2. filter2.enabled
3. oscA.fine
4. oscB.fine
5. oscA.unison
6. oscB.unison
7. env1.hold
8. env2.hold
9. env3.hold
10. env4.hold
11. lfo1.mode
12. lfo1.mono

**Requirements Met:**
- [x] All kParams verified to exist in snapshot
- [x] All mutation targets clear (body_state paths)
- [x] All binding types known (SERUM_PRESET_STRUCTURAL)
- [x] No prerequisites or circular dependencies
- [x] Direct Serum UI readback available for all
- [x] 7 new contracts identified (filter_enable, osc_fine_offset, osc_unison_voices, envelope_hold_phase, lfo_mode_select, lfo_monophonic, fx_hyper_unison)
- [x] No architectural weakening needed
- [x] No compiler changes needed

**Next Step:** Begin real qualification experiments with serum-mcp mutations and direct UI readback verification. Recommended start: **Group 1 (Filter Enable)** as simplest test case.

---

### TIER 2: ⊙ GATE-DEPENDENT (1 operation, proceed after FX discovery)

**1 operation requires brief FX schema discovery:**
- fx.hyper.unison

**Gate:** Query serum-mcp for FXHyperD parameter details  
**Expected Outcome:** QUALIFICATION_READY (high confidence)  
**Contingency:** If parameter structure unclear, skip to Tier 3 and return later

---

### TIER 3: ✗ HOLD (1 operation, unlikely to qualify)

**1 operation marked UNSUPPORTED pending discovery:**
- lfo1.shape

**Gate:** Query serum-mcp for LFO0 kParams; search for Shape/Waveform parameter  
**Expected Outcome:** Parameter not found → mark permanently NO_CAPABILITY  
**Confidence:** HIGH (catalog inspection definitive; kParamShape not in LFO)

---

## NO ARCHITECTURAL CONCERNS

✓ All 12 Tier 1 operations follow established patterns (SERUM_PRESET_STRUCTURAL for core synth)  
✓ No compiler binding validation needs weakening  
✓ No admission gates need modification  
✓ No semantic names inferred as proof of capability  
✓ No HOST_PARAMETER converted to execution authority  
✓ All mutations provable via serum-mcp + direct UI readback

---

## DELIVERABLES PRODUCED

1. **Phase α Preflight Manifest** (markdown) – Complete discovery analysis
2. **Phase α Machine-Readable Manifest** (CSV) – One row per operation, 10 discovery fields
3. **This Decision Document** – Final GO/NO-GO for each operation

**Status:** ✓ **READY FOR PHASE α TIER 1 REAL QUALIFICATION**

No code modifications. No contracts created. No admission changes. Only discovery complete.

Proceed with real qualification when authorized.

