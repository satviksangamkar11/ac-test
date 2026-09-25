"""Unified evidence record + DRY-RUN hand-off to the existing promotion pipeline. Writes ONE artifact; changes no authority file.

    python -m serum2.qualification.bulk_causal.unify <out.json>      (from the repo root)

Per parameter it joins: bulk causal record (engine contract v1) -> range fingerprint -> GUI display merge -> GUI semantic merge
-> incidents, converts the causal record to the SHAPE serum2.qualification.evidence_promotion already consumes, and calls the
existing pure `promote_verified_evidence` as a dry run. Nothing is persisted except this artifact: no contract is stored, no
admission is called, no binding table / surface / registry / Atlas is written. Where the existing pipeline would reject (or where
the evidence contradicts the Atlas's own declared domain) the record says so instead of forcing it through.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
ED = ROOT / "parameter_characterization" / "bulk_causal_evidence"
# FROZEN engine contract v1: the keys every bulk record / value row must carry (pinned by test_unify.py)
CONTRACT_KEYS = {"record": {"atlas_id", "context", "candidate", "declared", "value_vector", "values", "range", "restoration", "noise_floor_db"},
                 "row": {"written", "probe", "state_value", "state_diff_keys", "file_roundtrip", "band_db", "band_delta_db", "host_params_changed"}}


def load(name):
    p = ED / name
    return json.loads(p.read_text()) if p.exists() else None


def close(a, b):
    return a is not None and b is not None and abs(a - b) <= 1e-3 * max(1.0, abs(b))


def causal_ok(rec):
    kp = rec["candidate"]["kparam"]
    reasons = []
    if not rec["restoration"]["ok"]:
        reasons.append("restoration failed")
    if not all(v["file_roundtrip"] for v in rec["values"]):
        reasons.append("file round-trip lost a value")
    if not all(v["state_diff_keys"] in ([], [kp]) for v in rec["values"]):
        reasons.append("mutation leaked into other keys")
    if not any(v["state_value"] is not None for v in rec["values"] if not v["probe"]):
        reasons.append("Serum retained no in-range value")
    return not reasons, reasons


def pick_pair(rec, control, labels):
    """(baseline, mutated, gap) in the Atlas operand domain. Mutated is always a value Serum actually retained, in range."""
    g = rec["range"]
    base = g["discovered_default"] if g["discovered_default"] is not None else g["declared"].get("default")
    kept = [v for v in rec["values"] if not v["probe"] and v["state_value"] is not None and not close(v["state_value"], base)]
    kind = rec["declared"]["kind"]      # the value TYPE comes from the swept domain, so the existing pipeline can give its own verdict on the Atlas type
    if kind == "bool":
        m = next((v["state_value"] for v in kept if v["state_value"] in (0.0, 1.0)), None)
        return base, m, None if m is not None else "no retained 0/1 value differing from the default"
    if kind == "enum":
        if not labels:
            return base, None, "enum control needs GUI semantic labels (none recorded)"
        m = next((labels[repr(v["written"])] for v in kept if repr(v["written"]) in labels), None)
        return labels.get("null", base), m, None if m else "no raw value with a GUI semantic label"
    if not kept:
        return base, None, "no retained in-range value differing from the default"
    lo, hi = g["reachable_min"], g["reachable_max"]
    v = min(kept, key=lambda r: abs(r["state_value"] - (lo + hi) / 2))
    return base, v["state_value"], None


def to_binding_evidence(rec, harness, control, labels):
    ok, why = causal_ok(rec)
    base, mut, gap = pick_pair(rec, control, labels)
    if not ok or gap:
        return None, why + ([gap] if gap else [])
    path = ".".join(str(p) for p in rec["candidate"]["path"])
    return {"target": rec["atlas_id"], "derived_body_path": path,
            "epoch": {"serum_sha256": harness["serum_sha256"], "product_version": harness.get("product_version", "2.0.23"),
                      "state_version": harness.get("state_version", 9.0)},
            "run_status": "STRUCTURAL_VERIFIED", "restoration_verified": rec["restoration"]["ok"],
            "baseline_value": base, "mutated_value": mut, "persistence_verified": True, "state_changed": True,
            "backend": "bulk_causal engine v1 (real Serum VST3 in DawDreamer; state readback)"}, []


def unify(runs, gui_merges, semantic, incidents):
    from serum2.qualification.evidence_promotion import promote_verified_evidence
    from serum2.reference.serum_atlas import get_control
    display = {}
    for m in gui_merges:
        for t in m["tests"].values():
            display[t["atlas_id"]] = t
    sem = {t["atlas_id"]: t for t in (semantic or {"tests": {}})["tests"].values()}
    out = []
    for run in runs:
        h = run["harness"]
        for rec in run["records"]:
            aid = rec["atlas_id"]
            control = get_control(aid)
            s = sem.get(aid) or {}
            labels = s.get("raw_to_label") if s.get("status") == "SEMANTIC_BINDING_PROVEN" else None
            ok, why = causal_ok(rec)
            g = rec["range"]
            conflicts = []
            if control is not None and control.min_value is not None and control.max_value is not None:
                if not close(g["reachable_min"], control.min_value) or not close(g["reachable_max"], control.max_value):
                    conflicts.append({"atlas_declared": [control.min_value, control.max_value],
                                      "serum_reachable": [g["reachable_min"], g["reachable_max"]]})
            ev, gap = to_binding_evidence(rec, h, control, labels)
            dry = None
            if ev is not None:
                r = promote_verified_evidence(ev)
                dry = {"promoted": r.promoted, "reason": r.reason, "detail": r.detail, "contract_status": getattr(r.contract, "status", None)}
            d = display.get(aid)
            blocked = ([] if control is not None else ["NO_ATLAS_IDENTITY"]) + (["ATLAS_DOMAIN_CONFLICT"] if conflicts else []) \
                + (gap if ev is None else []) + ([dry["reason"]] if dry and not dry["promoted"] else [])
            blocked = list(dict.fromkeys(blocked))
            out.append({
                "atlas_id": aid, "context": rec["context"], "candidate": rec["candidate"],
                "engine_contract_version": h.get("engine_contract_version", 1), "source_manifest_sha256": h["manifest_sha256"],
                "tiers": {"causal_raw": {"ok": ok, "reasons": why},
                          "range": {k: g[k] for k in ("discovered_default", "reachable_min", "reachable_max", "clamp_low_at", "clamp_high_at",
                                                      "declared_matches_reachable")},
                          "display": None if d is None else {"status": d["status"], "default_display": d["default_display"],
                                                             "effective_display_range": d["effective_display_range"]},
                          "semantic": None if aid not in sem else {"status": s["status"], "raw_to_label": s["raw_to_label"]}},
                "atlas": None if control is None else {"control_type": control.control_type, "min": control.min_value, "max": control.max_value},
                "atlas_domain_conflicts": conflicts, "promotion_input": ev, "promotion_input_gap": gap, "promotion_dry_run": dry,
                "blocked_by": blocked, "eligible_for_promotion_review": not blocked,
                "incidents": [i["id"] for i in incidents if d is not None and "gui" in i["applies_to"]]})
    return out


def main(out_path):
    runs = [r for r in (load("bulk_fx_eq_pilot_v1.json"), load("bulk_osc_a_pilot_v1.json")) if r]
    merges = [m for m in (load("gui_range_merge_v1.json"), load("gui_osc_merge_v1.json")) if m]
    inc = load("incidents_v1.json")["incidents"]
    recs = unify(runs, merges, load("semantic_fx_v1.json"), inc)
    summary = {"records": len(recs), "eligible_for_promotion_review": sum(r["eligible_for_promotion_review"] for r in recs),
               "atlas_domain_conflicts": sum(1 for r in recs if r["atlas_domain_conflicts"]), "blocked_reasons": {}}
    for r in recs:
        for b in r["blocked_by"]:
            summary["blocked_reasons"][b] = summary["blocked_reasons"].get(b, 0) + 1
    json.dump({"engine_contract_version": 1, "authorizes_nothing": True, "changes_no_authority_file": True, "summary": summary,
               "incidents": inc, "records": recs}, open(out_path, "w"), indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
