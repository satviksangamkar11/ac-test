"""H1 regression + evidence-derived (never caller-supplied) execution binding."""
import inspect
from serum2.evidence.capability_contract import build_contract, STRUCTURAL_ONLY
from serum2.evidence.claim import ClaimDefinition, ClaimEngine, SINGLE_FIELD
from serum2.evidence.record import EvidenceRecord, PASS

PATH = "Env1.plainParams.kParamDecay"
BE = {"status": "BINDING_VERIFIED", "accessor": "envelopes[1].decay", "derived_body_path": PATH,
      "value_landed_in_derived_path": True, "collateral_semantically_neutral": True, "second_write_neutral": True}


def _defn():
    return ClaimDefinition(
        claim_type="t_env2_decay", subject_pattern={"kind": "envelope_field"}, predicate="constructs_mutates_persists",
        required_gate={"load": PASS, "persistence": PASS}, required_isolation=(SINGLE_FIELD,),
        breadth_rule={"sampled_min": 1}, coverage_rule={"generalizing_dimensions": [], "family_min_distinct": 1},
        contradiction_rule={"require_same_mutation": True}, dependency_rule={"enabled": False})


def _rec(binding_evidence=None, mut_path=PATH):
    exp = {"isolation_level": SINGLE_FIELD, "mutations": [{"target_path": mut_path, "value": 2.0}],
           "experiment_condition_signature": {"hash": "c1"}, "mutation_signature": "m1"}
    if binding_evidence is not None:
        exp["binding_evidence"] = binding_evidence
    return EvidenceRecord(experiment_id="E1", epoch={}, experiment=exp, arms=(), runtime_verifications=(),
                          state_observation={"status": PASS}, load_observation={"status": PASS}, render_observation={},
                          causal_measurements=(), persistence_observation={"status": PASS})


def _contract(rec):
    eng = ClaimEngine({"t_env2_decay": _defn()})
    return build_contract(eng.add(rec, "t_env2_decay"))


def test_h1_claim_definition_id_and_contract_build():
    d = _defn()
    assert d.claim_definition_id.startswith("t_env2_decay:") and len(d.claim_definition_id.split(":")[1]) == 8
    assert _contract(_rec()).status == STRUCTURAL_ONLY


def test_binding_derived_from_record_evidence():
    b = _contract(_rec(BE)).execution_binding
    assert (b.mutation_type, b.body_path, b.resolver_operation_id) == ("SERUM_PRESET_STRUCTURAL", PATH, "envelopes[1].decay")
    assert b.binding_source == "evidence:E1"


def test_no_binding_without_or_with_bad_evidence():
    assert _contract(_rec()).execution_binding is None
    assert _contract(_rec(dict(BE, status="BINDING_NOT_VERIFIED"))).execution_binding is None
    assert _contract(_rec(dict(BE, second_write_neutral=False))).execution_binding is None
    assert _contract(_rec(dict(BE, derived_body_path="Env2.plainParams.kParamDecay"))).execution_binding is None  # other path


def test_binding_cannot_be_caller_supplied():
    assert list(inspect.signature(build_contract).parameters) == ["group"]
