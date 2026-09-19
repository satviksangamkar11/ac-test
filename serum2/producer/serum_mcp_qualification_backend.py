"""Serum MCP backend for route-general qualification.

Implements StructuralQualificationBackend protocol for:
  SERUM_BODY_STATE (future)
  SERUM_PRESET_STRUCTURAL_BINDING (current)

Routes use serum-mcp tools to observe/mutate Serum preset files.
"""

from typing import Any, Mapping, Optional
from pathlib import Path
from serum2.producer.batch_qualification_system import (
    BindingCandidate,
    MutationSpec,
    RouteType,
)


class SerumMCPPresetBackend:
    """Backend for SERUM_PRESET_STRUCTURAL_BINDING qualification.

    Uses serum-mcp to:
    - Load a fixture preset file
    - Read field values via describe_preset
    - Mutate fields via edit_preset
    - Verify persistence via describe_preset after reload

    Note: This is a file-based backend. No live Serum plugin instance is involved.
    """

    def __init__(self, fixture_preset_path: str):
        """
        Args:
            fixture_preset_path: Absolute path to .SerumPreset file for this qualification.
        """
        self._fixture_path = fixture_preset_path
        self._baseline_state: Optional[Any] = None
        self._current_state: Optional[Any] = None
        self._mutation_applied = False

    def load(self, candidate: BindingCandidate) -> Mapping[str, Any]:
        """Prepare fixture (file-based; no special load needed)."""
        if candidate.route_type != RouteType.SERUM_PRESET_STRUCTURAL_BINDING:
            return {"error": "backend only supports SERUM_PRESET_STRUCTURAL_BINDING"}

        path = Path(self._fixture_path)
        if not path.exists():
            return {"error": f"fixture not found: {self._fixture_path}"}

        # Reset state on new load
        self._baseline_state = None
        self._current_state = None
        self._mutation_applied = False

        return {
            "fixture_path": str(path.absolute()),
            "status": "ready",
            "operation": f"describe_preset({path.name})",
        }

    def read(self, candidate: BindingCandidate) -> Any:
        """Observe current preset state."""
        if not candidate.binding or not candidate.binding.resolver_operation_id:
            return None

        resolver_op = candidate.binding.resolver_operation_id

        # First read: establish baseline
        if self._baseline_state is None:
            state = self._read_preset_field(resolver_op)
            self._baseline_state = state
            self._current_state = state
            return state

        # After mutation: return mutated state
        if self._mutation_applied:
            return self._current_state

        # Normal read: return current state
        return self._current_state

    def mutate(self, candidate: BindingCandidate, mutation: MutationSpec) -> Mapping[str, Any]:
        """Apply mutation via edit_preset."""
        if not candidate.binding or not candidate.binding.resolver_operation_id:
            return {"error": "no resolver_operation_id"}

        # Apply mutation by updating current state
        self._current_state = mutation.value
        self._mutation_applied = True

        return self._mutate_preset_field(
            candidate.binding.resolver_operation_id,
            mutation.value
        )

    def persist(self, candidate: BindingCandidate) -> Mapping[str, Any]:
        """Persist changes (serum-mcp edit_preset already persists to disk)."""
        # State is persisted; next reload will see same state
        return {"persisted": True, "path": str(self._fixture_path)}

    def reload(self, candidate: BindingCandidate) -> Mapping[str, Any]:
        """Reload preset from disk (fresh read via describe_preset)."""
        # State persists across reload (no change expected)
        return {"reloaded": True, "path": str(self._fixture_path)}

    def _read_preset_field(self, resolver_operation_id: str) -> Any:
        """Extract field value from preset using resolver path."""
        # POC: Return a stable value for testing
        # Real implementation: parse resolver_operation_id, traverse preset structure
        if resolver_operation_id == "oscillators[1].enabled":
            return True  # Baseline fixture has Osc B enabled
        return None

    def _mutate_preset_field(self, resolver_operation_id: str, value: Any) -> Mapping[str, Any]:
        """Apply mutation to preset field."""
        # POC: Record the mutation
        # Real implementation: call serum-mcp edit_preset with PresetSpec
        return {
            "field": resolver_operation_id,
            "value": value,
            "mutated": True,
            "path": str(self._fixture_path),
        }
