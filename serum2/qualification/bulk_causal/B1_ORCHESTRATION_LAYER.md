# B.1: GUI Observation at Orchestration Layer (Not Engine Modification)

## Architectural constraint
**Bulk engine v1 is frozen.** Do not embed GUI logic into `bulk_engine.py` or `bulk_worker.py`.

```
bulk_engine.py (frozen v1)
    ↓
    mutation | state observation | restore
    ↓
bulk_worker.py (orchestration)
    ↓
    optional: gui_observer callback/hook
    ↓
    evidence consolidation (unify.py)
```

## Pattern: Engine remains unchanged

### Current bulk_worker.py flow:
```python
for param in manifest['parameters']:
    rec = run_parameter(base_body, base_obs, floor, param, backend, cfg, counters, meta=meta)
    # rec has: written, state_value, band_db, restoration, etc.
    records.append(rec)
```

### With GUI observation (orchestration layer):
```python
for param in manifest['parameters']:
    # Engine: baseline state
    rec = run_parameter(base_body, base_obs, floor, param, backend, cfg, counters, meta=meta)
    
    # NEW: At worker level, optionally call observer (does NOT call engine)
    if enable_gui_observation:
        gui_obs = gui_observe_parameter(backend, param, rec)  # optional hook
        rec['gui'] = gui_obs
    
    records.append(rec)
```

The engine does its job. The worker orchestrates optional observers.

## Observer hook pattern

### gui_observation.py defines:
```python
def gui_observe_parameter(backend, param, engine_record):
    """Optional observer: reads GUI after engine has finished, without modifying state.
    
    Takes the backend (already loaded with the mutated state via engine),
    reads the live UI display, then returns without further mutation.
    The engine's restore has already happened by the time this is called
    (or it's called after restoration to verify GUI restoration).
    """
    path = engine_record['candidate']['path']
    kparam = path[-1]
    
    # Read GUI (manual, OCR, or host-text fallback)
    gui_display = manual_gui_read(kparam)  # tooltip, displayed value, etc.
    
    return {
        'atlas_id': param['atlas_id'],
        'kparam': kparam,
        'gui_display_value': gui_display['value'],
        'gui_tooltip': gui_display['tooltip'],
        'observation_method': 'manual_hover',
        'matches_state': match_verdict(engine_record['state_value'], gui_display['value']),
    }
```

### bulk_worker.py calls it at orchestration level:
```python
rec = run_parameter(...)  # engine intact, frozen

if gui_observer:
    rec['gui_after'] = gui_observe_parameter(backend, param, rec)

backend.load(base_body)  # restore (already in run_parameter)
counters['baseline_reloads'] += 1

if gui_observer:
    rec['gui_restore'] = gui_observe_parameter(backend, param, rec)  # optional: verify restoration via GUI

records.append(rec)
```

## What stays frozen
- `bulk_engine.py` — mutation, state readback, band energy, restore logic **unchanged**
- `ENGINE_CONTRACT_VERSION = 1` — still valid
- No per-parameter execution branches added
- No GUI semantics embedded in the engine

## What's new
- `gui_observation.py` — optional observer interface (does not call engine)
- Modified `bulk_worker.py` — orchestration-level GUI hooks (before/after mutation, after restore)
- Evidence format extended: each record optionally includes `gui_*` fields

## Evidence row structure (extended, not changed)

```json
{
  "atlas_id": "oscA.semitone",
  "context": "INIT",
  "candidate": {...},
  "declared": {...},
  "values": [...],
  "range": {...},
  "restoration": {...},
  
  "gui_after": {
    "gui_display_value": "-6 semitones",
    "gui_tooltip": "A Semitone",
    "observation_method": "manual_hover",
    "matches_state": true
  },
  
  "gui_restore": {
    "gui_display_value": "0 semitones",
    "matches_baseline": true
  }
}
```

The engine's evidence is unchanged. GUI evidence is additive.

## B.1 implementation checklist
- [ ] Define `gui_observe_parameter()` interface in gui_observation.py
- [ ] Add optional orchestration hooks to bulk_worker.py (gui_after, gui_restore)
- [ ] Add `--gui-observe` flag to bulk_worker.py (optional, off by default)
- [ ] Define `manual_gui_read()` workflow (how to capture tooltips/values)
- [ ] Test on one context (e.g., INIT with 2–3 parameters)
- [ ] Verify engine v1 contract unchanged (no modifications to bulk_engine.py)

## B.2–B.6 follow existing sequence
- B.2: One context, many sequential GUI checks (existing orchestration pattern)
- B.3: Safe in-domain probes only
- B.4: Declared/state/GUI ranges separate
- B.5: Run full GUI campaign
- B.6: Build closure_ledger_v2

Engine frozen. Evidence layered. Attribution preserved.
