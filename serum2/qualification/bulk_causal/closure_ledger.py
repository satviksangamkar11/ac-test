"""Closure ledger for the MCP-mutable candidates: every one of the 330 gets exactly one terminal-or-pending status, each pointing at
the evidence artifact that justifies it. Pure aggregation: reads evidence, writes ONE ledger file, changes no authority artifact.

    python -m serum2.qualification.bulk_causal.closure_ledger <campaign_run.json> <out.json>

Status vocabulary (a control can only move UP this list by adding evidence, never by inference):
  NOT_DERIVED                 no mutation mechanism could be derived; the reason and the missing evidence are named
  STATE_NOT_OBSERVED          the mutation was written but Serum's saved state never reflected it (observer cannot see this control)
  CAUSAL_INCOMPLETE           an observable control whose restoration / round-trip / isolation check failed
  STATE_QUALIFIED_UI_PENDING  identity path + domain + causal state evidence + restoration + round-trip complete; live-UI semantics NOT yet evidenced
  PROMOTION_BLOCKED           all evidence complete but the existing pipeline rejects it (Atlas conflict / no identity / no operand mapping)
  CLOSED                      every required evidence present AND the existing promotion pipeline accepts it in a dry run
Nothing here promotes anything: CLOSED means "evidence-complete", the authority artifacts are still changed only in Phase 7.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
ED = ROOT / "parameter_characterization" / "bulk_causal_evidence"


def load(name):
    p = ED / name
    return json.loads(p.read_text()) if p.exists() else None


def observable(rec):
    g = rec["range"]
    return any(v["state_value"] is not None for v in rec["values"] if not v["probe"]) or g.get("discovered_default") is not None or \
        any(v["state_value"] is not None for v in rec["values"])


def causal_flags(rec):
    kp = rec["candidate"]["kparam"]
    compound = rec["candidate"]["kind"] == "leaf_set"
    return {"restoration": rec["restoration"]["ok"],
            "file_roundtrip": all(v["file_roundtrip"] for v in rec["values"] if not v.get("load_error")),
            "isolation": True if compound else all(v["state_diff_keys"] in ([], [kp]) for v in rec["values"] if not v.get("load_error")),
            "wire_type_safety": {"load_errors": [v["written"] for v in rec["values"] if v.get("load_error")]}}


def build(run, acct, gui_ui, identity=None, boundary=None):
    from serum2.qualification.bulk_causal.unify import unify
    recs = {r["atlas_id"]: r for r in run["records"]}
    dry = {r["atlas_id"]: r for r in unify([run], gui_ui["merges"], gui_ui["semantic"], gui_ui["incidents"], identity, boundary)}
    out = []
    for c in acct["candidates"]:
        cid = c["atlas_id"]
        e = {"atlas_id": cid, "family": c["family"], "mechanism": c.get("mechanism")}
        if not c["derived"]:
            e.update({"status": "NOT_DERIVED", "reason": c["reason"],
                      "missing_evidence": "the live dropdown vocabulary (GUI read)" if "VOCABULARY_UNKNOWN" in c["reason"] else "a generic mutation mechanism"})
            out.append(e)
            continue
        rec = recs.get(cid)
        if rec is None:
            e.update({"status": "NOT_DERIVED", "reason": "derived but absent from the run evidence"})
            out.append(e)
            continue
        e.update({"raw_path": rec["candidate"]["path"], "context": rec["context"], "domain": rec["declared"], "range": {k: rec["range"].get(k) for k in
                  ("discovered_default", "reachable_min", "reachable_max", "clamp_low_at", "clamp_high_at", "vocabulary_retained", "vocabulary_rejected", "probes_dropped")}})
        if not observable(rec):
            e.update({"status": "STATE_NOT_OBSERVED", "reason": "no written value ever appeared in Serum's saved state (observer limitation)",
                      "needs": "an observer that can see this control: GUI readout and/or the saved .SerumPreset container"})
            out.append(e)
            continue
        flags = causal_flags(rec)
        e["causal"] = flags
        if not (flags["restoration"] and flags["file_roundtrip"] and flags["isolation"]):
            e.update({"status": "CAUSAL_INCOMPLETE", "reason": "a restoration / round-trip / isolation check failed"})
            out.append(e)
            continue
        d = dry.get(cid)
        e["ui_semantics"] = d["ui_semantics"] if d else {"status": "NOT_VERIFIED"}
        e["promotion_dry_run"] = d["promotion_dry_run"] if d else None
        e["blocked_by"] = d["blocked_by"] if d else ["NOT_EVALUATED"]
        if e["ui_semantics"]["status"] != "VERIFIED":
            e.update({"status": "STATE_QUALIFIED_UI_PENDING", "reason": "live-UI semantics not yet evidenced"})
        elif e["blocked_by"]:
            e.update({"status": "PROMOTION_BLOCKED", "reason": ", ".join(e["blocked_by"])})
        else:
            e.update({"status": "CLOSED", "reason": None})
        out.append(e)
    return out


def main(run_path, out_path):
    run = json.loads(Path(run_path).read_text())
    acct = load("campaign_accounting_v1.json")
    gui_ui = {"merges": [m for m in (load("gui_range_merge_v1.json"), load("gui_osc_merge_v1.json")) if m], "semantic": load("semantic_fx_v1.json"),
              "incidents": load("incidents_v1.json")["incidents"]}
    led = build(run, acct, gui_ui, load("identity_resolution_v1.json"), load("atlas_conflict_resolution_v1.json"))
    counts = {}
    for e in led:
        counts[e["status"]] = counts.get(e["status"], 0) + 1
    assert sum(counts.values()) == acct["total_candidates"], "every candidate must appear exactly once"
    json.dump({"total_candidates": acct["total_candidates"], "status_counts": counts, "authorizes_nothing": True,
               "evidence": {"campaign_run": Path(run_path).name, "accounting": "campaign_accounting_v1.json"}, "candidates": led}, open(out_path, "w"), indent=1)
    print(json.dumps(counts, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
