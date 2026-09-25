"""GUI semantic observation layer for bulk engine (extends, not replaces, the existing bulk worker).

The bulk worker already does:
  baseline → parameter mutation → state readback → restore → verify restoration

This module adds a GUI layer that wraps the mutation step:
  baseline GUI read → mutation → state readback → GUI read → restore → GUI restoration read

All happens in ONE live Serum session (same context); no new presets per value.
Each parameter gets ONE evidence row capturing:
  declared domain | state domain | GUI effective domain | displayed value | semantic match

Usage (integrated into bulk_worker.py):
  for param in manifest['parameters']:
      gui_baseline = gui_observe(backend, param_path)      # read before mutation
      do_mutation(backend, param, value)
      gui_after = gui_observe(backend, param_path)         # read after mutation
      gui_restore = gui_observe(backend, param_path)       # read after restore
      record evidence with gui_baseline, gui_after, gui_restore

"""

# gui_observe(backend: SeumBackend, path: list) -> {"display_value": "...", "tooltip": "...", "displayed_numeric": float|None}
# Reads the live UI for a single parameter in its current Serum session.
# Returns GUI display state WITHOUT mutating the session.
#
# Implementation: requires either:
# (a) Manual observation: user hovers Serum UI, records value
# (b) OCR-assisted: screenshot tooltip/readout, OCR the text
# (c) Automation (future): bridge Serum's own host parameter text display

def gui_observe_manual(param_atlas_id: str, context_name: str) -> dict:
    """Manual GUI observation: caller (user) hovers Serum UI and provides the display value.

    This is the initial implementation: preserve causal attribution by having the user
    confirm each observed value rather than inferring from screenshots or host text.
    """
    # Placeholder: integration would be interactive input or a callback
    return {
        "atlas_id": param_atlas_id,
        "observation_method": "manual_hover",
        "display_value": None,  # caller fills this in
        "tooltip_text": None,    # caller fills this in
        "displayed_numeric": None,
        "note": "manual observation required"
    }


def gui_observe_from_host_text(backend) -> dict:
    """GUI observation from Serum's VST3 host parameter display text (machine-readable, not user-visible UI).

    NOTE: This is NOT the same as actual UI observation. The host text and the displayed UI value
    can differ (e.g., compressed scales, rounded display, semantic names vs. raw values).
    This method is a fallback; use manual observation when the actual UI display matters.
    """
    # Would call backend.syn.get_parameter_text() for each parameter
    # Returns what the VST3 host displays, not the literal on-screen control value
    return {
        "observation_method": "host_text_fallback",
        "display_value": None,  # from host
        "is_user_visible_ui": False,  # important distinction
        "note": "machine-readable fallback; does not replace actual UI observation"
    }


def integrate_gui_into_bulk_worker():
    """Pseudo-code: how GUI observation integrates into the existing bulk worker.

    The pattern reuses the proven bulk principle: one context, many sequential mutations,
    but adds GUI observation alongside state observation.
    """
    # From existing run_parameter():
    # for v, probe in values:
    #     body = copy.deepcopy(base_body)
    #     for lp, lv in leaves:
    #         body_set(body, lp, lv)
    #     backend.load(body)
    #     o = backend.observe()  <- STATE observation
    #
    #     NEW: ADD GUI observation here
    #     gui_o = gui_observe(backend, path)
    #     <- loads Serum UI, reads control display WITHOUT further mutation
    #
    #     <- restore backend (existing)
    #
    #     rows.append({
    #         "written": v,
    #         "state_value": o["state_value"],
    #         "band_db": o["band_db"],
    #         "gui_display_value": gui_o["display_value"],  <- NEW
    #         "gui_matches_state": match(o["state_value"], gui_o["display_value"]),  <- NEW
    #         ...
    #     })
    pass


# Evidence record structure (extended from bulk_engine.py):
example_evidence_row = {
    "atlas_id": "oscA.semitone",
    "written": -6.0,
    "state_value": -6.0,
    "gui_display_value": "-6 semitones",  # <- NEW
    "gui_tooltip_text": "A Semitone",      # <- NEW
    "declared_domain": {"min": -12, "max": 12},
    "state_domain": {"min": -12, "max": 12},
    "gui_effective_domain": None,  # <- to be filled from accumulating GUI observations
    "semantic_match": "STATE_MATCHES_GUI",  # MATCH | STATE_CLAMP | GUI_CLAMP | MISMATCH | UNOBSERVABLE
}

# Semantic verdicts:
semantic_verdicts = {
    "MATCH": "declared = state = GUI",
    "STATE_CLAMP": "state ≠ declared, GUI matches state (clamping is normal)",
    "GUI_CLAMP": "state = declared, GUI differs (range-display issue, needs investigation)",
    "MISMATCH": "state ≠ GUI (critical: what Serum stores ≠ what UI shows)",
    "UNOBSERVABLE": "no GUI readout available (macro names, internal routing)",
    "DEFAULT_OMITTED": "in-range value absent from state (Serum's default behavior)",
}
