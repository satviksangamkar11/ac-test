"""Serum MCP backend for route-general qualification.

Implements StructuralQualificationBackend protocol for:
  SERUM_BODY_STATE (future)
  SERUM_PRESET_STRUCTURAL_BINDING (current)

Routes use serum-mcp tools to observe/mutate Serum preset files.
"""

from typing import Any, Mapping, Optional
from serum2.producer.batch_qualification_system import (
    BindingCandidate,
    MutationSpec,
    StructuralQualificationBackend,
    RouteType,
)


class SerumMCPPresetBackend:
    """Backend for SERUM_PRESET_STRUCTURAL_BINDING qualification.

    Uses serum-mcp to:
    - Load a fixture preset file
    - Read field values
    - Mutate fields via edit_preset
    - Verify persistence via describe_preset
    """

    def __init__(self, fixture_preset_path: str):
        """
        Args:
            fixture_preset_path: Absolute path to .SerumPreset file for this qualification.
        """
        self._fixture_path = fixture_preset_path
        self._baseline_state: Optional[Mapping[str, Any]] = None

    def load(self, candidate: BindingCandidate) -> Mapping[str, Any]:
        """Prepare fixture (serum-mcp can read files directly, no special load needed)."""
        return {"fixture_path": self._fixture_path, "status": "ready"}

    def read(self, candidate: BindingCandidate) -> Any:
        """Observe current preset field value using serum-mcp describe_preset.

        This is a stub; real implementation would call serum-mcp's describe_preset
        and extract the field value from the response.
        """
        # TODO: Call serum-mcp describe_preset, extract field from resolver_operation_id
        return None

    def mutate(self, candidate: BindingCandidate, mutation: MutationSpec) -> Mapping[str, Any]:
        """Apply mutation using serum-mcp edit_preset.

        This is a stub; real implementation would:
        1. Call serum-mcp edit_preset with the resolver_operation_id path
        2. Set the field to mutation.value
        3. Return result
        """
        # TODO: Call serum-mcp edit_preset with mutation.value at resolver_operation_id
        return {"mutation_applied": True}

    def persist(self, candidate: BindingCandidate) -> Mapping[str, Any]:
        """Persist changes (serum-mcp edit_preset already persists to disk)."""
        return {"persisted": True}

    def reload(self, candidate: BindingCandidate) -> Mapping[str, Any]:
        """Reload preset file from disk (serum-mcp reads fresh each time)."""
        return {"reloaded": True}
