"""Execution-binding qualification for the Pass-1 contracts (SERUM_PRESET_STRUCTURAL_BINDING).

For each Pass-1 target this runs the repo's unmodified StructuralQualificationRunner
(LOAD -> READ_BASELINE -> MUTATE -> READ_AFTER_MUTATION -> PERSIST -> RELOAD -> READ_AFTER_RELOAD) through
serum-mcp's own describe/edit tools, and adds the check that ties the binding to the CONTRACT:
the serum-mcp accessor must write the body path the contract was proven on (its
scope.mutation_target_path), with every other field semantically unchanged. Only then is a binding evidence file written;
the registry attaches a binding only from such a file.

Run:  python -m serum2.qualification.pass1.qualify_bindings_pass1   (from the current repo root)
"""
from __future__ import annotations

import hashlib
import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "D:/serum-mcp/src")

from serum2.evidence.capability_contract import ExecutionBinding  # noqa: E402
from serum2.pathmerge import read_path_value  # noqa: E402
from serum2.producer.batch_qualification_system import (  # noqa: E402
    BindingCandidate, MutationSpec, OperationFamily, RouteType, StructuralQualificationRunner)

STORE = ROOT / "experiments" / "_capability_contracts_pass1.pkl"
OUT = ROOT / "serum2" / "qualification" / "pass1" / "bindings"

# capability_key -> (spec list, index, field, semantic target, mutation value, family)
ACCESSORS = {}
for cap, idx, name in (("oscillator_field_OSC2-ENABLE", 1, "OSC2"), ("oscillator_field_OSC3-ENABLE", 2, "OSC3")):
    ACCESSORS[cap] = ("oscillators", idx, "enabled", "%s.Enable" % name, True, OperationFamily.TOGGLE)
for cap, idx, name in (("oscillator_field_OSC2-OCTAVE", 1, "OSC2"), ("oscillator_field_OSC3-OCTAVE", 2, "OSC3")):
    ACCESSORS[cap] = ("oscillators", idx, "octave", "%s.Octave" % name, 2.0, OperationFamily.NUMERIC)
for n in (2, 3, 4):
    for f in ("decay", "release"):
        ACCESSORS["envelope%d_field_%s" % (n, f)] = ("envelopes", n - 1, f, "Env%d.%s" % (n, f.capitalize()), 0.5, OperationFamily.NUMERIC)


class FieldBackend:
    """serum-mcp backed lifecycle for `<list>[i].<field>` accessors. State = the .SerumPreset file only."""

    def __init__(self, path, lst, idx, fld):
        from serum_mcp.tools.edit_preset import edit_preset
        from serum_mcp.preset.introspect import extract_spec
        from serum_mcp.preset.packer import unpack_file
        from serum_mcp.tools.describe_preset import describe_preset
        from serum_mcp.generation.spec import PresetSpec
        self.p, self.lst, self.idx, self.fld = str(path), lst, idx, fld
        self._edit, self._extract, self._unpack, self._describe, self._Spec = edit_preset, extract_spec, unpack_file, describe_preset, PresetSpec
        self.body_before = None

    def _value(self):
        items = getattr(self._extract(self._unpack(self.p).data), self.lst)
        return getattr(items[self.idx], self.fld)

    def load(self, c):
        self._describe(self.p)
        self.body_before = self._unpack(self.p).data
        self.spec_before = self._extract(self.body_before).model_dump()
        return {"preset_path": self.p, "tool": "serum_mcp.tools.describe_preset"}

    def read(self, c):
        return self._value()

    def mutate(self, c, m):
        items = list(getattr(self._extract(self._unpack(self.p).data), self.lst))
        items = items[:self.idx] + [items[self.idx].model_copy(update={self.fld: m.value})]
        written = self._edit(self.p, self._Spec(name="", description="", **{self.lst: items}))
        return {"tool": "serum_mcp.tools.edit_preset", "value": m.value, "written_path": written.splitlines()[0]}

    def persist(self, c):
        b = Path(self.p).read_bytes()
        return {"path": self.p, "size_bytes": len(b), "sha256": hashlib.sha256(b).hexdigest().upper()}

    def reload(self, c):
        return {"path": self.p, "tool": "serum_mcp.tools.describe_preset"}


def changed_top_keys(a, b):
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


def main():
    from serum_mcp.generation.spec import PresetSpec
    from serum_mcp.tools.generate_preset import generate_preset
    store = pickle.load(open(STORE, "rb"))
    contracts = {c.target: c for c in store.values()}
    OUT.mkdir(parents=True, exist_ok=True)
    results = {}
    for cap, (lst, idx, fld, target, value, family) in ACCESSORS.items():
        contract = contracts[cap]
        body_path = contract.scope["mutation_target_path"]
        fixture = generate_preset(PresetSpec(name="pass1-binding-%s" % cap, description="binding qualification fixture"),
                                  subfolder="VLP1-pass1-bindings").splitlines()[0]
        accessor = "%s[%d].%s" % (lst, idx, fld)
        cand = BindingCandidate(
            target=target, capability_key=cap, route_type=RouteType.SERUM_PRESET_STRUCTURAL_BINDING,
            binding=ExecutionBinding(mutation_type="SERUM_PRESET_STRUCTURAL", binding_source="pass1 accessor evidence",
                                     binding_version="pass1-2.0.23", resolver_operation_id=accessor),
            operation_family=family, provenance="pass1 evidence-derived accessor", confidence=1.0, verified=True,
            evidence_ref=str(OUT / (cap + ".json")))
        backend = FieldBackend(fixture, lst, idx, fld)
        baseline = backend._value()
        assert baseline != value, (cap, "baseline already equals mutation value", baseline)
        run = StructuralQualificationRunner(backend).run(cand, MutationSpec(target=target, value=value, operation="set"))
        after_body = backend._unpack(fixture).data
        tops = changed_top_keys(backend.body_before, after_body)
        root = body_path.split(".")[0]
        body_before_v = read_path_value(backend.body_before, body_path)
        body_after_v = read_path_value(after_body, body_path)
        import copy
        expected = copy.deepcopy(backend.spec_before)
        expected[lst][idx][fld] = value
        spec_after = backend._extract(after_body).model_dump()
        semantic_only_target_changed = (spec_after == expected)
        collateral = [k for k in tops if k != root]
        path_ok = (root in tops and body_before_v != body_after_v and float(body_after_v) == float(value)
                   and semantic_only_target_changed)
        verified = run.status == "STRUCTURAL_VERIFIED" and path_ok
        ev = {"capability_key": cap, "semantic_target": target, "accessor": accessor, "contract_body_path": body_path,
              "qualified_at": datetime.now(timezone.utc).isoformat(), "fixture": fixture,
              "baseline": baseline, "mutation_value": value, "run": run.to_dict(),
              "body_top_level_changes": tops, "collateral_body_key_changes": collateral,
              "collateral_semantically_neutral": semantic_only_target_changed, "body_value_before": body_before_v, "body_value_after": body_after_v,
              "accessor_writes_contract_body_path": path_ok,
              "status": "BINDING_VERIFIED" if verified else "BINDING_NOT_VERIFIED",
              "notes": "File-level, serum-mcp only. Binds the serum-mcp accessor to the contract's proven body path. "
                       "edit_preset re-serializes earlier slots (collateral_body_key_changes); verified semantically neutral: "
                       "the whole extracted spec equals the pre-mutation spec except the one targeted field."}
        (OUT / (cap + ".json")).write_text(json.dumps(ev, indent=2, default=str) + "\n", encoding="utf-8")
        results[cap] = ev["status"]
        print("%-32s %-18s run=%s tops=%s body %r->%r" % (cap, ev["status"], run.status, tops, body_before_v, body_after_v))
    return results


if __name__ == "__main__":
    r = main()
    sys.exit(0 if all(v == "BINDING_VERIFIED" for v in r.values()) else 1)
