"""U7: real serum-mcp qualification of the production SERUM_PRESET_STRUCTURAL_BINDING route.

Every test runs on a temp copy of the fixture. State is only ever observed from the
.SerumPreset file (describe_preset / raw unpack oracle) -- never from the backend object.
"""
import hashlib
import shutil
from pathlib import Path

import pytest

from serum2.evidence.capability_contract import ExecutionBinding
from serum2.producer.batch_qualification_system import (
    BindingCandidate,
    MutationSpec,
    OperationFamily,
    QualificationBucket,
    QualificationPlanner,
    RouteType,
    StructuralQualificationRunner,
)
from serum2.producer.serum_mcp_qualification_backend import (
    SerumMCPIntegrationError,
    SerumMCPPresetBackend,
)

FIXTURE = Path(
    r"C:\Users\Satvik\Documents\Xfer\Serum 2 Presets\Presets\User\VLP1-Phase3B-OSC2Enable-Test.SerumPreset"
)


def MUT(v):
    return MutationSpec(target="OSC2.Enable", value=v, operation="toggle")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


@pytest.fixture
def preset(tmp_path):
    assert FIXTURE.is_file(), "qualification fixture missing"
    p = tmp_path / "osc2.SerumPreset"
    shutil.copy(FIXTURE, p)
    return str(p)


@pytest.fixture(scope="module")
def candidate():
    plan = QualificationPlanner().plan()  # production mappings, nothing injected
    (q,) = [t for t in plan.all_targets if t.target == "OSC2.Enable"]
    assert q.bucket == QualificationBucket.READY_FOR_STRUCTURAL
    return q.candidate


def oracle(backend, path):
    """Independent raw read of Oscillator1.kParamEnable -- different code path than backend.read()."""
    return bool(backend._unpack(path).data["Oscillator1"]["plainParams"]["kParamEnable"])


def set_baseline(path, cand, on):
    b = SerumMCPPresetBackend(path)
    if b.read(cand) != on:
        b.mutate(cand, MUT(on))


@pytest.mark.parametrize("baseline", [False, True])
def test_route_can_execute_qualification_lifecycle(preset, candidate, baseline):
    set_baseline(preset, candidate, baseline)
    before_sha = sha(preset)
    backend = SerumMCPPresetBackend(preset)

    result = StructuralQualificationRunner(backend).run(candidate, MUT(not baseline))

    assert result.status == "STRUCTURAL_VERIFIED"
    assert result.verification_level == "STRUCTURAL_VERIFIED"  # never CAUSAL_VERIFIED
    assert result.baseline is baseline
    assert result.after_mutation is (not baseline)
    assert result.state_changed and result.persistence_verified
    assert result.trace == (
        "LOAD", "READ_BASELINE", "MUTATE", "READ_AFTER_MUTATION", "PERSIST",
        "RELOAD", "READ_AFTER_RELOAD", "PERSISTENCE_CHECK_PASSED",
    )
    assert sha(preset) != before_sha  # the file bytes really changed

    # independent oracles: raw codec read, and a brand-new backend instance
    assert oracle(backend, preset) is (not baseline)
    assert SerumMCPPresetBackend(preset).read(candidate) is (not baseline)
    assert result.after_reload is (not baseline)
    assert result.backend_evidence["persist"]["sha256"] == sha(preset).upper()


def test_only_the_targeted_oscillator_changes(preset, candidate):
    set_baseline(preset, candidate, True)
    b = SerumMCPPresetBackend(preset)
    osc_a_before = b._unpack(preset).data["Oscillator0"]
    StructuralQualificationRunner(b).run(candidate, MUT(False))
    assert b._unpack(preset).data["Oscillator0"] == osc_a_before


def test_backend_state_comes_from_the_file_not_the_object(preset, candidate):
    a = SerumMCPPresetBackend(preset)
    set_baseline(preset, candidate, True)
    assert a.read(candidate) is True
    SerumMCPPresetBackend(preset).mutate(candidate, MUT(False))  # change file via another instance
    assert a.read(candidate) is False  # `a` never mutated anything


def test_backend_really_invokes_serum_mcp_tools(preset, candidate):
    b = SerumMCPPresetBackend(preset)
    set_baseline(preset, candidate, True)
    calls = {"describe": 0, "edit": 0}
    d, e = b._describe, b._edit

    def spy_describe(*a, **k):
        calls["describe"] += 1
        return d(*a, **k)

    def spy_edit(*a, **k):
        calls["edit"] += 1
        return e(*a, **k)

    b._describe, b._edit = spy_describe, spy_edit
    r = StructuralQualificationRunner(b).run(candidate, MUT(False))
    assert r.status == "STRUCTURAL_VERIFIED"
    assert calls["edit"] == 1 and calls["describe"] >= 4  # load + 3 reads


def test_unavailable_serum_mcp_cannot_qualify(preset, tmp_path):
    with pytest.raises(SerumMCPIntegrationError):
        SerumMCPPresetBackend(preset, serum_mcp_src=tmp_path / "missing")


def test_missing_preset_file_fails_structurally(tmp_path, candidate):
    b = SerumMCPPresetBackend(str(tmp_path / "nope.SerumPreset"))
    r = StructuralQualificationRunner(b).run(candidate, MUT(False))
    assert r.status == "FAILED_BACKEND_ERROR" and r.verification_level == "BOUND"
    assert "preset not found" in r.error


def test_unresolvable_resolver_fails_structurally(preset, candidate):
    bad = BindingCandidate(
        target="OSC2.Enable", capability_key=candidate.capability_key,
        route_type=RouteType.SERUM_PRESET_STRUCTURAL_BINDING,
        binding=ExecutionBinding(mutation_type="SERUM_PRESET_STRUCTURAL",
                                 resolver_operation_id="oscillators[9].enabled"),
        operation_family=OperationFamily.TOGGLE, provenance="test", verified=True)
    r = StructuralQualificationRunner(SerumMCPPresetBackend(preset)).run(bad, MUT(False))
    assert r.status == "FAILED_BACKEND_ERROR"


def test_vst3_route_is_refused_and_file_untouched(preset, candidate):
    vst3 = BindingCandidate(
        target="OSC2.Enable", capability_key=candidate.capability_key,
        route_type=RouteType.VST3_HOST_PARAMETER,
        binding=ExecutionBinding(mutation_type="HOST_PARAMETER", host_parameter_name="B Enable"),
        operation_family=OperationFamily.TOGGLE, provenance="semantic_vst3_mapping.json", verified=True)
    before = sha(preset)
    r = StructuralQualificationRunner(SerumMCPPresetBackend(preset)).run(vst3, MUT(False))
    assert r.status == "REFUSED_ROUTE_NOT_EXECUTION_ELIGIBLE"
    assert "MUTATE" not in r.trace
    assert sha(preset) == before


def test_unbound_is_refused_and_file_untouched(preset):
    unbound = BindingCandidate(target="OSC2.Enable", capability_key="oscillator_field_OSC2-ENABLE",
                               route_type=RouteType.UNBOUND, binding=None,
                               operation_family=OperationFamily.TOGGLE, provenance="none")
    before = sha(preset)
    r = StructuralQualificationRunner(SerumMCPPresetBackend(preset)).run(unbound, MUT(False))
    assert r.status == "REFUSED_UNVERIFIED_BINDING" and r.verification_level == "UNBOUND"
    assert sha(preset) == before


class NoopMutate(SerumMCPPresetBackend):
    def mutate(self, candidate, mutation):
        return {"claimed": "success"}  # reports success, changes nothing


class ForgetOnPersist(SerumMCPPresetBackend):
    def persist(self, candidate):
        Path(self._path).write_bytes(self._original)  # mutation is lost before reload
        return super().persist(candidate)


def test_mutation_reported_but_readback_unchanged_fails(preset, candidate):
    set_baseline(preset, candidate, True)
    r = StructuralQualificationRunner(NoopMutate(preset)).run(candidate, MUT(False))
    assert r.status == "FAILED_NO_STATE_CHANGE"
    assert not r.state_changed and r.verification_level == "BOUND"


def test_reload_that_loses_the_mutation_fails_persistence(preset, candidate):
    set_baseline(preset, candidate, True)
    b = ForgetOnPersist(preset)
    b._original = Path(preset).read_bytes()
    r = StructuralQualificationRunner(b).run(candidate, MUT(False))
    assert r.status == "FAILED_PERSISTENCE"
    assert r.state_changed and not r.persistence_verified and r.verification_level == "BOUND"


@pytest.mark.parametrize("stage,after", [
    ("load", "START"), ("read", "LOAD"), ("mutate", "READ_BASELINE"),
    ("persist", "READ_AFTER_MUTATION"), ("reload", "PERSIST"),
])
def test_each_backend_stage_failure_is_a_structured_failure(preset, candidate, stage, after):
    set_baseline(preset, candidate, True)
    b = SerumMCPPresetBackend(preset)

    def boom(*a, **k):
        raise SerumMCPIntegrationError(f"{stage} exploded")

    setattr(b, stage, boom)
    r = StructuralQualificationRunner(b).run(candidate, MUT(False))
    assert r.status == "FAILED_BACKEND_ERROR"
    assert r.verification_level == "BOUND" and not r.persistence_verified
    assert f"{stage} exploded" in r.error
    assert r.trace[-1] == f"BACKEND_ERROR_AFTER_{after}"
