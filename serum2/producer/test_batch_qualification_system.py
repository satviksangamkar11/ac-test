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
        target_universe="FULL_ATLAS",
    ).plan()

    by_target = {x.target: x for x in plan.all_targets}
    # VST3_HOST_PARAMETER is evidence-only, not execution-eligible; even with
    # CAUSAL_VERIFIED contract, it needs a Serum execution binding (BODY_STATE or
    # SERUM_PRESET_STRUCTURAL_BINDING) to be executable.
    assert by_target["filter1.cutoff"].bucket == QualificationBucket.NEEDS_BINDING
    assert by_target["filter1.cutoff"].contract_status == "CAUSAL_VERIFIED"
    assert by_target["filter1.cutoff"].candidate.route_type == RouteType.VST3_HOST_PARAMETER
    assert by_target["env2.decay"].bucket == QualificationBucket.NEEDS_CAUSAL
    assert by_target["oscB.enabled"].bucket == QualificationBucket.NEEDS_BINDING
    assert by_target["matrix.amount"].bucket == QualificationBucket.NEEDS_BINDING
    assert by_target["oscB.enabled"].candidate.binding is None
    assert by_target["oscB.enabled"].candidate.verified is False


def test_exact_host_binding_becomes_ready_for_structural():
    # VST3 is evidence-only; use BODY_STATE for READY_FOR_STRUCTURAL
    atlas = {"FXDistortion.Drive": control("continuous")}
    semantic_targets = {
        "FXDistortion.Drive": ref("fx_field_dist_drive"),
    }
    plan = QualificationPlanner(
        atlas_controls=atlas,
        semantic_targets=semantic_targets,
        contract_registry=FakeRegistry({}),
        host_mapping={},
        body_mapping={
            "fx_field_dist_drive": {
                "body_path": "FXRack.Distortion.Drive"
            }
        },
        target_universe="CAPABILITY_TARGETS",
    ).plan()

    item = plan.ready_for_structural[0]
    assert item.bucket == QualificationBucket.READY_FOR_STRUCTURAL
    assert item.candidate.is_verified()
    assert item.candidate.route_type == RouteType.SERUM_BODY_STATE
    assert item.candidate.operation_family == OperationFamily.BODY_STATE
    assert item.candidate.binding.body_path == "FXRack.Distortion.Drive"


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
        target_universe="CAPABILITY_TARGETS",
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


def test_blocked_contract_puts_target_in_blocked_bucket():
    atlas = {"filter1.enabled": control("toggle")}
    semantic_targets = {"Filter1.Enabled": ref("filter_field_ENABLE")}
    contracts = {
        "filter_field_ENABLE": SimpleNamespace(status="BLOCKED_CONTRADICTED"),
    }
    plan = QualificationPlanner(
        atlas_controls=atlas,
        semantic_targets=semantic_targets,
        contract_registry=FakeRegistry(contracts),
        host_mapping={},
        body_mapping={},
        target_universe="CAPABILITY_TARGETS",
    ).plan()

    item = next((x for x in plan.all_targets if x.target == "Filter1.Enabled"), None)
    assert item is not None
    assert item.bucket == QualificationBucket.BLOCKED
    assert item.contract_status == "BLOCKED_CONTRADICTED"


def test_planner_respects_capability_targets_universe():
    atlas = {
        "filter1.enabled": control("toggle"),
        "oscA.level": control("continuous"),
        "extra.unknown": control("continuous"),
    }
    semantic_targets = {
        "Filter1.Enabled": ref("filter_field_ENABLE"),
        "OSC1.Level": ref("osc1_level"),
    }
    plan = QualificationPlanner(
        atlas_controls=atlas,
        semantic_targets=semantic_targets,
        contract_registry=FakeRegistry({}),
        host_mapping={},
        body_mapping={},
        target_universe="CAPABILITY_TARGETS",
    ).plan()

    # Should only qualify the 2 semantic targets, not "extra.unknown"
    assert plan.total == 2
    targets = {x.target for x in plan.all_targets}
    assert targets == {"Filter1.Enabled", "OSC1.Level"}
    assert "extra.unknown" not in targets


def test_planner_respects_full_atlas_universe():
    atlas = {
        "filter1.enabled": control("toggle"),
        "oscA.level": control("continuous"),
        "extra.unknown": control("continuous"),
    }
    semantic_targets = {
        "Filter1.Enabled": ref("filter_field_ENABLE"),
        "OSC1.Level": ref("osc1_level"),
    }
    plan = QualificationPlanner(
        atlas_controls=atlas,
        semantic_targets=semantic_targets,
        contract_registry=FakeRegistry({}),
        host_mapping={},
        body_mapping={},
        target_universe="FULL_ATLAS",
    ).plan()

    # Should qualify all 3 Atlas controls
    assert plan.total == 3
    targets = {x.target for x in plan.all_targets}
    assert targets == {"filter1.enabled", "oscA.level", "extra.unknown"}
