from types import SimpleNamespace

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


class FakeRegistry:
    def __init__(self, contracts):
        self._contracts = contracts

    def get(self, key):
        return self._contracts.get(key)


class FakeBackend:
    def __init__(self):
        self.calls = []
        self.state = {"value": 1}

    def load(self, candidate):
        self.calls.append("load")
        return {"loaded": True}

    def read(self, candidate):
        self.calls.append("read")
        return dict(self.state)

    def mutate(self, candidate, mutation):
        self.calls.append("mutate")
        self.state["value"] = mutation.value
        return {"value_written": mutation.value}

    def persist(self, candidate):
        self.calls.append("persist")
        return {"persisted": True}

    def reload(self, candidate):
        self.calls.append("reload")
        return {"reloaded": True}


def ref(cap):
    return SimpleNamespace(capability_key=cap)


def control(kind):
    return SimpleNamespace(control_type=kind)


def test_planner_refuses_unverified_osc2_enable_and_keeps_axes_visible():
    atlas = {
        "oscB.enabled": control("toggle"),
        "filter1.cutoff": control("continuous"),
        "env2.decay": control("continuous"),
        "matrix.amount": control("continuous"),
    }
    semantic_targets = {
        "OSC2.Enable": ref("oscillator_field_OSC2-ENABLE"),
        "Filter1.Cutoff": ref("filter_field_cutoff"),
        "Env2.Decay": ref("envelope2_field_decay"),
    }
    contracts = {
        "filter_field_cutoff": SimpleNamespace(status="CAUSAL_VERIFIED"),
        "envelope2_field_decay": SimpleNamespace(status="STRUCTURAL_ONLY"),
    }
    plan = QualificationPlanner(
        atlas_controls=atlas,
        semantic_targets=semantic_targets,
        contract_registry=FakeRegistry(contracts),
        host_mapping={"filter_field_cutoff": "Filter 1 Freq"},
        body_mapping={},
    ).plan()

    by_target = {x.target: x for x in plan.all_targets}
    assert by_target["filter1.cutoff"].bucket == QualificationBucket.ALREADY_VERIFIED
    assert by_target["env2.decay"].bucket == QualificationBucket.NEEDS_CAUSAL
    assert by_target["oscB.enabled"].bucket == QualificationBucket.NEEDS_BINDING
    assert by_target["matrix.amount"].bucket == QualificationBucket.NEEDS_BINDING
    assert by_target["oscB.enabled"].candidate.binding is None
    assert by_target["oscB.enabled"].candidate.verified is False


def test_exact_host_binding_becomes_ready_for_structural():
    atlas = {"FXDistortion.Drive": control("continuous")}
    semantic_targets = {
        "FXDistortion.Drive": ref("fx_field_dist_drive"),
    }
    plan = QualificationPlanner(
        atlas_controls=atlas,
        semantic_targets=semantic_targets,
        contract_registry=FakeRegistry({}),
        host_mapping={"fx_field_dist_drive": "Filter 1 Drive"},
        body_mapping={},
    ).plan()

    item = plan.ready_for_structural[0]
    assert item.bucket == QualificationBucket.READY_FOR_STRUCTURAL
    assert item.candidate.is_verified()
    assert item.candidate.route_type == RouteType.VST3_HOST_PARAMETER
    assert item.candidate.operation_family == OperationFamily.NUMERIC
    assert item.candidate.binding.host_parameter_name == "Filter 1 Drive"


def test_body_state_is_a_first_class_route_family():
    atlas = {"FXEQ.Freq1": control("continuous")}
    semantic_targets = {"FXEQ.Freq1": ref("fx_field_eq_freq1")}
    body = {
        "fx_field_eq_freq1": {
            "body_path": "FXRack0.FX.1.FXEQ.plainParams.kParamFreq1"
        }
    }
    plan = QualificationPlanner(
        atlas_controls=atlas,
        semantic_targets=semantic_targets,
        contract_registry=FakeRegistry({}),
        host_mapping={},
        body_mapping=body,
    ).plan()
    item = plan.ready_for_structural[0]
    assert item.candidate.route_type == RouteType.SERUM_BODY_STATE
    assert item.candidate.operation_family == OperationFamily.BODY_STATE
    assert item.candidate.is_verified()


def test_runner_refuses_unverified_binding_before_any_backend_call():
    backend = FakeBackend()
    candidate = BindingCandidate(
        target="oscB.enabled",
        capability_key="oscillator_field_OSC2-ENABLE",
        route_type=RouteType.UNBOUND,
        binding=None,
        operation_family=OperationFamily.TOGGLE,
        provenance="inventory-only observation",
        verified=False,
    )
    result = StructuralQualificationRunner(backend).run(
        candidate,
        MutationSpec(target="oscB.enabled", value=True, operation="toggle"),
    )
    assert result.status == "REFUSED_UNVERIFIED_BINDING"
    assert backend.calls == []


def test_runner_completes_load_mutate_read_persist_reload_cycle():
    backend = FakeBackend()
    candidate = BindingCandidate(
        target="FXDistortion.Drive",
        capability_key="fx_field_dist_drive",
        route_type=RouteType.VST3_HOST_PARAMETER,
        binding=ExecutionBinding(
            mutation_type="HOST_PARAMETER",
            host_parameter_name="Filter 1 Drive",
            binding_source="semantic_vst3_mapping.json",
            binding_version="1",
        ),
        operation_family=OperationFamily.NUMERIC,
        provenance="semantic_vst3_mapping.json",
        confidence=1.0,
        verified=True,
    )
    result = StructuralQualificationRunner(backend).run(
        candidate,
        MutationSpec(target="FXDistortion.Drive", value=0.75, operation="numeric_set"),
    )
    assert result.status == "STRUCTURAL_VERIFIED"
    assert result.state_changed is True
    assert result.persistence_verified is True
    assert backend.calls == [
        "load", "read", "mutate", "read", "persist", "reload", "read"
    ]
    assert result.after_reload == {"value": 0.75}
