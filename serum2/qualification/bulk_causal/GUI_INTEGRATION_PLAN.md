# GUI Bulk Verification Integration Plan (Step B — Corrected)

## The right architecture
Extend the existing bulk engine with a GUI observation layer. **Do not create a separate preset system.**

```
EXISTING BULK CONTEXT ENGINE
    ↓
One canonical context preset per module
    ↓
For each parameter (sequential):
    - baseline state read
    - baseline GUI read (before mutation)
    ↓
    - write safe test value
    - state readback
    - GUI read (after mutation)
    ↓
    - restore context
    - restoration state read
    - restoration GUI read
    ↓
    - evidence row: param | declared_domain | state_domain | gui_display | match_verdict
```

All happens in ONE live Serum session. No new presets per value. Attribution preserved.

## What needs to change

### 1. bulk_engine.py (run_parameter)
Add GUI observation calls alongside state observation:
```python
def run_parameter(base_body, base_obs, floor, param, backend, cfg, ...):
    # Existing: state readback + audio
    # NEW: add gui_baseline = gui_observe(backend, path)
    # NEW: add gui_after = gui_observe(backend, path) after mutation
    # NEW: add gui_restore = gui_observe(backend, path) after restore
    
    rows.append({
        ...existing fields...
        "gui_baseline": gui_baseline,
        "gui_after": gui_after,
        "gui_restore": gui_restore,
        "gui_match": analyze_gui_match(param, state_value, gui_after)
    })
```

### 2. gui_observation.py (new module)
Define the GUI observation interface:
- `gui_observe(backend, path)` → reads live UI, returns display value + tooltip
- Implementations: manual, OCR-assisted, or future automation
- Evidence structure: keeps gui_display separate from state_domain
- Semantic verdicts: MATCH | STATE_CLAMP | GUI_CLAMP | MISMATCH | UNOBSERVABLE

### 3. serum_backend.py (optional extension)
Add access to Serum's host parameter text (fallback for cases with no live UI readout):
```python
def gui_host_text(self) -> dict:
    """Returns VST3 host parameter display text (machine-readable, not user-visible UI)."""
    return {d["name"]: self.syn.get_parameter_text(d["index"]) 
            for d in self.syn.get_parameters_description()}
```

### 4. closure_ledger builder (new)
After GUI campaign, consolidate evidence into ledger_v2:
- Input: `campaign_run_v1.json` (state evidence)
- Input: `lfo_rate_rerun_evidence.json` (corrected LFO evidence)
- Input: `gui_semantic_evidence.json` (GUI observations, once captured)
- Output: `closure_ledger_v2.json` (330 parameters, all evidence merged)

## Workflow (unchanged core principle, extended observation)

### Phase 1: Prepare GUI harness
1. Define safe in-domain probes (already done via range_plan.py fix)
2. Write gui_observation.py (interface definition)
3. Integrate gui_observe() calls into bulk_worker.py
4. Plan manual GUI observation (which parameters, which contexts)

### Phase 2: Run GUI campaign
1. Load each context's canonical preset into Ableton/Serum once
2. For each parameter in that context:
   - Capture GUI baseline (the reference state display)
   - Mutate to a safe test value
   - Capture GUI after mutation
   - Restore context
   - Verify restoration via GUI
3. Record: param | declared_domain | state | gui_display | match_verdict

### Phase 3: Evidence consolidation
1. Merge campaign_run_v1 + lfo_rerun + gui_semantic → ledger_v2
2. Identify CLOSED (all gates passed), STATE_QUALIFIED_UI_PENDING (state OK, GUI pending), UNOBSERVABLE, etc.
3. Flag any STATE ≠ GUI mismatches as critical

### Phase 4: Authority preparation
1. Batch all evidence-backed corrections: domain fixes, enum additions, identity merges
2. Submit for review (do NOT apply until approved)

### Phase 5: Promotion
Only CLOSED controls move to binding → contract → admission → compiler

## Key distinctions (preserved)
- **Declared domain** (schema)
- **State domain** (what VST3 stores)
- **GUI effective domain** (what UI can display/read)
- **Host text** (machine-readable VST3 display, not user-visible UI)
- **Actual UI observation** (user sees this on screen)

Never collapse these. Each is separate evidence.

## Range characterization (corrected)
Per parameter, record:
- Declared: [min, max]
- Safe probes: [values within declared domain]
- State observed: [reachable_min, reachable_max] (from mutation attempts)
- GUI effective: [display_min, display_max] (from GUI observations, if available)

Do NOT blindly probe outside declared domain. (We learned this from LFO rate crashes.)

## Safety rule (from LFO bisection)
- range_plan now clamps probes to declared bounds
- Out-of-domain probes only if explicitly authorized (separate safety experiment)
- All six lfo*.rate now pass with safe probes

## Output (no changes to authority artifacts)
- `gui_semantic_evidence.json` — new evidence only
- `closure_ledger_v2.json` — derived from combined evidence
- (authority files unchanged: binding table, registry, contracts, Atlas)

## Timeline
- Phase 1 (harness setup): 1–2 hours (code integration)
- Phase 2 (GUI campaign): 30–60 min (live Serum observation)
- Phase 3 (consolidation): 1 hour (merging evidence)
- Phase 4–5 (authority + promotion): after GUI evidence is complete

## This preserves
- Bulk engine principle (one context, many sequential mutations)
- Attribution (each row is one parameter, one value)
- Evidence separation (declared ≠ state ≠ GUI, never collapsed)
- Historical evidence (no rewrites, only new artifacts)
- Safety (safe probes only, out-of-domain experiments separate)
