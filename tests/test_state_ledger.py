"""Reference-reproduction architecture tests. They run on a COMMITTED fixture (tests/fixtures/reference_reproduction)
and are never skipped: if the fixture or serum-mcp is missing they fail loudly."""
import copy
import json
import re
from pathlib import Path

import pytest

from serum2.execution import authorized_state_compiler as asc
from serum2.execution.authorized_state_compiler import (AuthorizedOperation, UnauthorizedOperation, compile_ops,
                                                        ops_from_rows)
from serum2.execution.state_comparator import DIRECT_UI, compare_ui, verification_level
from serum2.producer import state_ledger as sl
from serum2.producer.execution_epoch import EPOCH_2_0_21, EPOCH_2_0_23
from serum2.producer.state_admission import admit_rows
from serum2.producer.state_ledger import (DERIVED, IGNORED_NAVIGATION, UNREADABLE, build_all, conservation,
                                          observed_route_rows, resolve_enum)

FIX = Path(__file__).parent / "fixtures" / "reference_reproduction"
ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def stage_a():
    return load("stage_a_observation.json")


@pytest.fixture(scope="module")
def corrections():
    return load("stage_a_corrections.json")


@pytest.fixture(scope="module")
def admitted_rows(stage_a, corrections):
    rows = build_all(stage_a, load("reread_log.json"), corrections)
    return rows, {(t["control"], t["rack"]): t for t in admit_rows(rows, EPOCH_2_0_23)}


# ---- ledger --------------------------------------------------------------------------------------------------

def test_no_observation_is_silently_lost(stage_a, corrections):
    rows = build_all(stage_a, load("reread_log.json"), corrections)
    c = conservation(stage_a, rows, corrections)
    assert c["invariant_holds"], c
    nav = [r for r in rows if r.control_type in ("tab", "badge_count")]
    assert nav and all(r.terminal == IGNORED_NAVIGATION and r.op is None for r in nav)
    assert all(r.terminal != DERIVED or r.op for r in rows)


def test_route_amount_is_never_carried_forward():
    def frame(ts, amount):
        return {"timestamp_sec": ts, "controls": [], "mod_routes": [
            {"source": "Env 4", "destination": "Main Tuning", "amount": amount, "status": "OBSERVED"}]}
    rows = observed_route_rows({"frames": [frame(1.0, "57%"), frame(2.0, None)]})
    assert rows[0].value is None and rows[0].n_readings == 2


def test_no_heuristic_identity_remapping_exists():
    for banned in ("_alt_field", "_param_key", "_fx_type", "match_enum", "_tokens", "_SYN"):
        assert not hasattr(sl, banned), banned
    assert resolve_enum("filter1.type", "MG Low 18", ["MgL18"])[0] == "MgL18"   # approved alias with cited evidence
    assert resolve_enum("fx.filter.type", "MG Ladder", ["LadderMg"])[0] is None  # token/subset guessing is gone
    assert resolve_enum("x", "OVERDRIVE", ["kOverdrive", "kSoftClip"])[0] == "kOverdrive"  # exact normalised only


def test_binding_table_contains_only_exact_or_reviewed_alias_entries():
    t = sl.binding_table()
    assert {v["basis"] for v in t["controls"].values()} <= {"exact_normalized", "alias"}
    assert all("evidence" in a for m in t["value_aliases"].values() for a in m.values())


def test_unmapped_atlas_control_is_unbound_not_guessed(admitted_rows):
    rows, _ = admitted_rows
    r = next(r for r in rows if r.control_id == "oscA.phase")
    assert r.terminal == sl.UNBOUND and r.op is None


def test_stage_a_id_corrections_are_recorded_not_silent(admitted_rows):
    rows, _ = admitted_rows
    shape = next(r for r in rows if r.control_id == "lfo1.shape")
    assert shape.context["stage_a_correction"]["from"] == "lfo1.mode"


# ---- authority + epoch ---------------------------------------------------------------------------------------

def test_registry_epochs_are_isolated():
    from serum2.producer.contract_registry import ContractRegistry
    default, e21, e23 = ContractRegistry(), ContractRegistry(EPOCH_2_0_21), ContractRegistry(EPOCH_2_0_23)
    assert len(default.contracts) == 33 and "oscillator_field_OSC2-ENABLE" not in default.contracts
    assert not set(e21.contracts) & set(e23.contracts)
    assert "oscillator_field_OSC2-ENABLE" in e23.contracts and "oscillator_field_OSC2-ENABLE" not in e21.contracts
    assert "envelope_field_release" in e21.contracts and "envelope_field_release" not in e23.contracts
    assert all(c.scope["serum_binary_sha256"] == EPOCH_2_0_23.binary_sha256 for c in e23.contracts.values())


def test_legacy_contracts_cannot_authorize_a_2_0_23_run(admitted_rows):
    _, t = admitted_rows
    for k in ("oscA.octave", "env1.release", "fx.equalizer.left_freq", "filter1.type"):
        assert t[(k, 0 if k.startswith("fx.") else None)]["status"] == "EPOCH_MISMATCH", k
    for k in ("oscB.enabled", "oscC.enabled", "oscB.octave", "env2.decay", "env3.release", "env4.decay"):
        assert t[(k, None)]["status"] == "ADMITTED", k


def test_scope_fails_closed(admitted_rows):
    _, t = admitted_rows
    assert t[("oscA.wavetable", None)]["status"] == "NO_CAPABILITY"    # no wavetable contract exists on this build
    assert t[("fx.compressor.ratio", 0)]["status"] == "NO_CAPABILITY"
    assert all(v["contract"] for v in t.values() if v["status"] == "ADMITTED")


def test_the_same_ops_are_admitted_under_2_0_21_only_by_2_0_21_contracts(stage_a, corrections):
    rows = build_all(stage_a, load("reread_log.json"), corrections)
    t = {(x["control"], x["rack"]): x for x in admit_rows(rows, EPOCH_2_0_21)}
    assert t[("oscA.octave", None)]["status"] == "ADMITTED"
    assert t[("oscB.octave", None)]["status"] == "EPOCH_MISMATCH"


def test_octave_prerequisite_fails_closed():
    from serum2.evidence import admission as adm
    from serum2.producer.contract_registry import ContractRegistry
    contracts = ContractRegistry(EPOCH_2_0_23).get_contracts_dict()
    key = "oscillator_field_OSC2-OCTAVE"
    assert adm.admit(contracts, key).reason == "prerequisite_unverified"
    assert adm.admit(contracts, key, proposed_prerequisites_verified={"body:Oscillator1.plainParams.kParamEnable": 0.0}).reason == "prerequisite_unverified"
    assert adm.admit(contracts, key, proposed_prerequisites_verified={"body:Oscillator1.plainParams.kParamEnable": 1.0}).admitted


# ---- compiler boundary ---------------------------------------------------------------------------------------

def test_compiler_only_accepts_admitted_operations_and_never_drops(admitted_rows):
    rows, _ = admitted_rows
    ops = ops_from_rows(rows, EPOCH_2_0_23)
    rep = compile_ops(ops, "t", "t", EPOCH_2_0_23)
    assert rep.status == "SUCCESS" and rep.compiled == rep.admitted == len(ops) == 9
    assert {o.canonical_target for o in ops} == {"oscB.enabled", "oscC.enabled", "oscB.octave", "env2.decay", "env2.release",
                                                 "env3.decay", "env3.release", "env4.decay", "env4.release"}
    with pytest.raises(UnauthorizedOperation):
        compile_ops(ops, "t", "t", EPOCH_2_0_21)                       # different Serum build
    with pytest.raises(UnauthorizedOperation):
        compile_ops([{"kind": "field"}], "t", "t", EPOCH_2_0_23)       # not an AuthorizedOperation
    o = ops[0]
    forged = AuthorizedOperation(o.operation_id, o.canonical_target, o.operation, o.operand, o.binding, o.contract_key,
                                 o.contract_epoch, o.execution_path, o.contract_binding, {"status": "DERIVED"}, o.provenance)
    with pytest.raises(UnauthorizedOperation):
        compile_ops([forged], "t", "t", EPOCH_2_0_23)                  # derived is not admitted
    bad_binding = AuthorizedOperation(o.operation_id, o.canonical_target, o.operation, o.operand, o.binding, o.contract_key,
                                      o.contract_epoch, o.execution_path, "envelopes[9].decay", o.admission_evidence, o.provenance)
    with pytest.raises(UnauthorizedOperation):
        compile_ops([bad_binding], "t", "t", EPOCH_2_0_23)             # lowering disagrees with the contract's binding


def test_unadmitted_state_has_no_path_to_a_preset(admitted_rows):
    rows, _ = admitted_rows
    assert not any(hasattr(sl, n) for n in ("assemble_spec", "execute_and_verify"))
    assert "only_admitted" not in Path(asc.__file__).read_text(encoding="utf-8")
    derived_not_admitted = [r for r in rows if r.terminal == DERIVED and r.admission != "ADMITTED"]
    assert derived_not_admitted                                        # they exist ...
    admitted_ids = {o.operation_id for o in ops_from_rows(rows, EPOCH_2_0_23)}
    assert not admitted_ids & {"%s@%s" % (r.control_id, r.context.get("rack", "-")) for r in derived_not_admitted}  # ... and never compile


def test_new_compiler_is_operand_driven_and_independent_of_the_fixture_compiler():
    src = Path(asc.__file__).read_text(encoding="utf-8")
    assert not re.search(r"cap_0\d\d|capability_id", src)
    for f in ("serum2/execution/authorized_state_compiler.py", "serum2/execution/state_comparator.py",
              "serum2/server/reference_reproduction.py", "serum2/producer/state_ledger.py", "serum2/producer/state_admission.py"):
        assert "authorized_preset_compiler" not in (ROOT / f).read_text(encoding="utf-8"), f


# ---- verification levels -------------------------------------------------------------------------------------

def test_file_readback_alone_is_never_live_verification(admitted_rows):
    rows, _ = admitted_rows
    rep = compile_ops(ops_from_rows(rows, EPOCH_2_0_23), "t", "t", EPOCH_2_0_23)
    ok = {"field_counts": {"VERIFIED_EXACT": 3, "VERIFIED_WITH_NORMALIZATION": 6}}
    assert verification_level(ok) == "FILE_READBACK_VERIFIED_ONLY"
    assert verification_level({"field_counts": {"OVERRIDDEN_APPROXIMATION": 1}}) == "FILE_READBACK_FAILED_OR_APPROXIMATE"
    with pytest.raises(ValueError):
        compare_ui(rows, {"route": "FILE_READBACK", "values": {}}, rep)
    ui = compare_ui(rows, {"route": DIRECT_UI, "captured_at": "t", "values": {"oscB.enabled": "on"}}, rep)
    assert ui["field_counts"].get("UNREADABLE", 0) == 8                # compiled but never read back from the live UI
    assert verification_level(ok, ui) == "UI_READBACK_FAILED_OR_INCOMPLETE"


def test_reference_reproduction_run_end_to_end(tmp_path):
    from serum2.server.reference_reproduction import run_reference_reproduction
    run = run_reference_reproduction(FIX / "stage_a_observation.json", FIX / "reread_log.json", FIX / "stage_a_corrections.json",
                                     source={"video_id": "HEEGN1Xl5o4"}, name="test-reference-reproduction",
                                     epoch=EPOCH_2_0_23, subfolder="VLP1-tests")
    assert run.ledger["invariant_holds"] and run.compilation["status"] == "SUCCESS"
    assert run.compilation["admitted"] == run.compilation["compiled"] == len(run.authorized) == 9
    assert run.proof_level == "FILE_READBACK_VERIFIED_ONLY" and not run.operation_evidence_eligible and not run.reference_verified
    assert run.replay_pins["serum_binary_sha256"] == EPOCH_2_0_23.binary_sha256
    assert set(run.replay_pins["contracts"]) and len(run.preset["sha256"]) == 64
