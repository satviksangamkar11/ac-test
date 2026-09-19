# Binding Discovery: Frozen 5 Targets

**Date:** 2026-09-20  
**Method:** Authoritative surface inventory search  
**Source:** SERUM2_SEMANTIC_INVENTORY_FINAL.json (908 VST3 parameters)

---

## Summary

| Target | Canonical Name | Status | Binding Source | Evidence |
|--------|----------------|--------|-----------------|----------|
| OSC2.Enable | oscillator_field_OSC2-ENABLE | **FOUND** | VST3 (MIXER) | "B Enable -- channel on/off toggle" |
| LFO1.Rate | lfo_field_lfo1_rate | **FOUND** | VST3 (LFO) | "Rate" (6 instances, LFO1 = 1st) |
| Env2.Decay | envelope2_field_decay | **NOT FOUND** | ? | ENV section has generic labels, no per-slot numbering |
| Env2.Sustain | envelope2_field_sustain | **NOT FOUND** | ? | ENV section has generic labels, no per-slot numbering |
| Filter.Enable | filter_field_ENABLE | **NOT FOUND** | ? | FILTER section has no enable toggle |

---

## Detailed Findings

### 1. OSC2.Enable → oscillator_field_OSC2-ENABLE

**Authority:** SERUM2_SEMANTIC_INVENTORY_FINAL.json, MIXER section

**Inventory Entry:**
```
semantic_id: (OSC_B.ENABLE)
section: MIXER
module: OSC_B Channel
label: "B Enable -- channel on/off toggle"
control_type: toggle
```

**Assessment:** 
- ✅ Exact match: "B Enable" is the VST3 parameter for OSC2.Enable
- ✅ Control type matches (toggle)
- ✅ Inventory observation now **verified as authoritative**

**Next Step:** Create `BindingCandidate(verified=True)` with binding to "B Enable"

---

### 2. LFO1.Rate → lfo_field_lfo1_rate

**Authority:** SERUM2_SEMANTIC_INVENTORY_FINAL.json, LFO section

**Inventory Entries (6 instances):**
```
Label: "Rate"  (appears 6 times in LFO section)
section: LFO
modules: LFO1, LFO2, LFO3, LFO4, LFO5, LFO6
control_type: continuous
```

**Assessment:**
- ✅ Parameter "Rate" exists in LFO section
- ⚠ NOT disambiguated: 6 LFO slots, need to confirm LFO1 is first
- ⚠ No module-specific label (e.g., "LFO 1 Rate") in inventory

**Next Step:** Verify VST3 parameter indexing (LFO1 = first Rate parameter) via serum-mcp or preset inspection

---

### 3. Env2.Decay → envelope2_field_decay

**Authority:** SERUM2_SEMANTIC_INVENTORY_FINAL.json, ENV section

**Inventory Entries (generic):**
```
Labels:
  - "Attack"
  - "Hold"
  - "Decay"
  - "Sustain"
  - "Release"
  - "BPM MS toggle"
  - "Legato Inverted"
  - (and 40+ more)
```

**Assessment:**
- ❌ ENV section has generic labels with NO per-slot numbering
- ❌ "Decay" exists, but cannot disambiguate Env1 vs Env2 vs Env3 vs Env4
- ❌ **Inventory does not contain per-envelope indexing**

**Next Step:** Query body-state schema (preset body structure) to find Envelope2 decay path

---

### 4. Env2.Sustain → envelope2_field_sustain

**Assessment:** Same as Env2.Decay — generic ENV labels, no per-slot indexing.

---

### 5. Filter.Enable → filter_field_ENABLE

**Authority:** SERUM2_SEMANTIC_INVENTORY_FINAL.json, FILTER section

**Inventory Entries (first 15):**
```
  - Cutoff
  - Resonance
  - Drive
  - FAT
  - FREQ
  - MORPH
  - SMOOTH
  - LP FRQ
  - (and 58+ more)
```

**Assessment:**
- ❌ No "Enable" or "on/off toggle" in FILTER section inventory
- ❌ **Filter does not appear to have an enable control in VST3 interface**

**Next Step:** Check if filter enable is:
1. A body-state-only control (not exposed via VST3)
2. Not a capability (filter is always on)
3. Named differently (e.g., "Bypass")

---

## Next Actions (Priority)

1. **High Priority — Verify LFO1.Rate indexing**
   - Confirm "Rate" parameter sequence: LFO1 = 1st Rate
   - Use serum-mcp or preset inspection to map Rate→LFO1

2. **High Priority — Discover Env2 body-state bindings**
   - Extract Serum 2.0.21 preset body schema
   - Find body paths for Envelope2.Decay and Envelope2.Sustain
   - Document as body_state_mapping.json entries

3. **Medium Priority — Resolve Filter.Enable**
   - Determine if capability exists or if filter is not toggleable
   - If it exists, search body-state schema or other route

4. **Confirmed — Add OSC2.Enable to semantic_vst3_mapping.json**
   - Once LFO1.Rate is verified, commit both as BindingCandidate(verified=True)

---

## Authority Boundary

- **Inventory observation** ("B Enable" seen in MIXER section) → **Now verified as authoritative VST3 binding**
- **Generic ENV labels** (Decay, Sustain without slot numbering) → **Insufficient for VST3 binding, requires body-state verification**
- **FILTER section absence** of enable control → **Requires alternative route investigation or capability exclusion**

---

**Status:** Discovery complete for VST3 surface. Body-state schema inspection deferred to next phase.

---

## Phase 3B.3 Correction: Two Independent Evidence Layers (2026-09-20)

**Critical finding:** The real `serum-mcp` MCP server does not expose a
`read_parameter(name)` / `set_parameter(name, value)` VST3 host-parameter
interface. It never loads the Serum plugin or a DAW and never renders
audio -- it reads/writes `.SerumPreset` files directly through a
structured `PresetSpec` (`generate_preset`, `edit_preset`,
`describe_preset`).

This means **"B Enable" (VST3 plugin surface) and
`oscillators[1].enabled` (serum-mcp preset-execution surface) are two
distinct evidence layers for the same semantic target, not
interchangeable representations:**

```
OSC2.Enable
  |-- REFERENCE / PLUGIN SURFACE:  VST3 "B Enable"        (inventory evidence)
  '-- PRESET / EXECUTION SURFACE:  oscillators[1].enabled  (serum-mcp evidence)
```

Route type `SERUM_PRESET_STRUCTURAL_BINDING` was added to
`batch_qualification_system.py::RouteType`, distinct from
`VST3_HOST_PARAMETER`, so this distinction is never collapsed.

### Phase 3B.3 Real Qualification (executed this session)

Following the codebase's own established pattern
(`serum2/producer/qualify_modulation_route.py`), real serum-mcp tool
calls were made and packaged into
`serum2/qualification/osc2_enable_qualification.json`:

| Step | Action | Result |
|------|--------|--------|
| 1 | `generate_preset` (fixture, Osc B enabled=True) | baseline written |
| 2 | `describe_preset` (baseline read) | `Osc B: ON` |
| 3 | `edit_preset` (`oscillators[1].enabled=False`) | applied |
| 4 | `describe_preset` (after-mutation read) | `Osc B: off`, Osc A unaffected |
| 5 | state_changed check | `ON != off` &check; |
| 6 | persist (sha256 of on-disk file) | `C4A872A1...` |
| 7 | `describe_preset` (independent reload read) | `Osc B: off` |
| 8 | persistence_verified check | matches step 4 &check; |

**Result: `STRUCTURAL_VERIFIED`, tier `FILE_VERIFIED_ONLY`.**

This is explicitly **not** `CAUSAL_VERIFIED` — no live Serum 2.0.21
plugin instance was loaded, no audio was rendered or measured. A
separate live-Serum verification stage (load the fixture into Ableton,
observe the real plugin's OSC B enable state directly) is required
before any causal claim.

### Architecture correction

The earlier `SerumMCPAdapter` (`read_parameter`/`set_parameter`) and
`SerumStructuralBackend` files were **retired** (deleted) — they modeled
a live VST3 host-parameter interface serum-mcp does not have. Automated
pytest-style mocking doesn't fit serum-mcp's nature either: it is an
MCP-tool-call surface invoked by the agent session, not an importable
Python object. The correct pattern, already established in this
codebase by `qualify_modulation_route.py`, is a script that packages
**already-obtained real tool results** into a qualification evidence
JSON — see `serum2/producer/qualify_osc2_enable.py`.
