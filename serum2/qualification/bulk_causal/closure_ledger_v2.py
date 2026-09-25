"""Closure ledger v2: same frozen ledger pipeline as closure_ledger.py, run against the GUI-observed campaign
(campaign_run_gui_v1.json), with one ADDITIVE tier: host_text_evidence, reporting the mutated/restored host-text
observations collected by the B.1 GUI observer (bulk_causal.gui_observation).

    python -m serum2.qualification.bulk_causal.closure_ledger_v2 <campaign_run_gui.json> <out.json>

closure_ledger.build()/unify() are NOT modified and NOT re-implemented here: `status` and `ui_semantics` come
from exactly the same manual GUI evidence files (gui_range_merge_v1.json, semantic_fx_v1.json, ...) as v1 --
this file changes no closure logic and no authority artifact.

Why host_text_evidence cannot move ui_semantics to VERIFIED: the B.1 observer's own contract
(gui_observation.py) tags every observation `observation_method: "host_text_fallback"`,
`is_user_visible_ui: false`. Host text is a VST3-host-reported string, read via the plugin API -- it is
evidence that Serum's parameter automation surface reflects the mutation, not a screen-level observation of
what a human sees in the Serum window. Treating it as DIRECT_UI evidence would silently promote controls whose
GUI rendering has never actually been looked at (exactly the display/state divergence class this project
exists to catch). So it is reported as its own tier, and the pre-existing ui_semantics tier is left untouched.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from closure_ledger import build, load, ED  # noqa: E402


def host_text_evidence(rec):
    """Per-candidate summary of the B.1 host-text observer's coverage for this parameter. Three outcomes:
    OBSERVED       -- at least one mutated value produced non-empty host text, AND it's distinguishable from
                      the post-restore host text (proves the observer is reading real, not stale, state)
    UNOBSERVABLE   -- the observer ran (gui_restore present) but every value's host text came back empty
                      (this control has no host-automatable display name in this VST3's parameter list --
                      e.g. FX EQ per-band gain/freq; a real Serum limitation, not an observer defect)
    NOT_ATTEMPTED  -- no gui_restore on this record at all (--gui-observe evidence absent for this candidate)
    """
    if rec is None or "gui_restore" not in rec:
        return {"status": "NOT_ATTEMPTED", "is_direct_ui_verified": False}
    restored_text = rec["gui_restore"].get("host_text_display", {})
    mutated_texts = [v.get("gui_mutated", {}).get("host_text_display", {}) for v in rec["values"]]
    any_mutated_text = any(t for t in mutated_texts)
    if not any_mutated_text:
        return {"status": "UNOBSERVABLE", "reason": "no host-automatable display name found for this control",
                "is_direct_ui_verified": False}
    distinguishable = any(t and t != restored_text for t in mutated_texts)
    return {"status": "OBSERVED" if distinguishable else "OBSERVED_NO_CONTRAST",
            "sample_mutated": next((t for t in mutated_texts if t), None), "restored": restored_text,
            "is_direct_ui_verified": False,   # host_text_fallback is never literal on-screen UI evidence -- see module docstring
            "note": "machine-readable host-text (VST3 parameter API), not a screen-level UI observation"}


def main(run_path, out_path):
    run = json.loads(Path(run_path).read_text())
    acct = load("campaign_accounting_v1.json")
    gui_ui = {"merges": [m for m in (load("gui_range_merge_v1.json"), load("gui_osc_merge_v1.json")) if m], "semantic": load("semantic_fx_v1.json"),
              "incidents": load("incidents_v1.json")["incidents"]}
    led = build(run, acct, gui_ui, load("identity_resolution_v1.json"), load("atlas_conflict_resolution_v1.json"))

    recs = {r["atlas_id"]: r for r in run["records"]}
    for e in led:
        e["host_text_evidence"] = host_text_evidence(recs.get(e["atlas_id"]))

    counts = {}
    for e in led:
        counts[e["status"]] = counts.get(e["status"], 0) + 1
    host_counts = {}
    for e in led:
        s = e["host_text_evidence"]["status"]
        host_counts[s] = host_counts.get(s, 0) + 1
    assert sum(counts.values()) == acct["total_candidates"], "every candidate must appear exactly once"

    json.dump({"total_candidates": acct["total_candidates"], "status_counts": counts, "host_text_evidence_counts": host_counts,
               "authorizes_nothing": True, "direct_ui_verification_performed": False,
               "evidence": {"campaign_run": Path(run_path).name, "accounting": "campaign_accounting_v1.json",
                            "gui_observer_contract": "bulk_causal.gui_observation (host_text_fallback; see module docstring)"},
               "candidates": led}, open(out_path, "w"), indent=1)
    print("status_counts:", json.dumps(counts, indent=1))
    print("host_text_evidence_counts:", json.dumps(host_counts, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
