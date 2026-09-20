"""Exact-state comparator: writes nothing, reads the written preset back through serum-mcp's own
reader and compares normalized state tuples per feature (FX unit, oscillator, envelope, ...).
Every reproduced field ends as exactly one of:
  VERIFIED_EXACT | VERIFIED_WITH_NORMALIZATION | OVERRIDDEN_APPROXIMATION | MISMATCH | NOT_COMPILED
and every group as EXACT_STATE only if all of its OBSERVED members were reproduced and verified exactly.
"""
from __future__ import annotations

import math
import re
import sys
from collections import Counter, defaultdict
from typing import Any, Dict, List, Tuple

sys.path.insert(0, "D:/serum-mcp/src")

_GROUP_FX = re.compile(r"^fx\.([a-z]+)\.")
_RANK = {"VERIFIED_EXACT": 0, "VERIFIED_WITH_NORMALIZATION": 1, "OVERRIDDEN_APPROXIMATION": 2, "NOT_COMPILED": 3, "MISMATCH": 4}


def read_back(preset_path: str):
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


def compare(rows, back, compiled_ids: set) -> Dict[str, Any]:
    fields: Dict[str, str] = {}
    for r in rows:
        o = r.op
        if not o or r.terminal != "OPERATION_DERIVED":
            continue
        oid = "%s@%s" % (r.control_id, r.context.get("rack", "-"))
        if oid not in compiled_ids:
            continue
        want = o.get("value", o.get("amount"))
        got = _actual(o, r.context.get("rack"), back)
        fid = "APPROXIMATED" if o.get("fidelity") == "APPROXIMATED_FROM_TEMPO" else ("NORMALIZED" if o.get("normalized") else "EXACT")
        if got is None or not _close(got, want):
            st = "OVERRIDDEN_APPROXIMATION" if fid == "APPROXIMATED" else "MISMATCH"
        else:
            st = {"EXACT": "VERIFIED_EXACT", "NORMALIZED": "VERIFIED_WITH_NORMALIZATION", "APPROXIMATED": "OVERRIDDEN_APPROXIMATION"}[fid]
        r.execution = "%s(observed=%r, wanted=%r, file_has=%r)" % (st, r.value, want, got)
        fields[r.control_id + "@" + str(r.context.get("rack", "-"))] = st
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
        exact = worst == "VERIFIED_EXACT" and not g["unreproduced"]
        out[str(k)] = {"state": "EXACT_STATE" if exact else ("PARTIAL_STATE(%d observed members not reproduced)" % len(g["unreproduced"]) if worst in ("VERIFIED_EXACT", "VERIFIED_WITH_NORMALIZATION") else worst),
                       "fields": dict(g["fields"]), "unreproduced": g["unreproduced"]}
    return {"field_counts": dict(Counter(fields.values())), "groups": out}
