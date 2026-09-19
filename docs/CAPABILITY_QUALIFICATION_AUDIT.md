# Capability Qualification Audit — 5 B1-Resolved Targets

**Measurement Date:** 2026-09-20  
**Frozen Tutorial:** 2c0h3z41K58  
**Current Status:** All 5 refuse at CAPABILITY_RESOLUTION (no contract)  

---

## Audit Methodology

For each target, this document traces:
1. **Reference Coverage** — does Atlas know about it?
2. **Brain Coverage** — does B1 resolve it?
3. **Capability Coverage** — is there a contract? binding?
4. **Binding Coverage** — which VST3 parameter name?
5. **Evidence** — what execution/readback evidence exists?
6. **Qualification Path** — what's needed to execute?

---

## Target 1: Env2.Decay (`envelope2_field_decay`)

### Current State
```
Reference:       ✅ EXACT (Atlas knows "Env2.Decay" → "env2.decay")
Brain:           ✅ B1_CANONICAL (ProducerBrain resolves to canonical target)
Capability Key:  ✅ envelope2_field_decay (derived from SEMANTIC_TARGETS)
Contract:        ❌ MISSING
Binding:         ❌ MISSING (no VST3 mapping entry)
```

### Evidence Available
- **Visual (Stage A):** Observed change in frozen 2c0h3z41K58 event 2 (30-110s)
  - Before: 1.00 s
  - After: 1.77 s
  - Screen region: "ENV panel readout row [identity basis: tab highlighted: ENV2]"
  
### What Exists for Comparison: Env1.Decay
```
Reference:       ✅ EXACT (Atlas → "env1.decay")
Brain:           ✅ Legacy (LEGACY path for natural-language queries)
Capability Key:  ✅ envelope_field_decay
Contract:        ✅ CAUSAL_VERIFIED
  - allowed_operation: mutate_numeric_value
  - status: CAUSAL_VERIFIED
  - prerequisites: (none)
Binding:         ✅ HOST_PARAMETER → "Env 1 Decay" (from semantic_vst3_mapping.json)
Execution Path:  ✅ serum-mcp can set via HOST_PARAMETER
Readback:        ✅ VST3 parameter readback confirms the value
```

### To Make Env2.Decay Executable
**Required (minimum):**
1. Add `"envelope2_field_decay": "Env 2 Decay"` to `semantic_vst3_mapping.json`
2. Create a CapabilityContract for `envelope2_field_decay`
   - Copy structure from `envelope_field_decay` (Env1)
   - Set `allowed_operation: "mutate_numeric_value"`
   - Set `status: ??` (CAUSAL_VERIFIED or STRUCTURAL_ONLY, depending on evidence)
   - Attach ExecutionBinding to "Env 2 Decay"

**Evidence Bar for Status:**
- **STRUCTURAL_ONLY:** Env2.Decay can be set via VST3 parameter + readback works (no causal requirement)
- **CAUSAL_VERIFIED:** Same as Env1.Decay, meaning we'd need to measure before/after audio and prove the causal effect

**Decision Point:** Do we have causal evidence? The frozen tutorial shows the value changed (1.00 → 1.77), but:
- Is that a causal effect or just a GUI readback?
- Would serum-mcp actually be able to set it?
- Does readback confirm it persisted?

**Next Step:** Check if serum-mcp can address "Env 2 Decay" via VST3 parameter interface.

---

## Target 2: Env2.Sustain (`envelope2_field_sustain`)

### Current State
```
Reference:       ✅ EXACT (Atlas → "env2.sustain")
Brain:           ✅ B1_CANONICAL
Capability Key:  ✅ envelope2_field_sustain
Contract:        ❌ MISSING
Binding:         ❌ MISSING
```

### Evidence Available
- **Visual (Stage A):** Observed change in frozen 2c0h3z41K58 event 2
  - Before: 100%
  - After: – (dash, unclear what this means — maybe muted/off)
  
### Comparison: Env1.Sustain
```
Contract:        ✅ CAUSAL_VERIFIED (envelope_field_sustain)
Binding:         ✅ HOST_PARAMETER → "Env 1 Sustain"
```

### To Make Env2.Sustain Executable
**Required:**
1. Add `"envelope2_field_sustain": "Env 2 Sustain"` to `semantic_vst3_mapping.json`
2. Create CapabilityContract for `envelope2_field_sustain`
   - allowed_operation: `mutate_numeric_value`
   - ExecutionBinding to "Env 2 Sustain"

**Note:** The observed value "–" is unclear. Need to inspect stage_a_observation.json to understand what the "after" state actually represents.

---

## Target 3: OSCb.Enabled (`oscillator_field_OSC2-ENABLE`)

### Current State
```
Reference:       ✅ EXACT (Atlas → "oscb.enabled")
Brain:           ✅ B1_CANONICAL
Capability Key:  ✅ oscillator_field_OSC2-ENABLE
Contract:        ❌ MISSING
Binding:         ✅ EXISTS in semantic_vst3_mapping.json
  → Maps to "B Enable"
```

### Evidence Available
- **Visual (Stage A):** Observed change in frozen 2c0h3z41K58 event 2
  - Before: off
  - After: on

### Comparison: Env1.Enable (if it exists)
- No existing Env1-equivalent toggle for oscillator enable
- But Env1 uses the same pattern as other oscillators (A Enable, B Enable, C Enable)

### To Make OSCb.Enabled Executable
**Required:**
1. Create CapabilityContract for `oscillator_field_OSC2-ENABLE`
   - allowed_operation: `mutate_enum_value` (toggle on/off)
   - ExecutionBinding to "B Enable" (already in mapping)

**Note:** The binding already exists! Only the contract is missing. This is the simplest candidate.

---

## Target 4: LFO1.Rate (`lfo_field_lfo1_rate`)

### Current State
```
Reference:       ✅ EXACT (Atlas → "lfo1.rate")
Brain:           ✅ B1_CANONICAL
Capability Key:  ✅ lfo_field_lfo1_rate
Contract:        ❌ MISSING
Binding:         ❌ MISSING (no VST3 mapping entry)
```

### Evidence Available
- **Visual (Stage A):** Observed change in frozen 2c0h3z41K58 event 4 (60-90s)
  - Before: 1/4
  - After: 4.5 Hz

### To Make LFO1.Rate Executable
**Required:**
1. Find or infer the VST3 parameter name for LFO1 rate (likely "LFO 1 Rate")
2. Add to `semantic_vst3_mapping.json`
3. Create CapabilityContract for `lfo_field_lfo1_rate`
   - allowed_operation: `mutate_numeric_value`
   - ExecutionBinding to "LFO 1 Rate"

---

## Target 5: Filter1.Enabled (`filter_field_ENABLE`)

### Current State
```
Reference:       ✅ EXACT (Atlas → "filter1.enabled")
Brain:           ✅ B1_CANONICAL
Capability Key:  ✅ filter_field_ENABLE
Contract:        ❌ MISSING
Binding:         ❌ MISSING (no VST3 mapping entry)
```

### Evidence Available
- **Visual (Stage A):** Observed change in frozen 2c0h3z41K58 event 5 (60-170s)
  - Before: off
  - After: on

### To Make Filter1.Enabled Executable
**Required:**
1. Find or infer VST3 parameter name (likely "Filter 1 Enable" or similar)
2. Add to `semantic_vst3_mapping.json`
3. Create CapabilityContract for `filter_field_ENABLE`
   - allowed_operation: `mutate_enum_value` (toggle)
   - ExecutionBinding to the discovered parameter name

---

## Summary Table

| Target | Reference | Brain | Contract | Binding | VST3 Param | Priority |
|--------|-----------|-------|----------|---------|------------|----------|
| **Env2.Decay** | ✅ | ✅ | ❌ | ❌ | Inferred: "Env 2 Decay" | 1 (has Env1 analog) |
| **Env2.Sustain** | ✅ | ✅ | ❌ | ❌ | Inferred: "Env 2 Sustain" | 2 (Env1 analog) |
| **OSCb.Enabled** | ✅ | ✅ | ❌ | ✅ | "B Enable" | **1** (binding exists!) |
| **LFO1.Rate** | ✅ | ✅ | ❌ | ❌ | Inferred: "LFO 1 Rate" | 3 |
| **Filter1.Enabled** | ✅ | ✅ | ❌ | ❌ | Inferred: "Filter 1 Enable" | 4 |

---

## Recommended Next Steps

### Step 1: Verify VST3 Parameter Names
Before creating contracts, confirm the actual VST3 parameter names in Serum 2.0.21:
- "Env 2 Decay", "Env 2 Sustain", "Env 2 Attack", "Env 2 Release"
- "LFO 1 Rate" (and LFO 2, 3, 4 if used)
- "Filter 1 Enable"

**Method:** Check existing execution results or VST3 parameter enumeration.

### Step 2: Start with OSCb.Enabled
Since the binding already exists, this is the fastest path to prove the full chain:
- Create contract for `oscillator_field_OSC2-ENABLE`
- Run full chain: B1 → Capability Resolution → Admission → serum-mcp → readback
- Verify toggle actually changes the oscillator enable state

### Step 3: Qualify Env2 Targets
Once OSCb.Enabled works, expand to Env2.Decay and Env2.Sustain (they follow the same pattern as Env1).

### Step 4: Expand to Filter/LFO
Once the pattern is proven, add Filter1.Enabled and LFO1.Rate.

---

## Authority Boundaries (Do NOT Change)

These contracts will **NOT:**
- Grant execution authority (Admission still gates all execution)
- Bypass TargetResolver (canonical target identity is unchanged)
- Invent parameters or mappings (only use discovered VST3 names)
- Hardcode tutorial-specific values
- Create genre/artist/timestamp rules

They WILL:
- Declare that serum-mcp CAN mutate these VST3 parameters
- Attach evidence for the execution path
- Enable the full Producer Brain → Admission chain to succeed

---

**Status:** Audit complete. Ready to implement contracts for OSCb.Enabled (priority 1).
