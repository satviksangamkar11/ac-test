"""Generic: candidate_binding_qualifier evidence -> EvidenceRecord -> ClaimEngine -> build_contract.

No control-specific logic. Everything control-specific (control id, accessor, body path, values) is DATA read from the
qualifier's evidence dict. The contract's binding is derived by build_contract from the record; nothing is passed in.
Returns None for anything that is not BINDING_VERIFIED."""
import dataclasses
from typing import Any, Dict, Optional

from serum2.evidence.canonical import digest
from serum2.evidence.capability_contract import CapabilityContract, build_contract
from serum2.evidence.claim import ClaimDefinition, ClaimEngine, SINGLE_FIELD
from serum2.evidence.record import EvidenceRecord, PASS, FAIL


def _definition(control_id: str) -> ClaimDefinition:
    return ClaimDefinition(
        claim_type=control_id, subject_pattern={"kind": "candidate_binding"}, predicate="constructs_mutates_persists",
        required_gate={"load": PASS, "persistence": PASS}, required_isolation=(SINGLE_FIELD,),
        breadth_rule={"sampled_min": 1}, coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
        contradiction_rule={"require_same_mutation": True}, dependency_rule={"enabled": False})


def record_from_binding_evidence(ev: Dict[str, Any], epoch) -> Optional[EvidenceRecord]:
    if ev.get("status") != "BINDING_VERIFIED" or ev.get("second_write_value") is None or not ev.get("derived_body_path"):
        return None
    ok = PASS if ev.get("run_status") == "STRUCTURAL_VERIFIED" else FAIL
    binding_evidence = {k: ev.get(k) for k in ("status", "accessor", "derived_body_path", "value_landed_in_derived_path",
                                               "collateral_semantically_neutral", "second_write_neutral")}
    mut = {"target_path": ev["derived_body_path"], "value": ev["second_write_value"]}
    exp = {"isolation_level": SINGLE_FIELD, "mutations": [mut], "binding_evidence": binding_evidence,
           "mutation_signature": digest(mut), "experiment_condition_signature": {"hash": digest({"epoch": epoch.binary_sha256, "accessor": ev.get("accessor")})},
           "notes": ev.get("notes", "")}
    return EvidenceRecord(
        experiment_id="BIND-%s-%s" % (ev["control_id"], digest(ev)[:8]),
        epoch={"serum_binary_sha256": epoch.binary_sha256, "serum_product_version": epoch.serum_version},
        experiment=exp, arms=(), runtime_verifications=(),
        state_observation={"status": ok}, load_observation={"status": ok}, render_observation={},
        causal_measurements=(), persistence_observation={"status": ok})


def contract_from_binding_evidence(ev: Dict[str, Any], epoch) -> Optional[CapabilityContract]:
    rec = record_from_binding_evidence(ev, epoch)
    if rec is None:
        return None
    engine = ClaimEngine({ev["control_id"]: _definition(ev["control_id"])})
    group = engine.add(rec, ev["control_id"])
    c = build_contract(group) if group is not None else None
    if c is None:
        return None
    scope = dict(c.scope)
    scope.update({"mutation_value_semantics": "ABSOLUTE_PARAMETER_VALUE", "serum_binary_sha256": epoch.binary_sha256,
                  "serum_product_version": epoch.serum_version, "evidence_level": "FILE_LEVEL_SERUM_MCP",
                  "instance_scope": "this control's own body path only; not evidence for any other control"})
    lims = tuple(c.limitations) + ("file-level evidence only (no direct-UI readback); STRUCTURAL_ONLY, no causal claim",
                                   "single-field isolated write, N=1 witness")
    return dataclasses.replace(c, scope=scope, limitations=lims)


def validate_binding_evidence(ev: Any) -> Optional[str]:
    """None if the evidence is complete and internally valid, else the reason. Values must satisfy the domain the qualifier recorded."""
    if not isinstance(ev, dict):
        return "not a JSON object"
    if ev.get("status") != "BINDING_VERIFIED":
        return "status is %r, not BINDING_VERIFIED" % ev.get("status")
    for k in ("control_id", "accessor", "derived_body_path", "run_status", "value_domain", "serum_identity"):
        if not ev.get(k):
            return "missing %s" % k
    d = ev["value_domain"]
    for k in ("mutation_value", "second_write_value"):
        v = ev.get(k)
        if v is None:
            return "missing %s" % k
        if d.get("kind") == "bool":
            if not isinstance(v, bool):
                return "%s=%r is not a bool" % (k, v)
        elif d.get("kind") in ("integer", "float"):
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                return "%s=%r is not numeric" % (k, v)
            if d["kind"] == "integer" and float(v) != int(v):
                return "%s=%r is not an integer for an integer control" % (k, v)
            if not d["lo"] <= v <= d["hi"]:
                return "%s=%r outside recorded domain [%r, %r]" % (k, v, d["lo"], d["hi"])
        else:
            return "unknown value_domain kind %r" % d.get("kind")
    return None


def load_binding_contracts(files, epoch):
    """Generic registry loader: evidence files -> (contracts by target, diagnostics). Contract logic stays in
    ClaimEngine/build_contract; this only discovers, validates, epoch-filters and collects."""
    import json
    diag = {"loaded": [], "rejected_invalid_evidence": {}, "rejected_no_binding": {}, "rejected_epoch": {}, "rejected_contract": {}}
    out: Dict[str, CapabilityContract] = {}
    for f in sorted(map(str, files)):
        try:
            ev = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            diag["rejected_invalid_evidence"][f] = "unreadable: %s" % e
            continue
        why = validate_binding_evidence(ev)
        if why:
            diag["rejected_invalid_evidence"][f] = why
            continue
        sha = ev["serum_identity"].get("serum_binary_sha256")
        if sha != epoch.binary_sha256:
            diag["rejected_epoch"][f] = "recorded %s, run epoch %s" % (str(sha)[:8], epoch.label)
            continue
        c = contract_from_binding_evidence(ev, epoch)
        if c is None or c.execution_binding is None:
            diag["rejected_no_binding"][f] = "evidence did not yield an evidence-derived binding"
            continue
        if not (c.scope or {}).get("mutation_target_path") or c.target in out:
            diag["rejected_contract"][f] = "no mutation_target_path" if c.target not in out else "duplicate target %s" % c.target
            continue
        out[c.target] = c
        diag["loaded"].append(c.target)
    return out, diag
