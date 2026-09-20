"""Operand-driven state compiler. The ONLY input is AuthorizedOperation records: operations that passed
admission, under a contract qualified on the SAME Serum build the run executes on. There is no way to compile
merely-derived or observed state: ops_from_rows() only ever emits ADMITTED operations, and compile_ops()
re-validates every operation (type, admission status, epoch, and agreement with the contract's own binding) and
raises rather than skipping anything.

The compiler contains no capability IDs and no video-specific values: every value written is an operation's own
operand. No-drop invariant: admitted == to_compile before lowering and compiled == admitted after; any gap is
COMPILATION_INCOMPLETE, never success.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from serum2.producer.execution_epoch import ExecutionEpoch

# Only these binding types can authorize LOWERING. HOST_PARAMETER is VST3 evidence-surface only (target_surfaces.py)
# and an unbound contract has no binding at all; neither may reach the compiler.
EXECUTION_ELIGIBLE_BINDINGS = ("SERUM_PRESET_STRUCTURAL", "BODY_STATE", "TOPOLOGY")
_FX_PATH = re.compile(r"^FXRack(\d+)\.FX\.\d+\.(FX\w+)\.plainParams\.(kParam\w+)$")


class UnauthorizedOperation(RuntimeError):
    """An operation reached the compiler without valid authority. Never swallowed."""


@dataclass(frozen=True)
class AuthorizedOperation:
    operation_id: str
    canonical_target: str
    operation: str                 # SET | SELECT | TOGGLE_ON | TOGGLE_OFF | ADD
    operand: Any
    binding: Dict[str, Any]        # lowering target: {kind: field|fx|route, ...}
    contract_key: Optional[str]
    contract_epoch: str            # binary sha256 the contract was qualified on
    execution_path: Optional[str]
    contract_binding: Optional[str]
    admission_evidence: Dict[str, Any]
    provenance: Dict[str, Any]
    fidelity: str = "EXACT"        # EXACT | NORMALIZED | APPROXIMATED
    binding_type: Optional[str] = None       # the contract's ExecutionBinding.mutation_type
    contract_body_path: Optional[str] = None
    contract_domain: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompileReport:
    spec: Dict[str, Any]
    status: str                    # SUCCESS | COMPILATION_INCOMPLETE
    admitted: int
    compiled: int
    epoch: ExecutionEpoch
    ops: Tuple[AuthorizedOperation, ...] = ()
    missing: List[str] = field(default_factory=list)


def ops_from_rows(rows, epoch: ExecutionEpoch) -> List[AuthorizedOperation]:
    out = []
    for r in rows:
        o = r.op
        if not o or r.terminal != "OPERATION_DERIVED" or r.admission != "ADMITTED":
            continue                      # derived-but-not-admitted state never leaves the ledger
        fid = "APPROXIMATED" if o.get("fidelity") == "APPROXIMATED_FROM_TEMPO" else ("NORMALIZED" if o.get("normalized") else "EXACT")
        out.append(AuthorizedOperation(
            operation_id="%s@%s" % (r.control_id, r.context.get("rack", "-")), canonical_target=r.control_id,
            operation=o["operation"], operand=o.get("value", o.get("amount")),
            binding={k: o[k] for k in o if k in ("kind", "module", "list", "index", "field", "fx_type", "param", "source", "destination")},
            contract_key=o.get("capability"), contract_epoch=o.get("contract_epoch", ""), execution_path=o.get("execution_path"),
            contract_binding=o.get("contract_binding"),
            admission_evidence={"status": r.admission, "contract_status": o.get("contract_status")},
            provenance={"frame_ts": r.source_ts, "readings": r.n_readings, "read_quality": r.read_quality,
                        "observed": r.value, "rack": r.context.get("rack")}, fidelity=fid,
            binding_type=o.get("contract_binding_type"), contract_body_path=o.get("contract_body_path"),
            contract_domain=o.get("contract_domain") or {}))
    return out


def _validate(op, epoch: ExecutionEpoch):
    if not isinstance(op, AuthorizedOperation):
        raise UnauthorizedOperation("not an AuthorizedOperation: %r" % type(op).__name__)
    if op.admission_evidence.get("status") != "ADMITTED" or not op.contract_key:
        raise UnauthorizedOperation("%s carries no admission" % op.operation_id)
    if op.contract_epoch != epoch.binary_sha256:
        raise UnauthorizedOperation("%s authorized on a different Serum build (%s..) than the run (%s)" % (
            op.operation_id, op.contract_epoch[:8], epoch.label))
    if op.binding_type not in EXECUTION_ELIGIBLE_BINDINGS:
        raise UnauthorizedOperation("%s: contract has no execution-eligible binding (binding type %r)" % (op.operation_id, op.binding_type))
    b = op.binding
    if b["kind"] == "field":
        from serum2.producer.contract_scope import _ROOT, kparam_for
        from serum2.producer.state_ledger import catalog
        accessor = "%s[%d].%s" % (b["list"], b["index"], b["field"])
        if op.binding_type != "SERUM_PRESET_STRUCTURAL" or accessor != op.contract_binding:
            raise UnauthorizedOperation("%s lowers to %s but its contract binding is %s/%s" % (
                op.operation_id, accessor, op.binding_type, op.contract_binding))
        kp = kparam_for(b["module"], b["field"], catalog())
        expected = "%s%d.plainParams.%s" % (_ROOT[b["module"]][0], b["index"], kp)
        if not kp or expected != op.contract_body_path:
            raise UnauthorizedOperation("%s lowers to body path %s but its contract was proven on %s" % (
                op.operation_id, expected, op.contract_body_path))
    elif b["kind"] == "fx":
        m = _FX_PATH.match(op.contract_body_path or "")
        rack = op.provenance.get("rack") or 0
        if op.binding_type != "BODY_STATE" or not m or (int(m.group(1)), m.group(2), m.group(3)) != (rack, b["fx_type"], b["param"]):
            raise UnauthorizedOperation("%s lowers to FXRack%s %s.%s but its contract binding is %s/%s" % (
                op.operation_id, rack, b["fx_type"], b["param"], op.binding_type, op.contract_body_path))
    elif b["kind"] == "route":
        d = op.contract_domain
        amount = op.operand
        ok = (op.binding_type == "TOPOLOGY" and d and any(b["source"].startswith(p) for p in d.get("supported_source_prefixes", ()))
              and b["destination"].split(".")[0].rstrip("0123456789") in d.get("supported_destination_families", ())
              and isinstance(amount, (int, float)) and d["amount_range"][0] <= amount <= d["amount_range"][1])
        if not ok:
            raise UnauthorizedOperation("%s route %s -> %s (amount %r) is outside its contract's qualified domain" % (
                op.operation_id, b["source"], b["destination"], amount))
    else:
        raise UnauthorizedOperation("%s has unknown lowering kind %r" % (op.operation_id, b["kind"]))


def compile_ops(ops: List[AuthorizedOperation], name: str, description: str, epoch: ExecutionEpoch) -> CompileReport:
    for op in ops:
        _validate(op, epoch)
    spec: Dict[str, Any] = {"name": name, "description": description, "oscillators": [], "envelopes": [],
                            "lfos": [], "filters": [], "fx_chain": [], "mod_routes": []}
    units: Dict[Tuple[Any, str], Dict[str, Any]] = {}
    done: List[str] = []
    for op in sorted(ops, key=lambda o: o.provenance["frame_ts"]):
        b = op.binding
        if b["kind"] == "route":
            spec["mod_routes"].append({"source": b["source"], "destination": b["destination"], "amount": op.operand})
        elif b["kind"] == "field":
            lst = spec[b["list"]]
            while len(lst) <= b["index"]:
                lst.append({})
            lst[b["index"]][b["field"]] = op.operand
        elif b["kind"] == "fx":
            u = units.setdefault((op.provenance["rack"], b["fx_type"]),
                                 {"type": b["fx_type"], "rack": op.provenance["rack"], "wet": 100, "params": {}})
            if b["param"] == "kParamWet":
                u["wet"] = op.operand
            else:
                u["params"][b["param"]] = op.operand
        else:
            continue
        done.append(op.operation_id)
    spec["fx_chain"] = list(units.values())
    spec = {k: v for k, v in spec.items() if v or k in ("name", "description")}
    missing = [o.operation_id for o in ops if o.operation_id not in done]
    return CompileReport(spec, "SUCCESS" if not missing and len(done) == len(ops) else "COMPILATION_INCOMPLETE",
                         len(ops), len(done), epoch, tuple(ops), missing)
