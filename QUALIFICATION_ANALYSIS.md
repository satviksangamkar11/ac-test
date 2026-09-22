# Reference-to-Serum Reproduction: Qualification Gap Analysis

**Date:** 2026-09-21  
**Branch:** phase-state-ledger-admission  
**Epoch:** 2.0.23@9293eb90  
**Current State:** 216 observations → 49 derived operations → 9 admitted → 5.1% coverage

---

## Executive Summary

The frozen 9-operation live-UI regression establishes proof-of-concept for the admission → compilation → verification pipeline. Reaching 100% reference reproduction requires:

- **7 binding-gap operations** (existing contracts, execution-ineligible due to HOST_PARAMETER only)
- **27 NO_CAPABILITY operations** (no contracts; requires genuine capability qualification)

Total unmet: **34 operations** covering **178 state fields** = **95.5% of reference coverage**.

This analysis identifies the exact binding gaps, groups the 27 NO_CAPABILITY operations by capability family, and prescribes a qualification order that minimizes redundant experiments.

---

## Part 1: The 7 Binding-Gap Operations

These operations have **verified contracts but are NOT execution-eligible** because they expose only `HOST_PARAMETER` bindings (evidence-surface only, insufficient for preset/body-state lowering).

| Control | Contract Key | Structural Key | Binding Status | Why No Execution Binding |
|---------|--------------|----------------|-----------------|--------------------------|
| **oscA.enabled** | oscillator_field_OSC-ENABLE | Oscillator0.kParamEnable | HOST_PARAMETER | VST3 parameter found ("A Enable") but not proven as executable mutation path |
| **oscA.octave** | oscillator_field_OSC-OCTAVE | Oscillator0.kParamOctave | HOST_PARAMETER | VST3 parameter found ("A Octave") but not proven as executable mutation path |
| **env1.decay** | envelope_field_decay | Env0.kParamDecay | HOST_PARAMETER | VST3 parameter found ("Env 1 Decay") but not proven as executable mutation path |
| **env1.sustain** | envelope_field_sustain | Env0.kParamSustain | HOST_PARAMETER | VST3 parameter found ("Env 1 Sustain") but not proven as executable mutation path |
| **env1.release** | envelope_field_release | Env0.kParamRelease | HOST_PARAMETER | VST3 parameter found ("Env 1 Release") but not proven as executable mutation path |
| **filter1.type** | filter_field_type | VoiceFilter0.kParamType | HOST_PARAMETER | VST3 parameter found ("Filter 1 Type") but not proven as executable mutation path |
| **fx.distortion.type** | fx_field_distortion_mode | FXRack0.FXDistortion.kParamMode | UNMAPPED | No VST3 mapping exists; parameter exposed only as OBSERVED evidence |

**Execution-Eligible Bindings for Comparison:**
- **BODY_STATE:** Direct body path mutation (FXRack0.FX.1.FXEQ.plainParams.kParam*) – used successfully for FXEQ operations
- **SERUM_PRESET_STRUCTURAL:** Pass-1 qualified, proven to write contract.scope.mutation_target_path – used for 6 envelope operations (env2/3/4 decay/release)

**Why This Matters:**
The 7 contracts represent proven capability (evidence verified, causal link established at 2.0.21 epoch). Converting them requires:
1. **Execution binding qualification:** Direct mutation proof (call serum-mcp → readback → confirm expected field changed)
2. **No structural inference:** Binding must be demonstrated, not guessed from parameter name

---

## Part 2: The 27 NO_CAPABILITY Operations

These operations have **no existing contracts**. They range from clearly structured (filter enable/type) to complex (wavetable selection, LFO shape) to unresolved (osc.semitone, lfo.shape without kParam).

Grouped by **capability family** with stop-stage diagnosis:

### **Family 1: Filter Control – 2 NO_CAPABILITY**

| Control | Structural Key | Stop Stage | Issue |
|---------|----------------|-----------|-------|
| **filter1.enabled** | VoiceFilter0.kParamEnable | CONTRACT_LOOKUP | No contract exists for Filter 0 enable |
| **filter2.enabled** | VoiceFilter1.kParamEnable | CONTRACT_LOOKUP | No contract exists for Filter 1 enable |

**Qualification Need:** Structure + capability proof  
**Evidence Type Required:** STRUCTURAL_ONLY (prove VoiceFilter.kParamEnable exists and is writable)  
**Complexity:** Low – straightforward toggle control  
**Reference:** Filter 1 is OBSERVED as enabled in live UI; Filter 2 disabled  
**Reuse Potential:** Same family as filter1.type (EPOCH_MISMATCH); may share body-state path

---

### **Family 2: Oscillator Selection Controls – 6 NO_CAPABILITY**

| Control | Structural Key | Stop Stage | Issue |
|---------|----------------|-----------|-------|
| **oscA.wavetable** | Oscillator0.<wavetable operand> | CONTRACT_LOOKUP | No wavetable selection contract |
| **oscB.wavetable** | Oscillator1.<wavetable operand> | CONTRACT_LOOKUP | No wavetable selection contract |
| **oscC.wavetable** | Oscillator2.<wavetable operand> | CONTRACT_LOOKUP | No wavetable selection contract |
| **oscA.semitone** | N/A (structural_key=null) | STRUCTURAL_KEY | No kParam catalog entry for osc.semitone |
| **oscB.semitone** | N/A | STRUCTURAL_KEY | No kParam catalog entry for osc.semitone |
| **oscNoise.noise_type** | Oscillator3.kParamNoiseType | CONTRACT_LOOKUP | No contract for Noise oscillator type selection |

**Qualification Need:** Structure discovery + capability proof  
**Evidence Type Required:** 
- **Wavetables (3 ops):** Operand mapping (which table ↔ which string), then contract with mutation binding  
- **Semitone (2 ops):** Requires kParam discovery or evidence that semitone is not exposed as a discrete parameter  
- **Noise type (1 op):** STRUCTURAL_ONLY contract + capability proof  
**Complexity:** Medium-High (wavetable is enum with 100+ entries; semitone may be missing or folded into fine-tuning)  
**Reuse Potential:** Wavetables share operand codebook; semitone may resolve as "not independently exposed"

---

### **Family 3: Oscillator Fine-Tuning – 5 NO_CAPABILITY**

| Control | Structural Key | Stop Stage | Issue |
|---------|----------------|-----------|-------|
| **oscA.fine** | Oscillator0.kParamFine | CONTRACT_LOOKUP | No contract for osc fine-tuning |
| **oscA.unison** | Oscillator0.kParamUnison | CONTRACT_LOOKUP | No contract for unison |
| **oscB.fine** | Oscillator1.kParamFine | CONTRACT_LOOKUP | No contract for osc fine-tuning |
| **oscB.unison** | Oscillator1.kParamUnison | CONTRACT_LOOKUP | No contract for unison |
| **fx.hyper.unison** | FXRack0.FXHyperD.kParamUnison | CONTRACT_LOOKUP | No contract for FX Hyper unison |

**Qualification Need:** Capability proof (structure exists but not proven executable)  
**Evidence Type Required:** BODY_STATE for osc fine/unison; likely FX-slot-specific path for hyper.unison  
**Complexity:** Medium (likely straightforward numeric mutation paths)  
**Reuse Potential:** Unison controls may share body_state pattern; fine-tuning is independent per oscillator

---

### **Family 4: Envelope Hold Control – 4 NO_CAPABILITY**

| Control | Structural Key | Stop Stage | Issue |
|---------|----------------|-----------|-------|
| **env1.hold** | Env0.kParamHold | CONTRACT_LOOKUP | No contract for Hold phase |
| **env2.hold** | Env1.kParamHold | CONTRACT_LOOKUP | No contract for Hold phase |
| **env3.hold** | Env2.kParamHold | CONTRACT_LOOKUP | No contract for Hold phase |
| **env4.hold** | Env3.kParamHold | CONTRACT_LOOKUP | No contract for Hold phase |

**Qualification Need:** Single generic envelope contract (covers all 4 envelopes)  
**Evidence Type Required:** STRUCTURAL_ONLY (prove Env.kParamHold exists and is writable on 1-2 envelopes; generalize)  
**Complexity:** Low (standard envelope parameter, similar to decay/release already admitted)  
**Reuse Potential:** **HIGH** – single contract qualifies all 4 operations  
**Note:** Decay/Release for env2/3/4 are STRUCTURAL_ONLY; Hold may follow same pattern

---

### **Family 5: LFO Control – 3 NO_CAPABILITY**

| Control | Structural Key | Stop Stage | Issue |
|---------|----------------|-----------|-------|
| **lfo1.shape** | N/A | STRUCTURAL_KEY | No kParam catalog entry for lfo.shape |
| **lfo1.mode** | LFO0.kParamMode | CONTRACT_LOOKUP | No contract for LFO mode |
| **lfo1.mono** | LFO0.kParamMono | CONTRACT_LOOKUP | No contract for LFO monophonic toggle |

**Qualification Need:** LFO parameter discovery + capability proof  
**Evidence Type Required:** 
- **Shape (1 op):** Discover if kParam exists or if shape is mapped differently (may not exist)  
- **Mode + Mono (2 ops):** BODY_STATE or STRUCTURAL_ONLY contracts  
**Complexity:** Medium (LFO parameter space is less standardized than oscillator/envelope)  
**Reuse Potential:** Mode and Mono may share LFO0 body_state path; Shape may resolve to "unmapped"

---

### **Family 6: FX Delay Control – 3 NO_CAPABILITY**

| Control | Structural Key | Stop Stage | Issue |
|---------|----------------|-----------|-------|
| **fx.delay.time_l** | FXRack0.FXDelay.kParamTimeL | CONTRACT_LOOKUP | No contract for delay time L |
| **fx.delay.time_r** | FXRack0.FXDelay.kParamTimeR | CONTRACT_LOOKUP | No contract for delay time R |
| **fx.delay.bpm** | FXRack0.FXDelay.kParamBeatSync | CONTRACT_LOOKUP | No contract for beat sync toggle |

**Qualification Need:** FX-slot-specific BODY_STATE bindings  
**Evidence Type Required:** BODY_STATE (delay is in FX rack, body paths must include FXRack0.FXDelay)  
**Complexity:** Medium (FX parameters are less exposed than core synth; beat sync may have discrete logic)  
**Reuse Potential:** All three share FXRack0.FXDelay context; time_l and time_r likely mirror each other

---

### **Family 7: FX Compressor Control – 4 NO_CAPABILITY**

| Control | Structural Key | Stop Stage | Issue |
|---------|----------------|-----------|-------|
| **fx.compressor.ratio** | FXRack0.FXComp.kParamRatio | CONTRACT_LOOKUP | No contract for compressor ratio |
| **fx.compressor.attack** | FXRack0.FXComp.kParamAttack | CONTRACT_LOOKUP | No contract for attack time |
| **fx.compressor.release** | FXRack0.FXComp.kParamRelease | CONTRACT_LOOKUP | No contract for release time |
| **fx.compressor.gain** | FXRack0.FXComp.kParamMakeup | CONTRACT_LOOKUP | No contract for makeup gain |

**Qualification Need:** FX-slot-specific BODY_STATE bindings  
**Evidence Type Required:** BODY_STATE (compressor is in FX rack, body paths must include FXRack0.FXComp)  
**Complexity:** Low-Medium (standard compressor parameters, patterns similar to delay)  
**Reuse Potential:** All four share FXRack0.FXComp context; attack and release mirror envelope envelope patterns

---

### **Summary Table: 27 NO_CAPABILITY Operations by Family**

| Family | Count | Stop Stage Breakdown | Qualification Type | Min Contracts Needed |
|--------|-------|----------------------|-------------------|----------------------|
| Filter Control | 2 | 2 CONTRACT_LOOKUP | STRUCTURAL_ONLY | 1 (generic) |
| Osc Selection | 6 | 4 CONTRACT_LOOKUP, 2 STRUCTURAL_KEY | Mixed | 4 (wavetable map + noise + semitone resolution) |
| Osc Fine-Tuning | 5 | 5 CONTRACT_LOOKUP | BODY_STATE | 2 (fine per-osc + unison generic + fx-specific) |
| Envelope Hold | 4 | 4 CONTRACT_LOOKUP | STRUCTURAL_ONLY | 1 (generic + replicable to all envelopes) |
| LFO Control | 3 | 1 STRUCTURAL_KEY, 2 CONTRACT_LOOKUP | Mixed | 1-2 (depends on shape resolution) |
| FX Delay | 3 | 3 CONTRACT_LOOKUP | BODY_STATE | 1 (generic delay + FX-slot pattern) |
| FX Compressor | 4 | 4 CONTRACT_LOOKUP | BODY_STATE | 1 (generic compressor + FX-slot pattern) |
| **TOTAL** | **27** | — | — | **~11-13 contracts** |

---

## Part 3: Capability Family Qualification Requirements

### **Family 1: Filter Control (2 ops, 1 contract)**
**Contract Scope:** `filter_field_enable` – works for Filter 0 and Filter 1  
**Required Evidence:**
1. Observe Filter 0 disabled in reference video → observe enabled when changed
2. Direct Serum readback: `VoiceFilter0.plainParams.kParamEnable` and `VoiceFilter1.plainParams.kParamEnable`
3. Prove body_state BODY_STATE path mutation works

**Mutation Target:** FXRack0.FX.1.FXEQ context NOT needed; filter is core synth  
**Execution Binding:** Likely BODY_STATE (VoiceFilter[0..1].plainParams.kParamEnable)  
**Prerequisite:** None (toggle is atomic)  

---

### **Family 2: Oscillator Selection Controls (6 ops, 4 contracts)**

#### 2a. Wavetable Selection (3 ops → 1 contract with operand map)
**Contract Scope:** `oscillator_wavetable_select` – enum operand mapping  
**Required Evidence:**
1. Discover all valid wavetable strings in reference observation (only "default" observed)
2. Map each string to Serum's internal wavetable enum
3. Prove operand mutation: change table → readback confirms table changed
4. Publish OperandMap contract (wavetable string ↔ Serum enum)

**Execution Binding:** SERUM_PRESET_STRUCTURAL (wavetable lives in preset body)  
**Complexity:** Operand codebook discovery (one-time cost, applies to all 3 osc)  
**Prerequisite:** Operand map contract must be qualified before table mutations can be executed

#### 2b. Noise Type Selection (1 op → 1 contract)
**Contract Scope:** `oscillator_noise_type_select`  
**Required Evidence:**
1. Prove Oscillator3.kParamNoiseType is writable
2. Observe reference noise type ("White") → execute mutation → readback confirms
3. Document noise type enum (White, Pink, Brown, Violet, etc.)

**Execution Binding:** SERUM_PRESET_STRUCTURAL  
**Prerequisite:** None (noise is one slot, no interdependencies)

#### 2c. Semitone Offset (2 ops → resolution + 0-1 contracts)
**Contract Scope:** Depends on discovery outcome  
**Required Evidence:**
1. **Discovery:** Search kParam catalog for oscillator semitone parameter
   - If found: prove it's independently writable (not folded into fine)
   - If not found: declare "not independently exposed" → 0 contracts, NO_CAPABILITY remains
2. If found: execute mutation → readback confirms semitone changed

**Execution Binding:** SERUM_PRESET_STRUCTURAL (if exposed)  
**Prerequisite:** Depends on discovery result  
**Risk:** May resolve to "not exposed," blocking 2 operations permanently

---

### **Family 3: Oscillator Fine-Tuning (5 ops, 2 contracts)**

#### 3a. Oscillator Fine (2 ops → 1 contract)
**Contract Scope:** `oscillator_fine_offset` – generic, applies to Osc A/B  
**Required Evidence:**
1. Prove Oscillator[0..1].kParamFine is writable
2. Execute fine offset (e.g., −50 → 0 → +50 cents) → readback confirms
3. Document range and unit (cents, fine-tuning steps, etc.)

**Execution Binding:** SERUM_PRESET_STRUCTURAL  
**Prerequisite:** None (fine is independent)

#### 3b. Unison Control (3 ops → 2 contracts)
- **Osc Unison (2 ops):** `oscillator_unison_voices` – applies to Osc A/B
- **FX Hyper Unison (1 op):** `fx_hyper_unison` – FX-slot-specific

**Required Evidence:**
1. For osc unison: prove Oscillator[0..1].kParamUnison writable, execute 1→3→7 voices, readback confirms
2. For FX hyper: prove FXRack0.FXHyperD.kParamUnison writable in preset body, execute, readback
3. Document both ranges and semantics

**Execution Binding:** SERUM_PRESET_STRUCTURAL  
**Prerequisite:** None (unison is independent)

---

### **Family 4: Envelope Hold (4 ops, 1 contract)**

**Contract Scope:** `envelope_hold_phase` – generic, applies to all 4 envelopes  
**Required Evidence:**
1. Prove Env[0..3].kParamHold is writable on at least 2 envelopes (e.g., Env 0 and Env 2)
2. Execute hold time mutation (e.g., 0.0 → 0.5) → readback confirms
3. Document range and relationship to decay

**Execution Binding:** SERUM_PRESET_STRUCTURAL  
**Prerequisite:** None (hold is atomic)  
**Reuse:** Single contract proven on Env 0 generalizes to Env 1/2/3 (OperatorPattern)

---

### **Family 5: LFO Control (3 ops, 1-2 contracts)**

#### 5a. LFO Mode (1 op → 1 contract)
**Contract Scope:** `lfo_mode_select`  
**Required Evidence:**
1. Prove LFO0.kParamMode is writable
2. Execute mode mutation (Free → Sync → Trig, etc.) → readback confirms
3. Document mode enum (reference shows "Free")

**Execution Binding:** SERUM_PRESET_STRUCTURAL  
**Prerequisite:** None

#### 5b. LFO Monophonic Toggle (1 op → 1 contract)
**Contract Scope:** `lfo_monophonic` (or fold into lfo_mode contract if related)  
**Required Evidence:**
1. Prove LFO0.kParamMono is writable
2. Execute toggle (on/off) → readback confirms
3. Document semantics (poly vs mono behavior)

**Execution Binding:** SERUM_PRESET_STRUCTURAL  
**Prerequisite:** None

#### 5c. LFO Shape (1 op → resolution + 0-1 contracts)
**Contract Scope:** Depends on discovery  
**Required Evidence:**
1. **Discovery:** Search for LFO shape parameter
   - If found kParam (e.g., LFO0.kParamShape): prove writable, execute mutation (Sine → Tri → Saw → Lorenz, etc.), readback
   - If not found: declare "not independently exposed" → 0 contracts, NO_CAPABILITY remains
2. Reference observation shows "lorenz" shape

**Execution Binding:** SERUM_PRESET_STRUCTURAL (if exposed)  
**Risk:** May resolve to "not exposed"

---

### **Family 6: FX Delay (3 ops, 1 contract with FX-slot pattern)**

**Contract Scope:** `fx_delay_time` (generic for left/right) + FX-slot binding pattern  
**Required Evidence:**
1. Prove FXRack0.FXDelay.kParamTimeL and kParamTimeR are writable
2. Execute time mutation (e.g., 0.1 → 0.2 beats) → readback confirms both channels
3. Prove beat-sync toggle works (FXRack0.FXDelay.kParamBeatSync)
4. Document range, unit (beats or milliseconds), and relationship to BPM

**Execution Binding:** BODY_STATE (FXRack0.FXDelay.plainParams.kParam*)  
**Prerequisite:** Delay must exist in FX rack (verified in observation)  
**FX-Slot Pattern:** Establishes pattern for other FX controls (Compressor, Hyper, etc.)

---

### **Family 7: FX Compressor (4 ops, 1 contract with FX-slot pattern)**

**Contract Scope:** `fx_compressor_control` – generic for ratio, attack, release, makeup  
**Required Evidence:**
1. Prove FXRack0.FXComp.kParam{Ratio, Attack, Release, Makeup} are writable
2. Execute mutations:
   - Ratio: 4.0 (reference) → 2.0 → 8.0 → readback confirms
   - Attack: 90.1 (reference) → 10 → 200 → readback confirms
   - Release: 90.1 (reference) → 10 → 300 → readback confirms
   - Makeup: 1.0 (reference) → 2.0 → 0.5 → readback confirms
3. Document ranges, units, and mutual dependencies

**Execution Binding:** BODY_STATE (FXRack0.FXComp.plainParams.kParam*)  
**Prerequisite:** Compressor must exist in FX rack (verified in observation)  
**FX-Slot Pattern:** Reuses FXRack0 slot context; compressor parameters are independent

---

## Part 4: Safest Qualification Order

### **Phase α: Structure & Reusability (Unlock 11 operations, enable 7 dependent)**

**Goal:** Qualify contracts with maximum reusability and minimal prerequisites.

1. **Envelope Hold (4 ops)** ← 1 contract, generic, enables family
   - Requires: Single Env.kParamHold proof on Env 0
   - Generalizes: Same body_state path for Env 1/2/3 (OperatorPattern)
   - Time: ~10 minutes (simple mutation, Serum readback)

2. **Filter Enable (2 ops)** ← 1 contract, enables filter family, low complexity
   - Requires: Toggle proof on Filter 0 and Filter 1
   - Complexity: Straightforward; uses existing CONTRACT_LOOKUP path
   - Time: ~15 minutes (simple toggle)

3. **Oscillator Fine (2 ops)** ← 1 contract, enables fine-tuning family
   - Requires: Prove Oscillator0.kParamFine and Oscillator1.kParamFine writable
   - Complexity: Low (numeric mutation, standard unit)
   - Time: ~15 minutes

4. **Osc Unison (2 ops)** ← 1 contract, enables unison controls
   - Requires: Prove Oscillator[0..1].kParamUnison (enum 1,3,5,7 voices)
   - Complexity: Enum operand mapping (like wavetable but smaller codebook)
   - Time: ~15 minutes

5. **LFO Mode (1 op)** ← 1 contract, low complexity
   - Requires: Prove LFO0.kParamMode writable (enum: Free, Sync, Trig, Gate)
   - Complexity: Standard enum
   - Time: ~10 minutes

6. **LFO Monophonic (1 op)** ← 1 contract, pairs with mode
   - Requires: Prove LFO0.kParamMono toggle
   - Complexity: Boolean toggle
   - Time: ~5 minutes

**Phase α Subtotal:** 13 operations admitted, 6 new contracts, **~70 minutes**

---

### **Phase β: FX-Slot Pattern & Generic Parameters (Unlock 7 operations, 4 new contracts)**

**Goal:** Establish FX-slot binding pattern (reusable for remaining FX families) and prove generic FX parameters.

7. **FX Delay Time (3 ops)** ← 1 contract, establishes FXRack0 pattern
   - Requires: Prove FXRack0.FXDelay.kParamTimeL/R/BeatSync writable
   - Complexity: Numeric mutation + beat-sync toggle; establishes FXRack0 slot pattern for other FX
   - Time: ~20 minutes

8. **FX Compressor Ratio (1 op, part of family)** ← 1 contract, generalizes to all compressor controls
   - Requires: Prove FXRack0.FXComp.kParamRatio writable
   - Complexity: Numeric mutation (2.0 → 4.0 → 8.0)
   - Time: ~10 minutes
   - Note: Ratio alone gates full compressor; other params (attack, release, makeup) follow same body_state path

9. **FX Compressor Attack/Release (2 ops embedded in same contract)**
   - Requires: Prove kParamAttack and kParamRelease within same FXComp contract
   - Complexity: Numeric mutations, mirror each other
   - Time: ~15 minutes

10. **FX Compressor Makeup Gain (1 op, embedded in same contract)**
    - Requires: Prove kParamMakeup writable
    - Complexity: Numeric mutation
    - Time: ~5 minutes

**Phase β Subtotal:** 7 operations admitted, 2 new contracts (delay + compressor), **~50 minutes**

---

### **Phase γ: Oscillator Selection & Discovery (Unlock 6 operations, 3-4 new contracts/resolutions)**

**Goal:** Qualify operand codebooks and resolve "unmapped" discovery failures safely.

11. **Oscillator Wavetable Operand Map (3 ops)** ← 1 contract + operand codebook
    - Requires: Build complete wavetable enum → prove mutation works on all 3 oscillators
    - Complexity: Operand discovery (one-time cost); mutation proof is straightforward
    - Time: ~25 minutes (operand discovery + 3 proofs)
    - Risk: High operand count (100+ wavetables); test sample (default, saw, sine, square)

12. **Oscillator Noise Type (1 op)** ← 1 contract
    - Requires: Prove Oscillator3.kParamNoiseType writable; build noise type enum
    - Complexity: Numeric enum (5-6 types)
    - Time: ~10 minutes

13. **Oscillator Semitone Offset (2 ops)** ← Discovery + 0-1 contracts
    - Requires: **DISCOVERY** – search kParam catalog for semitone offset
      - If found: prove writable on Osc A/B → 1 contract
      - If not found: mark NO_CAPABILITY as "parameter not exposed" → 0 contracts
    - Complexity: Depends on discovery result
    - Time: ~10 minutes (discovery) + 10 minutes (if proven) = **20 minutes max**
    - Risk: May not exist; blocking both operations permanently

14. **LFO Shape (1 op)** ← Discovery + 0-1 contracts
    - Requires: **DISCOVERY** – search kParam catalog for LFO shape
      - If found: prove writable (enum: Sine, Triangle, Saw, Lorenz, etc.) → 1 contract
      - If not found: mark NO_CAPABILITY as "parameter not exposed" → 0 contracts
    - Complexity: Depends on discovery result
    - Time: ~10 minutes (discovery) + 10 minutes (if proven) = **20 minutes max**
    - Risk: May not exist; blocking operation permanently

**Phase γ Subtotal:** 6-8 operations admitted (2 ops may remain NO_CAPABILITY if discovery fails), 3-4 new contracts, **~85-105 minutes**

---

### **Phase δ: FX Hyper Unison (Unlock 1 operation, 1 new contract)**

**Goal:** Qualify FX-specific unison control; reuses FXRack0 pattern.

15. **FX Hyper Unison (1 op)** ← 1 contract (FX-slot-specific)
    - Requires: Prove FXRack0.FXHyperD.kParamUnison writable
    - Complexity: Enum voices (1,3,5,7), mirrors osc unison but in FX rack
    - Time: ~10 minutes
    - Dependency: Must follow FX-slot pattern proof (Phase β)

**Phase δ Subtotal:** 1 operation admitted, 1 new contract, **~10 minutes**

---

### **Summary: Qualification Roadmap**

| Phase | Focus | Operations | Contracts | Time | Cumulative |
|-------|-------|-----------|-----------|------|------------|
| **α** | Structural foundation + reusable generic | 13 ops | 6 | ~70 min | 13/34 ops |
| **β** | FX-slot pattern + compressor | 7 ops | 2 | ~50 min | 20/34 ops |
| **γ** | Oscillator selection + discovery | 6-8 ops | 3-4 | ~85-105 min | 26-28/34 ops |
| **δ** | FX Hyper unison | 1 op | 1 | ~10 min | 27-29/34 ops |
| **Remaining** | Discovery failures (semitone, shape, etc.) | 5-7 ops | 0 | — | **0-2 NO_CAPABILITY** |

**Total Qualification Time:** ~215–250 minutes (~4–4.5 hours)

---

## Part 5: Architectural Gaps & Safeguards

### **Gap 1: Discovery Failures → Permanent NO_CAPABILITY**

**Issue:** Oscillator semitone and LFO shape may not exist as independent parameters.  
**Risk:** If not exposed, 2–3 operations remain permanently unrepresentable.

**Safeguard:**
- Run STRUCTURAL_KEY lookup before attempting qualification
- If kParam not found, declare `UNRESOLVED_REFERENCE` (distinct from NO_CAPABILITY) and halt that family
- Document "not independently exposed in Serum 2.0.23" for future reference

**Mitigation:** Check Serum kParam catalog (qualification/serum_kparam_catalog.json) BEFORE scheduling qualification work for these families.

---

### **Gap 2: Operand Codebook Completeness**

**Issue:** Wavetable operand map must enumerate 100+ wavetables; incomplete map blocks mutations.

**Risk:** If only "default" is mapped, all other wavetable values remain INCOMPATIBLE_OPERATION.

**Safeguard:**
- Qualify wavetable operand map from Serum binary (not reference observation alone)
- Test sample: default, sine, saw, square, triangle + custom user tables
- Contract scope must list "covers all Serum wavetables" or explicitly exclude unlisted tables
- Compiler validates operand against codebook before lowering

**Mitigation:** Use serum-mcp's wavetable enumeration (if available) to build complete codebook upfront.

---

### **Gap 3: FX-Slot Pattern Generalization**

**Issue:** FXRack0.FX.1 path used for FXEQ (EPOCH_MISMATCH). New FX contracts must use same pattern or prove it's different.

**Risk:** If delay/compressor use FXRack0.FX.0 or FXRack0.FXDelay (different path), body_state bindings fail silently.

**Safeguard:**
- Prove FX-slot path experimentally (mutate FXRack0.FXDelay.kParamTimeL via serum-mcp → readback from preset body)
- Contract scope must include exact path (FXRack0.FXDelay, not FXRack0.FX.1.FXDelay)
- Compiler validates provenance.rack == 0 matches FXRack0 slot

**Mitigation:** Run Phase β delay qualification with explicit body_state path verification before rolling out to compressor.

---

### **Gap 4: Epoch Isolation for 2.0.21 Legacy Contracts**

**Issue:** 13 EPOCH_MISMATCH operations have 2.0.21 contracts; 6 FXEQ contracts have legacy binding.

**Risk:** If 2.0.21 contracts are re-enabled without re-qualification on 2.0.23, execution may fail due to Serum binary changes.

**Safeguard:**
- Do NOT re-qualify legacy 2.0.21 contracts on 2.0.23 epoch by assumption
- Each legacy contract must be re-proven on 2.0.23 (new experiment, fresh evidence)
- Registry entry must record epoch qualification was done on 2.0.23, not inherited
- Compiler rejects mismatched epoch contracts

**Mitigation:** Phases α–δ generate NEW 2.0.23 contracts; legacy 2.0.21 contracts remain frozen in registry.excluded.

---

### **Gap 5: Learning Gate – OperationEvidence vs VerifiedEpisode**

**Issue:** Newly admitted operations are eligible for OperationEvidence (operation-level learning); only when COMPLETE coverage is reached can a full VerifiedReferenceEpisode be learned.

**Risk:** Over-eagerness to learn from partial progress may publish incomplete episodes.

**Safeguard:**
- OperationEvidence: Published after each phase completion (α=13 ops, β=20 ops, etc.), advisory only
- VerifiedReferenceEpisode: ONLY when coverage_status == COMPLETE AND proof_level == LIVE_UI_VERIFIED, with reference_verified = True
- Learning contract: Must explicitly guard `if coverage < 100%: skip whole_reference_learning`

**Mitigation:** Phase δ completion triggers COMPLETE coverage check; only then does whole-reference learning unlock.

---

## Part 6: Validation Checklist

Before starting qualification work:

- [ ] Serum 2.0.23 binary is pinned in EPOCH_2_0_23
- [ ] serum-mcp is running and responsive (test with serum_mcp.describe_preset)
- [ ] Contract registry is loaded (EPOCH_2_0_23 only, no 2.0.21 fallback)
- [ ] Body_state_mapping.json has FXRack0 patterns for FXEQ (reference)
- [ ] semantic_vst3_mapping.json is up-to-date (last checked 2026-09-21)
- [ ] Serum kParam catalog is available for discovery lookups (qualification/serum_kparam_catalog.json)
- [ ] Reference reproduction run pinned to 2.0.23 epoch
- [ ] UI readback fixtures prepared for Phase α–δ verification
- [ ] Compiler validation tests in place (test_reference_boundaries.py)

---

## Conclusion

The 7 binding-gap operations and 27 NO_CAPABILITY operations form a clear qualification roadmap:

1. **7 Binding-Gap Operations** require execution binding proof (direct mutation + readback) on existing contracts. No discovery risk; deterministic qualification path.

2. **27 NO_CAPABILITY Operations** group into 7 capability families with ~11–13 contracts needed. Phases α–δ provide a sequential order that maximizes reusability, minimizes duplicate experiments, and establishes reusable patterns (FX-slot, OperatorPattern).

3. **Architectural safeguards** prevent gap-closure failures (discovery timeouts, operand incompleteness, epoch mismatches) and enforce learning gates.

**Target Outcome:**
- Phase α: 13/34 operations qualified (~70 min)
- Phase β: 20/34 operations qualified (~120 min)
- Phase γ: 26–28/34 operations qualified (~205–250 min)
- Phase δ: 27–29/34 operations qualified (~215–260 min)
- **Result:** 27–29 operations newly admitted + 9 existing = **36–38 total admitted** = **~20% reference coverage** (up from current 5.1%)

Remaining 2–7 operations marked `UNRESOLVED_REFERENCE` (discovery failures) or `NO_CAPABILITY` (architecture gaps), not execution failures.

**Next step:** Execute Phase α (Envelope Hold, Filter Enable, Osc Fine, Osc Unison, LFO Mode, LFO Mono) with fresh 2.0.23 qualification evidence.
