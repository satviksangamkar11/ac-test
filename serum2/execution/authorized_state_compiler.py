"""Operand-driven state compiler. Consumes AuthorizedOperation records and lowers each admitted
operand into a PresetSpec dict. It contains no capability IDs and no video-specific values: every
value written comes from an operation's own operand.

No-drop invariant: admitted == to_compile before lowering, and compiled == admitted after; any gap
is COMPILATION_INCOMPLETE, never success.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class AuthorizedOperation:
    operation_id: str
    canonical_target: str
    operation: str                 # SET | SELECT | TOGGLE_ON | TOGGLE_OFF | ADD
    operand: Any
    binding: Dict[str, Any]        # lowering target: {kind: field|fx|route, ...}
    contract_key: Optional[str]
    execution_path: Optional[str]
    admission_evidence: Dict[str, Any]
    provenance: Dict[str, Any]
    fidelity: str = "EXACT"        # EXACT | NORMALIZED | APPROXIMATED


@dataclass
class CompileReport:
    spec: Dict[str, Any]
    status: str                    # SUCCESS | COMPILATION_INCOMPLETE
    admitted: int
    compiled: int
    missing: List[str] = field(default_factory=list)


def ops_from_rows(rows, only_admitted: bool = True) -> List[AuthorizedOperation]:
    out = []
    for r in rows:
        o = r.op
        if not o or r.terminal != "OPERATION_DERIVED" or (only_admitted and r.admission != "ADMITTED"):
            continue
        operand = o.get("value", o.get("amount"))
        fid = "APPROXIMATED" if o.get("fidelity") == "APPROXIMATED_FROM_TEMPO" else ("NORMALIZED" if o.get("normalized") else "EXACT")
        out.append(AuthorizedOperation(
            operation_id="%s@%s" % (r.control_id, r.context.get("rack", "-")), canonical_target=r.control_id,
            operation=o["operation"], operand=operand, binding={k: o[k] for k in o if k in (
                "kind", "list", "index", "field", "fx_type", "param", "source", "destination")},
            contract_key=o.get("capability"), execution_path=o.get("execution_path"),
            admission_evidence={"status": r.admission, "contract_status": o.get("contract_status")},
            provenance={"frame_ts": r.source_ts, "readings": r.n_readings, "read_quality": r.read_quality,
                        "observed": r.value, "rack": r.context.get("rack")}, fidelity=fid))
    return out


def compile_ops(ops: List[AuthorizedOperation], name: str, description: str,
                approximated_beat_sync: Optional[Dict[str, Any]] = None) -> CompileReport:
    spec: Dict[str, Any] = {"name": name, "description": description, "oscillators": [], "envelopes": [],
                            "lfos": [], "filters": [], "fx_chain": [], "mod_routes": []}
    to_compile = list(ops)
    assert len(to_compile) == len(ops)                                  # pre: nothing dropped before lowering
    units: Dict[Tuple[Any, str], Dict[str, Any]] = {}
    done: List[str] = []
    for op in sorted(to_compile, key=lambda o: o.provenance["frame_ts"]):
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
                         len(ops), len(done), missing)
