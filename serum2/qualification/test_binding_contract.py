"""The universal path works for ARBITRARY candidates; no control is special. Fixtures are data only."""
import glob, json, pathlib
import pytest
from serum2.producer.execution_epoch import EPOCH_2_0_23, EPOCH_2_0_21
from serum2.qualification.binding_contract import contract_from_binding_evidence

def _ev(cid, path, acc, v=1.0, **kw):
    d = {"control_id": cid, "accessor": acc, "derived_body_path": path, "status": "BINDING_VERIFIED", "run_status": "STRUCTURAL_VERIFIED",
         "second_write_value": v, "value_landed_in_derived_path": True, "collateral_semantically_neutral": True, "second_write_neutral": True}
    d.update(kw); return d

CANDIDATES = [_ev("x.a", "ModuleA0.plainParams.kParamOne", "things[0].one"),
              _ev("x.b", "ModuleB3.plainParams.kParamTwo", "others[3].two", False),
              _ev("x.c", "Deep.Nested.path", "l[7].f", 0.25)]

@pytest.mark.parametrize("ev", CANDIDATES, ids=lambda e: e["control_id"])
def test_arbitrary_candidate_yields_evidence_derived_contract(ev):
    c = contract_from_binding_evidence(ev, EPOCH_2_0_23)
    assert c.status == "STRUCTURAL_ONLY" and c.target == ev["control_id"]
    b = c.execution_binding
    assert (b.mutation_type, b.body_path, b.resolver_operation_id) == ("SERUM_PRESET_STRUCTURAL", ev["derived_body_path"], ev["accessor"])
    assert c.scope["mutation_target_path"] == ev["derived_body_path"] and c.scope["serum_binary_sha256"] == EPOCH_2_0_23.binary_sha256
    assert c.verified["causal"] == "NOT_RUN" and c.provenance["supporting_evidence"]

def test_epoch_is_data_not_assumed():
    a = contract_from_binding_evidence(CANDIDATES[0], EPOCH_2_0_23); b = contract_from_binding_evidence(CANDIDATES[0], EPOCH_2_0_21)
    assert a.scope["serum_binary_sha256"] != b.scope["serum_binary_sha256"]

@pytest.mark.parametrize("bad", [{"status": "BINDING_NOT_VERIFIED"}, {"second_write_neutral": False}, {"value_landed_in_derived_path": False},
                                 {"derived_body_path": None}, {"second_write_value": None}, {"run_status": "FAILED"}])
def test_unverified_evidence_gives_no_binding(bad):
    c = contract_from_binding_evidence(_ev("x.a", "P.q", "l[0].f", **bad), EPOCH_2_0_23)
    assert c is None or c.execution_binding is None

def test_real_qualifier_outputs_use_the_same_unmodified_path():
    files = glob.glob(str(pathlib.Path(__file__).parents[2] / "serum2/data/runs/*/capability/binding_qualification/*.json"))
    files = [f for f in files if json.load(open(f)).get("status") == "BINDING_VERIFIED"]
    if not files:
        pytest.skip("no real qualifier evidence on disk")
    for f in files:
        ev = json.load(open(f)); c = contract_from_binding_evidence(ev, EPOCH_2_0_23)
        assert c.execution_binding.body_path == ev["derived_body_path"], f
