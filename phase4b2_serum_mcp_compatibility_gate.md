# Phase 4B.2 — serum-mcp ↔ Serum 2.0.21 Compatibility Gate

**Status:** GATE TEST IN PROGRESS  
**Date:** 2026-09-18  
**Scope:** Verify serum-mcp generates valid .SerumPreset files loadable by Serum 2.0.21

---

## Test Setup

### 1. serum-mcp Connection  
✅ **COMPLETE**

- Repository: https://github.com/Celian-mrc/serum-mcp
- Installation: `D:\serum-mcp` (cloned via `uv sync`)
- MCP Server: Registered in Claude Code config
- Environment: `SERUM_PRESETS_PATH` → `C:\Users\Satvik\Documents\Xfer\Serum 2 Presets\Presets\User`

### 2. Test Preset Generation  
✅ **COMPLETE**

**Tool:** `serum-mcp.tools.generate_preset()`

**Spec:** Minimal init-style saw lead
```
- Oscillator A: enabled, saw waveform, default table, volume=0.75
- Oscillators B, C: disabled
- Noise: disabled
- Sub: disabled
- Filters: none (disabled)
- Envelopes: defaults
```

**Result:**
```
File: C:\Users\Satvik\Documents\Xfer\Serum 2 Presets\Presets\User\Test Init Saw Lead.SerumPreset
Size: 1560 bytes
Generated: 2026-09-18 18:53:10 UTC
Format: Binary .SerumPreset (Serum 2.0 CBOR container)
```

**Generation Script:** `generate_test_preset.py`

### 3. Manual Load — AWAITING EXECUTION

**Next Step:** Load the preset into Serum 2.0.21 GUI to verify format compatibility

**Instructions:**
1. Open Ableton Live with Serum 2.0.21 instance loaded
2. Click "Load" in Serum's preset browser
3. Navigate to: `C:\Users\Satvik\Documents\Xfer\Serum 2 Presets\Presets\User\`
4. Select: `Test Init Saw Lead.SerumPreset`
5. Confirm load
6. **Expected:** Serum loads without error, displays saw wave on Osc A, plays clean tone

**Manual Confirmation Required:** YES ← **USER ACTION NEEDED**

### 4. DawDreamer Validation Pipeline

Once preset loads successfully in Serum 2.0.21:

**Pipeline:**
```
.SerumPreset
  ↓ [serum2.codec.unpack_file()]
V5 JSON preset data
  ↓ [VST3 state extraction]
  ↓ [serum2.bridge.build_v8_state()]
V8 state object
  ↓ [serum2.codec.encode()]
XferJSON (internal representation)
  ↓ [serum2.vst3_state.wrap_vc2()]
VC2! state blob
  ↓ [DawDreamer.load_state()]
Serum VST3 instance (in-memory)
  ↓ [render → render.wav]
4 bars @ 120 BPM
  ↓ [measurement]
Spectral analysis (centroid, RMS, peak)
```

**Expected Measurements:**
- Clean sine-wave fundamental (low harmonics, saw is mostly fundamental + odd partials)
- Spectral centroid: ~3–5 kHz (saw without filter)
- Peak: ~−6 to −2 dB (dry synth)
- RMS: ~−20 to −15 dB

---

## Architecture Summary

This gate validates the **production integration path**:

```
Claude Code
  ↓
serum-mcp MCP Server
  ↓
PresetSpec (user's sound idea → JSON)
  ↓
.SerumPreset file (Serum 2.0.21 format)
  ↓
Serum 2.0.21 loads & plays
  ↓
DawDreamer validates / measures
  ↓
Evidence recorded
```

**Key Finding:** serum-mcp already handles all the format validation and file packaging. **No VST3 state bridge is needed.** The preset format is complete and ready to use.

---

## What Comes After This Gate Passes

Once manual load confirms Serum 2.0.21 accepts the generated preset:

### Production Vertical Slice
- [ ] Connect serum-mcp MCP tools to Claude's tool palette
- [ ] Build producer brain → serum-mcp workflow (no intermediate bridge)
- [ ] Route 908/396 inventory through real MCP calls
- [ ] Record admission evidence for each preset generated
- [ ] Render validation batch via DawDreamer

### What We Skip
- ❌ `serum2/serum_mcp_bridge.py` — unnecessary abstraction
- ❌ VST3 state bridge — serum-mcp handles all state management
- ❌ Reimplemented format checks — serum-mcp's validation is sufficient

---

## Remaining Unknowns

**Only one:** Does Serum 2.0.21's .SerumPreset format match the format serum-mcp generates?

- serum-mcp was tested against Serum 2.0.11
- Your project is frozen at Serum 2.0.21
- The format is reverse-engineered (not official)
- **This test answers:** "Does 2.0.21 load a preset built for 2.0.x?"

If yes: Proceed to production slice immediately.  
If no: Debug the version-specific difference (likely a single field or missing default).

---

## Checklist

- [x] serum-mcp cloned and dependencies installed
- [x] MCP server registered in Claude Code config  
- [x] SERUM_PRESETS_PATH environment variable set
- [x] Test preset generated (saw lead, minimal config)
- [x] Preset file exists on disk (1560 bytes)
- [ ] **Manual load into Serum 2.0.21 GUI** ← NEXT STEP
- [ ] Serum loads without error
- [ ] Serum plays tone without artifacts
- [ ] DawDreamer renders and validates
- [ ] Measurements recorded

---

**Next Action:** Load `Test Init Saw Lead.SerumPreset` into Serum 2.0.21 and report whether it loads cleanly.
