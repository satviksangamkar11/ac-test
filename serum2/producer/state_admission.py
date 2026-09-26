"""Authority chain for ledger operations. Per operation, exactly where it stops is recorded:

  Atlas identity -> structural key -> contract lookup (the contract's own path grammar, IN THE RUN'S EPOCH ONLY)
  -> scope -> operand-kind compatibility -> status/prerequisites via the UNCHANGED admission.admit().

The Brain is not consulted (literal observed state). Nothing here loosens admit(); a contract covers an operation
only where its own scope.mutation_target_path literally covers it, and only if it was qualified on the same Serum
build the run executes on. A contract that exists but belongs to another epoch is reported as EPOCH_MISMATCH.
"""
from __future__ import annotations

from typing import Dict, List

from serum2.evidence import admission as adm
from serum2.reference.serum_atlas import normalize_control
from serum2.producer.execution_epoch import ExecutionEpoch, KNOWN_EPOCHS, is_offline_test
from serum2.producer.state_ledger import Row, DERIVED, catalog
from serum2.producer.contract_scope import bridge_index, find_contract, op_operand, Trace, kparam_for, _ROOT


ROUTE_KEY = "serum.modulation_route.add"


def observed_body_state(rows: List[Row], cat) -> Dict[str, float]:
    """Directly observed field values keyed by body path, used ONLY to verify a contract's declared
    prerequisites against this video's own state (never to widen a contract's scope)."""
    out = {}
    for r in rows:
        o = r.op
        if not o or o["kind"] != "field" or r.terminal != DERIVED or o["module"] not in _ROOT:
            continue
        kp = kparam_for(o["module"], o["field"], cat)
        v = o.get("value")
        if kp and isinstance(v, (bool, int, float)):
            out["body:%s%d.plainParams.%s" % (_ROOT[o["module"]][0], o["index"], kp)] = float(v)
    return out


def admit_rows(rows: List[Row], epoch: ExecutionEpoch, binding_evidence_dir=None, promoted_evidence_dir=None) -> List[Dict]:
    from serum2.producer.contract_registry import ContractRegistry
    registry = ContractRegistry(epoch=epoch, binding_evidence_dir=binding_evidence_dir, promoted_evidence_dir=promoted_evidence_dir)
    contracts = registry.get_contracts_dict()
    cov = bridge_index(registry)
    others = {e: bridge_index(ContractRegistry(epoch=e, binding_evidence_dir=binding_evidence_dir, promoted_evidence_dir=promoted_evidence_dir))
              for e in KNOWN_EPOCHS if e != epoch}
    cat = catalog()
    observed = observed_body_state(rows, cat)
    table = []
    for r in rows:
        if r.terminal != DERIVED:
            r.admission = "NOT_APPLICABLE(%s)" % r.terminal
            continue
        o = r.op
        tr = Trace("PENDING", "ATLAS")
        c = None
        if o["kind"] == "route":
            c = next((c for c in cov if c.contract_key == ROUTE_KEY), None)
            if c is None:
                tr.stop_stage = "CONTRACT_LOOKUP"
                other = next((e for e, co in others.items() if any(x.contract_key == ROUTE_KEY for x in co)), None)
                if other is not None:
                    tr.status, tr.detail = "EPOCH_MISMATCH", "%s was qualified on %s; run epoch is %s" % (ROUTE_KEY, other.label, epoch.label)
                else:
                    tr.status = "NO_CAPABILITY"
                    tr.detail = "no %s contract usable in epoch %s (%s)" % (
                        ROUTE_KEY, epoch.label, registry.excluded.get(ROUTE_KEY, "none registered"))
        elif normalize_control(r.control_id).status not in ("EXACT", "ALIAS"):
            tr.status, tr.detail = "UNRESOLVED_REFERENCE", "Atlas has no identity"
        else:
            c, tr = find_contract(o, r.context, cov, cat)
            if c is None and tr.status in ("NO_CAPABILITY", "SCOPE_WOULD_EXPAND"):
                for e, cov_o in others.items():
                    c_o, _ = find_contract(o, r.context, cov_o, cat)
                    if c_o is not None:
                        tr.status, tr.stop_stage = "EPOCH_MISMATCH", "EPOCH"
                        tr.detail = "contract %s covers this operation but was qualified on %s; run epoch is %s" % (
                            c_o.contract_key, e.label, epoch.label)
                        break
        if c is not None:
            contract = registry.get(c.contract_key)
            want = op_operand(o)
            if c.operand != want:
                tr.status, tr.stop_stage = "INCOMPATIBLE_OPERATION", "OPERAND_KIND"
                tr.detail = "contract %s proven for %s operand; operation is %s" % (c.contract_key, c.operand, want)
            else:
                res = adm.admit(contracts, c.contract_key, proposed_prerequisites_verified=observed)
                tr.contract_key, tr.stop_stage = c.contract_key, "ADMISSION"
                if res.admitted:
                    # A2: final-contract gate — required for every real production epoch.
                    # Skipped only for offline/test epochs so the offline suite can run without evidence files.
                    if not is_offline_test(epoch):
                        # execution_spec is keyed by Atlas atlas_id (e.g. "env2.decay"), not contract_key
                        spec = registry.execution_spec(r.control_id)
                        if spec is None:
                            tr.status, tr.stop_stage = "REFUSED_NO_FINAL_CONTRACT_EVIDENCE", "FINAL_CONTRACT"
                            tr.detail = "no final execution contract evidence for %s on epoch %s" % (c.contract_key, epoch.label)
                        elif spec.get("final_execution_classification") == "MCP_EXEC_CONFORMANCE_EXCEPTION":
                            tr.status, tr.stop_stage = "REFUSED_CONFORMANCE_EXCEPTION", "FINAL_CONTRACT"
                            tr.detail = "contract %s is a conformance exception; not executable" % c.contract_key
                        elif spec.get("expected_raw"):
                            # expected_raw is a list of {path, value}; check the first path agrees
                            raw_list = spec["expected_raw"]
                            raw_path = raw_list[0]["path"] if raw_list else None
                            # expected_raw path may be a list or a dot-notation string; normalise both
                            first_path = ".".join(raw_path) if isinstance(raw_path, list) else raw_path
                            binding_body = getattr(contract.execution_binding, "body_path", None)
                            if first_path and binding_body and first_path != binding_body:
                                tr.status, tr.stop_stage = "REFUSED_BODY_PATH_MISMATCH", "FINAL_CONTRACT"
                                tr.detail = "body path in final contract (%r) != capability contract binding (%r)" % (
                                    first_path, binding_body)
                        elif spec.get("declared_domain"):
                            val = o.get("value", o.get("amount"))
                            d = spec["declared_domain"]
                            mn, mx = d.get("min"), d.get("max")
                            if val is not None and mn is not None and mx is not None:
                                try:
                                    if not (float(mn) <= float(val) <= float(mx)):
                                        tr.status, tr.stop_stage = "OUT_OF_QUALIFIED_DOMAIN", "FINAL_CONTRACT"
                                        tr.detail = "value %r outside qualified domain [%s, %s] for %s" % (
                                            val, mn, mx, c.contract_key)
                                except (TypeError, ValueError):
                                    pass
                    if tr.status == "PENDING":
                        tr.status = "ADMITTED"
                    o["capability"], o["contract_status"] = c.contract_key, contract.status
                    o["contract_epoch"] = contract.scope["serum_binary_sha256"]
                    o["execution_path"] = (contract.scope or {}).get("mutation_target_path")
                    b = contract.execution_binding
                    o["contract_binding"] = getattr(b, "resolver_operation_id", None)
                    o["contract_binding_type"] = getattr(b, "mutation_type", None)
                    o["contract_body_path"] = getattr(b, "body_path", None)
                    o["contract_domain"] = {k: (contract.scope or {}).get(k) for k in (
                        "supported_source_prefixes", "supported_destination_families", "amount_range") if (contract.scope or {}).get(k)}
                else:
                    tr.status = {"REFUSED_PREREQUISITE_UNVERIFIED": "PREREQUISITE_UNVERIFIED"}.get(res.reason, res.reason)
                    tr.detail = res.detail
        r.admission, r.reason = tr.status, (tr.detail or r.reason)
        table.append({"control": r.control_id, "rack": r.context.get("rack"), "operation": o["operation"],
                      "structural_key": next((s[1] for s in tr.stages), None), "contract": tr.contract_key,
                      "stop_stage": tr.stop_stage, "status": tr.status, "detail": tr.detail})
    stuck = [r.control_id for r in rows if r.terminal == DERIVED and r.admission in ("PENDING", "NOT_EVALUATED")]
    if stuck:   # conservation: every derived operation reaches exactly one admission outcome
        raise RuntimeError("derived operations left without an admission outcome: %s" % stuck)
    return table
