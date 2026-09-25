"""Operand kind / domain come from the evidenced PARAMETER CONTRACT, not from the Atlas widget type (knob != numeric,
toggle_buttons != boolean); the Atlas only supplies identity and is checked against the evidence."""
import copy

import pytest

from serum2.qualification.evidence_promotion import (REJECT_ATLAS_DOMAIN_CONFLICT, REJECT_BAD_PARAMETER_CONTRACT,
                                                     REJECT_INCONSISTENT_OPERAND_KIND, REJECT_MISSING_DOMAIN,
                                                     REJECT_UI_SEMANTICS_NOT_VERIFIED, promote_verified_evidence)
from serum2.producer.execution_epoch import installed_epoch
from serum2.reference.serum_atlas import get_control


def ev(target, path, baseline, mutated, pc):
    return {"target": target, "derived_body_path": path, "epoch": {"serum_sha256": installed_epoch().binary_sha256},
            "run_status": "STRUCTURAL_VERIFIED", "restoration_verified": True, "baseline_value": baseline, "mutated_value": mutated,
            "parameter_contract": pc}


UI_OK = {"status": "VERIFIED", "evidence": "test"}


def numeric(lo, hi, ui=UI_OK):
    return {"operand_kind": "numeric", "domain": {"lo": lo, "hi": hi}, "ui_semantics": ui, "domain_source": "test"}


def test_atlas_knob_is_promoted_as_numeric_only_because_the_contract_says_so():
    assert get_control("fx.equalizer.left_freq").control_type == "knob"      # legacy path would reject this type
    r = promote_verified_evidence(ev("fx.equalizer.left_freq", "FXRack0.FX.0.FXEQ.plainParams.kParamFreq1", 200.0, 2153.3, numeric(21.5, 20000.0)))
    from serum2.evidence.capability_contract import MUTATE_NUMERIC
    assert r.promoted and r.contract.allowed_operation == MUTATE_NUMERIC
    assert r.contract.scope["domain"] == {"kind": MUTATE_NUMERIC, "lo": 21.5, "hi": 20000.0}
    assert r.contract.provenance["operand_kind_source"] == "parameter_contract"


def test_toggle_buttons_is_enum_when_the_evidence_says_enum():
    assert get_control("fx.equalizer.left_type").control_type == "toggle_buttons"
    pc = {"operand_kind": "enum", "domain": {"enum_values": ["Shelf", "Peak", "High Pass"]}, "ui_semantics": UI_OK, "domain_source": "test"}
    assert promote_verified_evidence(ev("fx.equalizer.left_type", "FXRack0.FX.0.FXEQ.plainParams.kParamType1", "Shelf", "High Pass", pc)).promoted
    bad = promote_verified_evidence(ev("fx.equalizer.left_type", "p", "Shelf", "Notch", pc))
    assert not bad.promoted and bad.reason == REJECT_INCONSISTENT_OPERAND_KIND
    wrong = dict(pc, domain={"enum_values": ["Shelf", "Peak", "Elliptic"]})
    assert promote_verified_evidence(ev("fx.equalizer.left_type", "p", "Shelf", "Peak", wrong)).reason == REJECT_ATLAS_DOMAIN_CONFLICT


def test_evidence_contradicting_the_atlas_domain_is_rejected_not_forced():
    assert (get_control("oscA.coarse_pitch").min_value, get_control("oscA.coarse_pitch").max_value) == (-72.0, 72.0)
    r = promote_verified_evidence(ev("oscA.coarse_pitch", "Oscillator0.plainParams.kParamCoarsePit", 0.0, 12.0, numeric(-64.0, 64.0)))
    assert not r.promoted and r.reason == REJECT_ATLAS_DOMAIN_CONFLICT


def test_unverified_or_missing_ui_semantics_never_promotes():
    for ui in ({"status": "PARTIAL"}, {"status": "NOT_VERIFIED"}, {}):
        r = promote_verified_evidence(ev("oscA.octave", "Oscillator0.plainParams.kParamOctave", 0.0, 2.0, numeric(-4.0, 4.0, ui)))
        assert not r.promoted and r.reason == REJECT_UI_SEMANTICS_NOT_VERIFIED


def test_numeric_contract_needs_verified_bounds_and_in_range_value():
    assert promote_verified_evidence(ev("oscA.octave", "p", 0.0, 2.0, numeric(None, 4.0))).reason == REJECT_MISSING_DOMAIN
    assert promote_verified_evidence(ev("oscA.octave", "p", 0.0, 9.0, numeric(-4.0, 4.0))).reason == REJECT_INCONSISTENT_OPERAND_KIND
    assert promote_verified_evidence(ev("oscA.octave", "p", 0.0, 2.0, {"operand_kind": "knob", "domain": {}, "ui_semantics": UI_OK})).reason == REJECT_BAD_PARAMETER_CONTRACT


def test_boolean_contract_requires_boolean_shaped_value():
    pc = {"operand_kind": "boolean", "domain": {}, "ui_semantics": UI_OK}
    assert promote_verified_evidence(ev("oscA.enabled", "p", 1.0, 0.0, pc)).promoted
    assert promote_verified_evidence(ev("oscA.enabled", "p", 1.0, 0.5, pc)).reason == REJECT_INCONSISTENT_OPERAND_KIND


def test_legacy_evidence_without_a_parameter_contract_is_unchanged():
    legacy = ev("oscA.octave", "Oscillator0.plainParams.kParamOctave", 0.0, 2.0, None)
    legacy.pop("parameter_contract")
    r = promote_verified_evidence(legacy)
    assert r.promoted and "operand_kind_source" not in r.contract.provenance     # Atlas-typed legacy path, exactly as before
