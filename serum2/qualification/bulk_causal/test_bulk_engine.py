"""The context-based bulk engine: parameter-by-parameter mutation inside ONE context, restoration between parameters,
generic range plans, deterministic evidence, no preset-per-observation, no authority files touched."""
import copy
import glob
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bulk_engine as be  # noqa: E402
from compare import compare  # noqa: E402
from range_plan import plan  # noqa: E402

ED = HERE.parents[2] / "parameter_characterization" / "bulk_causal_evidence"
BASE = {"FXRack0": {"FX": [{"type": 7, "FXEQ": {"plainParams": {"a": 1.0, "b": 2.0, "c": 3.0}}}]}, "Other": {"x": 1}}


class FakeBackend:
    """Stands in for Serum: keeps the loaded body, 'clamps' every param to [0,100], synthesizes audio from it."""
    instances = []

    def __init__(self):
        self.body, self.history = None, []
        FakeBackend.instances.append(self)

    def load(self, body):
        self.body = copy.deepcopy(body)
        self.history.append(be.sha(body))

    def observe(self):
        pp = copy.deepcopy(self.body["FXRack0"]["FX"][0]["FXEQ"]["plainParams"])
        for k, v in pp.items():
            pp[k] = min(100.0, max(0.0, v))
        st = copy.deepcopy(self.body)
        st["FXRack0"]["FX"][0]["FXEQ"]["plainParams"] = pp
        return {"state": st, "band_db": [round(sum(pp.values()) / 10, 2), 0.0], "hosts": {"h": "%s" % sum(pp.values())}}


def params(*keys, kind="continuous"):
    return [{"atlas_id": "t." + k, "context": "C", "mutation": {"kind": "fx_param", "index": 0, "module": "FXEQ", "kparam": k},
             "domain": {"kind": kind, "min": 0.0, "max": 100.0}} for k in keys]


def run(ps, size=10):
    FakeBackend.instances = []
    c = {}
    r = be.run_context("C", BASE, ps, FakeBackend, {"session_size": size}, c)
    return r, c


def test_context_loaded_once_per_session_batch():
    _, c = run(params("a", "b", "c", "d", "e"), size=3)
    assert c["sessions"] == 2 and c["context_loads"] == 2 and len(FakeBackend.instances) == 2


def test_restoration_after_every_parameter_and_isolation():
    r, _ = run(params("a", "b", "c"))
    h = FakeBackend.instances[0].history
    base = be.sha(BASE)
    assert h[0] == base
    seg = [i for i, x in enumerate(h) if x == base]
    assert len(seg) >= 2 + 3                       # initial load + floor reload + one restore per parameter
    for rec in r:
        assert rec["restoration"]["ok"]
        for v in rec["values"]:
            assert v["state_diff_keys"] in ([], [rec["candidate"]["kparam"]])  # only the mutated key can differ


def test_base_body_never_mutated_and_no_persistent_files():
    before = copy.deepcopy(BASE)
    run(params("a", "b"))
    assert BASE == before


def test_range_plans_are_generic_per_kind():
    for kind, dom in (("bool", {}), ("enum", {"values": [0, 1, 2]}), ("int", {"min": 0, "max": 20}), ("continuous", {"min": 0.0, "max": 1.0}),
                      ("signed", {"min": -1.0, "max": 1.0}), ("log", {"min": 1.0, "max": 1000.0})):
        d = {"kind": kind, **dom}
        ps = [{"atlas_id": "t", "context": "C", "mutation": {"kind": "fx_param", "index": 0, "module": "FXEQ", "kparam": "a"}, "domain": d}]
        r, _ = run(ps)
        assert r[0]["value_vector"] == plan(d)
        assert [v["written"] for v in r[0]["values"]] == plan(d)["values"] + plan(d)["probes"]


def test_engine_evidence_is_deterministic():
    a, _ = run(params("a", "b", "c"))
    b, _ = run(params("a", "b", "c"))
    assert a == b


def test_raw_path_mutation_works_for_any_family():
    ps = [{"atlas_id": "t", "context": "C", "mutation": {"kind": "raw_path", "path": ["Other", "x"]}, "domain": {"kind": "bool"}}]
    body = copy.deepcopy(BASE)
    be.body_set(body, ps[0]["mutation"]["path"], 5.0)
    assert body["Other"]["x"] == 5.0 and BASE["Other"]["x"] == 1.0


def test_engine_has_no_per_parameter_code_and_touches_no_authority_files():
    for f in ("bulk_engine.py", "bulk_worker.py", "serum_backend.py", "preset_build.py"):
        src = (HERE / f).read_text()
        for banned in ("serum_mcp_binding_table", "serum_mcp_mutable_surface", "master_parameter_registry", "admission", "capability_contract"):
            assert banned not in src, (f, banned)
    assert "kParam" not in (HERE / "bulk_engine.py").read_text()


PILOT = ED / "bulk_fx_eq_pilot_v1.json"


@pytest.mark.skipif(not PILOT.exists(), reason="pilot evidence not present")
def test_pilot_is_parameter_by_parameter_inside_one_context():
    d = json.loads(PILOT.read_text())
    h = d["harness"]
    assert h["persistent_presets_written"] == 1 and len(h["context_presets"]) == 1
    assert h["parameters"] >= 10 and h["values_observed"] >= 80 and h["sessions"] == 1 and h["context_loads"] == 1
    assert h["state_loads"] > 5 * h["persistent_presets_written"] * h["parameters"] / 5   # many loads, still one preset
    assert not [p for p in glob.glob(str(HERE / "**" / "*.SerumPreset"), recursive=True) if not p.endswith("QUAL_FX_EQ.SerumPreset")]
    for r in d["records"]:
        assert r["restoration"]["ok"], r["candidate"]["kparam"]
        assert all(v["file_roundtrip"] for v in r["values"])
        assert all(v["state_diff_keys"] in ([], [r["candidate"]["kparam"]]) for v in r["values"])


@pytest.mark.skipif(not PILOT.exists(), reason="pilot evidence not present")
def test_pilot_agrees_with_the_legacy_per_test_range_evidence():
    res = compare(json.loads(PILOT.read_text()), json.loads((ED / "fx_range_v1.json").read_text()))
    assert len(res) == 8 and all(v["agree"] for v in res.values()), res


def test_historical_evidence_is_still_present():
    v1 = json.loads((ED / "fx_verify_v1.json").read_text())["records"]
    v2 = json.loads((ED / "fx_verify_v2.json").read_text())["records"]
    assert {r["id"]: r["status"] for r in v1}["eq_right_type"] == "FAILED" and {r["id"]: r["status"] for r in v2}["eq_right_type"] == "PROVEN"
    assert len(json.loads((ED / "fx_range_v1.json").read_text())["records"]) == 18
