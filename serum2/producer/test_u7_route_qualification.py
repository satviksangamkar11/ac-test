"""U7: Route-General Qualification

The qualification runner must handle multiple execution routes (SERUM_BODY_STATE,
SERUM_PRESET_STRUCTURAL_BINDING) through the same lifecycle without route-specific
logic in the runner itself.

Each route provides a backend adapter implementing:
    load()     → prepare fixture/environment
    read()     → observe current state
    mutate()   → apply mutation
    persist()  → write to persistent storage
    reload()   → reload from persistent storage

The runner orchestrates the universal lifecycle:
    LOAD → READ_BASELINE → MUTATE → READ_AFTER → PERSIST → RELOAD → READ_AFTER → COMPARE

Qualification levels are distinct:
    BOUND               → binding verified, ready for qualification
    STRUCTURAL_VERIFIED → lifecycle completed, state changed, persistence verified
    (CAUSAL_VERIFIED    → separate step, requires additional evidence beyond structural)
"""

import pytest
from unittest.mock import MagicMock, call
from serum2.producer.batch_qualification_system import (
    BindingCandidate,
    OperationFamily,
    RouteType,
    StructuralQualificationRunner,
    StructuralQualificationResult,
    MutationSpec,
)
from serum2.evidence.capability_contract import ExecutionBinding


class TestU7RouteGenericLifecycle:
    """Any route with a valid backend must complete the qualification lifecycle."""

    def test_any_route_type_can_qualify_with_valid_backend(self):
        """The runner accepts any route type if the backend is verified and binding is complete."""
        # Create a candidate with an arbitrary route (not Serum-specific)
        backend = MagicMock()
        backend.load.return_value = {}
        backend.read.side_effect = [True, False, False]  # baseline, after mutation, after reload
        backend.mutate.return_value = {}
        backend.persist.return_value = {}
        backend.reload.return_value = {}

        candidate = BindingCandidate(
            target="arbitrary.target",
            capability_key="some_capability",
            route_type=RouteType.SERUM_BODY_STATE,  # Any route is ok if backend is there
            binding=ExecutionBinding(
                mutation_type="BODY_STATE",
                body_path="some.path",
                host_parameter_name=None,
                meta_path=None,
                binding_source="test",
                binding_version="1",
                resolver_operation_id=None,
            ),
            operation_family=OperationFamily.NUMERIC,
            provenance="test",
            verified=True,
        )

        runner = StructuralQualificationRunner(backend)
        result = runner.run(candidate, MutationSpec(target="arbitrary.target", value=42, operation="set"))

        # Result must complete the full lifecycle
        assert result.status == "STRUCTURAL_VERIFIED"
        assert result.state_changed
        assert result.persistence_verified
        assert "LOAD" in result.trace
        assert "MUTATE" in result.trace
        assert "PERSIST" in result.trace
        assert "RELOAD" in result.trace

    def test_runner_does_not_branch_on_route_type(self):
        """The runner's logic must be identical regardless of route type."""
        runner = StructuralQualificationRunner(MagicMock())

        # Run with SERUM_BODY_STATE
        backend_body = MagicMock()
        backend_body.load.return_value = {}
        backend_body.read.side_effect = [1, 2, 2]
        backend_body.mutate.return_value = {}
        backend_body.persist.return_value = {}
        backend_body.reload.return_value = {}
        runner._backend = backend_body

        candidate_body = BindingCandidate(
            target="test.body",
            capability_key="test_body",
            route_type=RouteType.SERUM_BODY_STATE,
            binding=ExecutionBinding(
                mutation_type="BODY_STATE",
                body_path="path1",
                host_parameter_name=None,
                meta_path=None,
                binding_source="test",
                binding_version="1",
            ),
            operation_family=OperationFamily.NUMERIC,
            provenance="test",
            verified=True,
        )
        result_body = runner.run(candidate_body, MutationSpec(target="test.body", value=1, operation="set"))

        # Run with SERUM_PRESET_STRUCTURAL_BINDING
        backend_preset = MagicMock()
        backend_preset.load.return_value = {}
        backend_preset.read.side_effect = [1, 2, 2]
        backend_preset.mutate.return_value = {}
        backend_preset.persist.return_value = {}
        backend_preset.reload.return_value = {}
        runner._backend = backend_preset

        candidate_preset = BindingCandidate(
            target="test.preset",
            capability_key="test_preset",
            route_type=RouteType.SERUM_PRESET_STRUCTURAL_BINDING,
            binding=ExecutionBinding(
                mutation_type="SERUM_PRESET_STRUCTURAL",
                body_path=None,
                host_parameter_name=None,
                meta_path=None,
                binding_source="test",
                binding_version="1",
                resolver_operation_id="some.field",
            ),
            operation_family=OperationFamily.NUMERIC,
            provenance="test",
            verified=True,
        )
        result_preset = runner.run(candidate_preset, MutationSpec(target="test.preset", value=1, operation="set"))

        # Both must follow identical trace sequence
        assert result_body.trace == result_preset.trace
        assert result_body.status == result_preset.status == "STRUCTURAL_VERIFIED"


class TestU7NegativeCases:
    """Qualification must refuse invalid states safely."""

    def test_vst3_cannot_become_execution_route(self):
        """VST3_HOST_PARAMETER (evidence-only) must never complete qualification."""
        backend = MagicMock()
        backend.load.return_value = {}
        backend.read.side_effect = [1, 2, 2]
        backend.mutate.return_value = {}
        backend.persist.return_value = {}
        backend.reload.return_value = {}

        candidate = BindingCandidate(
            target="vst3.target",
            capability_key="vst3_param",
            route_type=RouteType.VST3_HOST_PARAMETER,
            binding=ExecutionBinding(
                mutation_type="HOST_PARAMETER",
                body_path=None,
                host_parameter_name="Some Param",
                meta_path=None,
                binding_source="test",
                binding_version="1",
            ),
            operation_family=OperationFamily.NUMERIC,
            provenance="test",
            verified=True,  # VST3 can be "verified" per its own route
        )

        result = StructuralQualificationRunner(backend).run(
            candidate, MutationSpec(target="vst3.target", value=1, operation="set"))
        assert result.status == "REFUSED_ROUTE_NOT_EXECUTION_ELIGIBLE"
        assert result.verification_level == "BOUND"
        backend.load.assert_not_called()
        backend.mutate.assert_not_called()

    def test_unbound_cannot_qualify(self):
        """UNBOUND candidates must be rejected before any backend call."""
        backend = MagicMock()
        candidate = BindingCandidate(
            target="unbound.target",
            capability_key="unbound_param",
            route_type=RouteType.UNBOUND,
            binding=None,
            operation_family=OperationFamily.NUMERIC,
            provenance="test",
            verified=False,
        )

        runner = StructuralQualificationRunner(backend)
        result = runner.run(candidate, MutationSpec(target="unbound.target", value=1, operation="set"))

        assert result.status == "REFUSED_UNVERIFIED_BINDING"
        backend.load.assert_not_called()
        backend.mutate.assert_not_called()

    def test_missing_resolver_cannot_qualify(self):
        """A binding without resolver evidence cannot qualify."""
        backend = MagicMock()
        candidate = BindingCandidate(
            target="incomplete.target",
            capability_key="incomplete",
            route_type=RouteType.SERUM_PRESET_STRUCTURAL_BINDING,
            binding=ExecutionBinding(
                mutation_type="SERUM_PRESET_STRUCTURAL",
                body_path=None,
                host_parameter_name=None,
                meta_path=None,
                binding_source="test",
                binding_version="1",
                resolver_operation_id=None,  # MISSING
            ),
            operation_family=OperationFamily.TOGGLE,
            provenance="test",
            verified=False,  # Not verified without resolver_operation_id
        )

        runner = StructuralQualificationRunner(backend)
        result = runner.run(candidate, MutationSpec(target="incomplete.target", value=True, operation="toggle"))

        assert result.status == "REFUSED_UNVERIFIED_BINDING"
        backend.load.assert_not_called()

    def test_state_mismatch_fails_qualification(self):
        """If mutation doesn't change state, qualification fails."""
        backend = MagicMock()
        backend.load.return_value = {}
        backend.read.side_effect = [1, 1, 1]  # No change after mutation
        backend.mutate.return_value = {}
        backend.persist.return_value = {}
        backend.reload.return_value = {}

        candidate = BindingCandidate(
            target="immutable.target",
            capability_key="immutable",
            route_type=RouteType.SERUM_BODY_STATE,
            binding=ExecutionBinding(
                mutation_type="BODY_STATE",
                body_path="immutable.path",
                host_parameter_name=None,
                meta_path=None,
                binding_source="test",
                binding_version="1",
            ),
            operation_family=OperationFamily.NUMERIC,
            provenance="test",
            verified=True,
        )

        runner = StructuralQualificationRunner(backend)
        result = runner.run(candidate, MutationSpec(target="immutable.target", value=42, operation="set"))

        assert result.status == "FAILED_NO_STATE_CHANGE"
        assert not result.state_changed

    def test_persistence_mismatch_fails_qualification(self):
        """If state doesn't persist after reload, qualification fails."""
        backend = MagicMock()
        backend.load.return_value = {}
        backend.read.side_effect = [1, 2, 1]  # State lost after reload
        backend.mutate.return_value = {}
        backend.persist.return_value = {}
        backend.reload.return_value = {}

        candidate = BindingCandidate(
            target="volatile.target",
            capability_key="volatile",
            route_type=RouteType.SERUM_BODY_STATE,
            binding=ExecutionBinding(
                mutation_type="BODY_STATE",
                body_path="volatile.path",
                host_parameter_name=None,
                meta_path=None,
                binding_source="test",
                binding_version="1",
            ),
            operation_family=OperationFamily.NUMERIC,
            provenance="test",
            verified=True,
        )

        runner = StructuralQualificationRunner(backend)
        result = runner.run(candidate, MutationSpec(target="volatile.target", value=2, operation="set"))

        assert result.status == "FAILED_PERSISTENCE"
        assert result.state_changed
        assert not result.persistence_verified
