# Production Behavior Architecture

**Status:** LOCKED  
**Date:** September 23, 2026

---

## Core Principle

**"Preset generated" never means "reference completely reproduced."**

**It means:** Everything executable was generated and verified, while every remaining requested state was explicitly accounted for.

---

## Three Final States

| State | Meaning | Use Case |
|-------|---------|----------|
| `AUTO_VERIFIED` | serum-mcp set it + Serum readback confirmed value | Oscillator volume, filter cutoff, LFO rate, etc. |
| `MANUAL_REQUIRED` | Reference value known, but backend cannot safely set it | Granular density in certain modes, MPE routing, curve edits |
| `UNRESOLVED` | Could not determine control or value reliably | Ambiguous visual reference, no extraction evidence |

---

## Execution Pipeline

```
REFERENCE VIDEO
    ↓
EXTRACT INTENDED STATE (canonical Atlas IDs + values)
    ↓
CAPABILITY RESOLUTION + ADMISSION
    │
    ├─→ EXECUTABLE (serum-mcp supported)
    │   ├─ Write via serum-mcp
    │   ├─ Read back from Serum
    │   └─ State: AUTO_VERIFIED
    │
    └─→ NOT EXECUTABLE (known but unsupported)
        ├─ Extract exact value
        ├─ Record UI path / manual instruction
        └─ State: MANUAL_REQUIRED
    ↓
GENERATE .SerumPreset (with AUTO_VERIFIED items only)
    ↓
PRODUCE REFERENCE_COMPLETION_MANIFEST.json
    ├─ AUTO_VERIFIED items (with evidence)
    ├─ MANUAL_REQUIRED checklist (exact instructions)
    └─ UNRESOLVED items (reason + needed evidence)
    ↓
FINAL COMPLETION REPORT
```

---

## Output Artifacts

### 1. Generated Preset File
```
reference_reproduction.SerumPreset
```
- Contains ONLY auto-verified, safely-executable controls
- Everything AUTO_VERIFIED was tested live
- Serum loads cleanly (no broken state)

### 2. Reference Completion Manifest
```json
{
  "reference_id": "HEEGN1Xl5o4",
  "date": "2026-09-23",
  "preset_file": "reference_reproduction.SerumPreset",
  
  "summary": {
    "automatically_configured": 147,
    "automatically_verified": 139,
    "manual_required": 6,
    "unresolved": 2,
    "total_expected": 155
  },
  
  "controls": [
    {
      "canonical_id": "oscA.volume",
      "reference_value": 0.82,
      "representation": "float (0.0-1.0)",
      "execution_status": "EXECUTABLE",
      "verification_status": "AUTO_VERIFIED",
      "evidence": "live serum-mcp write + Serum readback confirmed 0.82",
      "reason": null,
      "manual_instruction": null
    },
    {
      "canonical_id": "granular_b.density",
      "reference_value": 18.3,
      "representation": "float (0.0-30.0)",
      "execution_status": "NOT_EXECUTABLE",
      "verification_status": "MANUAL_REQUIRED",
      "evidence": "extracted from video frame analysis",
      "reason": "serum-mcp granular_density write exists but UI readback cannot confirm value in real-time (Serum display widget shows range, not exact number)",
      "manual_instruction": "Osc B → Granular Density knob → set to 18.3"
    },
    {
      "canonical_id": "lfo3.curve_points",
      "reference_value": "custom hand-drawn curve",
      "representation": "curve (xVals, yVals, curveVals)",
      "execution_status": "NOT_EXECUTABLE",
      "verification_status": "UNRESOLVED",
      "evidence": "visual curve visible in reference, but precise point coordinates not extractable from video",
      "reason": "serum-mcp can round-trip curves but cannot author custom drawn curves; extraction precision insufficient for reliable reproduction",
      "manual_instruction": "LFO 3 → Curve tab → draw curve approximating reference (see reference frame T=42:15)"
    }
  ]
}
```

### 3. Completion Summary Report
```
REFERENCE REPRODUCTION REPORT
=============================

Reference: HEEGN1Xl5o4 (Serum ID)
Date: 2026-09-23
Preset Generated: reference_reproduction.SerumPreset

EXECUTION SUMMARY
─────────────────
Automatically Configured:   147 controls
Automatically Verified:     139 controls (readback confirmed)
Manual Configuration Required: 6 controls
Unresolved:                  2 controls
─────────────────────────────────────────
Total Identified:           155 controls

WHAT WAS DONE
─────────────
✅ Oscillators: all parameters AUTO_VERIFIED
✅ Filters: cutoff/resonance/drive AUTO_VERIFIED; stereo mode MANUAL_REQUIRED (UI-only control)
✅ Envelopes: all parameters AUTO_VERIFIED
✅ LFOs: rate/shape/mode AUTO_VERIFIED; curve edits MANUAL_REQUIRED (hand-drawn state)
✅ Matrix: all routes AUTO_VERIFIED; 2 auxiliary destinations MANUAL_REQUIRED (API limitation)
✅ Global: master volume/mono/portamento AUTO_VERIFIED
⚠️  Granular: density/grain_length MANUAL_REQUIRED (widget readback insufficient)
❌ MPE routing: UNRESOLVED (insufficient video evidence)

MANUAL CONFIGURATION CHECKLIST
──────────────────────────────
The preset is ready to load. Before testing:

1. Osc B → Granular Density knob → set to 18.3
   Reason: automated write cannot be verified against UI display
   
2. LFO 3 → Curve tab → hand-draw curve
   Reference: see attached frame at T=42:15
   Approximate shape: soft rise, plateau, sharp fall
   
3. Filter 2 → Stereo → 37% width
   Reason: stereo is GUI-only state, not writable via API
   
4. Matrix slot 7 → Auxiliary Destination → Osc C Fine
   Reference value: +1.2
   Reason: this MCP operation is not yet implemented for aux destinations
   
5. Matrix slot 9 → Auxiliary Destination → unknown
   (reference video too blurry to read, see frame T=44:23)
   
6. Global → Tuning: A = 438 Hz
   Reason: global_tuning is in schema but write confirmation mechanism pending

UNRESOLVED (CANNOT PROVIDE INSTRUCTION)
────────────────────────────────────────
1. MPE configuration
   Evidence: none found in reference video
   Status: not visible in standard Serum UI view used in reference
   
2. VoicePanel per-voice randomization (Osc C specific)
   Evidence: insufficient visual evidence
   Status: would require direct preset inspection

NEXT STEPS
──────────
1. Load reference_reproduction.SerumPreset into Serum
2. Follow manual configuration checklist above (6 items, ~2 minutes)
3. For unresolved items: inspect live Serum or accept defaults
4. Test: render + compare to reference audio/visuals

VERIFICATION NOTES
──────────────────
- 139/147 automatically configured controls were readback-verified live
- 8 controls were written but await manual confirmation (not in audio path)
- 2 controls require manual effort due to UI-only or hand-drawn state
- 2 controls cannot be reliably extracted from reference

Preset is production-ready after manual setup.
```

---

## Why This Architecture Works

### 1. **Honest Automation**
- No pretense of 100% automatic reproduction
- Clear distinction between what we did automatically and what remains

### 2. **Maximum Coverage**
- 147/155 controls are in the preset (95%)
- 139/155 are verified via live readback (90%)
- User gets a working preset immediately, not a stub

### 3. **Explicit Remainder**
- Every unsupported control has a reason + instruction
- User knows exactly what to do if they want 100% fidelity
- Unresolved items are clearly marked (can't do anything about them)

### 4. **Verification Trail**
- Every AUTO_VERIFIED item has evidence (file + test result)
- MANUAL_REQUIRED items have extraction evidence + UI path
- UNRESOLVED items explain why we stopped

### 5. **Reusable Manifest**
- REFERENCE_COMPLETION_MANIFEST.json is machine-readable
- Can be consumed by UI, CLI, or future auto-completion tools
- Survives across session boundaries

---

## State Transitions

### AUTO_VERIFIED Pathway
```
Extracted Value
    ↓
serum-mcp write
    ↓
Serum preset updated
    ↓
Read back from preset
    ↓
Value matches?
    ├─ YES → AUTO_VERIFIED (include in preset)
    └─ NO → MANUAL_REQUIRED (log instruction)
```

### MANUAL_REQUIRED Pathway
```
Extracted Value
    ↓
Check serum-mcp capability
    ├─ EXISTS but verification fails → MANUAL_REQUIRED
    └─ NOT PRESENT → MANUAL_REQUIRED
    ↓
Record: exact value + UI path
    ↓
Include in manifest checklist
```

### UNRESOLVED Pathway
```
Cannot extract value (video too blurry, ambiguous state)
    ↓
Cannot locate in serum-mcp (no parameter match)
    ↓
Record: reason + what evidence would be needed
    ↓
Exclude from preset + manifest
    ↓
Note in completion report
```

---

## Implementation Notes

### REFERENCE_COMPLETION_MANIFEST.json Structure

**Required for each control:**
- `canonical_id` — Atlas identifier (e.g., `oscA.volume`)
- `reference_value` — extracted from reference
- `representation` — type + range (float, enum, curve, etc.)
- `execution_status` — EXECUTABLE / NOT_EXECUTABLE / UNKNOWN
- `verification_status` — AUTO_VERIFIED / MANUAL_REQUIRED / UNRESOLVED
- `evidence` — source of the claim (file + line or test result)
- `reason` — why it's not auto-verified (if applicable)
- `manual_instruction` — exact UI steps (if MANUAL_REQUIRED)

### Preset Generation Logic

1. **Filter to AUTO_VERIFIED only** — only these go into the generated .SerumPreset
2. **Write AUTO_VERIFIED to preset** — via serum-mcp
3. **No partial states** — don't write MANUAL_REQUIRED or UNRESOLVED to preset (avoid broken state)
4. **Leave other controls untouched** — preset round-trips unmodified controls

### Completion Report Generation

- Summary from manifest counts
- Checklist auto-generated from MANUAL_REQUIRED items
- Unresolved section from UNRESOLVED items
- Evidence links back to source (video frame, test result, etc.)

---

## Success Criteria

✅ Preset loads cleanly in Serum  
✅ All AUTO_VERIFIED controls are audibly correct (readback-verified)  
✅ MANUAL_REQUIRED checklist is accurate and complete  
✅ UNRESOLVED items are documented with clear reasons  
✅ User can follow checklist to reach 100% if desired  
✅ Manifest is machine-readable + reusable  

---

## Failure Cases (Still Succeed)

| Case | Handling |
|------|----------|
| **serum-mcp lacks parameter entirely** | MANUAL_REQUIRED + instruction |
| **readback fails (widget display too coarse)** | MANUAL_REQUIRED + instruction |
| **video evidence insufficient** | UNRESOLVED + reason |
| **parameter exists but semantics unclear** | MANUAL_REQUIRED + note ambiguity |
| **oscillator mode-specific state** | MANUAL_REQUIRED + context-dependent instruction |

In all cases: **preset generates, manifest explains, user completes.**

---

## Final Statement

This architecture delivers:
1. **Working preset immediately** (all AUTO_VERIFIED items)
2. **Exact completion instructions** for remaining state
3. **Honest accounting** of what was done vs. what remains
4. **Machine-readable manifest** for tooling and verification

**Not 100% automatic. Better than 100% automatic: transparent + actionable.**

