# PHASE 4B.1 — SERUM-IN-ABLETON CONTROL GATE

**Status:** BLOCKED — No mechanism to load DawDreamer Serum state into Ableton-hosted Serum.

**Date:** 2026-09-18  
**Repository:** D:\ableton claude final best

---

## Investigation Summary

### Question
Can a Serum parameter mutated through DawDreamer be loaded into the real Ableton-hosted Serum instance to produce the final render?

### Findings

#### 1. Ableton MCP Serum parameter exposure
**Result:** NEGATIVE

- `get_device_parameters(track=0, device=0)` returns only "Device On" wrapper
- `write_automation()` accepts only "Device On" parameter
- No VST3 parameter mapping available through MCP tool surface
- Full Serum synth parameters (Oscillators, Filters, Envelopes, LFOs) are NOT accessible

#### 2. Existing Serum state infrastructure
**Result:** FOUND BUT DISCONNECTED

The repository contains:
- `serum2/bridge.py` — v5 preset → v8 state converter (DawDreamer format)
- `serum2/vst3_state.py` — VC2! VST3 state wrapper/unwrapper
- `serum2/codec.py` — Serum state encoding/decoding
- `serum2/statemodel.py` — State mutation machinery

This infrastructure proves DawDreamer can mutate Serum state and export it as VC2! binary blobs.

#### 3. Serum preset/state loading into Ableton
**Result:** NO MECHANISM FOUND

- Ableton browser does NOT expose Serum presets as loadable items through MCP
- No MCP tool to load a VST3 state file directly into a plugin instance
- Ableton's `load_instrument_or_effect()` loads instrument DEFINITIONS (URIs), not state files
- Serum's state/preset files are internal to the Serum plugin, not exposed to the host
- No existing codebase mechanism connects DawDreamer Serum output → Ableton Serum instance

#### 4. Proof of the gap

**DawDreamer side (WORKS):**
```python
bridge.build_v8_state(preset_path) → (meta8, body8)
codec.encode(meta8, body8) → XferJson bytes
vst3_state.wrap_vc2(xferjson) → VC2! state blob
# State blob can be written to disk as .bin or embedded
```

**Ableton side (BLOCKED):**
```
# No MCP tool exists to:
# - load a .bin state file into a plugin instance
# - inject a VC2! blob into the running Serum instance
# - expose Serum's preset storage for programmatic access
```

---

## Exact Limitation

**Missing mechanism:**

There is no Ableton MCP tool or documented Serum host API that allows:
1. Taking a DawDreamer-generated Serum state blob
2. Delivering it to the Ableton-hosted Serum instance
3. Triggering state load without manual UI interaction

**What exists:**
- DawDreamer can mutate Serum state and write it to disk
- Ableton MCP can create tracks, load plugins, trigger clips, render audio
- Serum can be triggered via MIDI
- Serum can accept state loads through its VST3 interface (in principle)

**What doesn't exist:**
- No MCP tool to load plugin state from file
- No documented Serum "accept state from host" mechanism exposed through Ableton's scripting layer
- No existing integration in this repository connecting the two sides

---

## Smallest legitimate alternative

**Option 1: Use MIDI mutation only (REJECTED by spec)**
- Spec says: "Do not use MIDI velocity/pitch as substitute"

**Option 2: Use DawDreamer render standalone (NOT Ableton-hosted)**
- DawDreamer can generate audio with mutated Serum state
- Output: WAV file (NOT from Ableton)
- Proof of concept works, but contradicts the stated goal (Ableton-hosted render)

**Option 3: Manual preset export/import (NOT automated)**
- Manually capture DawDreamer state as Serum preset
- Manually load into Ableton UI
- Render
- This defeats the automation goal

**Option 4: Request new Ableton MCP tool**
- Feature request: `load_plugin_state(track, device, state_file)`
- Currently does not exist

---

## Conclusion

**The gate cannot be resolved with existing infrastructure.**

The DawDreamer Serum state mutation layer and Ableton-hosted Serum instance are **architecturally disconnected**. No mechanism exists to bridge them.

### Next options:

1. **Proceed with DawDreamer render only** (not Ableton-hosted)
   - Mutate Serum in DawDreamer
   - Render to WAV via DawDreamer
   - Skip Ableton-hosted phase

2. **Implement custom Ableton plugin loader**
   - Write a Python bridge that loads Serum state directly into a plugin instance
   - Requires VST3 SDK / AbletonLink internals
   - High complexity, outside current scope

3. **Stop Phase 4B.1 and escalate**
   - Document the architectural gap
   - No further progress until the missing tool exists

---

## Files Inspected

- `serum2/bridge.py` — State bridge (FOUND)
- `serum2/vst3_state.py` — State wrapper (FOUND)
- `serum2/codec.py` — State encoding (FOUND)
- `serum2/compiler/context.py` — Mutation context (FOUND)
- Ableton MCP tools — State loading tool (NOT FOUND)
- Repository for Ableton↔DawDreamer integration (NOT FOUND)

---

## Recommendation

**Do not proceed with Phase 4B.2 (full 16-bar production) until this gap is resolved.**

Current state:
- ✅ DawDreamer Serum mutations proven
- ✅ Ableton MCP rendering proven
- ❌ Bridge between them does not exist

The vertical slice (STEP 6) proved intent→MCP→Ableton render, but only with **MIDI input** and **default Serum preset**. To advance beyond this requires closing the control gap.
