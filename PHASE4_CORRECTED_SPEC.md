# PHASE 4: 16-BAR PRODUCTION — CORRECTED SPECIFICATION

**Status:** REVISED FOR ACCURACY  
**Date:** 2026-09-18

---

## CRITICAL CORRECTIONS

### 1. Track Model
**MIDI Instrument Track with Serum VST3** (not audio track)

```
Ableton Session
  └── Track 1: MIDI Instrument
       ├── Device: Serum VST3
       └── MIDI Clip: C3 note (bars 1-16)
```

AbletonMCP operations:
- `create_midi_track()` → creates MIDI track
- `load_instrument_or_effect()` → loads Serum into track
- `create_clip()` → creates MIDI clip
- `add_notes_to_clip()` → inserts C3 note

### 2. Mutation Count: FOUR, Not Five
**Corrected to exactly 4 admitted mutations:**

| Bar | Target | Contract | Mechanism | Value Before | Value After |
|---|---|---|---|---|---|
| 5 | Env1.Attack | CAUSAL_VERIFIED | HOST_PARAMETER (MCP) | 0.10 | 0.30 |
| 9 | Filter.Cutoff | CAUSAL_VERIFIED | HOST_PARAMETER (MCP) | 0.50 | 0.65 |
| 12 | FXEQ.Freq1 | CAUSAL_VERIFIED | BODY_STATE (pathmerge) | 639.84 Hz | 1200.0 Hz |
| 14 | Filter.Resonance | CAUSAL_VERIFIED | HOST_PARAMETER (MCP) | 0.10 | 0.35 |

No fifth mutation added.

### 3. Execution Mechanism Clarity

**AbletonMCP Role:** Arrange session structure, time Serum mutations

**Phase-3 Mechanisms (Authoritative):**
- HOST_PARAMETER targets: Use existing DawDreamer MCP bridge
- BODY_STATE targets: Use existing pathmerge + FXEQ fixture

```
Env1.Attack
  Contract: CAUSAL_VERIFIED (Phase 3)
  Mechanism: HOST_PARAMETER via MCP host parameter #12
  AbletonMCP role: Schedule mutation at bar 5
  Ableton representation: Parameter change event (not automation)

Filter.Cutoff
  Contract: CAUSAL_VERIFIED (Phase 3)
  Mechanism: HOST_PARAMETER via MCP host parameter #11
  AbletonMCP role: Schedule mutation at bar 9
  Ableton representation: Parameter change event

FXEQ.Freq1
  Contract: CAUSAL_VERIFIED (Phase 3)
  Mechanism: BODY_STATE via pathmerge (Phase 3 fixture)
  AbletonMCP role: Provide Serum instance context at bar 12
  Ableton representation: Serum state change event
  Fixture requirement: corpus_cache.pkl bodies[4] with FXEQ pre-loaded

Filter.Resonance
  Contract: CAUSAL_VERIFIED (Phase 3)
  Mechanism: HOST_PARAMETER via MCP host parameter #75
  AbletonMCP role: Schedule mutation at bar 14
  Ableton representation: Parameter change event
```

### 4. FXEQ Fixture Requirement

**Before FXEQ.Freq1 mutation at bar 12:**

Serum instance must have:
```
FXRack0.FX[1].FXEQ.plainParams.kParamFreq1 = 639.84 Hz
```

**How fixture is obtained:**
- Load Serum with corpus_cache.pkl bodies[4] (established Phase 3 fixture)
- Verify FXRack0.FX[1] exists and contains FXEQ
- If fixture unavailable: STOP and report missing context
- Do NOT create new FXEQ initialization

**Verification before mutation:**
```python
baseline = pathmerge.read_path_value(serum_body, 
  "FXRack0.FX.1.FXEQ.plainParams.kParamFreq1")
assert baseline == 639.84, f"FXEQ not loaded: got {baseline}"
```

### 5. Temporal Mutations: Exact Representation

**How bar-based mutations are represented in Ableton:**

Each mutation is a **parameter state-change event**, not continuous automation.

```
Bar 5, Beat 1:
  Event: SetParameter(Env1.Attack, 0.30)
  Representation: Recorded in evidence log with timestamp
  Ableton internals: May use parameter change clips or direct set

Bar 9, Beat 1:
  Event: SetParameter(Filter.Cutoff, 0.65)
  Representation: Recorded in evidence log with timestamp

Bar 12, Beat 1:
  Event: ApplyBODYSTATEMutation(FXEQ.Freq1, 1200.0)
  Representation: Recorded in evidence log + Serum state snapshot

Bar 14, Beat 1:
  Event: SetParameter(Filter.Resonance, 0.35)
  Representation: Recorded in evidence log with timestamp
```

**Verification in rendered audio:**
- Spectral content must show discontinuities at bar boundaries
- RMS envelope must show step changes at mutation points
- No gradual automation transitions (only state changes)

### 6. Replay Requirement: Defined Tolerances

**Same across runs:**
- Musical intent (C3 pad)
- Specification (16 bars, 4 mutations)
- Contract selection (same 4 CAUSAL_VERIFIED)
- Execution mechanism (same MCP/pathmerge)
- MIDI content (C3, bars 1-16)
- Mutation schedule (bars 5/9/12/14)

**Within defined tolerance:**
- Duration: ±0.1 seconds (target: 32.0 ± 0.1 sec)
- BPM deviation: ±1 BPM (target: 120 ± 1)
- Parameter values: ±1 unit (e.g., Freq1 1200 ± 1 Hz)
- RMS difference: ±3 dB (tolerance for measurement variance)

**Record differences explicitly:**
- Log all parameters and measurements with timestamps
- Note any environmental variations (Serum version, audio driver, etc.)
- Do NOT hide or ignore differences

---

## AUTHORITATIVE EXECUTION TABLE

| Bar | Target | Contract Status | Mechanism | Ableton Representation | Before | After | Verification |
|---|---|---|---|---|---|---|---|
| 1-4 | (baseline) | — | — | No events | C3 pad plays | Unchanged | Audio spec |
| 5 | Env1.Attack | CAUSAL_VERIFIED | HOST_PARAMETER #12 | Parameter event | 0.10 | 0.30 | MCP readback + audio envelope |
| 9 | Filter.Cutoff | CAUSAL_VERIFIED | HOST_PARAMETER #11 | Parameter event | 0.50 | 0.65 | MCP readback + spectral analysis |
| 12 | FXEQ.Freq1 | CAUSAL_VERIFIED | BODY_STATE pathmerge | State change event | 639.84 Hz | 1200.0 Hz | pathmerge read + audio spectrum |
| 14 | Filter.Resonance | CAUSAL_VERIFIED | HOST_PARAMETER #75 | Parameter event | 0.10 | 0.35 | MCP readback + resonance peak |
| 16+ | (restoration) | — | — | No events | State held | Held | Final audio sample |

---

## SESSION STRUCTURE

### Ableton Session

```
Session: Phase 4 Production
├── BPM: 120
├── Time Signature: 4/4
├── Sample Rate: 44.1 kHz
├── Duration: 16 bars (32.0 seconds)
├── Master Volume: 0 dB
└── Track 1: Serum Pad
    ├── Type: MIDI Instrument
    ├── Device: Serum VST3
    ├── MIDI Clip: "Phase4_Pad"
    │   ├── Start: Bar 1
    │   ├── End: Bar 16
    │   └── Note: C3 (60), Velocity 100, Full duration
    └── Parameter Events (recorded in evidence log)
        ├── Bar 5: Env1.Attack 0.10 → 0.30
        ├── Bar 9: Filter.Cutoff 0.50 → 0.65
        ├── Bar 12: FXEQ.Freq1 639.84 → 1200.0 Hz
        └── Bar 14: Filter.Resonance 0.10 → 0.35
```

### MIDI Specification

**Single MIDI Clip:**
- Name: "Phase4_Pad"
- Track: Serum Pad (MIDI instrument)
- Start Time: 1:1:0 (bar 1, beat 1)
- Duration: 16 bars (32.0 beats at 120 BPM = 32 seconds)

**MIDI Content:**
```
Note-on:  C3 (pitch 60), velocity 100
Start:    Bar 1, Beat 1 (time 0.0)
Duration: 16 bars (32 seconds at 120 BPM)
End:      Bar 16, Beat 4 (time 32.0 seconds)
```

### Serum Fixture Requirement

**For FXEQ.Freq1 mutation at bar 12:**

Serum instance initialization:
1. Start with default Serum skeleton
2. Before bar 12: Load/merge FXEQ state from corpus_cache.pkl bodies[4]
3. Verify: `FXRack0.FX[1].EQEQ.plainParams.kParamFreq1 == 639.84`
4. Proceed with mutation

**If fixture unavailable:**
- STOP before bar 12
- Report: "FXEQ fixture not available; cannot apply FXEQ.Freq1 mutation"
- Do NOT attempt blind path mutation

---

## RENDER SPECIFICATION

### Render Configuration

- **Duration:** 16 bars (exactly 32.0 seconds at 120 BPM)
- **Format:** WAV (RIFF uncompressed)
- **Sample Rate:** 44.1 kHz
- **Channels:** Stereo (2 channels)
- **Bit Depth:** 16-bit (or higher)
- **Output:** experiments/phase4_render.wav

### Render Verification

**Before accepting render:**
1. ✓ File exists
2. ✓ Duration: 32.0 ± 0.1 seconds
3. ✓ Sample rate: 44.1 kHz
4. ✓ Channels: 2 (stereo)
5. ✓ Samples are finite (no NaN/Inf)
6. ✓ RMS > -60 dB (not silent/clipped)
7. ✓ Peak level < 0 dBFS (no clipping)

---

## AUDIO MEASUREMENTS

### Measurement Plan

Each measurement captures state at specific musical time points.

| Bar | Measurement | Expected | Verification Method |
|---|---|---|---|
| 1-4 | Baseline spectral content | Defined Serum tone | FFT analysis, RMS envelope |
| 5 | Env1.Attack effect | Attack slope change | RMS envelope slope |
| 9 | Filter.Cutoff effect | Spectral brightness increase | FFT/centroid analysis |
| 12 | FXEQ.Freq1 effect | Mid-low frequency boost | Targeted frequency bin analysis |
| 14 | Filter.Resonance effect | Resonance peak at cutoff | Q-factor/peak analysis |

### Measurement Metrics

**RMS/Loudness Envelope:**
- Window size: 2048 samples (46.4 ms)
- Hop size: 512 samples (11.6 ms)
- Expected: Smooth rise at bar 5 (attack), step increases at bars 9/12/14

**Spectral Content (FFT):**
- FFT size: 4096 samples
- Window: Hann
- Measurement points: Bars 1, 5, 9, 12, 14, 16
- Expected: Spectral centroid shifts at mutation points

**Peak/RMS:**
- Expected: -15 dB to -12 dB (comfortable headroom)
- No clipping (< 0 dBFS)

---

## REPLAY REQUIREMENT

### Reproducibility Test

**Clean replay from scratch:**

1. Start with Phase 4 spec only (no prior state)
2. Execute same steps:
   - Create session (120 BPM, 4/4, C major)
   - Load Serum instance
   - Load FXEQ fixture (if needed for FXEQ.Freq1)
   - Create MIDI clip with C3 note
   - Apply 4 mutations at scheduled bars
3. Render to new audio file
4. Compare measurements

**Allowed differences:**
- Duration: ±0.1 seconds
- RMS values: ±3 dB
- Spectral measurements: ±2% frequency error
- Timestamps: ±11.6 ms (one FFT hop)

**Required identities:**
- Same contracts used
- Same mechanisms used
- Same MIDI content
- Same parameter values
- Same bar schedule

**Failure criterion:**
If FXEQ.Freq1 fixture is unavailable on second run, that is documented as an environmental issue, not a pipeline failure.

---

## PHASE 4 EXIT GATE

Implementation proceeds only after all conditions are met:

1. ✓ Track structure: MIDI instrument track (not audio)
2. ✓ Serum instance: Loads successfully
3. ✓ MIDI content: C3 note present for bars 1-16
4. ✓ Mutation count: Exactly 4 (Env1.Attack, Filter.Cutoff, FXEQ.Freq1, Filter.Resonance)
5. ✓ Mutation mechanism: Uses Phase-3 contracts + authorized execution paths
6. ✓ FXEQ fixture: Corpus fixture available or mutation skipped with documentation
7. ✓ Render: Succeeds, 32 seconds, 44.1 kHz stereo
8. ✓ Audio valid: Finite samples, RMS > -60 dB, no clipping
9. ✓ Measurements: Recorded for all mutation points
10. ✓ Replay: Clean re-execution succeeds

**No modifications to Phase 1-3 artifacts.**

---

## NEXT ACTION

Proceed to STEP 3: Build Ableton arrangement (if specification approved).

Implementation requires:
1. Ableton session creation via MCP
2. Serum VST3 loading
3. MIDI clip generation
4. Parameter mutation scheduling
5. Render execution
6. Measurement and evidence capture
