"""Generic tests for evidence_promotion.promote_verified_evidence.

Every case here is target-independent: the assertions check operand
kind/domain/rejection reason, never hardcode a body path or Atlas bound that
would make the test itself a disguised per-target branch.
"""
import copy
import json
from pathlib import Path

import pytest

from serum2.qualification.evidence_promotion import (
    promote_verified_evidence,
    REJECT_EPOCH_MISMATCH, REJECT_MISSING_EPOCH, REJECT_MISSING_VERIFICATION,
    REJECT_RESTORATION_NOT_VERIFIED,
)
from serum2.evidence.capability_contract import (
    MUTATE_BOOLEAN, MUTATE_NUMERIC, MUTATE_ENUM, STRUCTURAL_ONLY,
)
from serum2.producer.execution_epoch import installed_epoch

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "parameter_characterization" / "binding_evidence"


def _load(name):
    return json.loads((EVIDENCE_DIR / name).read_text())


def _has_installed_epoch():
    try:
        installed_epoch()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not (EVIDENCE_DIR / "oscB.enabled.json").exists() or not _has_installed_epoch(),
    reason="parameter_characterization evidence or a known-epoch Serum installation is not present in this environment",
)


def test_boolean_evidence_promotes_to_boolean_operand():
    result = promote_verified_evidence(_load("oscB.enabled.json"))
    assert result.promoted, result.detail
    assert result.contract.allowed_operation == MUTATE_BOOLEAN
    assert result.contract.status == STRUCTURAL_ONLY
    assert result.contract.execution_binding.body_path


def test_numeric_evidence_promotes_with_verified_domain():
    result = promote_verified_evidence(_load("oscA.semitone.json"))
    assert result.promoted, result.detail
    assert result.contract.allowed_operation == MUTATE_NUMERIC
    domain = result.contract.scope["domain"]
    assert domain["lo"] == -12.0
    assert domain["hi"] == 12.0


def test_enum_evidence_promotes_with_evidence_derived_identity():
    result = promote_verified_evidence(_load("lfo1.mode.json"))
    assert result.promoted, result.detail
    assert result.contract.allowed_operation == MUTATE_ENUM
    assert result.contract.execution_binding.resolver_operation_id == "lfos[0].mode"


def test_missing_field_is_rejected():
    ev = copy.deepcopy(_load("oscB.enabled.json"))
    del ev["restore"]
    result = promote_verified_evidence(ev)
    assert not result.promoted
    assert result.reason == REJECT_RESTORATION_NOT_VERIFIED


def test_missing_epoch_is_rejected():
    ev = copy.deepcopy(_load("oscB.enabled.json"))
    del ev["epoch"]
    result = promote_verified_evidence(ev)
    assert not result.promoted
    assert result.reason == REJECT_MISSING_EPOCH


def test_epoch_mismatch_is_rejected():
    ev = copy.deepcopy(_load("oscB.enabled.json"))
    ev["epoch"]["serum_sha256"] = "0" * 64
    result = promote_verified_evidence(ev)
    assert not result.promoted
    assert result.reason == REJECT_EPOCH_MISMATCH


def test_unverified_status_is_rejected():
    ev = copy.deepcopy(_load("oscB.enabled.json"))
    ev["restore"]["verified"] = False
    result = promote_verified_evidence(ev)
    assert not result.promoted
    assert result.reason == REJECT_RESTORATION_NOT_VERIFIED


def test_no_target_specific_branches_in_promotion_source():
    """Static guard: the promotion function must not contain a target-name
    dispatch (if target == "..."/target in (...))."""
    src = (ROOT / "serum2" / "qualification" / "evidence_promotion.py").read_text()
    assert 'target ==' not in src
    assert 'target in (' not in src
    for forbidden in ("oscB.enabled", "oscC.enabled", "oscA.semitone",
                      "lfo1.mode", "lfo2.mode", "lfo3.mode", "lfo4.mode",
                      "oscNoise.noise_type"):
        assert forbidden not in src
