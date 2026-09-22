# STEP 1B — RECONCILIATION FRAMEWORK

**Date:** September 23, 2026  
**Status:** Fingerprint complete, reconciliation ready

---

## Critical Finding: Actual MCP Runtime vs. Earlier Analysis

### The Ground Truth (from live serum-mcp `list_parameters()`)

| Metric | Value | Source |
|--------|-------|--------|
| Live serum-mcp top-level modules | 26 | runtime call |
| Live serum-mcp execution parameters | **448** | list_parameters() |
| serum-mcp schema.py raw | 596 | code inspection |
| Earlier instance-weighted estimate | 1,589 | (discarded) |
| Atlas semantic records | 908 | serum_atlas.py |

**What this means:**
- **448** = execution parameters serum-mcp actually exposes (client-facing, generation-relevant)
  - Includes: oscillator, filter, envelope, LFO, macro, global, mod matrix, FX, arp
  - Excludes: SampleOsc (alternative engine), VoicePanel (GUI), RoutingSlot (internal), some nested structures
- **596** = schema.py raw (internal schema with alternative engines and GUI state)
- **1,589** = instance-weighted calculation (discarded — this was schema × instances, not parameter types)
- **908** = Atlas semantic records (your canonical control identities; each maps to 1+ of the 448 MCP parameters)

**Reconciliation logic:**
```
Atlas 908 semantic items
    ↓
Each maps to 1+ of the 448 MCP parameters
    ↓
MCP 448 parameters
    ↓
Each applied to N instances in Serum engine
    ↓
Serum 2.0.21 live state
```

---

## The Three Universes

### 1. MCP RUNTIME (448 parameters)

Live serum-mcp `list_parameters()` breakdown:

**Sound-design parameters:**
- oscillator: 17 (shared across OSC A/B/C/Noise/Sub)
- wavetable_oscillator: 9
- noise_oscillator: 3
- sub_oscillator: 1
- granular_oscillator: 34
- multisample_oscillator: 17
- spectral_oscillator: 15
- voice_filter: 10
- envelope: 8
- lfo: 12
- macro: 1
- global: 25

**Execution infrastructure:**
- mod_matrix_slot: 13 (per-slot routing params)
- mod_source_ids: 50 (source enum values)
- mod_dest_targets: 96 (destination enum values)
- arp: 6
- arp_clip: 26
- fx_params: 16
- fx_type_ids: 16

**Reference/schema data:**
- simple_filter_types: 11
- simple_wavetables: 12
- simple_warp_modes: 11
- simple_sub_shapes: 5
- simple_arp_shapes: 16
- multisample_instruments: 10
- role_starting_points: 8

**Total: 448 unique parameters**

### 2. ATLAS SEMANTIC UNIVERSE (908 records)

From your existing `serum_atlas.py`:

- 879 VERIFIED (user-controllable, observed)
- 23 PROVEN_NOT_USER_CONTROL (internal state, not editable)
- 6 UNVERIFIED_CANDIDATE (uncertain status)

Each record has a canonical `control_id` (e.g., `oscA.unison`, `filter1.cutoff`, `lfo3.rate`).

**Key property:** These are INSTANCES, not parameter types.
- Example: `lfo1.rate`, `lfo2.rate`, ..., `lfo10.rate` = 10 Atlas records mapping to 1 MCP parameter `lfo.rate`

### 3. SERUM 2.0.21 LIVE STATE

What the installed Serum 2.0.21 actually supports, verified by:
- Live MCP operations (write → Serum)
- Live UI readback (screenshot verification)
- Raw CBOR state inspection

---

## Step 1B Reconciliation Task

### Input:
- MCP 448 parameters (ground truth from live runtime)
- Atlas 908 semantic records (canonical identities)
- existing `SERUM_CONTROL_LAYER_MATRIX.json` (prior evidence)
- Serum 2.0.21 snapshot (expected parameter schema)

### Process:

**Phase 1: Map Atlas → MCP**

For each Atlas control_id:
```
atlas_id (e.g., lfo1.rate)
    ↓
which MCP parameter? (e.g., lfo.rate)
    ↓
does MCP parameter exist? (check 448)
    ↓
if yes: MAPPED
if no: EXECUTION_GAP
```

**Phase 2: Cross-check MCP → Atlas**

For each MCP parameter:
```
mcp_parameter (e.g., lfo.rate)
    ↓
how many Atlas records use it? (e.g., lfo1.rate, lfo2.rate, ..., lfo10.rate)
    ↓
are all 10 mapped? or gaps?
```

**Phase 3: Verify Against Snapshot**

For each MCP parameter:
```
does serum_2_0_21_schema_snapshot.json
contain an equivalent field?
    ↓
if yes: version-compatible
if no or different: FLAG FOR LIVE TEST
```

**Phase 4: Live Testing (batch by mechanism)**

Test representative items:
- Scalar parameters (1-2 per category)
- Enum parameters (1-2 per category)
- Oscillator nested state
- Matrix routing
- FX parameters
- Curve/structured state

Not all 908, just enough to verify each MECHANISM works.

**Phase 5: Classify Every Row**

For each Atlas record:

```json
{
  "canonical_id": "lfo1.rate",
  "semantic_status": "VERIFIED",
  "mcp_mapping": "lfo.rate",
  "mcp_modeled": true,
  "mcp_authorable": true,
  "mcp_roundtrip": true,
  "serum_2021_verified": "yes",
  "live_readback": "unverified",
  "representation": "float",
  "gap_type": null,
  "evidence": "live MCP runtime + snapshot match",
  "status": "KNOWN"
}
```

Status values:
- **KNOWN** — MCP knows it, snapshot has it, ready to test
- **MAPPED** — Atlas → MCP mapping exists, need live test
- **AUTHORABLE** — Can be written via MCP, need readback proof
- **2.0.21_VERIFIED** — Confirmed to work on installed Serum
- **READBACK_VERIFIED** — UI/raw state proves value was set
- **EXECUTION_GAP** — MCP doesn't expose it
- **REPRESENTATION_GAP** — MCP knows it but doesn't model for generation
- **ROUNDTRIP_ONLY** — MCP preserves but doesn't generate
- **UNRESOLVED** — Mapping unclear or conflicting
- **OUT_OF_SCOPE** — Intentionally excluded (GUI, MIDI, MPE, etc.)

---

## Current Inventory State (What We Already Have)

| Source | Records | Status | Use in 1B |
|--------|---------|--------|-----------|
| serum_atlas.py | 908 semantic | VERIFIED/UNVERIFIED/NOT_CONTROL | Primary universe |
| SERUM_CONTROL_LAYER_MATRIX.json | 908+396 | Existing evidence | Reuse, extend |
| semantic_vst3_mapping.json | 18 | Legacy VST3 mappings | Cross-reference only |
| expected_inventory.py | dynamic | Episode-specific | Not for universal 1B |
| MCP runtime | 448 | Ground truth | Execution source |

---

## What STEP 1B Will Deliver

**Machine-readable reconciliation table:**
```
STEP_1B_RECONCILIATION_MATRIX.json
├── 908 rows (one per Atlas record)
└── 16 columns (canonical_id, mcp_mapping, status, evidence, etc.)
```

**Human-readable summary:**
```
STEP_1B_RECONCILIATION_SUMMARY.md
├── MCP ↔ Atlas mapping completeness
├── Gap categories and counts
├── Live test results by mechanism
└── Recommendations for Step 3 (close gaps)
```

**No implementation changes yet.**
Only evidence collection and classification.

---

## Next Immediate Action

**Phase 1: Map Atlas 908 → MCP 448**

For every Atlas record, determine:
1. Which MCP parameter it maps to (if any)
2. Does that MCP parameter exist in the live runtime?
3. Populate reconciliation table

This is mechanical work, no guessing.

Then we batch-test to verify the mappings work.

