# Critical Path Seam Fixes — Fastest Route to Product Closure

**Branch:** `claude/gallant-cerf-u953wn @ a02a8dc`  
**Date:** 2026-09-27  
**Objective:** Fix the 4 blocking seams in the one-command pipeline runner, then execute:  
`Gate B rerun → fresh W2 observation → native reference verification → 16-bar Ableton → product closure`

---

## Why This Path is Fastest

**NOT the family-grouping strategy** (that would prove ~20 more controls, taking 4–8 weeks).

**The actual blocker is not "need to prove controls."** The current codebase already has:
- ✅ 330-control execution evidence (MCP characterization)
- ✅ 10 controls proven executable + admitted
- ✅ Capability contracts + ledger + compiler
- ✅ Universal observation pipeline (Phase 1)
- ✅ Authority chain fixed (Gate A-core)

**The blocker is:** the runner has 4 integration seams that stop it from completing end-to-end on real data.

**Fixing those 4 seams** (2–4 weeks) opens the canonical product path without additional control qualification.

---

## Seam S1: REFERENCE_VERIFY — Generate Reread Log

**File:** `serum2/pipeline/runner.py:737–803`  
**Problem:** Line 785 passes `reread_log_path=None`, but line 93 of `reference_reproduction.py` does:
```python
reread = json.loads(Path(reread_log_path).read_text(encoding="utf-8"))
```

This crashes with `TypeError: 'NoneType' object has no attribute read_text` or AttributeError.

**Fix:** Before calling `run_reference_reproduction()`, the REFERENCE_VERIFY stage must generate an actual `reread_log.json` containing the native Serum module re-save state.

### Required structure for reread_log.json

```json
{
  "manifest": {
    "run_id": "<from NATIVE_VERIFY.run_id_native>",
    "epoch": "Serum 2.0.23",
    "serum_module_sha256": "<from NATIVE_VERIFY.serum_module_sha256>"
  },
  "control_readbacks": [
    {
      "atlas_id": "env2.decay",
      "observed_value": 123.45,
      "display_value": "123 ms",
      "source": "native_ui_screenshot",
      "screenshot_hash": "<from NATIVE_VERIFY.screenshot_hash>",
      "confidence": 0.95
    }
  ],
  "preset_sha256": "<from NATIVE_LOAD.compiled_preset_sha>",
  "native_resave_sha256": "<from NATIVE_VERIFY.native_resave_sha>",
  "analysis_timestamp": "2026-09-27T...",
  "analysis_status": "COMPLETE"
}
```

### Implementation steps

**Step S1.1: Collect native readback from NATIVE_VERIFY outputs**

The NATIVE_VERIFY stage (which runs on LOCAL Windows) must already output:
```python
NATIVE_VERIFY.outputs = {
    "run_id_native": "...",
    "serum_module_sha256": "...",
    "screenshot_hash": "...",
    "screenshot_path": "...",
    "native_resave_sha": "...",
    "control_readbacks": [
        {"atlas_id": "env2.decay", "value": 123.45, ...},
        ...
    ],
}
```

**Step S1.2: REFERENCE_VERIFY generates reread_log.json**

In `_stage_reference_verify()`, after line 770, before calling `run_reference_reproduction()`:

```python
# Generate reread_log.json from NATIVE_VERIFY outputs
reread_log = {
    "manifest": {
        "run_id": nv.get("run_id_native"),
        "epoch": "Serum 2.0.23",
        "serum_module_sha256": nv.get("serum_module_sha256"),
    },
    "control_readbacks": nv.get("control_readbacks", []),
    "preset_sha256": nv.get("compiled_preset_sha"),
    "native_resave_sha256": nv.get("native_resave_sha"),
    "analysis_timestamp": datetime.now().isoformat(),
}

reread_log_path = run_dir / "reread_log.json"
with open(reread_log_path, "w") as fh:
    json.dump(reread_log, fh, indent=2)

# Now call reference_reproduction with the actual path
run = run_reference_reproduction(
    stage_a_path=str(stage_a_path),
    reread_log_path=str(reread_log_path),  # ← FIXED
    source={"url": manifest.source_url},
    ...
)
```

**Step S1.3: Update NATIVE_VERIFY to populate control_readbacks**

Ensure the NATIVE_VERIFY stage actually extracts observed values from the native screenshot/UI readback, not just collecting hashes.

---

## Seam S2: ARRANGEMENT — Implement or Fallback

**File:** `serum2/pipeline/runner.py:806–847`  
**Problem:** Line 828 imports `from serum2.ableton.arrangement import create_16bar_arrangement` — the module does **not** exist.

The stage fails immediately with `ModuleNotFoundError`.

**Fix:** Either implement the module or provide a AWAITING_NATIVE_ENVIRONMENT fallback that explains the manual step.

### Option A: Implement create_16bar_arrangement (Preferred)

**File to create:** `serum2/ableton/arrangement.py`

```python
"""Create a 16-bar MIDI arrangement in Ableton Live (MCP-driven or manual guide)."""

def create_16bar_arrangement(track_id: str, run_dir: str) -> dict:
    """
    Create a 16-bar MIDI arrangement in the Serum track.
    
    This is a LOCAL-only stage that requires actual Ableton + serum-mcp running.
    On cloud, it marks AWAITING_NATIVE_ENVIRONMENT.
    
    Args:
        track_id: Ableton track ID or name (e.g., "Serum Lead")
        run_dir: Pipeline run directory to save arrangement.json
        
    Returns:
        dict with arrangement metadata: clip_id, duration_bars, notes_count, etc.
    """
    try:
        # Try to connect to Ableton MCP
        from serum2.ableton.ableton_mcp_extended.server import AbletonMCPBridge
        bridge = AbletonMCPBridge()
        
        # Create MIDI clip in arrangement
        clip = bridge.create_arrangement_clip(
            track_id=track_id,
            duration_bars=16,
            tempo_bpm=120
        )
        
        # Populate with MIDI notes (currently a placeholder)
        # In a real implementation, this reads the verified control state
        # and generates performance MIDI
        bridge.write_midi_notes(clip_id=clip['id'], notes=[
            (60, 0, 0.25),   # C3, beat 0
            (62, 0.25, 0.25),  # D3, beat 0.25
            (64, 0.5, 0.25),   # E3, beat 0.5
            (65, 0.75, 0.25),  # F3, beat 0.75
        ])
        
        # Verify arrangement
        saved_clip = bridge.read_clip(clip['id'])
        
        return {
            "success": True,
            "clip_id": clip['id'],
            "track_id": track_id,
            "duration_bars": 16,
            "notes_count": len(saved_clip.get('notes', [])),
            "tempo_bpm": 120,
        }
        
    except ImportError:
        # MCP unavailable; caller will mark AWAITING_NATIVE_ENVIRONMENT
        raise RuntimeError(
            "Ableton MCP bridge unavailable. "
            "This stage must run on Windows with Ableton 11.3+ and serum-mcp active."
        )
```

### Option B: AWAITING_NATIVE_ENVIRONMENT Fallback

If MCP integration is not ready, the stage should gracefully mark itself as awaiting the native environment (what it already does, but with clearer guidance):

```python
except Exception as exc:
    rec.mark_awaiting(
        f"AWAITING_NATIVE_ENVIRONMENT: Ableton arrangement creation failed: {exc}. "
        "Manual step required (LOCAL machine only):\n"
        "1. Open Ableton Live 11.3+\n"
        "2. Locate the Serum track (should be in the song)\n"
        "3. In Arrangement view, create a new MIDI clip\n"
        "4. Duration: 16 bars\n"
        "5. Tempo: 120 BPM\n"
        "6. Add 4 MIDI notes: C3-D3-E3-F3 (pitches 60-62-64-65)\n"
        "7. Save the arrangement details to: " + str(run_dir / "arrangement.json") + "\n"
        "   Format: {\"clip_id\": \"...\", \"duration_bars\": 16, \"notes_count\": 4}\n"
        "8. Re-run with --resume",
        {"halted_for": "AWAITING_NATIVE_ENVIRONMENT"},
    )
```

**Recommendation:** Use Option B for now (graceful fallback). Option A requires full Ableton MCP integration which is out of scope for this seam fix.

---

## Seam S3: RENDER VALIDATION — Fail Closed on Silent Audio

**File:** `serum2/pipeline/runner.py:850+`  
**Problem:** Current render validation doesn't distinguish between:
- ✓ Actual audible render (signal present)
- ✗ Digital silence (file exists but no sound)
- ✗ Measurement failure (unreadable file)

A measurement failure can get converted into a numeric success value that accidentally passes the threshold check.

**Fix:** Implement robust audio validation that fails closed on ambiguity.

### Implementation

**File:** `serum2/execution/render_verifier.py` (create new)

```python
"""Audio render verification — fail closed on ambiguity."""

import json
import struct
from pathlib import Path

def verify_render_audio(wav_path: str, expected_duration_sec: float, tolerance_sec: float = 2.0) -> dict:
    """
    Verify that a WAV render contains actual audible signal.
    
    Checks:
    1. File exists and is readable
    2. Valid WAV format
    3. Duration ≈ expected (±tolerance_sec)
    4. Sample rate = 44100 Hz
    5. Non-zero signal (RMS > -60 dB, peak > -50 dB)
    6. Non-silent duration fraction > 80%
    
    Returns: dict with status (OK, SILENT, FAILED) + metrics
    Raises: RuntimeError if file is unreadable or format invalid
    """
    path = Path(wav_path)
    
    # Check 1: File existence
    if not path.exists():
        raise RuntimeError(f"Render file not found: {wav_path}")
    
    if path.stat().st_size < 1024:
        raise RuntimeError(f"Render file too small: {wav_path} ({path.stat().st_size} bytes)")
    
    # Check 2: WAV format validation
    try:
        import wave
        with wave.open(str(path), 'rb') as wav_file:
            n_channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frame_rate = wav_file.getframerate()
            n_frames = wav_file.getnframes()
    except Exception as e:
        raise RuntimeError(f"Unreadable WAV file: {wav_path}\n{e}")
    
    # Check 3: Duration
    actual_duration_sec = n_frames / frame_rate
    if abs(actual_duration_sec - expected_duration_sec) > tolerance_sec:
        raise RuntimeError(
            f"Render duration mismatch: expected {expected_duration_sec}±{tolerance_sec}s, "
            f"got {actual_duration_sec}s"
        )
    
    # Check 4: Sample rate
    if frame_rate != 44100:
        raise RuntimeError(f"Unexpected sample rate: {frame_rate} (expected 44100 Hz)")
    
    # Check 5: Signal analysis
    try:
        import numpy as np
        with wave.open(str(path), 'rb') as wav_file:
            audio_data = wav_file.readframes(n_frames)
        
        # Convert bytes to numpy array
        if sample_width == 2:
            samples = np.frombuffer(audio_data, dtype=np.int16)
        elif sample_width == 4:
            samples = np.frombuffer(audio_data, dtype=np.int32)
        else:
            raise RuntimeError(f"Unsupported sample width: {sample_width}")
        
        # Normalize to [-1, 1]
        samples = samples.astype(np.float32) / (2 ** (8 * sample_width - 1))
        
        # Calculate metrics
        rms = np.sqrt(np.mean(samples ** 2))
        rms_db = 20 * np.log10(rms + 1e-9)
        peak = np.max(np.abs(samples))
        peak_db = 20 * np.log10(peak + 1e-9)
        
        # Threshold for "non-silent" (arbitrary: -50 dB)
        non_silent_mask = np.abs(samples) > 10 ** (-50 / 20)
        non_silent_fraction = np.sum(non_silent_mask) / len(samples)
        
    except Exception as e:
        raise RuntimeError(f"Audio analysis failed: {e}")
    
    # Verdict
    result = {
        "status": "UNKNOWN",
        "file_path": str(path),
        "duration_sec": actual_duration_sec,
        "frame_rate": frame_rate,
        "n_channels": n_channels,
        "sample_width": sample_width,
        "rms_db": float(rms_db),
        "peak_db": float(peak_db),
        "non_silent_fraction": float(non_silent_fraction),
        "analysis_error": None,
    }
    
    # Decision logic (fail closed)
    if rms_db < -60 or peak_db < -50:
        result["status"] = "SILENT"
    elif non_silent_fraction < 0.8:
        result["status"] = "MOSTLY_SILENT"
    elif rms_db > -30 or peak_db > -15:
        result["status"] = "OK"
    else:
        result["status"] = "AMBIGUOUS"  # Don't guess; fail closed
    
    return result
```

**Update _stage_render():**

```python
def _stage_render(manifest: RunManifest, run_dir: Path) -> StageRecord:
    # ... existing code ...
    
    try:
        # Render produces a WAV file
        render_path = run_dir / "render.wav"
        
        # (Render logic here — LOCAL stage)
        
        # Verify the audio
        from serum2.execution.render_verifier import verify_render_audio
        verification = verify_render_audio(
            wav_path=str(render_path),
            expected_duration_sec=32,  # 16 bars @ 120 BPM
            tolerance_sec=2.0,
        )
        
        if verification["status"] != "OK":
            rec.mark_failed(
                f"Render verification failed: {verification['status']}. "
                f"RMS: {verification['rms_db']:.1f} dB, Peak: {verification['peak_db']:.1f} dB, "
                f"Non-silent: {verification['non_silent_fraction']:.1%}"
            )
            manifest.update_stage(rec)
            return rec
        
        rec.mark_complete({
            "render_path": str(render_path),
            "audio_verification": verification,
        })
        
    except Exception as e:
        rec.mark_failed(f"Render failed: {e}")
    
    manifest.update_stage(rec)
    return rec
```

---

## Seam S4: NATIVE PROOF BOUNDARY — No Change Needed

**File:** `serum2/pipeline/runner.py` (AWAITING_NATIVE_ENVIRONMENT handling)  
**Status:** ✅ **Working as designed.** This is intentional.

The runner correctly halts at the OBSERVATION stage when VLM/easyocr are unavailable (cloud environment). This preserves the **session boundary** (CLOUD work ≠ LOCAL work).

**No fix needed.** The runner correctly:
1. ✅ Completes all CLOUD stages (ACQUIRE → TRANSCRIPT → LEDGER → ADMISSION → COMPILE)
2. ✅ Halts with AWAITING_NATIVE_ENVIRONMENT when LOCAL stages (OBSERVATION, NATIVE_LOAD, etc.) are reached
3. ✅ Saves a durable manifest so `--resume` can pick up on a LOCAL Windows machine

---

## Execution Order: Fastest Route to Closure

### Phase 0: Fix Seams (This Week) — CLOUD

1. **S1: reread_log generation** (3–4 hours)
   - Update NATIVE_VERIFY to output `control_readbacks`
   - Update REFERENCE_VERIFY to generate reread_log.json before calling reference_reproduction

2. **S2: arrangement fallback** (2–3 hours)
   - Add graceful AWAITING_NATIVE_ENVIRONMENT message and fallback
   - OR implement `create_16bar_arrangement()` if MCP is available

3. **S3: render validation** (4–6 hours)
   - Create `render_verifier.py`
   - Add robust audio analysis
   - Update `_stage_render()` to fail closed on silent/ambiguous

**Outcome after Phase 0:** Runner can complete CLOUD stages without crashing. Ready for LOCAL testing.

### Phase 1: Current Gate B Rerun (1–2 weeks) — LOCAL Windows

Re-run the Gate B path on the current branch with the seams fixed:

```text
env2.decay
  ↓
state ledger
  ↓
admitted value
  ↓
compiled preset
  ↓
Serum 2.0.23 native load
  ↓
native re-save
  ↓
screenshot readback
  ↓
comparison PASS
```

This produces **Cert 2 — Native Serum** evidence.

### Phase 2: Fresh W2 (2–3 weeks) — LOCAL Windows

Real untouched tutorial → full pipeline → reference_verified=True with COMPLETE coverage.

This produces **Cert 3 — Product** evidence.

### Phase 3: 20 Exceptions & Final Certs (1–2 weeks) — CLOUD + selective LOCAL

Classify the 20 exceptions, produce final Cert 4.

**Total timeline: 4–8 weeks to product closure** (without family-grouping delays).

---

## Testing the Fixes

### Test S1: Reread Log Generation

```python
# Test that REFERENCE_VERIFY generates reread_log.json
from serum2.pipeline.runner import _stage_reference_verify

manifest = RunManifest(...)
# Populate NATIVE_VERIFY outputs
manifest.stage_record("NATIVE_VERIFY").outputs = {
    "run_id_native": "test_run",
    "serum_module_sha256": "...",
    "control_readbacks": [
        {"atlas_id": "env2.decay", "value": 123.45}
    ],
}

rec = _stage_reference_verify(manifest, run_dir, "test_run")

# Verify reread_log.json exists and is valid
reread_path = run_dir / "reread_log.json"
assert reread_path.exists()
reread = json.loads(reread_path.read_text())
assert reread["manifest"]["run_id"] == "test_run"
```

### Test S3: Audio Validation

```python
from serum2.execution.render_verifier import verify_render_audio

# Test silent audio
result = verify_render_audio("tests/fixtures/render_silent.wav", expected_duration_sec=32)
assert result["status"] == "SILENT"

# Test good audio
result = verify_render_audio("tests/fixtures/render_good.wav", expected_duration_sec=32)
assert result["status"] == "OK"

# Test unreadable file
with pytest.raises(RuntimeError):
    verify_render_audio("/nonexistent/path.wav", expected_duration_sec=32)
```

---

## Summary

**These 4 seam fixes are the critical path to closure.** They unblock:
- ✅ Current Gate B rerun (prove authority works on Serum 2.0.23)
- ✅ Fresh W2 (prove real tutorial works)
- ✅ Native reference verification
- ✅ 16-bar Ableton product
- ✅ Final certificates

**Estimated effort:** 2–4 weeks of CLOUD-only work, no new control qualification.

**Do NOT start family-grouping strategy until seams are fixed.** The current architecture is already sufficient for product closure once the runner completes end-to-end.
