# Group 1: Filter Enable Real Qualification Plan

**Date:** 2026-09-21  
**Epoch:** 2.0.23@9293eb90  
**Target:** filter1.enabled, filter2.enabled  
**Pipeline:** Generic StructuralQualificationRunner (no parameter-specific logic)

---

## Current State (Preflight → Qualification)

### What We Know (Preflight)
- **Semantic Targets:** Filter.Enable, Filter2.Enable (in compiler/targets.py SEMANTIC_TARGETS)
- **Atlas Controls:** filter1.enabled, filter2.enabled (in serum_atlas.py)
- **kParam Existence:** VoiceFilter0.kParamEnable, VoiceFilter1.kParamEnable (confirmed in schema snapshot)
- **Operand Kind:** toggle (boolean)
- **Mutation Targets:** VoiceFilter[0..1].plainParams.kParamEnable (inferred from kParam structure)

### What Needs to Happen (Qualification)

```
Preflight discovers: "Filter Enable kParam exists"
         ↓
Generic Planner classifies: NEEDS_BINDING (no execution binding yet)
         ↓
StructuralQualificationRunner probes the actual preset/body
         ↓
Serum-MCP mutates filter1.enabled toggle → observe body state change
         ↓
Record evidence: before/after/reload state confirmations
         ↓
Verify mutation target (which exact path changed?)
         ↓
Create ExecutionBinding from proven evidence
         ↓
Persist binding → preset_structural_mapping.json
         ↓
Admission: Filter.Enable now resolves to execution-eligible contract
         ↓
AuthorizedOperation: can be compiled and executed
```

---

## Exact Qualification Pipeline

### 1. Classification via QualificationPlanner

**Current State:**
```python
planner = QualificationPlanner()  # Loads SEMANTIC_TARGETS + mappings
plan = planner.plan()
```

**Expected Classification:**
```
Target: "Filter.Enable"
  ├─ Semantic Target: Filter.Enable (exists in targets.py)
  ├─ Capability Key: filter_field_enable (semantic reference)
  ├─ Atlas Control: filter1.enabled (control_type="toggle")
  ├─ Body Mapping: MISSING (not in body_state_mapping.json)
  ├─ Preset Mapping: MISSING (not in preset_structural_mapping.json)
  ├─ Host Mapping: MISSING (not in semantic_vst3_mapping.json)
  └─ BUCKET: NEEDS_BINDING (route_type=UNBOUND, verified=False)
  
Target: "Filter2.Enable"
  ├─ Same as Filter.Enable
  └─ BUCKET: NEEDS_BINDING
```

**Result:** Both targets land in `plan.needs_binding` (list of BindingCandidates)

---

### 2. Execution via StructuralQualificationRunner

**Setup:**
```python
from serum2.producer.batch_qualification_system import (
    QualificationPlanner,
    StructuralQualificationRunner,
    MutationSpec,
)
from serum2.producer.serum_mcp_qualification_backend import SerumMCPPresetBackend

# Fixture: A real .SerumPreset with Filter Enable observed state known
FIXTURE = Path.home() / "Documents" / "Xfer" / "Serum 2 Presets" / "Presets" / "User" / "VLP1-Filter-Enable-Test.SerumPreset"

# Backend: serum-mcp interface to the preset
backend = SerumMCPPresetBackend(str(FIXTURE))

# Runner: Generic mutation executor
runner = StructuralQualificationRunner(backend)

# Get the candidate from the NEEDS_BINDING bucket
(candidate,) = [t for t in planner.plan().needs_binding if t.target == "Filter.Enable"]
```

**Mutation:**
```python
# Read current state from fixture
baseline = backend.read(candidate)  # e.g., {"value": True, "enabled": True}

# Mutate to opposite state (toggle)
target_value = not baseline

# Execute mutation through generic runner
result = runner.run(
    candidate,
    MutationSpec(
        target="Filter.Enable",
        value=target_value,
        operation="toggle"
    )
)
```

**Evidence Captured:**
```python
result.baseline          # State before mutation (preset file)
result.after_mutation    # State after serum-mcp edit_preset() call
result.after_reload      # State after re-reading file (persistence check)
result.state_changed     # Boolean: did the mutation succeed?
result.persistence_verified  # Boolean: did the change stick in file?
result.status            # "SUCCESS" | "FAILED" | ...
result.verification_level  # "FILE_VERIFIED_ONLY" (no live plugin)
```

---

### 3. Evidence Recording

**Persisted JSON Structure (evidence_filter1_enable.json):**
```json
{
  "semantic_target": "Filter.Enable",
  "capability_key": "filter_field_enable",
  "qualified_at": "2026-09-21T...",
  "backend": "serum-mcp (describe_preset / edit_preset, in-process)",
  "route_type": "UNBOUND",
  "fixture_preset_path": "...",
  "fixture_preset_sha256_before": "...",
  "fixture_preset_sha256_after": "...",
  "baseline": {
    "VoiceFilter0.plainParams.kParamEnable": 1.0
  },
  "mutation": {
    "value": 0.0
  },
  "post_mutation": {
    "VoiceFilter0.plainParams.kParamEnable": 0.0
  },
  "after_reload": {
    "VoiceFilter0.plainParams.kParamEnable": 0.0
  },
  "state_change_verified": true,
  "persistence_verified": true,
  "verification_level": "FILE_VERIFIED_ONLY",
  "status": "SUCCESS",
  "tier": "FILE_VERIFIED_ONLY",
  "notes": "File-level structural qualification through serum-mcp."
}
```

---

### 4. Binding Discovery from Evidence

**From successful evidence, infer:**
```python
ExecutionBinding(
    mutation_type="SERUM_PRESET_STRUCTURAL",
    body_path="VoiceFilter0.plainParams.kParamEnable",
    host_parameter_name=None,
    binding_source="qualification/evidence/evidence_filter1_enable.json",
    binding_version="2.0.23",
    resolver_operation_id="serum-mcp.edit_preset"
)
```

---

### 5. Register Binding → preset_structural_mapping.json

**Add to qualification/preset_structural_mapping.json:**
```json
{
  "bindings": {
    "filter_field_enable": {
      "mutation_type": "SERUM_PRESET_STRUCTURAL",
      "body_path": "VoiceFilter0.plainParams.kParamEnable",
      "evidence_source": "Phase-α Group 1 real qualification (filter1.enabled)",
      "semantic_target": "Filter.Enable",
      "unit": "toggle (0=off, 1=on)"
    },
    "filter_field_enable_filter2": {
      "mutation_type": "SERUM_PRESET_STRUCTURAL",
      "body_path": "VoiceFilter1.plainParams.kParamEnable",
      "evidence_source": "Phase-α Group 1 real qualification (filter2.enabled)",
      "semantic_target": "Filter2.Enable",
      "unit": "toggle (0=off, 1=on)"
    }
  }
}
```

---

### 6. Admission: Evidence → Contract

**After binding is registered:**
```python
# Re-run planner with updated mappings
planner = QualificationPlanner()  # Reloads mappings
plan = planner.plan()

# Filter.Enable now classified as:
target = [t for t in plan.ready_for_structural if t.target == "Filter.Enable"][0]
# ✓ route_type = RouteType.SERUM_PRESET_STRUCTURAL_BINDING
# ✓ binding = ExecutionBinding(...)
# ✓ verified = True
```

**CapabilityContract created:**
```python
contract = CapabilityContract(
    target="filter_field_enable",
    status=STRUCTURAL_ONLY,  # No causal evidence yet (file-level only)
    scope={
        "mutation_target_path": "VoiceFilter0.plainParams.kParamEnable",
        "operand_kind": "toggle",
        "prerequisite": None,
    },
    execution_binding=ExecutionBinding(...),
    admission_evidence={"status": "STRUCTURAL_ONLY"},
    contract_epoch=EPOCH_2_0_23.binary_sha256,
)
```

---

### 7. Admission Admission → AuthorizedOperation

**During run_reference_reproduction():**
```python
rows = build_all(stage_a, reread, corrections)
admission = admit_rows(rows, epoch)

# For filter1.enabled row:
# ├─ structural_key: "VoiceFilter0.kParamEnable" ✓ resolves
# ├─ contract: "filter_field_enable" ✓ found in registry
# ├─ execution_binding: ExecutionBinding(...) ✓ verified
# └─ ADMISSION: "ADMITTED" ✓

# Generate AuthorizedOperation:
auth_op = AuthorizedOperation(
    operation_id="filter1.enabled@-",
    canonical_target="filter1.enabled",
    operation="TOGGLE_OFF",
    operand=False,
    binding={"kind": "field", "path": "VoiceFilter0.plainParams.kParamEnable"},
    contract_key="filter_field_enable",
    contract_binding="serum_mcp.edit_preset",
    execution_path="VoiceFilter0.plainParams.kParamEnable",
    contract_body_path="VoiceFilter0.plainParams.kParamEnable",
    binding_type="SERUM_PRESET_STRUCTURAL",
    admission_evidence={"status": "ADMITTED"},
    provenance={"rack": None, "frame_ts": 0.0},
)
```

---

### 8. Compilation → Preset Mutation

**Generic compiler accepts AuthorizedOperation:**
```python
result = compile_ops([auth_op], "test", "filter enable test", EPOCH_2_0_23)
# ✓ status = "SUCCESS"
# ✓ compiled = 1
# ✓ no missing or unauthorized operations
```

**Mutation applied to preset:**
```python
# Compiler → serum-mcp.generate_preset() call
spec = AuthorizedStateSpec(
    operations=[auth_op, ...],
    epoch=EPOCH_2_0_23,
)
# → .SerumPreset file written with filter enabled/disabled as observed
```

---

### 9. Verification: File & UI Readback

**File Readback Comparison:**
```python
readback_file = read_back_file(preset_path)
# Compare filter1.enabled observed value vs. compiled value
# Expected match (or normalized match)
```

**Direct Serum UI Readback:**
```python
# Load preset in Serum VST3 plugin
# Read Filter 1 enable state from UI
# Verify it matches the compiled state
```

---

## Hard STOP Conditions (Must All Pass)

Before proceeding to Group 2, **all 8 conditions must be true:**

```
[✓ or ✗] 1. Real mutation succeeded.
           Evidence: result.status == "SUCCESS"
           
[✓ or ✗] 2. Direct Serum readback confirms the intended state.
           Evidence: file_readback["filter1.enabled"] == observed_value
           
[✓ or ✗] 3. Execution binding is independently proven.
           Evidence: ExecutionBinding object created from evidence, not inferred
           
[✓ or ✗] 4. Contract scope is recorded from evidence, not inferred.
           Evidence: mutation_target_path recorded in CapabilityContract.scope
           
[✓ or ✗] 5. Compiler accepts the resulting AuthorizedOperation.
           Evidence: compile_ops() returns status="SUCCESS"
           
[✓ or ✗] 6. No hardcoded parameter-specific execution logic was added.
           Evidence: StructuralQualificationRunner used unchanged, no new if/else for "filter"
           
[✓ or ✗] 7. Existing 9-operation regression remains green.
           Evidence: test_frozen_nine_operation_live_ui_regression() passes
           
[✓ or ✗] 8. Full test suite remains green.
           Evidence: pytest serum2/ returns 0 failures
```

**All 8 must pass. If any fails, do not proceed to Group 2. Stop and investigate.**

---

## What NOT to Do

```python
# ✗ DO NOT write parameter-specific logic:
if target == "filter1.enabled":
    path = "VoiceFilter0.plainParams.kParamEnable"
    
# ✓ DO use generic runner:
result = runner.run(candidate, MutationSpec(...))

# ✗ DO NOT infer binding from semantic name:
binding = ExecutionBinding(body_path="inferred_from_name")

# ✓ DO record binding from evidence:
binding = ExecutionBinding(
    body_path=evidence["post_mutation"].keys()[0],  # Actual path from readback
)

# ✗ DO NOT count as "newly admitted" until full chain completes:
# Wrong: "filter1.enabled is now qualified"
# Right: "filter1.enabled evidence exists; pending compilation/verification"

# ✓ DO only report when full chain reaches verification:
# "filter1.enabled: ADMITTED → COMPILED → VERIFIED_EXACT"
```

---

## Expected Outcomes

### Success Path
```
filter1.enabled
  ├─ Qualification: SUCCEEDED (FILE_VERIFIED_ONLY)
  ├─ Admission: ADMITTED
  ├─ Compilation: SUCCESS
  ├─ File Readback: VERIFIED_EXACT
  ├─ UI Readback: VERIFIED_EXACT
  └─ Result: +1 operation admitted, +~1 reference row covered
     Coverage: 9 + 1 = 10 / 178 (5.6%)
  
filter2.enabled (parallel, same contract)
  └─ Result: +1 operation admitted
     Coverage: 10 / 178 (5.6%)
     
Group 1 Total: +2 operations, +2 rows, 1 contract (filter_enable)
```

### Failure Modes (Stop & Investigate)
```
Failure #1: Mutation fails
  Evidence: result.status != "SUCCESS"
  Action: Check preset fixture, verify kParam writable
  
Failure #2: Readback mismatch
  Evidence: file_readback != expected
  Action: Verify serum-mcp describe_preset accuracy
  
Failure #3: Compiler rejection
  Evidence: compile_ops() raises UnauthorizedOperation
  Action: Review binding_type, contract_domain, scope
  
Failure #4: Regression breaks
  Evidence: test_frozen_nine_operation_live_ui_regression() fails
  Action: Review changes to admission/binding tables
```

---

## Success Criteria

### Definition: Group 1 COMPLETE
```
BOTH filter1.enabled AND filter2.enabled:
  ✓ Qualification evidence recorded
  ✓ Execution binding persisted
  ✓ Contract created
  ✓ Admission resolved to ADMITTED
  ✓ AuthorizedOperation compiled
  ✓ File readback verified
  ✓ UI readback verified
  ✓ Regression suite green
  ✓ Full test suite green
```

### Then Report
```
Group 1: COMPLETE
  Operations: 2 (filter1.enabled, filter2.enabled)
  New Contract: 1 (filter_enable)
  Coverage Gain: 2 rows (~1.1%)
  Total Admitted: 9 + 2 = 11 operations
  Total Coverage: 11 / 178 (6.2%)
  
READY FOR: Group 2 (Osc Fine) OR Tier 2 (FX Hyper)
```

---

## No Code Written Yet

This document describes the pipeline. **No real qualification has begun.**

Ready to execute when authorized.

