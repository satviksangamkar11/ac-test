"""Tests for Serum structural qualification backend."""
import tempfile
from pathlib import Path

from serum2.evidence.capability_contract import ExecutionBinding
from serum2.producer.batch_qualification_system import (
    BindingCandidate,
    MutationSpec,
    OperationFamily,
    RouteType,
)
from serum2.producer.structural_backend_serum import (
    SerumStructuralBackend,
    SerumBackendConfig,
)


def test_backend_load_creates_preset_file():
    """Backend loads reference preset and saves to work directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = SerumStructuralBackend(
            SerumBackendConfig(work_dir=tmpdir)
        )

        candidate = BindingCandidate(
            target="OSC2.Enable",
            capability_key="oscillator_field_OSC2-ENABLE",
            route_type=RouteType.VST3_HOST_PARAMETER,
            binding=ExecutionBinding(
                mutation_type="HOST_PARAMETER",
                host_parameter_name="B Enable",
                binding_source="semantic_vst3_mapping.json",
                binding_version="1",
            ),
            operation_family=OperationFamily.TOGGLE,
            provenance="semantic_vst3_mapping.json",
            confidence=1.0,
            verified=True,
        )

        result = backend.load(candidate)

        assert result["loaded"] is True
        assert "preset_path" in result
        assert result["target"] == "OSC2.Enable"
        assert result["binding"] == "B Enable"
        assert Path(result["preset_path"]).exists()


def test_backend_persist_and_reload_cycle():
    """Backend persists preset and reloads it."""
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = SerumStructuralBackend(
            SerumBackendConfig(work_dir=tmpdir)
        )

        candidate = BindingCandidate(
            target="OSC2.Enable",
            capability_key="oscillator_field_OSC2-ENABLE",
            route_type=RouteType.VST3_HOST_PARAMETER,
            binding=ExecutionBinding(
                mutation_type="HOST_PARAMETER",
                host_parameter_name="B Enable",
                binding_source="semantic_vst3_mapping.json",
                binding_version="1",
            ),
            operation_family=OperationFamily.TOGGLE,
            provenance="semantic_vst3_mapping.json",
            confidence=1.0,
            verified=True,
        )

        # Load
        load_result = backend.load(candidate)
        assert load_result["loaded"]
        file_size_1 = load_result["file_size"]

        # Persist
        persist_result = backend.persist(candidate)
        assert persist_result["persisted"]

        # Reload
        reload_result = backend.reload(candidate)
        assert reload_result["reloaded"]
        assert reload_result["file_size"] == file_size_1


def test_backend_read_returns_stub_for_vst3():
    """Backend read returns stub value for VST3_HOST_PARAMETER (Phase 3B.2)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = SerumStructuralBackend(
            SerumBackendConfig(work_dir=tmpdir)
        )

        candidate = BindingCandidate(
            target="OSC2.Enable",
            capability_key="oscillator_field_OSC2-ENABLE",
            route_type=RouteType.VST3_HOST_PARAMETER,
            binding=ExecutionBinding(
                mutation_type="HOST_PARAMETER",
                host_parameter_name="B Enable",
                binding_source="semantic_vst3_mapping.json",
                binding_version="1",
            ),
            operation_family=OperationFamily.TOGGLE,
            provenance="semantic_vst3_mapping.json",
            confidence=1.0,
            verified=True,
        )

        backend.load(candidate)
        result = backend.read(candidate)

        # Stub: returns status=STUB until Phase 3B.2
        assert result["status"] == "STUB"
        assert result["parameter"] == "B Enable"


def test_backend_mutate_returns_stub_for_vst3():
    """Backend mutate returns stub for VST3_HOST_PARAMETER (Phase 3B.2)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        backend = SerumStructuralBackend(
            SerumBackendConfig(work_dir=tmpdir)
        )

        candidate = BindingCandidate(
            target="OSC2.Enable",
            capability_key="oscillator_field_OSC2-ENABLE",
            route_type=RouteType.VST3_HOST_PARAMETER,
            binding=ExecutionBinding(
                mutation_type="HOST_PARAMETER",
                host_parameter_name="B Enable",
                binding_source="semantic_vst3_mapping.json",
                binding_version="1",
            ),
            operation_family=OperationFamily.TOGGLE,
            provenance="semantic_vst3_mapping.json",
            confidence=1.0,
            verified=True,
        )

        backend.load(candidate)
        mutation = MutationSpec(target="OSC2.Enable", value=True, operation="toggle")
        result = backend.mutate(candidate, mutation)

        # Stub: returns status=MUTATED until Phase 3B.2
        assert result["status"] == "MUTATED"
        assert result["parameter"] == "B Enable"
        assert result["value_set"] is True
