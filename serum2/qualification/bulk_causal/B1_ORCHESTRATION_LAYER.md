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
    optional: gui_observer hooks
    ↓
    evidence consolidation (unify.py)
```

## Pattern: two hooks, two distinct lifecycle points

GUI observation attached only after restore cannot prove anything about the mutated value — by
the time it runs, the parameter is already back at baseline. The engine exposes **two** optional
hooks, at the two points where each kind of evidence actually exists:

```
baseline
  ↓
mutate value                              (run_parameter, per value in the sweep)
  ↓
state/band observation
  ↓
on_value_observe(row, o, backend, param)  ← sees the JUST-MUTATED backend, pre-restore
  ↓                                          this is the ONLY hook that can see mutated GUI evidence
  ... (repeat for every value tried)
  ↓
restore context baseline                  (once, after all values for this parameter)
  ↓
on_gui_restore(rec, backend, param)       ← sees the RESTORED backend
                                             proves restoration reached the GUI; NOT mutation evidence
```

### bulk_engine.py signatures
```python
def run_parameter(base_body, base_obs, floor, param, backend, cfg, counters, meta=None, on_value_observe=None):
    ...
    if on_value_observe:
        on_value_observe(rows[-1], o, backend, param)   # backend in JUST-MUTATED state (pre-restore)

def run_context(..., on_value_observe=None, on_gui_restore=None):
    ...
    rec = run_parameter(..., on_value_observe=on_value_observe)
    ...
    backend.load(base_body)          # restore
    if on_gui_restore:
        on_gui_restore(rec, backend, param)              # backend in RESTORED state
```

### bulk_worker.py wiring
```python
on_value_observe, on_gui_restore = gui_observer_factory(use_host_text=True) if args.gui_observe else (None, None)
run_context(..., on_value_observe=on_value_observe, on_gui_restore=on_gui_restore)
```

## What stays frozen
- `bulk_engine.py` — mutation, state readback, band energy, restore logic **unchanged**
- `ENGINE_CONTRACT_VERSION = 1` — still valid
- No per-parameter execution branches added
- No GUI semantics embedded in the engine — the two hooks are generic callback points; all GUI-specific
  logic (host-text lookup, manual observation, verdicts) lives entirely in `gui_observation.py`

## What's new
- `gui_observation.py` — `gui_observer_factory()` returns `(on_value_observe, on_gui_restore)`
- Modified `bulk_worker.py` — orchestration-level GUI hooks wired at both lifecycle points
- Modified `bulk_engine.py` — added the two optional hook parameters (no GUI code inside the engine itself)
- Evidence format extended: each per-value row optionally carries `gui_mutated`; each parameter record
  optionally carries `gui_restore`

## Evidence row structure (extended, not changed)

```json
{
  "atlas_id": "oscA.semitone",
  "context": "OSC_A",
  "candidate": {...},
  "declared": {...},
  "values": [
    {
      "written": -12.0,
      "state_value": -12.0,
      "host_params_changed": ["A Semi"],
      "gui_mutated": {
        "written": -12.0,
        "host_text_display": {"A Semi": "-12"},
        "observation_method": "host_text_fallback",
        "note": "machine-readable fallback (gui_mutated); does not replace manual UI observation"
      }
    }
  ],
  "range": {...},
  "restoration": {"ok": true, ...},

  "gui_restore": {
    "host_text_display": {"A Semi": " 0"},
    "observation_method": "host_text_fallback",
    "note": "post-restore GUI readback; NOT mutation evidence"
  }
}
```

The engine's evidence is unchanged. GUI evidence is additive, and is only ever populated when
`--gui-observe` is passed.

## Live-Serum proof (2.0.23, oscA.semitone, 2026-09-25)
```
written=-12.0  gui_mutated={'A Semi': '-12'}
written=+12.0  gui_mutated={'A Semi': '+12'}
...restore...  gui_restore={'A Semi': ' 0'}
```
Mutated and restored GUI text are distinct — the hook is genuinely reading two different states,
not reporting the restored value twice.

## B.1 implementation checklist
- [x] Define `gui_observer_factory()` returning `(on_value_observe, on_gui_restore)` in gui_observation.py
- [x] Add optional orchestration hooks to bulk_engine.py/bulk_worker.py at both lifecycle points
- [x] Add `--gui-observe` flag to bulk_worker.py (optional, off by default) — verified wired end-to-end
- [x] Define `gui_observe_manual()` placeholder for a future manual hover-based workflow
- [x] Test on one context (OSC_A, 2 parameters) against live Serum 2.0.23
- [x] Verify engine v1 contract unchanged (bulk_engine.py mutation/restore logic untouched; only additive
      optional hook parameters); 44/44 tests pass including a FakeBackend regression that fails if
      `on_value_observe` is not actually wired to the pre-restore point

## B.2–B.6 follow existing sequence
- B.2: One context, many sequential GUI checks (existing orchestration pattern)
- B.3: Safe in-domain probes only
- B.4: Declared/state/GUI ranges separate
- B.5: Run full GUI campaign
- B.6: Build closure_ledger_v2

Engine frozen. Evidence layered at the correct lifecycle point. Attribution preserved.
