# Phase 3B Diagnostic: SOURCE vs SYSTEM MISMATCH ANALYSIS

## Video: 2c0h3z41K58 — "hRm - Bass Guitar" Tutorial
**Source:** Tutorial screenshots at t=170s (final preset state)  
**Date:** 2026-09-20  
**Task:** Identify exact mismatches between tutorial intent and system-generated state

---

## A. SOURCE INTENDED STATE (Tutorial Final Frame t=170s)

### Preset Metadata
| Field | Value | Status |
|-------|-------|--------|
| Preset Name | hRm - Bass Guitar * | VERIFIED_VISUAL |
| Frame ID | frame_yt_116c5b12037d_00170000 | VERIFIED_VISUAL |
| Timestamp | 170.0s | VERIFIED_VISUAL |
| UI Visible | Yes (OSC+ENV+LFO panel) | VERIFIED_VISUAL |

### Oscillators
| Control | Value | Observable? | Confidence |
|---------|-------|-------------|-----------|
| SUB.enabled | OFF | VERIFIED_VISUAL (grey dot) | 0.95 |
| OSC A.enabled | ON | VERIFIED_VISUAL (green dot) | 0.95 |
| OSC A.mode | WAVETABLE | VERIFIED_VISUAL | 0.95 |
| OSC A.wavetable | Default Shapes | VERIFIED_VISUAL | 0.9 |
| OSC A.warp_mode | REMAP 2 | VERIFIED_VISUAL | 0.9 |
| OSC A.phase | 180° | VERIFIED_VISUAL | 0.85 |
| OSC A.random_phase | 100 | VERIFIED_VISUAL | 0.8 |
| OSC A.unison | 1 | VERIFIED_VISUAL | 0.9 |
| **OSC B.enabled** | **ON** | VERIFIED_VISUAL (green dot) | **0.95** |
| **OSC B.mode** | **MULTISAMPLE** | VERIFIED_VISUAL | **0.95** |
| **OSC B.instrument_identity** | **Five String Bass** | VERIFIED_VISUAL | **0.9** |
| **OSC B.zone_identity** | **XF5String Bass 02 D#0** | VERIFIED_VISUAL | **0.85** |
| OSC B.vel_track | 100 | VERIFIED_VISUAL | 0.8 |
| OSC C.enabled | OFF | VERIFIED_VISUAL | 0.95 |
| NOISE.enabled | ON | AMBIGUOUS (hard to see toggle) | 0.7 |
| NOISE.type | elastic 1 | AMBIGUOUS (label small) | 0.7 |

### Filters
| Control | Value | Observable? | Confidence |
|---------|-------|-------------|-----------|
| Filter 1.enabled | ON | VERIFIED_VISUAL | 0.95 |
| **Filter 1.type** | **MG Low 12** | VERIFIED_VISUAL | **0.95** |
| Filter 1.cutoff | UNREADABLE | screenshot resolution | — |
| Filter 1.resonance | UNREADABLE | screenshot resolution | — |
| Filter 2.enabled | OFF | VERIFIED_VISUAL | 0.9 |

### Envelopes (visible: ENV 1 selected)
| Control | Value | Observable? | Confidence |
|---------|-------|-------------|-----------|
| ENV.selected | ENV 1 | VERIFIED_VISUAL | 0.95 |
| ENV1.attack | 1.0 ms | VERIFIED_VISUAL | 0.85 |
| ENV1.hold | 0.0 ms | VERIFIED_VISUAL | 0.85 |
| **ENV1.decay** | **5.11 s** | VERIFIED_VISUAL | **0.85** |
| ENV1.sustain | UNREADABLE | –/off symbol, not quantified | 0.6 |
| ENV1.release | UNREADABLE | screenshot cutoff | — |

### LFOs (not fully visible in frame)
| Control | Value | Observable? | Confidence |
|---------|-------|-------------|-----------|
| LFO1.rate | 4.5 Hz | TRANSCRIPT_ONLY (teaser text) | 0.7 |
| LFO other fields | UNKNOWN | panel not visible | — |

### Modulation Matrix
| Route | Observable? | Status |
|-------|-------------|--------|
| Routes visible | AMBIGUOUS | routes UI partially visible | UNKNOWN |

---

## B. GENERATED PRESET STATE (B1 BRAIN BASELINE — What System Would Create)

### Controls Attempted (from B1_BASELINE_AFTER.json)
| Event | Control | FROM | TO | B1 Intent | Terminal Status |
|-------|---------|------|----|---------|----|
| 1 | oscA.warp_mode | OFF | REMAP 2 | ATTEMPTED | REFUSED_NO_BRAIN_CONCEPT |
| 2 | env2.decay | 1.00s | 1.77s | ATTEMPTED | REFUSED_NO_CAPABILITY |
| 2 | env2.sustain | 100% | – | ATTEMPTED | REFUSED_NO_CAPABILITY |
| **2** | **oscB.enabled** | **OFF** | **ON** | **toggle_on** | **REFUSED_NO_CAPABILITY** |
| 2 | oscB.mode | WAVETABLE | MULTISAMPLE | NOT_EXECUTED | (blocked by oscB.enabled refusal) |
| 4 | lfo1.rate | 1/4 BPM | 4.5 Hz | ATTEMPTED | REFUSED_NO_CAPABILITY |
| 5 | filter1.enabled | OFF | ON | ATTEMPTED | REFUSED_NO_CAPABILITY |

### Current Capability Status (as of Phase 3B.4)
| Capability | Status | Tier |
|------------|--------|------|
| oscillator_field_OSC2-ENABLE | ✅ QUALIFIED | UI_VERIFIED (Phase 3B.4) |
| envelope2_field_decay | ❌ MISSING | — |
| envelope2_field_sustain | ❌ MISSING | — |
| lfo_field_lfo1_rate | ❌ MISSING | — |
| filter_field_ENABLE | ❌ MISSING | — |

---

## C. ACTUAL SERUM UI STATE (Phase 3B.4 Live Verification)

### From VLP1-Phase3B-OSC2Enable-Test Fixture (t=0s, just loaded)
| Control | Value | Source |
|---------|-------|--------|
| **OSC B.enabled** | **OFF** (grey dot) | LIVE_UI_SCREENSHOT |
| OSC A.enabled | ON (green dot) | LIVE_UI_SCREENSHOT |
| Preset Name | VLP1-Phase3B-OSC2Enable-Test | LIVE_UI_OBSERVATION |

**NOTE:** This fixture is a STRUCTURAL TEST for OSC B Enable only, not the full tutorial preset.

---

## D. FIELD-BY-FIELD COMPARISON: Tutorial Intent vs B1 Baseline

### CRITICAL MISMATCH ZONE: oscB Control

#### oscB.enabled (OSC2.Enable capability)
| Layer | Tutorial Intent | B1 System Intent | Status |
|-------|-----------------|-----------------|--------|
| **Tutorial Screenshot** | **ON** (green dot visible) | — | SOURCE_VERIFIED |
| **B1 Baseline Attempt** | — | **OFF → ON** (toggle_on) | B1_WOULD_ATTEMPT |
| **Actual Generated Preset** | N/A (not executed) | REFUSED_NO_CAPABILITY | BLOCKED |
| **Phase 3B.4 Fixture** | **OFF** (deliberate test) | — | STRUCTURALLY_VERIFIED |
| **MATCH?** | ✅ B1 matches tutorial intent (both say ON) | — | **ALIGNED** |

#### oscB.mode
| Layer | Tutorial Intent | B1 Capability | Status |
|-------|-----------------|---------------|--------|
| **Tutorial Screenshot** | **MULTISAMPLE** | — | VERIFIED_VISUAL |
| **B1 Baseline Attempt** | — | BLOCKED_by_oscB.enabled_refusal | CHAIN_BLOCKED |
| **Capability Status** | — | NO_BRAIN_CONCEPT | NOT_IMPLEMENTED |

#### oscB.instrument_identity (Five String Bass)
| Layer | Tutorial Intent | B1 Capability | Status |
|-------|-----------------|---------------|--------|
| **Tutorial Screenshot** | **XF5String Bass 02 D#0** | — | VERIFIED_VISUAL |
| **B1 Baseline Attempt** | — | NO_BRAIN_CONCEPT | NOT_IMPLEMENTED |
| **Dependency** | Requires oscB.mode = MULTISAMPLE first | — | CHAIN_DEPENDENCY |

---

## E. ROOT CAUSE FOR EACH REAL MISMATCH

### Issue 1: oscB.enabled — Capability JUST NOW Qualified (Phase 3B.4)
- **Mismatch Type:** TEMPORAL_GAP
- **Tutorial Intent:** oscB.enabled = ON
- **B1 System Intent:** OFF → ON (toggle_on)
- **Actual Status:** REFUSED_NO_CAPABILITY (B1 baseline made before Phase 3B.4 qualification)
- **Current Status:** CAPABILITY NOW EXISTS (oscillator_field_OSC2-ENABLE, UI_VERIFIED)
- **Resolution:** Re-run B1 baseline with new capability; should now EXECUTE

### Issue 2: oscB.mode — No Brain Concept
- **Mismatch Type:** MISSING_BRAIN_LOGIC
- **Tutorial Intent:** oscB.mode = WAVETABLE → MULTISAMPLE
- **B1 System Intent:** NOT_ATTEMPTED (blocked by oscB.enabled refusal)
- **Failure Class:** F. Operation-direction error (wrong mode selection semantics)
- **Root Cause:** Producer brain has no concept for "select instrument mode" or "switch MULTISAMPLE"
- **Code Location:** serum2/producer/producer_brain.py — missing mode_selection concept

### Issue 3: oscB.instrument_identity — No Brain Concept
- **Mismatch Type:** MISSING_BRAIN_LOGIC + CHAIN_DEPENDENCY
- **Tutorial Intent:** Set to "Five String Bass"
- **B1 System Intent:** NOT_ATTEMPTED
- **Failure Class:** H. Capability missing (instrument selection not a standalone operation)
- **Root Cause:** Only possible AFTER oscB.mode = MULTISAMPLE; no brain concept for instrument selection
- **Code Location:** serum2/producer/producer_brain.py — missing instrument_selector concept

### Issue 4: env2.decay — Capability Missing but B1 Would Attempt
- **Mismatch Type:** MISSING_CAPABILITY_CONTRACT
- **Tutorial Intent:** ?1.0s → 1.77s (from ENVELOPE_1, not ENV2 — possible mislabeling)
- **B1 System Intent:** numeric_set from 1.00s to 1.77s
- **Actual Status:** REFUSED_NO_CAPABILITY
- **Failure Class:** C. Wrong structural binding (may be ENV1.decay, not ENV2.decay)
- **Evidence Issue:** Screenshot shows "ENV1" selected; value shows ENV1.decay = 5.11s

### Issue 5: env2.sustain — Completely Unobservable
- **Mismatch Type:** EVIDENCE_INSUFFICIENT
- **Tutorial Intent:** UNKNOWN (unreadable in screenshot; shown as –)
- **B1 System Intent:** numeric_set (exact value unknown)
- **Actual Status:** REFUSED_NO_CAPABILITY + UNREADABLE_VALUE
- **Failure Class:** I. Evidence insufficient / screenshot unreadable

### Issue 6: lfo1.rate — Capability Missing
- **Mismatch Type:** MISSING_CAPABILITY_CONTRACT
- **Tutorial Intent:** 1/4 BPM → 4.5 Hz (from transcript; rate change observed at t=60-90s)
- **B1 System Intent:** numeric_set from "1/4 BPM" to "4.5 Hz"
- **Actual Status:** REFUSED_NO_CAPABILITY
- **Failure Class:** E. Value/unit conversion error (BPM vs Hz unit mismatch?)
- **Evidence Issue:** Transcript says "4.5 Hz" but B1 shows "1/4 BPM" as source unit

### Issue 7: filter1.enabled — Capability Missing
- **Mismatch Type:** MISSING_CAPABILITY_CONTRACT
- **Tutorial Intent:** OFF → ON (toggle)
- **B1 System Intent:** toggle operation
- **Actual Status:** REFUSED_NO_CAPABILITY
- **Failure Class:** H. Capability missing (filter_field_ENABLE contract not yet written)
- **Code Location:** serum2/evidence/filter_capability.py (does not exist)

---

## F. ITEMS THAT CANNOT BE DETERMINED FROM EVIDENCE

| Item | Why Unknown | Impact |
|------|------------|--------|
| filter.cutoff actual value | Screenshot resolution too low | Affects filter routing resolution |
| filter.resonance actual value | Screenshot resolution too low | Affects filter tone character |
| ENV1.sustain numeric value | Shown as "–" symbol only | Envelope shape incomplete |
| ENV1.release value | Visible panel cutoff | Unknown envelope tail behavior |
| LFO1.smooth value | Panel not visible in final frame | LFO rate ramping behavior unknown |
| Modulation matrix routes | Routes UI partially clipped | Cannot determine routing chain |
| Exact LFO1 rate unit | Transcript says "4.5 Hz"; B1 says "1/4 BPM start" | Unit conversion mismatch |

---

## G. EXACT CODE/DATA LOCATIONS TO INVESTIGATE NEXT

### 1. **oscB.mode Selection — Missing Brain Concept**
**Location:** `serum2/producer/producer_brain.py`
**Query:** Search for "oscB.mode" or "instrument.mode" handling
**Issue:** No Producer concept for "set oscillator to MULTISAMPLE mode"
**Fix Needed:** Add mode_selection concept that maps UI "MULTISAMPLE"/"WAVETABLE" to underlying operation

### 2. **oscB.instrument_identity — Missing Brain Concept**
**Location:** `serum2/producer/producer_brain.py`
**Query:** Search for "instrument_identity" or "instrument_selector"
**Issue:** No Producer concept for "select instrument from loaded set"
**Fix Needed:** Chain concept that requires oscB.mode=MULTISAMPLE first, then selects instrument

### 3. **env2.decay vs env1.decay Confusion**
**Location:** `serum2/data/runs/2c0h3z41K58/stage_a_observation.json` (line 2, event 2)
**Query:** Check if "env2.decay" label is correct or should be "env1.decay"
**Evidence:** Tutorial frame shows "ENV1" selected, decay = 5.11s. But control_id says "env2.decay"
**Mismatch:** env2 was not selected; only ENV1 visible

### 4. **lfo1.rate — Unit Conversion Error**
**Location:** `serum2/producer/batch_qualification_system.py` (RouteType matching)
**Query:** How is "1/4 BPM" converted to "4.5 Hz"?
**Issue:** B1 baseline shows source as "1/4 BPM", target as "4.5 Hz" — different unit systems
**Investigation:** Does TargetResolver have unit-conversion logic for BPM↔Hz?

### 5. **filter1.enabled Capability — Completely Missing**
**Location:** `serum2/evidence/` (no filter_enable_contract.py exists)
**Query:** grep for "filter.*enable\|field_ENABLE" across evidence layers
**Issue:** No capability contract exists for filter enable toggle
**Path to Fix:** Require binding discovery for filter enable (VST3 parameter or body-state path)

### 6. **oscB.enabled State Mismatch in Baseline vs Tutorial**
**Location:** `docs/b1_measurement/B1_BASELINE_AFTER.json` (line 65-75)
**Query:** Verify that B1 correctly marked oscB.enabled as "OFF → ON"
**Evidence Check:** Tutorial clearly shows OSC B green dot (ON); B1 says toggle to ON — this is CORRECT
**Status:** No mismatch here; B1 intent aligns with tutorial

---

## SUMMARY: What is Actually Wrong?

### Correctly Identified
1. ✅ **oscB.enabled:** B1 intent (toggle ON) matches tutorial visual (ON). Now qualified as capability.
2. ✅ **filter1.enabled:** B1 intent (toggle ON) matches tutorial visual (ON). Capability missing, not matching error.

### Misaligned Between Tutorial and B1
1. **env2.decay control ID:** Tutorial shows ENV1.decay, not ENV2.decay. Possible mislabeling in stage_a_observation.json.
2. **lfo1.rate unit system:** B1 shows "1/4 BPM" as source, "4.5 Hz" as target. Conversion logic unclear.

### Missing Entirely (Not Tutorial Error, System Limitation)
1. **oscB.mode selection:** No brain concept; cannot switch MULTISAMPLE/WAVETABLE
2. **oscB.instrument_identity:** No brain concept; cannot select loaded instrument
3. **env2.sustain:** Unobservable in screenshot; cannot verify

### Capability Contracts Missing
1. **envelope2_field_decay:** Contract missing; blocking event 2
2. **envelope2_field_sustain:** Contract missing; blocking event 2
3. **lfo_field_lfo1_rate:** Contract missing; blocking event 4
4. **filter_field_ENABLE:** Contract missing; blocking event 5

