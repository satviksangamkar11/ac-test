# PHASE 4B.2 — NEW ARCHITECTURE: serum-mcp Integration

**Status:** Architecture redesigned. New path established. Ready for implementation.

**Date:** 2026-09-18  
**Repository:** D:\ableton claude final best  
**Commit:** b12106c

---

## Executive Summary

After Phase 4B.1 identified a blocking gap (no VST3 state bridge), the architecture has been redesigned to use `serum-mcp` as the Serum authoring actuator, with manual preset loading as an explicit human-in-loop boundary.

**Result:** The path is now 5-10x simpler, requires no missing infrastructure, and maintains clear component responsibilities.

---

## Problem Statement (Phase 4B.1)

**Gate test found:**
- Ableton MCP exposes only "Device On" wrapper for Serum
- No tool to load VST3 plugin state into Ableton
- No tool to load Serum presets programmatically
- Existing DawDreamer-generated V8/VC2! state blobs have no delivery mechanism

**Blocked state:** Could not automate Serum parameter mutations inside Ableton-hosted Serum.

---

## New Architecture

### Overall Flow

```
LEARNING LOOP
──────────────
YouTube / manual / reference
    ↓
Knowledge extraction
    ↓
Production concepts / parameter relationships
    ↓
Claude Producer Brain

PRODUCTION LOOP
──────────────
User intent
    ↓
Producer brain reasoning
    ↓
Retrieve knowledge + episodes
    ↓
Plan production
    │
    ├─────────────────────────────┐
    ↓                             ↓
SERUM DOMAIN                 ABLETON DOMAIN
    ↓                             ↓
Admission / authority         Ableton MCP
    ↓                             ↓
serum-mcp                    MIDI / tracks /
    ↓                        tempo / arrangement /
.SerumPreset                 transport / render
    ↓                             │
MANUAL LOAD                    actual DAW
into Serum in Ableton             │
    └──────────────┬──────────────┘
                   ↓
              actual production
                   ↓
              render / bounce
                   ↓
          measurement / diagnosis
                   ↓
            EvidenceRecord
                   ↓
               Episode
                   ↓
           memory / retrieval
                   ↓
         next production decision
```

---

## Component Responsibilities

### Claude Code Brain

**Responsible for:**
- Understanding user intent
- Reading retrieved knowledge
- Deciding what sound/production is needed
- Deciding what Serum needs to do
- Deciding what Ableton needs to do
- Selecting admitted capabilities
- Coordinating the sequence
- Interpreting render/measurement results
- Deciding the next iteration

### Serum Authority System (Existing)

**Responsible for:**
- Semantic Serum vocabulary
- Evidence collection
- Capability contracts
- Admission/authorization
- Causal knowledge
- Measurement kernels
- Episode history
- Determining what is known about Serum

**Critical:** Serum knowledge does NOT move into serum-mcp. Authority remains here.

### serum-mcp

**Role:** Serum preset ACTUATOR only.

**Capabilities:**
- Generates .SerumPreset files
- Edits .SerumPreset parameters
- Lists available parameters
- Describes presets
- Searches reference presets

**What it is NOT:**
- Authority on Serum capabilities
- Validator of causal relationships
- Source of semantic knowledge
- Able to make admission decisions

**Important:** serum-mcp is a community reverse-engineering project. Serum preset format is not officially documented by Xfer. Parameter coverage is empirically verified. Our existing evidence system remains authoritative.

### Ableton MCP

**Responsible for:**
- Creating/selecting tracks
- Creating MIDI clips
- Writing notes
- Setting tempo
- Arranging clips
- Controlling transport
- Recording/rendering

**Limitation accepted:** Cannot expose Serum's internal parameters. This is not architectural failure; it's the boundary of what Ableton exposes.

### DawDreamer

**New role:** Validation oracle.

**Responsible for:**
- Independent Serum preset validation
- Rendering presets in isolated environment
- Measuring audio characteristics
- Providing ground-truth measurements

**Path:**
```
.SerumPreset → V8 state → DawDreamer → render → measurement
```

The existing V8/VC2! infrastructure (bridge.py, codec.py, vst3_state.py) is NOT wasted. It now serves validation instead of delivery.

---

## The Human-in-Loop Boundary

### Manual Serum Preset Loading

After serum-mcp generates a .SerumPreset:

1. **System records:**
   ```
   preset_generated = true
   preset_path = "C:\...\pluck_dark_evolving.SerumPreset"
   preset_hash = "b20fae49bf1fc362"
   manual_load_required = true
   ```

2. **Human action:**
   - Open Serum in Ableton
   - File → Load Preset
   - Select the generated .SerumPreset
   - Confirm it loads

3. **System records:**
   ```
   manual_load_confirmed = true
   load_timestamp = "2026-09-18T13:06:00Z"
   ```

**This is not architectural failure.** It is an honest acknowledgment of the automation boundary.

The system does NOT claim the preset reached Ableton until the human confirms it.

---

## Full Production Path (Example)

**User intent:** "Create a dark evolving pluck for a techno track"

**Step 1 — Brain**
```
role = pluck
character = dark
evolving = yes
genre = techno
```

**Step 2 — Knowledge**
Retrieve tutorial knowledge + previous episodes + known Serum relationships

**Step 3 — Serum plan**
Brain produces semantic Serum specification:
```
{
  "role": "pluck",
  "character": "dark",
  "evolving": true,
  "osc1_type": "wavetable",
  "filter_type": "lowpass",
  "env_attack_ms": 5,
  "env_release_ms": 800,
  "lfo_enabled": true,
  "fx_reverb": true
}
```

**Step 4 — Admission**
Authority system determines: which capabilities are admissible for this intent?

**Step 5 — serum-mcp**
Generate:
```
Dark_Evolving_Pluck.SerumPreset
```

**Step 6 — Validation (DawDreamer)**
```
.SerumPreset
  ↓
V8/VC2 conversion
  ↓
DawDreamer render
  ↓
Measure: attack (ms), spectral centroid (Hz), RMS (dB), peak (dB)
  ↓
Record evidence
```

**Step 7 — Manual load**
```
File: Dark_Evolving_Pluck.SerumPreset
Human: Opens in Serum GUI and loads
System: Records manual_load_confirmed = true
```

**Step 8 — Ableton MCP**
```
Create MIDI track
Create 16-bar clip
Add MIDI notes (C3, velocity 80)
Set tempo (120 BPM)
Create arrangement clip
```

**Step 9 — Render**
```
record_section(0, 64, "Resampling")
  ↓
Bounce_0001.wav (actual Ableton render with loaded Serum preset)
```

**Step 10 — Compare**
```
DawDreamer validation render
        vs
Ableton production render

Not byte-identical; compare declared measurements/tolerances
```

**Step 11 — Episode**
```
{
  "intent": "Create a dark evolving pluck for a techno track",
  "semantic_spec": {...},
  "serum_preset": {
    "path": "...",
    "hash": "...",
    "manual_load_confirmed": true
  },
  "ableton_operations": [...],
  "render": "Bounce_0001.wav",
  "measurements": {...},
  "decision": "ACCEPTED",
  "what_worked": [...],
  "what_failed": [...]
}
```

**Step 12 — Next request**
Producer retrieves episode. System gets better from experience.

---

## Solving the 16-Bar Problem

**Old approach (BLOCKED):**
```
Bar 5 → mutate hidden Serum parameter through Ableton MCP
Bar 9 → mutate hidden Serum parameter
...
[Doesn't work - Ableton MCP can't expose them]
```

**New approach (WORKS):**

Serum presets themselves can encode movement over time:
- Filter modulation (via Serum LFO)
- Envelope behavior
- Macro relationships
- FX behavior (reverb, delay modulation)

Design the Serum preset to have internal movement built in. Then Ableton's job is simply to:
1. Play the MIDI
2. Arrange the piece
3. Render

This is more faithful to how Serum actually works.

---

## Three Separate Truth Domains

**Serum truth:**
What Serum parameters/specification were created?
What behavior was observed in DawDreamer validation?

**Ableton truth:**
What actually happened in the DAW?
(tracks, MIDI, arrangement, transport, render)

**Production truth:**
What did the final rendered audio actually sound like?
(spectral, RMS, peak measurements)

Evidence system connects all three without conflating them.

---

## What's NOT Changed

### Still Complete:
- ✅ Canonical repository
- ✅ Knowledge/YouTube acquisition
- ✅ Producer brain
- ✅ Serum authority system
- ✅ Serum learning system
- ✅ DawDreamer validation
- ✅ Ableton MCP
- ✅ MIDI clip creation
- ✅ Arrangement
- ✅ 16-bar render
- ✅ Evidence/episodes

### No Longer Needed:
- ❌ Custom VST3 state bridge
- ❌ Plugin state loader MCP tool
- ❌ Ableton ↔ DawDreamer automation
- ❌ Hidden parameter exposure workarounds

---

## Remaining Path

```
✅ Canonical repository
✅ Knowledge / YouTube
✅ Producer brain
✅ Serum authority
✅ Serum learning
✅ serum-mcp preset generation
✅ DawDreamer validation
✅ Manual Serum preset loading
✅ Ableton MCP
✅ MIDI
✅ Arrangement
✅ 16-bar render
✅ Evidence / episodes

NEXT STEPS
────────────────────────────
1. Integrate serum-mcp (GitHub project)
2. Generate one real .SerumPreset
3. Validate through existing Serum/DawDreamer path
4. Manual load into Ableton
5. Ableton MCP creates 16-bar production
6. Render
7. Compare/measure
8. Episode record
9. DONE
```

---

## Files

**New/Modified:**

- `serum2/serum_mcp_bridge.py` — Bridge to serum-mcp (PresetSpec, generate_preset_from_spec)
- `phase4b2_serum_mcp_first_proof.py` — First end-to-end proof
- `docs/archive/superseded/` — Phase 4B.1 reports (archived, not deleted)

**Not Changed:**
- All existing Serum authority code
- All existing Ableton MCP code
- All existing evidence/episode code
- DawDreamer validation pipeline

---

## Critical Caveats

1. **serum-mcp is community-driven**
   - Serum preset format is not officially documented by Xfer
   - Parameter coverage is empirically verified
   - Our evidence system remains the authority, not serum-mcp's schema

2. **Manual load is honest**
   - We do not claim to have automated Serum parameter control
   - We do not fabricate automation that doesn't exist
   - We explicitly record human-in-loop boundaries

3. **DawDreamer validation is independent**
   - Proves presets work outside of Ableton
   - Allows comparison of validation vs. production renders
   - Does not replace Ableton testing

---

## Success Criteria for Phase 4B.2

**Prove:**

```
user intent
  ↓
producer brain
  ↓
serum-mcp preset generation
  ↓
.SerumPreset file (real)
  ↓
DawDreamer validation (real)
  ↓
manual load into Ableton Serum (real)
  ↓
Ableton MCP MIDI + arrangement (real)
  ↓
16-bar render (real)
  ↓
measurement + evidence (real)
  ↓
episode (real)
```

One complete vertical slice. No mock operations.

---

## Comparison to Old Path

| Aspect | Phase 4B.1 Path | Phase 4B.2 Path |
|--------|-----------------|-----------------|
| **Serum control** | Hidden VST3 params in Ableton | serum-mcp presets |
| **State delivery** | Custom bridge (MISSING) | Manual load (HONEST) |
| **Validation** | DawDreamer sidelined | DawDreamer oracle |
| **Complexity** | High (multiple bridges) | Low (two domains) |
| **Authority** | Threatened | Clear |
| **Automation boundary** | Hidden gap | Explicit |
| **16-bar mutations** | Bar-specific param tweaks | Preset design + MIDI |

---

## Conclusion

The Phase 4B.2 architecture is simpler, cleaner, and doesn't require infrastructure we don't have.

It maintains clear component boundaries and honest automation boundaries.

It reuses existing infrastructure (DawDreamer, evidence, authority system) without overloading them.

It is ready for implementation.

---

**Recommendation:** Proceed to Phase 4B.2 implementation. Connect serum-mcp, generate real presets, and build the first vertical slice.
