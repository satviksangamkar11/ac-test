"""Terminal-state, universal-binding and frozen-regression tests for the reference-reproduction path.
Committed fixtures only; never skipped."""
import json
from pathlib import Path

import pytest

from serum2.execution.authorized_state_compiler import (AuthorizedOperation, UnauthorizedOperation, compile_ops,
                                                        ops_from_rows)
from serum2.producer.execution_epoch import EPOCH_2_0_21, EPOCH_2_0_23
from serum2.producer.state_admission import admit_rows
from serum2.producer.state_ledger import DERIVED, Row, build_all
from serum2.server.reference_reproduction import run_reference_reproduction

FIX = Path(__file__).parent / "fixtures" / "reference_reproduction"


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def _rows():
    return build_all(load("stage_a_observation.json"), load("reread_log.json"), load("stage_a_corrections.json"))


def _route_row():
    r = Row("route:LFO 1->A Fine", "44%", None, "OBSERVED", "route", 1.0, 1, False, {"source": "LFO 1", "destination": "A Fine"})
    r.terminal = DERIVED
    r.op = {"kind": "route", "source": "lfo0", "destination": "oscillator0.fine", "amount": 44.0, "operation": "ADD"}
    return r


# ---- every derived operation reaches exactly one admission outcome ---------------------------------------------

@pytest.mark.parametrize("epoch", [EPOCH_2_0_21, EPOCH_2_0_23])
def test_route_admission_always_terminates(epoch):
    r = _route_row()
    table = admit_rows([r], epoch)
    assert r.admission not in ("PENDING", "NOT_EVALUATED") and table[0]["status"] == r.admission
    assert r.admission in ("NO_CAPABILITY", "EPOCH_MISMATCH")


def test_no_derived_operation_is_ever_left_without_an_outcome():
    for epoch in (EPOCH_2_0_21, EPOCH_2_0_23):
        rows = _rows()
        admit_rows(rows, epoch)
        assert all(r.admission not in ("PENDING", "NOT_EVALUATED") for r in rows if r.terminal == DERIVED)


# ---- the compiler validates the binding of EVERY operation kind --------------------------------------------------

def _op(**over):
    base = dict(operation_id="x@-", canonical_target="x", operation="ADD", operand=10.0,
                binding={"kind": "route", "source": "lfo0", "destination": "filter0.cutoff"}, contract_key="serum.modulation_route.add",
                contract_epoch=EPOCH_2_0_23.binary_sha256, execution_path=None, contract_binding="serum_mcp.add_modulation_route",
                admission_evidence={"status": "ADMITTED"}, provenance={"frame_ts": 0.0, "rack": 0}, binding_type="TOPOLOGY",
                contract_body_path=None,
                contract_domain={"supported_source_prefixes": ("lfo", "env"), "supported_destination_families": ("oscillator", "filter"),
                                 "amount_range": (-100, 100)})
    base.update(over)
    return AuthorizedOperation(**base)


def test_route_operations_are_checked_against_their_contract_domain():
    assert compile_ops([_op()], "t", "t", EPOCH_2_0_23).status == "SUCCESS"
    for bad in (_op(operand=250.0), _op(binding={"kind": "route", "source": "zzz0", "destination": "filter0.cutoff"}),
                _op(binding={"kind": "route", "source": "lfo0", "destination": "arp0.rate"}), _op(binding_type="HOST_PARAMETER"),
                _op(binding_type=None), _op(contract_domain={})):
        with pytest.raises(UnauthorizedOperation):
            compile_ops([bad], "t", "t", EPOCH_2_0_23)


def test_fx_and_field_bindings_are_mandatory_and_must_match():
    rows = _rows()
    admit_rows(rows, EPOCH_2_0_21)
    ops = {o.canonical_target: o for o in ops_from_rows(rows, EPOCH_2_0_21)}
    assert compile_ops([ops["fx.equalizer.left_freq"]], "t", "t", EPOCH_2_0_21).status == "SUCCESS"     # BODY_STATE, path agrees
    for name in ("oscA.octave", "env1.release", "filter1.type", "fx.distortion.type"):                # no execution-eligible binding
        with pytest.raises(UnauthorizedOperation):
            compile_ops([ops[name]], "t", "t", EPOCH_2_0_21)
    eq = ops["fx.equalizer.left_freq"]
    wrong_param = AuthorizedOperation(**{**eq.__dict__, "binding": {**eq.binding, "param": "kParamFreq2"}})
    with pytest.raises(UnauthorizedOperation):
        compile_ops([wrong_param], "t", "t", EPOCH_2_0_21)                                            # lowering != contract path
    wrong_rack = AuthorizedOperation(**{**eq.__dict__, "provenance": {**eq.provenance, "rack": 1}})
    with pytest.raises(UnauthorizedOperation):
        compile_ops([wrong_rack], "t", "t", EPOCH_2_0_21)
    rows = _rows()
    admit_rows(rows, EPOCH_2_0_23)
    f = ops_from_rows(rows, EPOCH_2_0_23)[0]
    for bad in (AuthorizedOperation(**{**f.__dict__, "contract_binding": None}),
                AuthorizedOperation(**{**f.__dict__, "contract_body_path": "Oscillator9.plainParams.kParamEnable"}),
                AuthorizedOperation(**{**f.__dict__, "binding_type": "BODY_STATE"})):
        with pytest.raises(UnauthorizedOperation):
            compile_ops([bad], "t", "t", EPOCH_2_0_23)                                                # missing/mismatched binding never passes


# ---- frozen 9-operation live-UI regression ---------------------------------------------------------------------

FROZEN_OPS = {
    "oscB.enabled": ("TOGGLE_ON", True, "oscillator_field_OSC2-ENABLE", "oscillators[1].enabled"),
    "oscC.enabled": ("TOGGLE_OFF", False, "oscillator_field_OSC3-ENABLE", "oscillators[2].enabled"),
    "oscB.octave": ("SET", 1.0, "oscillator_field_OSC2-OCTAVE", "oscillators[1].octave"),
    "env2.decay": ("SET", 0.753, "envelope2_field_decay", "envelopes[1].decay"),
    "env2.release": ("SET", 0.267, "envelope2_field_release", "envelopes[1].release"),
    "env3.decay": ("SET", 0.54, "envelope3_field_decay", "envelopes[2].decay"),
    "env3.release": ("SET", 0.015, "envelope3_field_release", "envelopes[2].release"),
    "env4.decay": ("SET", 0.014, "envelope4_field_decay", "envelopes[3].decay"),
    "env4.release": ("SET", 0.015, "envelope4_field_release", "envelopes[3].release"),
}


def test_frozen_nine_operation_live_ui_regression():
    run = run_reference_reproduction(FIX / "stage_a_observation.json", FIX / "reread_log.json", FIX / "stage_a_corrections.json",
                                     source={"video_id": "HEEGN1Xl5o4"}, name="frozen-regression", epoch=EPOCH_2_0_23,
                                     ui_readback=load("ui_readback_authorized_9.json"), subfolder="VLP1-tests")
    rows = _rows()
    admit_rows(rows, EPOCH_2_0_23)
    got = {o.canonical_target: (o.operation, o.operand, o.contract_key, o.contract_binding) for o in ops_from_rows(rows, EPOCH_2_0_23)}
    assert set(got) == set(FROZEN_OPS)
    for k, want in FROZEN_OPS.items():
        assert got[k][0] == want[0] and got[k][2:] == want[2:] and got[k][1] == pytest.approx(want[1]), k
    counts = {}
    for a in run.admission:
        counts[a["status"]] = counts.get(a["status"], 0) + 1
    assert counts == {"ADMITTED": 9, "EPOCH_MISMATCH": 13, "NO_CAPABILITY": 27}
    assert run.compilation == {"status": "SUCCESS", "admitted": 9, "compiled": 9, "missing": []}
    assert run.proof_level == "LIVE_UI_VERIFIED" and run.coverage_status == "PARTIAL" and not run.reference_verified
    assert run.file_comparison["field_counts"] == {"VERIFIED_EXACT": 3, "VERIFIED_WITH_NORMALIZATION": 6}
    assert run.ui_comparison["field_counts"] == {"VERIFIED_EXACT": 3, "VERIFIED_WITH_NORMALIZATION": 6}
    assert run.ledger["ledger_rows"] == 216 and run.ledger["invariant_holds"]
