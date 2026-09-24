"""Deterministic op -> contract bridge with scope validation. No fuzzy or substring matching.

A contract states, in its own evidence, WHERE it was proven: scope.mutation_target_path.
That path grammar is the only key used to relate an operation to a contract:
  FXRack<r>.FX.<i>.<FXType>.plainParams.<kParam>   rack r, any slot holding that FX type
                                                  (repo rule: compiler/context.py is index-agnostic on the FX list)
  <Root><n>.plainParams.<kParam>                   instance n only (Env0 = Env 1, Oscillator0 = Osc A, ...)
  <Root><n>[.<sub>]                                structured operand (e.g. Oscillator0.WTOsc0, ModSlotN)
Anything the path does not literally cover is refused, with the specific reason.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

_FX = re.compile(r"^FXRack(\d+)\.FX\.(\d+)\.(FX\w+)\.plainParams\.(kParam\w+)$")
_INST = re.compile(r"^([A-Za-z]+?)(\d+)\.plainParams\.(kParam\w+)$")
_STRUCT = re.compile(r"^([A-Za-z]+?)(\d+)(?:\.(\w+))?$")

_OPERAND = {"mutate_numeric_value": "numeric", "mutate_numeric": "numeric", "mutate_enum_value": "enum",
            "mutate_structured_value": "structured", "unknown_operation": "unknown"}
_ROOT = {"env": ("Env", ["envelope"]),
         "osc": ("Oscillator", ["oscillator", "wavetable_oscillator", "noise_oscillator"]),
         "filter": ("VoiceFilter", ["voice_filter"]), "lfo": ("LFO", ["lfo"])}


@dataclass(frozen=True)
class Coverage:
    contract_key: str
    kind: str                    # fx | instance | structured | pathless
    operand: str                 # numeric | enum | structured | unknown
    rack: Optional[int] = None
    fx_type: Optional[str] = None
    root: Optional[str] = None
    index: Optional[int] = None
    kparam: Optional[str] = None


def coverage_of(key: str, contract) -> Coverage:
    path = (contract.scope or {}).get("mutation_target_path")
    operand = _OPERAND.get(contract.allowed_operation, "unknown")
    if not path:
        return Coverage(key, "pathless", operand)
    m = _FX.match(path)
    if m:
        return Coverage(key, "fx", operand, rack=int(m.group(1)), fx_type=m.group(3), kparam=m.group(4))
    m = _INST.match(path)
    if m:
        return Coverage(key, "instance", operand, root=m.group(1), index=int(m.group(2)), kparam=m.group(3))
    m = _STRUCT.match(path)
    if m:
        return Coverage(key, "structured", operand, root=m.group(1), index=int(m.group(2)), kparam=m.group(3))
    return Coverage(key, "pathless", operand)


def _norm(k: str) -> str:
    return re.sub(r"^kParam", "", k).lower().replace("_", "")


def kparam_for(module: str, fld: str, catalog: Dict[str, Any]) -> Optional[str]:
    """Exact-normalized equality between a spec field and a catalog kParam (enabled == enable). No prefixes."""
    want = {"enabled": "enable"}.get(fld, fld)
    for section in _ROOT[module][1]:
        for k in catalog.get(section, {}):
            if _norm(k) == _norm(want):
                return k
    return None


def op_operand(op: Dict[str, Any]) -> str:
    return {"SET": "numeric", "SELECT": "enum", "TOGGLE_ON": "boolean", "TOGGLE_OFF": "boolean",
            "ADD": "structured"}.get(op["operation"], "unknown")


@dataclass
class Trace:
    status: str
    stop_stage: str
    contract_key: Optional[str] = None
    detail: str = ""
    stages: List[Tuple[str, str]] = field(default_factory=list)


def bridge_index(registry) -> List[Coverage]:
    return [coverage_of(k, c) for k, c in registry.contracts.items()]


def find_contract(op: Dict[str, Any], ctx: Dict[str, Any], cov: List[Coverage], catalog: Dict[str, Any]
                  ) -> Tuple[Optional[Coverage], Trace]:
    tr = Trace("PENDING", "STRUCTURAL_KEY")
    if op["kind"] == "fx":
        if not op.get("param"):
            tr.status, tr.detail = "NO_CAPABILITY", "%s recognized but parameter has no catalog kParam" % op["fx_type"]
            return None, tr
        rack = ctx.get("rack", 0)
        key = "FXRack%s.%s.%s" % (rack, op["fx_type"], op["param"])
        tr.stages.append(("STRUCTURAL_KEY", key))
        same_param = [c for c in cov if c.kind == "fx" and c.fx_type == op["fx_type"] and c.kparam == op["param"]]
        exact = [c for c in same_param if c.rack == rack]
        if exact:
            return exact[0], tr
        if same_param:
            tr.status, tr.stop_stage = "SCOPE_WOULD_EXPAND", "SCOPE"
            tr.detail = "contract %s proven in rack %s only; operation targets rack %s" % (
                same_param[0].contract_key, same_param[0].rack, rack)
            return None, tr
        tr.status, tr.stop_stage, tr.detail = "NO_CAPABILITY", "CONTRACT_LOOKUP", "no contract covers %s" % key
        return None, tr
    if op["kind"] == "field":
        root = _ROOT.get(op["module"], (None, None))[0]
        kp = kparam_for(op["module"], op["field"], catalog) if root else None
        if root and op["field"] == "wavetable":
            wt = [c for c in cov if c.kind == "structured" and c.root == root and c.kparam and "WT" in c.kparam.upper()]
            tr.stages.append(("STRUCTURAL_KEY", "%s%d.<wavetable operand>" % (root, op["index"])))
            if wt and wt[0].index == op["index"]:
                tr.status, tr.stop_stage = "INCOMPATIBLE_OPERATION", "OPERAND_KIND"
                tr.detail = "contract %s proven for a structured wavetable operand, not a named wavetable selection" % wt[0].contract_key
            elif wt:
                tr.status, tr.stop_stage = "SCOPE_WOULD_EXPAND", "SCOPE"
                tr.detail = "contract %s proven on %s%d only, and for a structured operand" % (wt[0].contract_key, root, wt[0].index)
            else:
                tr.status, tr.stop_stage, tr.detail = "NO_CAPABILITY", "CONTRACT_LOOKUP", "no wavetable contract"
            return None, tr
        if not root or not kp:
            tr.status, tr.stop_stage = "NO_CAPABILITY", "STRUCTURAL_KEY"
            tr.detail = "no catalog kParam for %s.%s" % (op["module"], op["field"])
            return None, tr
        key = "%s%d.%s" % (root, op["index"], kp)
        tr.stages.append(("STRUCTURAL_KEY", key))
        same = [c for c in cov if c.root == root and c.kparam == kp and c.kind == "instance"]
        exact = [c for c in same if c.index == op["index"]]
        if exact:
            return exact[0], tr
        if same:
            tr.status, tr.stop_stage = "SCOPE_WOULD_EXPAND", "SCOPE"
            tr.detail = "contract %s proven on %s%d only; operation targets %s%d" % (
                same[0].contract_key, root, same[0].index, root, op["index"])
            return None, tr
        tr.status, tr.stop_stage, tr.detail = "NO_CAPABILITY", "CONTRACT_LOOKUP", "no contract covers %s" % key
        return None, tr
    tr.status, tr.stop_stage, tr.detail = "NO_CAPABILITY", "CONTRACT_LOOKUP", "unsupported operation kind %s" % op["kind"]
    return None, tr
