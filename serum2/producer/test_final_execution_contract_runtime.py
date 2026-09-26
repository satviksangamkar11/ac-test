"""Runtime-consumption proof (Finish Line B, "final runtime-consumption proof" step).

Proves, through the REAL ProducerBrain / ContractRegistry lookup path (never by opening the JSON
file directly in the test), that:

  1. `env1.attack` -- the one already-proven MCP_EXEC_HOST_CONFIRMED control this step is scoped to
     -- resolves through the real chain (ProducerBrain -> TargetResolver/Atlas -> CapabilityResolver
     -> AdmissionHandoff -> admit() -> ContractGovernedExecutor) to an admitted Serum preset plan.
  2. That plan's execution-EVIDENCE fields (mcp_operation, expected_raw, declared_domain,
     final_execution_classification, exception_policy) come from ContractRegistry's
     `execution_specs` index, sourced ONLY from the committed
     `parameter_characterization/bulk_causal_evidence/final_execution_contract_v1.json`.
  3. The plan's AUTHORITY fields (allowed_operation, admitted status, mutation_target_path,
     mutation_value_used) still come from the existing CapabilityContract / admission chain --
     the final contract never supplies or overrides them.
  4. No legacy pickle store, evidence directory, or hand-authored fallback mapping is the source
     of the execution-evidence fields: this is proven by pointing ContractRegistry.
     FINAL_EXECUTION_CONTRACT_PATH at a temp file with a distinguishable value and observing the
     plan's execution-evidence fields change to exactly that value (they could only have come from
     the file the registry was told to load).
"""
import copy
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
for p in (str(ROOT), str(HERE.parent / "knowledge")):
    if p not in sys.path:
        sys.path.insert(0, p)

from serum2.producer.producer_brain import ProducerBrain, ProducerRequest
from serum2.producer.contract_registry import ContractRegistry

ATLAS_ID = "env1.attack"
CAPABILITY_KEY = "envelope_field_attack"
FINAL_CONTRACT_PATH = (
    ROOT / "parameter_characterization" / "bulk_causal_evidence" / "final_execution_contract_v1.json"
)


def _run():
    return ProducerBrain().execute(ProducerRequest(
        user_intent="longer Env1.Attack to 1.5 ms", mode="EXECUTE", visual_mode="NEVER"))


@pytest.fixture(scope="module")
def final_contract_doc():
    return json.loads(FINAL_CONTRACT_PATH.read_text())


@pytest.fixture(scope="module")
def final_contract_row(final_contract_doc):
    rows = {r["atlas_id"]: r for r in final_contract_doc["rows"]}
    assert ATLAS_ID in rows, "env1.attack must be one of the 330 committed rows"
    return rows[ATLAS_ID]


def test_source_path_is_the_committed_final_contract():
    assert ContractRegistry.FINAL_EXECUTION_CONTRACT_PATH.resolve() == FINAL_CONTRACT_PATH.resolve()


def test_env1_attack_is_host_confirmed_and_restoration_verified(final_contract_row):
    # Scope guard: this step uses exactly the one already-proven HOST_CONFIRMED control named
    # in the task, not a new characterization target.
    assert final_contract_row["final_execution_classification"] == "MCP_EXEC_HOST_CONFIRMED"
    assert final_contract_row["restoration_verified"] is True


def test_registry_execution_spec_matches_the_committed_row(final_contract_row):
    reg = ContractRegistry()
    spec = reg.execution_spec(ATLAS_ID)
    assert spec is not None
    assert spec["source_path"] == str(FINAL_CONTRACT_PATH)
    assert spec["mcp_operation"] == final_contract_row["mcp_operation"]
    assert spec["expected_raw"] == final_contract_row["expected_raw"]
    assert spec["declared_domain"] == final_contract_row["declared_domain"]
    assert spec["final_execution_classification"] == final_contract_row["final_execution_classification"]
    assert spec["restoration_verified"] == final_contract_row["restoration_verified"]


def test_registry_never_falls_back_for_an_unknown_atlas_id():
    reg = ContractRegistry()
    assert reg.execution_spec("not.a.real.control") is None
    assert reg.execution_spec(None) is None


def test_producer_brain_admits_env1_attack_through_the_real_chain():
    r = _run()
    assert r.admitted is True
    assert r.execution_route == "dawdreamer_serum"
    plan = r._serum_preset_plan
    assert plan["status"] == "ADVISORY_ONLY"
    assert plan["contract_id"] == CAPABILITY_KEY  # authority: CapabilityContract.target


def test_plan_authority_fields_come_from_capability_contract_not_final_contract(final_contract_row):
    """allowed_operation / mutation_target_path / mutation_value_used are authority fields.
    They must equal the CapabilityContract that ContractRegistry loaded from the pickle stores,
    and must NOT equal (or be sourced from) anything in the final contract row -- whose own
    mcp_operation/expected_raw use a different shape and a different test value entirely."""
    r = _run()
    plan = r._serum_preset_plan
    reg = ContractRegistry()
    contract = reg.get(CAPABILITY_KEY)
    assert contract is not None
    assert plan["mutation_target_path"] == contract.scope["mutation_target_path"]
    assert plan["qualification_test_value"] == contract.scope["mutation_value_used"]
    # the authority value used is NOT the final-contract's test_value (different provenance)
    assert plan["qualification_test_value"] != {"attack": final_contract_row["mcp_operation"]["edit"]["value"]}


def test_plan_execution_evidence_fields_come_from_final_contract(final_contract_row):
    r = _run()
    fc = r._serum_preset_plan["final_execution_contract"]
    assert fc is not None
    assert fc["source_path"] == str(FINAL_CONTRACT_PATH)
    assert fc["atlas_id"] == ATLAS_ID
    assert fc["mcp_operation"] == final_contract_row["mcp_operation"]
    assert fc["expected_raw"] == final_contract_row["expected_raw"]
    assert fc["declared_domain"] == final_contract_row["declared_domain"]
    assert fc["final_execution_classification"] == "MCP_EXEC_HOST_CONFIRMED"
    assert fc["exception_policy"] == "NONE"
    assert fc["agrees_with_admitted_mutation_path"] is True


def test_execution_evidence_traces_only_to_the_file_the_registry_was_pointed_at(tmp_path):
    """No pickle store, no evidence directory, no hand-authored fallback supplies these fields:
    swap the file ContractRegistry.FINAL_EXECUTION_CONTRACT_PATH names for one whose env1.attack
    row carries a value that exists nowhere else, and prove the plan's execution-evidence field
    changes to exactly that value -- it can only have come from the swapped file."""
    doc = json.loads(FINAL_CONTRACT_PATH.read_text())
    sentinel_row = copy.deepcopy(next(r for r in doc["rows"] if r["atlas_id"] == ATLAS_ID))
    sentinel_row["exception_policy_sentinel"] = "PROOF_SENTINEL_7f3a9c"
    sentinel_row["mcp_operation"]["edit"]["value"] = 999.0
    doc["rows"] = [sentinel_row if r["atlas_id"] == ATLAS_ID else r for r in doc["rows"]]
    doc["producer_lookup"][ATLAS_ID] = dict(
        doc["producer_lookup"][ATLAS_ID], exception_policy="PROOF_SENTINEL_7f3a9c")

    swapped = tmp_path / "swapped_final_execution_contract.json"
    swapped.write_text(json.dumps(doc))

    orig = ContractRegistry.FINAL_EXECUTION_CONTRACT_PATH
    ContractRegistry.FINAL_EXECUTION_CONTRACT_PATH = swapped
    try:
        r = _run()
        fc = r._serum_preset_plan["final_execution_contract"]
        assert fc["mcp_operation"]["edit"]["value"] == 999.0
        assert fc["exception_policy"] == "PROOF_SENTINEL_7f3a9c"
        assert fc["source_path"] == str(swapped)
        # the authority chain (unswapped) still produced the same admitted mutation --
        # proving the swap only ever touches the evidence side, never authority.
        assert r.admitted is True
        assert fc["mcp_operation"]["edit"]["value"] != r._serum_preset_plan["qualification_test_value"]
    finally:
        ContractRegistry.FINAL_EXECUTION_CONTRACT_PATH = orig


def test_missing_final_contract_row_fails_closed(tmp_path):
    """A control the atlas resolves but the final contract has no row for must refuse the plan
    outright (fail closed), not silently proceed with no evidence attached."""
    doc = json.loads(FINAL_CONTRACT_PATH.read_text())
    doc["rows"] = [r for r in doc["rows"] if r["atlas_id"] != ATLAS_ID]
    del doc["producer_lookup"][ATLAS_ID]
    swapped = tmp_path / "missing_row.json"
    swapped.write_text(json.dumps(doc))

    orig = ContractRegistry.FINAL_EXECUTION_CONTRACT_PATH
    ContractRegistry.FINAL_EXECUTION_CONTRACT_PATH = swapped
    try:
        r = _run()
        assert r.execution_status == "REFUSED_AUTHORITY"
        assert "REFUSED_NO_FINAL_CONTRACT_EVIDENCE" in r.error
    finally:
        ContractRegistry.FINAL_EXECUTION_CONTRACT_PATH = orig


def test_conformance_exception_row_fails_closed_even_if_admitted(tmp_path):
    """A row the final contract marks MCP_EXEC_CONFORMANCE_EXCEPTION must never become executable --
    even if CapabilityResolver/admission independently admit it. Rule 7 of Finish Line B."""
    doc = json.loads(FINAL_CONTRACT_PATH.read_text())
    for r in doc["rows"]:
        if r["atlas_id"] == ATLAS_ID:
            r["final_execution_classification"] = "MCP_EXEC_CONFORMANCE_EXCEPTION"
    doc["producer_lookup"][ATLAS_ID]["class"] = "CONFORMANCE_EXCEPTION"
    swapped = tmp_path / "forced_exception.json"
    swapped.write_text(json.dumps(doc))

    orig = ContractRegistry.FINAL_EXECUTION_CONTRACT_PATH
    ContractRegistry.FINAL_EXECUTION_CONTRACT_PATH = swapped
    try:
        r = _run()
        assert r.execution_status == "REFUSED_AUTHORITY"
        assert "REFUSED_CONFORMANCE_EXCEPTION_NOT_EXECUTABLE" in r.error
    finally:
        ContractRegistry.FINAL_EXECUTION_CONTRACT_PATH = orig


def test_mismatched_raw_path_fails_closed(tmp_path):
    """A row whose expected_raw disagrees with the admitted mutation_target_path must refuse,
    not attach mismatched evidence to a ready plan."""
    doc = json.loads(FINAL_CONTRACT_PATH.read_text())
    for r in doc["rows"]:
        if r["atlas_id"] == ATLAS_ID:
            r["expected_raw"] = [{"path": ["SomeOtherModule", "plainParams", "kParamUnrelated"], "value": 1.0}]
    swapped = tmp_path / "forced_mismatch.json"
    swapped.write_text(json.dumps(doc))

    orig = ContractRegistry.FINAL_EXECUTION_CONTRACT_PATH
    ContractRegistry.FINAL_EXECUTION_CONTRACT_PATH = swapped
    try:
        r = _run()
        assert r.execution_status == "REFUSED_AUTHORITY"
        assert "REFUSED_FINAL_CONTRACT_MISMATCH" in r.error
    finally:
        ContractRegistry.FINAL_EXECUTION_CONTRACT_PATH = orig


def test_epoch_mismatch_fails_closed():
    """A ProducerBrain run under an epoch that does not match the final contract's own recorded
    epoch (2.0.23 / the committed sha) must refuse env1.attack's plan, not silently serve stale
    execution evidence across epochs. The existing epoch machinery decides the match; this test
    only proves the final-contract gate respects it."""
    from serum2.producer.execution_epoch import EPOCH_2_0_21

    r = ProducerBrain(epoch=EPOCH_2_0_21).execute(ProducerRequest(
        user_intent="longer Env1.Attack to 1.5 ms", mode="EXECUTE", visual_mode="NEVER"))
    assert r.execution_status == "REFUSED_AUTHORITY"
    assert "REFUSED_NO_FINAL_CONTRACT_EVIDENCE" in r.error


def test_no_authority_field_is_duplicated_into_a_hand_authored_table():
    """allowed_operation is a CapabilityContract field only; the final execution contract schema
    (per the task's schema fact) carries no such field, and this module never invents one."""
    reg = ContractRegistry()
    for spec in reg.execution_specs.values():
        assert "allowed_operation" not in spec
        assert "raw_body_path" not in spec
        assert "valid_domain" not in spec
