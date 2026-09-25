"""GUI semantic observation layer for bulk engine (orchestration-level observer, not engine modification).

The bulk engine is frozen at v1. This module provides optional observer callbacks for GUI verification,
attached at TWO distinct points in the existing mutation lifecycle (never conflate the two):

    baseline -> mutate value -> state observe -> GUI OBSERVE (mutated)   [on_value_observe, per VALUE]
             -> ... (all values) -> restore -> GUI OBSERVE (restored)    [on_gui_restore, per PARAMETER]

Usage (in bulk_worker.py):
    on_value_observe, on_gui_restore = gui_observer_factory(use_host_text=True) if args.gui_observe else (None, None)
    run_context(..., on_value_observe=on_value_observe, on_gui_restore=on_gui_restore)

on_value_observe(row, o, backend, param): called once per VALUE, right after that value's mutation is
    observed. `o` is backend.observe() from that exact mutated load (pre-restore) -- this is the only
    place mutated GUI evidence can be read. Adds row['gui_mutated'] in-place.
on_gui_restore(rec, backend, param): called once per PARAMETER, after the engine has restored the
    context baseline. Proves restoration reached the GUI too. Adds rec['gui_restore'] in-place.
    Does NOT see the mutated value -- never report this as mutation evidence.

Keep three domains separate:
- declared_domain (from schema/Atlas)
- state_domain (from VST3 state readback)
- gui_effective_domain (from live UI observations)

Semantic verdicts:
- MATCH: declared = state = GUI
- STATE_CLAMP: state != declared, but GUI matches state (normal clamping)
- GUI_CLAMP: state = declared, but GUI differs (range-display issue)
- MISMATCH: state != GUI (critical: what Serum stores != what UI shows)
- UNOBSERVABLE: no GUI readout available
"""


def gui_observer_factory(use_host_text=False, manual=False):
    """Create the two optional GUI observer callbacks for run_context().

    use_host_text=True:  fallback to VST3 host parameter text (machine-readable, not UI)
    manual=True:         placeholder for manual hover-based observation

    Returns (on_value_observe, on_gui_restore) -- see module docstring for their signatures.
    """
    def on_value_observe(row, o, backend, param):
        """Callback signature: (value_row, observe_result, backend, parameter) -> modifies row in-place.
        Called with the backend in the JUST-MUTATED state (pre-restore)."""
        try:
            if use_host_text:
                gui_evidence = _host_text_for_changed(row, o, param, tag="gui_mutated")
            elif manual:
                gui_evidence = gui_observe_manual(backend, param, row)
            else:
                gui_evidence = None
            if gui_evidence:
                row["gui_mutated"] = gui_evidence
        except Exception as e:
            row["gui_mutated_error"] = str(e)

    def on_gui_restore(rec, backend, param):
        """Callback signature: (record, backend, parameter) -> modifies rec in-place.
        Called AFTER the context baseline has been restored; proves restoration reached the GUI."""
        try:
            if use_host_text:
                gui_evidence = gui_observe_host_text_restored(backend, param, rec)
            elif manual:
                gui_evidence = gui_observe_manual(backend, param, rec)
            else:
                gui_evidence = None
            if gui_evidence:
                rec["gui_restore"] = gui_evidence
        except Exception as e:
            rec["gui_restore_error"] = str(e)

    return on_value_observe, on_gui_restore


def _host_text_for_changed(row, o, param, tag):
    """Shared helper: pull host text for exactly the display-name keys the engine already found changed
    for this value (row['host_params_changed'], computed by bulk_engine.run_parameter by diffing hosts
    against the pre-mutation baseline). DawDreamer exposes parameters by DISPLAY name (e.g. "A Enable"),
    not the raw kParam* id used in the mutation path -- never look up by kparam id."""
    changed_names = row.get("host_params_changed", [])
    return {
        "atlas_id": param["atlas_id"],
        "written": row.get("written"),
        "observation_method": "host_text_fallback",
        "host_text_display": {n: o["hosts"].get(n) for n in changed_names},
        "state_value": row.get("state_value"),
        "is_user_visible_ui": False,
        "note": "machine-readable fallback (%s); does not replace manual UI observation" % tag,
    }


def gui_observe_host_text_restored(backend, param, rec):
    """After-restore check: read current host text for whatever display names changed across the sweep,
    to confirm the GUI itself reads back to baseline (not just the underlying state)."""
    changed_names = sorted({n for v in rec.get("values", []) for n in v.get("host_params_changed", [])})
    current_hosts = backend.observe()["hosts"]
    return {
        "atlas_id": param["atlas_id"],
        "kparam": rec["candidate"]["kparam"],
        "observation_method": "host_text_fallback",
        "host_text_display": {n: current_hosts.get(n) for n in changed_names},
        "is_user_visible_ui": False,
        "note": "post-restore GUI readback; NOT mutation evidence",
    }


def gui_observe_manual(backend, param, row_or_rec):
    """Manual GUI observation: placeholder for live hover-based capture.

    This is the high-fidelity method: preserve causal attribution by having someone
    confirm each observed value via live Serum UI rather than inferring from screenshots/host text.

    Requires interactive input or pre-recorded observations.
    """
    return {
        "atlas_id": param["atlas_id"],
        "observation_method": "manual_hover",
        "gui_display_value": None,  # requires human input
        "tooltip_text": None,
        "note": "manual observation required (not automated)",
    }
