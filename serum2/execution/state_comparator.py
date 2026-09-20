"""Serialisation + state comparison, with the proof levels kept apart.

  COMPILED -> SERIALIZED -> FILE_READBACK -> (Serum loads it) -> DIRECT_UI_READBACK -> NORMALIZED_COMPARISON

A .SerumPreset that matches what the compiler intended is FILE evidence only. It says nothing about what a real
Serum instance loaded. Only a DIRECT_UI readback of the live plugin can raise a run to LIVE_UI_VERIFIED, and an
OVERRIDDEN_APPROXIMATION is never counted as exact.

Every reproduced field ends as exactly one of:
  VERIFIED_EXACT | VERIFIED_WITH_NORMALIZATION | OVERRIDDEN_APPROXIMATION | MISMATCH | NOT_COMPILED | UNREADABLE
and every group as EXACT_STATE only if all OBSERVED members were reproduced and verified exactly.
"""
from __future__ import annotations

import math
import re
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple

sys.path.insert(0, "D:/serum-mcp/src")

from serum2.execution.authorized_state_compiler import CompileReport  # noqa: E402

_GROUP_FX = re.compile(r"^fx\.([a-z]+)\.")
_RANK = {"VERIFIED_EXACT": 0, "VERIFIED_WITH_NORMALIZATION": 1, "OVERRIDDEN_APPROXIMATION": 2, "UNREADABLE": 3,
         "NOT_COMPILED": 4, "MISMATCH": 5}
FILE_READBACK = "FILE_READBACK"
DIRECT_UI = "DIRECT_UI"


def serialize(report: CompileReport, subfolder: str = "VLP1") -> str:
    """Write the .SerumPreset for a COMPLETE compile of authorized operations. Nothing else can be serialized."""
    if report.status != "SUCCESS" or report.admitted != report.compiled or not report.ops:
        raise RuntimeError("refusing to serialize: compilation is %s (%d/%d)" % (report.status, report.compiled, report.admitted))
    from serum_mcp.generation.spec import PresetSpec
    from serum_mcp.tools.generate_preset import generate_preset
    return generate_preset(PresetSpec(**report.spec), subfolder=subfolder).splitlines()[0]


def read_back_file(preset_path: str):
    from serum_mcp.preset.introspect import extract_spec
    from serum_mcp.preset.packer import unpack_file
    return extract_spec(unpack_file(preset_path).data)


def _actual(op: Dict[str, Any], rack, back):
    if op["kind"] == "field":
        items = getattr(back, op["list"])
        return getattr(items[op["index"]], op["field"], None) if op["index"] < len(items) else None
    if op["kind"] == "fx":
        u = next((u for u in back.fx_chain if u.type == op["fx_type"] and u.rack == (rack or 0)), None)
        return None if u is None else (u.wet if op["param"] == "kParamWet" else u.params.get(op["param"]))
    m = next((m for m in back.mod_routes if m.source == op["source"] and m.destination == op["destination"]), None)
    return m.amount if m else None


def _close(a, b) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return bool(a) == bool(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=1e-6, abs_tol=1e-6)
    return a == b


def _group(row) -> Tuple:
    o = row.op
    if o and o["kind"] == "fx":
        return ("fx", row.context.get("rack", 0), o["fx_type"])
    if o and o["kind"] == "field":
        return (o["list"], o["index"])
    m = _GROUP_FX.match(row.control_id)
    if m:
        return ("fx-unit-token", row.context.get("rack", 0), m.group(1))
    return (row.control_id.split(".")[0],)


def _grade(fid: str, ok: bool) -> str:
    if fid == "APPROXIMATED":
        return "OVERRIDDEN_APPROXIMATION"
    if not ok:
        return "MISMATCH"
    return "VERIFIED_WITH_NORMALIZATION" if fid == "NORMALIZED" else "VERIFIED_EXACT"


def _groups(rows, fields: Dict[str, str]) -> Dict[str, Any]:
    groups: Dict[Tuple, Dict[str, Any]] = defaultdict(lambda: {"fields": {}, "unreproduced": []})
    for r in rows:
        if r.terminal in ("IGNORED_NAVIGATION", "NOT_SERUM_SURFACE"):
            continue
        g = groups[_group(r)]
        key = r.control_id + "@" + str(r.context.get("rack", "-"))
        if key in fields:
            g["fields"][r.control_id] = fields[key]
        else:
            g["unreproduced"].append((r.control_id, r.terminal if r.terminal != "OPERATION_DERIVED" else "NOT_ADMITTED/" + r.admission))
    out = {}
    for k, g in groups.items():
        if not g["fields"]:
            continue
        worst = max(g["fields"].values(), key=lambda s: _RANK[s])
        ok = worst in ("VERIFIED_EXACT", "VERIFIED_WITH_NORMALIZATION")
        state = "EXACT_STATE" if (worst == "VERIFIED_EXACT" and not g["unreproduced"]) else (
            "PARTIAL_STATE(%d observed members not reproduced)" % len(g["unreproduced"]) if ok else worst)
        out[str(k)] = {"state": state, "fields": dict(g["fields"]), "unreproduced": g["unreproduced"]}
    return out


def compare_file(rows, back, report: CompileReport) -> Dict[str, Any]:
    """FILE_READBACK comparison of the serialized preset against the authorized operands."""
    ids = {o.operation_id for o in report.ops}
    fields: Dict[str, str] = {}
    for r in rows:
        o = r.op
        oid = "%s@%s" % (r.control_id, r.context.get("rack", "-"))
        if not o or r.terminal != "OPERATION_DERIVED" or oid not in ids:
            continue
        want = o.get("value", o.get("amount"))
        got = _actual(o, r.context.get("rack"), back)
        fid = "APPROXIMATED" if o.get("fidelity") == "APPROXIMATED_FROM_TEMPO" else ("NORMALIZED" if o.get("normalized") else "EXACT")
        st = _grade(fid, got is not None and _close(got, want))
        r.execution = "%s[%s](observed=%r, wanted=%r, file_has=%r)" % (st, FILE_READBACK, r.value, want, got)
        fields[r.control_id + "@" + str(r.context.get("rack", "-"))] = st
    return {"route": FILE_READBACK, "field_counts": dict(Counter(fields.values())), "fields": fields,
            "groups": _groups(rows, fields)}


def _ui_equal(expected: Any, ui_text: Any) -> bool:
    from serum2.producer.state_ledger import _numeric, exact_norm
    a, b = _numeric(expected, None), _numeric(ui_text, None)
    if a and b:
        return a[1] == b[1] and math.isclose(a[0], b[0], rel_tol=1e-9, abs_tol=1e-9)
    return exact_norm(expected) == exact_norm(ui_text)


def compare_ui(rows, ui_readback: Dict[str, Any], report: CompileReport) -> Dict[str, Any]:
    """DIRECT_UI comparison: what the LIVE Serum showed, per control id, against what the video showed for the
    same control. ui_readback = {"route": "DIRECT_UI", "captured_at": ..., "values": {control_id: text}}.
    A control that was compiled but has no UI reading is UNREADABLE (never assumed correct)."""
    if ui_readback.get("route") != DIRECT_UI:
        raise ValueError("ui_readback must come from the DIRECT_UI route")
    ids = {o.operation_id for o in report.ops}
    vals = ui_readback["values"]
    fields: Dict[str, str] = {}
    for r in rows:
        oid = "%s@%s" % (r.control_id, r.context.get("rack", "-"))
        if not r.op or oid not in ids:
            continue
        fid = "APPROXIMATED" if r.op.get("fidelity") == "APPROXIMATED_FROM_TEMPO" else ("NORMALIZED" if r.op.get("normalized") else "EXACT")
        if r.control_id not in vals:
            st = "UNREADABLE"
        else:
            st = _grade(fid, _ui_equal(r.value, vals[r.control_id]))
        fields[r.control_id + "@" + str(r.context.get("rack", "-"))] = st
    return {"route": DIRECT_UI, "captured_at": ui_readback.get("captured_at"), "field_counts": dict(Counter(fields.values())),
            "fields": fields, "groups": _groups(rows, fields)}


def verification_level(file_cmp: Dict[str, Any], ui_cmp: Dict[str, Any] = None) -> str:
    """The highest proof actually reached. Approximation/mismatch/unreadable never reach VERIFIED."""
    bad = ("MISMATCH", "UNREADABLE", "NOT_COMPILED", "OVERRIDDEN_APPROXIMATION")
    if any(k in file_cmp["field_counts"] for k in bad):
        return "FILE_READBACK_FAILED_OR_APPROXIMATE"
    if ui_cmp is None:
        return "FILE_READBACK_VERIFIED_ONLY"
    if any(k in ui_cmp["field_counts"] for k in bad):
        return "UI_READBACK_FAILED_OR_INCOMPLETE"
    return "LIVE_UI_VERIFIED"
