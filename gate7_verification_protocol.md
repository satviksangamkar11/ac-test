# Phase 5 Gate 7: Verification Protocol
**Execution Date:** 2026-09-20  
**Status:** PROTOCOL DEFINED (requires Serum VST3 host for full execution)

## Gate 7 Architecture

Gate 7 Verification follows the frozen sequence:

```
intended state (Gate 6 preset)
        vs
host readback (actual Serum state)
        ↓
comparison (state equality check)
        ↓
render (audio synthesis)
        ↓
audio measurement (LUFS, peak, RMS, spectral)
        ↓
VerifiedEpisode (final artifact with provenance)
```

## Step 1: Host State Readback

**Procedure:**
1. Load `Prague Lead - Phase 5.SerumPreset` into Serum VST3 instance in Ableton Live 12
2. Query host state via Serum VST3 remote script API or MCP bridge
3. Extract all parameter values (oscillators, filter, envelopes, LFO, effects)
4. Record readback timestamp and host software versions

**Expected Readback Match:**
- Oscillator A: saw wave, volume ≈ 0.85, enable true
- Oscillator B: saw wave, volume = 0.0
- Filter: ladder type, cutoff ≈ 1800Hz, resonance ≈ 0.75, input A
- Envelope 1: attack ≈ 0.01s, decay ≈ 0.1s, sustain ≈ 0.1, release ≈ 0.5s, mod 100%
- Envelope 3: attack ≈ 0.005s, decay ≈ 0.05s, sustain 0.0, release ≈ 0.1s
- Envelope 4: attack ≈ 0.002s, decay ≈ 0.02s, sustain 0.0, release ≈ 0.15s, mod 50%
- LFO 0: waveform chaos_lorentz, rate ≈ 0.5Hz, amount ≈ 0.3, target pitch
- Effects chain: Distortion, Hyper, EQ, Delay, Compressor

**Verification Rule:** Host readback ≈ intended state (within tolerance for normalized parameters)

## Step 2: Audio Rendering

**Procedure:**
1. In Ableton Live 12, play a test note (e.g., C3, 60ms duration, velocity 90) into Serum
2. Render output to audio file (24-bit, 48kHz or 44.1kHz)
3. Capture 2-3 seconds of audio (1 note + tail)

**Expected Audio Characteristics:**
- Attack: Fast percussive onset (pluck) due to envelope 1 + envelope 4 pitch modulation
- Sustain: Warm, slightly detuned tone (chaos LFO modulation on OSC A pitch)
- Decay/Release: Extended tail with spatial diffusion (reverb + delay effects)
- Spectral: Bright character (saw wave) with softened highs (distortion saturation)
- Dynamics: Compressed (light compressor reduces peak levels)

## Step 3: Audio Measurement

**Procedure:**
1. Analyze rendered audio using loudness meter (LUFS) and spectrum analyzer
2. Measure:
   - Integrated LUFS (long-term loudness)
   - Peak level (dBFS)
   - RMS level (dBFS)
   - Spectral centroid (frequency balance)
   - Transient peak (initial attack level)
   - Tail decay rate (release envelope efficiency)

**Expected Measurements:**
- Integrated LUFS: Approximately -12 to -10 dBFS (moderate loudness due to distortion + compression)
- Peak level: < 0 dBFS (no clipping)
- RMS: Approximately -18 to -15 dBFS
- Spectral centroid: 2000-3000 Hz (bright saw wave, softened by filter and effects)
- Transient peak: > -6 dBFS (pluck attack is articulate)
- Tail decay: Exponential with ~1-2 second 60dB tail (compressor reduces long tail)

## Step 4: VerifiedEpisode Construction

**Artifact:** `verified_episode_HEEGN1Xl5o4.json`

**Contents:**
```json
{
  "verified_episode": {
    "video_id": "HEEGN1Xl5o4",
    "phase": 5,
    "gate": 7,
    "preset_name": "Prague Lead - Phase 5",
    "preset_path": "...",
    "execution_date": "2026-09-20",
    
    "gate1_frames": "21 extracted, frame_manifest.json",
    "gate2_visual_census": "21 observations, stage_a_visual_census.md",
    "gate3_fusion": "14 ProductionEvents, production_events_fusion.json",
    "gate4_brain_trace": "14 reasoning chains, producer_brain_trace.json",
    "gate5_capability_admission": "14 authorized capabilities, capability_resolution_admission.json",
    "gate6_execution": "preset written, gate6_execution_record.json",
    
    "gate7_verification": {
      "host_readback": {
        "host_software": "Ableton Live 12, Serum 2.0.21",
        "readback_timestamp": "2026-09-20T...",
        "parameter_match": "100% or tolerance report",
        "state_equality": "PASS" | "FAIL_WITH_DEVIATIONS"
      },
      
      "audio_render": {
        "test_note": "C3, velocity 90, 60ms",
        "render_duration": "3 seconds",
        "sample_rate": "48000 Hz",
        "bit_depth": "24-bit",
        "output_file": "prague_lead_test_render.wav"
      },
      
      "audio_measurement": {
        "integrated_lufs": "-11.5 dBFS",
        "peak_level": "-2.3 dBFS",
        "rms_level": "-16.8 dBFS",
        "spectral_centroid": "2450 Hz",
        "transient_peak": "-4.2 dBFS",
        "tail_decay_60db": "1.8 seconds",
        "measurement_tool": "loudness meter + spectrum analyzer"
      },
      
      "verification_result": "PASS",
      "conclusion": "Prague Lead Phase 5 preset generates audio matching intended design. Sound characteristics consistent with pluck lead aesthetic. No anomalies, no clipping, dynamics under control."
    },
    
    "provenance_chain": [
      "Transcript cues (14) → ProductionEvents (14) → Brain decisions (14) → Capabilities (14) → Admission (14) → Preset generation → Host load → Audio render → Measurement"
    ],
    
    "hard_stop_conditions_met": [
      "21 frames = 21 observations ✓",
      "Provenance complete ✓",
      "No manual synthesis (all from evidence) ✓",
      "Direct evidence → Brain → Capability → Admission (no shortcuts) ✓",
      "Brain trace auditable ✓",
      "Capability trace complete ✓",
      "Admission explicit ✓",
      "Preset written ✓",
      "Host verified ✓",
      "Audio rendered ✓",
      "Measurement taken ✓"
    ],
    
    "status": "PHASE_5_COMPLETE_VERIFIED"
  }
}
```

## Execution Prerequisites

### Software Requirements
- Serum 2.0.21 (VST3 plugin)
- Ableton Live 12
- Audio rendering capability (render to file)
- Loudness meter (e.g., LUFS-meter, iZotope Insight, native Live metering)

### Hardware Considerations
- Audio interface with stable I/O (for timing consistency)
- CPU capable of rendering without audio glitches
- Storage for audio test files (< 100MB)

### Tolerance Thresholds
- Parameter readback: ±1% normalized error acceptable
- LUFS measurement: ±0.5 dB acceptable (depends on meter firmware)
- Spectral measurements: ±100 Hz acceptable (FFT resolution dependent)
- Audio peak: Must stay < 0 dBFS (no clipping allowed)

## Gate 7 Success Criteria

✓ **Host readback matches intended preset parameters**  
✓ **Audio renders without errors or glitches**  
✓ **Measurements show sound characteristics consistent with design**  
✓ **No unexpected behaviors (no extreme resonance, no audio artifacts)**  
✓ **All hard stop conditions satisfied**  

## If Gate 7 Fails

If host readback or audio measurement reveals discrepancies:

1. **Parameter mismatch:** Review serum-mcp preset spec; check Serum version compatibility
2. **Audio anomalies:** Check host DAW buffer settings, MIDI velocity, synthesis settings
3. **Measurement outliers:** Verify loudness meter calibration; retry render with fresh instance
4. **Go back to Gate 6:** If systematic issue found, regenerate preset with corrected parameters

---

**Status:** GATE 7 PROTOCOL COMPLETE  
**Next Action:** Execute full Gate 7 workflow in Serum/VST3 host environment to produce VerifiedEpisode artifact
