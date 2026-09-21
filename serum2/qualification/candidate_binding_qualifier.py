"""Candidate-driven execution-binding qualification through serum-mcp (no per-capability table).

Input is only a control id. Its candidate accessor {list, index, field} comes from serum_mcp_binding_table.json
(a name match = a CANDIDATE, never proof); its value domain comes from the Atlas. The mutation value is any domain
value different from the fixture's own baseline. The body path is NOT read from any table: it is the single body key
that changes on a second, observably effective write (after the first write has materialised serum-mcp's default keys). Verified only if: lifecycle run passes, the requested value lands in that key, the whole extracted spec differs
only in the targeted field after each write (collateral neutral).

Run: python -m serum2.qualification.candidate_binding_qualifier <control_id> [...] [--out DIR]
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "vendor" / "serum-mcp" / "src"))

from serum2.evidence.capability_contract import ExecutionBinding  # noqa: E402
from serum2.producer.batch_qualification_system import (  # noqa: E402
    BindingCandidate, MutationSpec, OperationFamily, RouteType, StructuralQualificationRunner)
from serum2.qualification.pass1.qualify_bindings_pass1 import FieldBackend  # noqa: E402
from serum2.reference.serum_atlas import get_control  # noqa: E402

TABLE = ROOT / "serum2" / "reference" / "serum_mcp_binding_table.json"
FAMILY = {"toggle": OperationFamily.TOGGLE, "continuous": OperationFamily.NUMERIC}


def _flat(d, pre=""):
    if isinstance(d, dict):
        return {k2: v for k, v in d.items() for k2, v in _flat(v, f"{pre}.{k}" if pre else k).items()}
    if isinstance(d, list):
        return {k2: v for i, x in enumerate(d) for k2, v in _flat(x, f"{pre}[{i}]").items()}
    return {pre: d}


def _changed(a, b):
    """keys present in both whose value changed / keys added or removed."""
    fa, fb = _flat(a), _flat(b)
    return (sorted(k for k in fa.keys() & fb.keys() if fa[k] != fb[k]), sorted(fa.keys() ^ fb.keys()))


def field_domain(lst: str, fld: str) -> dict:
    """The serum-mcp schema's own declaration for one field: bool / int / float and its numeric bounds."""
    import typing
    from serum_mcp.generation.spec import PresetSpec
    item = typing.get_args(PresetSpec.model_fields[lst].annotation)[0]
    f = item.model_fields[fld]
    ann = f.annotation
    lo = hi = None
    for m in f.metadata:
        lo = getattr(m, "ge", getattr(m, "gt", lo)) if hasattr(m, "ge") or hasattr(m, "gt") else lo
        hi = getattr(m, "le", getattr(m, "lt", hi)) if hasattr(m, "le") or hasattr(m, "lt") else hi
    return {"is_bool": ann is bool, "is_int": ann is int, "is_float": ann is float, "lo": lo, "hi": hi}


def value_domain(control, dom: dict) -> dict:
    """Valid mutation domain = Atlas bounds INTERSECT schema bounds; integer if Atlas (VST3 class INTEGER) or schema says so.
    Raises NotImplementedError when the schema cannot establish a domain (-> QUALIFICATION_BLOCKED)."""
    if control.control_type == "toggle":
        if not dom["is_bool"]:
            raise NotImplementedError("toggle control but schema field is not bool")
        return {"kind": "bool"}
    if control.control_type != "continuous":
        raise NotImplementedError("no generic domain rule for control_type=%r" % control.control_type)
    los = [x for x in (control.min_value, dom["lo"]) if x is not None]
    his = [x for x in (control.max_value, dom["hi"]) if x is not None]
    if not los or not his or not (dom["is_int"] or dom["is_float"]):
        raise NotImplementedError("bounds/type not established by schema")
    integer = dom["is_int"] or (getattr(control, "audit", None) or {}).get("control_type") == "integer"
    return {"kind": "integer" if integer else "float", "lo": max(los), "hi": min(his)}


def domain_value(control, baseline, domain: dict):
    """Any in-domain value different from baseline, respecting type."""
    if domain["kind"] == "bool":
        return not baseline
    lo, hi = domain["lo"], domain["hi"]
    step = 0.1 * (hi - lo)
    if domain["kind"] == "integer":
        step = max(1, round(step))
    for v in (baseline + step, baseline - step):
        if lo <= v <= hi and v != baseline:
            return float(v) if domain["kind"] == "integer" else v
    raise NotImplementedError("no in-domain value differs from baseline %r within [%r, %r]" % (baseline, lo, hi))


_EPOCH = []


def _serum_identity() -> dict:
    """Serum build installed when this evidence was produced (serum-mcp itself never runs Serum). None if not a known build."""
    if not _EPOCH:
        from serum2.producer.execution_epoch import installed_epoch
        try:
            e = installed_epoch()
            _EPOCH.append({"serum_binary_sha256": e.binary_sha256, "serum_product_version": e.serum_version})
        except Exception:
            _EPOCH.append({"serum_binary_sha256": None, "serum_product_version": None})
    return _EPOCH[0]


def qualify(control_id: str, out: Path) -> dict:
    from serum_mcp.generation.spec import PresetSpec
    from serum_mcp.tools.generate_preset import generate_preset
    entry = json.loads(TABLE.read_text(encoding="utf-8"))["controls"].get(control_id)
    if not entry or entry.get("kind") != "field":
        return {"control_id": control_id, "status": "NOT_A_FIELD_CANDIDATE", "entry": entry}
    lst, idx, fld = entry["list"], entry["index"], entry["field"]
    control = get_control(control_id)
    out.mkdir(parents=True, exist_ok=True)
    gen = Path(generate_preset(PresetSpec(name="qual-%s" % control_id.replace(".", "-"), description="qualification fixture"),
                               subfolder="VLP1-qual-scratch").splitlines()[0])
    fixture = out / gen.name
    shutil.move(str(gen), fixture)
    be = FieldBackend(fixture, lst, idx, fld)
    baseline = be._value()
    try:
        domain = value_domain(control, field_domain(lst, fld))
        value = domain_value(control, baseline, domain)
    except NotImplementedError as e:
        return {"control_id": control_id, "accessor": "%s[%d].%s" % (lst, idx, fld), "status": "QUALIFICATION_BLOCKED", "reason": str(e)}
    accessor = "%s[%d].%s" % (lst, idx, fld)
    cand = BindingCandidate(
        target=control_id, capability_key="candidate:" + control_id,  # label only, grants nothing
        route_type=RouteType.SERUM_PRESET_STRUCTURAL_BINDING,
        binding=ExecutionBinding(mutation_type="SERUM_PRESET_STRUCTURAL", binding_source="candidate accessor (unverified)",
                                 binding_version="candidate", resolver_operation_id=accessor),
        operation_family=FAMILY[control.control_type], provenance="binding-table candidate", confidence=0.0, verified=True)
    run = StructuralQualificationRunner(be).run(cand, MutationSpec(target=control_id, value=value, operation="set"))
    if run.status != "STRUCTURAL_VERIFIED":
        return {"control_id": control_id, "accessor": accessor, "status": "BINDING_NOT_VERIFIED", "run_status": run.status, "run": run.to_dict()}
    after = be._unpack(str(fixture)).data
    spec_before = be.spec_before
    expected = copy.deepcopy(spec_before)
    expected[lst][idx][fld] = value
    neutral = be._extract(after).model_dump() == expected
    # Isolating write: serum-mcp silently drops a write equal to a field's default (stale value stays), so try baseline
    # first and fall back to another in-domain value; keep the first write that observably takes effect.
    second = None
    for v2 in dict.fromkeys([baseline, domain_value(control, value, domain)]):
        be.mutate(cand, MutationSpec(target=control_id, value=v2, operation="set"))
        if be._value() == v2:
            second = v2
            break
    reverted = be._unpack(str(fixture)).data
    changed, added_removed = _changed(after, reverted)
    expected2 = copy.deepcopy(spec_before)
    expected2[lst][idx][fld] = second
    reversible = second is not None and be._extract(reverted).model_dump() == expected2
    body_path = changed[0] if len(changed) == 1 and not added_removed else None
    landed = body_path is not None and second is not None and float(_flat(reverted)[body_path]) == float(second)
    collateral = sorted(set(sum(_changed(be.body_before, after), [])) - {body_path})
    ok = run.status == "STRUCTURAL_VERIFIED" and neutral and reversible and landed
    ev = {"control_id": control_id, "accessor": accessor, "derived_body_path": body_path, "baseline": baseline,
          "value_domain": domain, "serum_identity": _serum_identity(), "mutation_value": value, "run_status": run.status, "run": run.to_dict(), "collateral_semantically_neutral": neutral,
          "collateral_body_keys": collateral, "second_write_value": second, "baseline_restorable": second == baseline, "second_write_neutral": reversible, "value_landed_in_derived_path": landed,
          "status": "BINDING_VERIFIED" if ok else "BINDING_NOT_VERIFIED", "fixture": str(fixture),
          "qualified_at": datetime.now(timezone.utc).isoformat(),
          "notes": "File-level, serum-mcp only; path derived from the revert-step diff, not from any table or contract."}
    (out / (control_id + ".json")).write_text(json.dumps(ev, indent=2, default=str) + "\n", encoding="utf-8")
    return ev


if __name__ == "__main__":
    argv = sys.argv[1:]
    out = ROOT / "serum2" / "qualification" / "candidates"
    if "--out" in argv:
        i = argv.index("--out")
        out = Path(argv[i + 1])
        del argv[i:i + 2]
    args = argv
    for cid in args:
        r = qualify(cid, out)
        print("%-18s %-22s path=%s value=%r->%r" % (cid, r["status"], r.get("derived_body_path"), r.get("baseline"), r.get("mutation_value")))
