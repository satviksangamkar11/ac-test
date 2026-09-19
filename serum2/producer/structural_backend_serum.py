"""Phase 3B: Structural Qualification Backend for Serum 2.0.21 presets.

Real load/read/mutate/persist/reload cycle against .SerumPreset files.
Implements StructuralQualificationBackend Protocol.

This backend:
- Loads reference presets (minimal seed or user-provided)
- Reads VST3 parameters (via serum-mcp or stub)
- Mutates a single target to a known treatment value
- Persists and reloads the preset
- Reads after-reload to verify persistence
- Emits raw evidence for StructuralQualificationResult

The backend is non-authoritative: it records observations only.
Admission and capability authority remain unchanged.

NOTE: Phase 3B.2 integrates real serum-mcp parameter read/write.
      No fallback to stubs. Explicit failure if adapter missing.
"""
from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Optional

from serum2.codec import load_preset_file, dump_preset_file
from serum2.producer.batch_qualification_system import (
    BindingCandidate,
    MutationSpec,
    StructuralQualificationBackend,
    RouteType,
)
from serum2.producer.serum_mcp_adapter import SerumMCPAdapter


@dataclass
class SerumBackendConfig:
    """Configuration for Serum structural backend."""
    reference_preset_path: Optional[str] = None  # User preset or None for minimal seed
    work_dir: Optional[str] = None  # Temp dir for load/save cycles
    adapter: Optional[SerumMCPAdapter] = None  # REQUIRED: real adapter (Phase 3B.2+)


class SerumStructuralBackend:
    """Real structural qualification backend for Serum 2.0.21 presets.

    Cycle: load → read → mutate → read → persist → reload → read

    REQUIRES real SerumMCPAdapter. Does NOT fall back to stubs.
    Raises explicit error if adapter is missing.
    """

    def __init__(self, config: Optional[SerumBackendConfig] = None):
        self._config = config or SerumBackendConfig()

        # Phase 3B.2: require real adapter, no stubs allowed
        if not self._config.adapter:
            raise ValueError(
                "SerumStructuralBackend requires config.adapter (SerumMCPAdapter). "
                "No stubs allowed for production qualification."
            )

        self._adapter = self._config.adapter
        self._work_dir = Path(self._config.work_dir or tempfile.gettempdir())
        self._current_preset: Optional[tuple] = None  # (meta, body)
        self._preset_path: Optional[Path] = None

    def _get_reference_preset(self) -> tuple:
        """Load reference preset or return minimal seed."""
        if self._config.reference_preset_path:
            return load_preset_file(self._config.reference_preset_path)
        # Return minimal empty preset structure (stub for now)
        return (
            {"version": 5.0},
            {},  # Empty body — will be populated by serum-mcp
        )

    def load(self, candidate: BindingCandidate) -> Mapping[str, Any]:
        """Load reference preset for qualification.

        Returns: {loaded: bool, preset_path: str, file_size: int}
        """
        meta, body = self._get_reference_preset()
        self._current_preset = (meta, body)

        # Save to work directory
        self._preset_path = self._work_dir / f"qual_{candidate.target}.SerumPreset"
        dump_preset_file(str(self._preset_path), meta, body)

        return {
            "loaded": True,
            "preset_path": str(self._preset_path),
            "file_size": self._preset_path.stat().st_size,
            "target": candidate.target,
            "binding": candidate.binding.host_parameter_name if candidate.binding else None,
        }

    def read(self, candidate: BindingCandidate) -> Any:
        """Read current parameter value via real adapter.

        For VST3_HOST_PARAMETER: use adapter.read_parameter()
        For SERUM_BODY_STATE: read from preset body (TODO Phase 3B.3)

        Returns: observed value (actual from Serum 2.0.21, never stub)

        Raises: RuntimeError if adapter fails or route unsupported
        """
        if candidate.route_type == RouteType.VST3_HOST_PARAMETER:
            param_name = candidate.binding.host_parameter_name if candidate.binding else None
            if not param_name:
                raise ValueError("No parameter name in binding")

            # Phase 3B.2: use real adapter, no stubs
            try:
                value = self._adapter.read_parameter(param_name)
                return {"parameter": param_name, "value": value, "status": "READ"}
            except Exception as e:
                raise RuntimeError(f"Failed to read parameter '{param_name}': {e}")

        elif candidate.route_type == RouteType.SERUM_BODY_STATE:
            body_path = candidate.binding.body_path if candidate.binding else None
            if not body_path or not self._current_preset:
                raise ValueError("No body path or preset loaded")

            # TODO Phase 3B.3: Traverse body_path in preset body
            raise NotImplementedError("SERUM_BODY_STATE read not yet implemented")

        raise ValueError(f"Unsupported route type: {candidate.route_type}")

    def mutate(self, candidate: BindingCandidate, mutation: MutationSpec) -> Mapping[str, Any]:
        """Mutate target to treatment value via real adapter.

        For VST3_HOST_PARAMETER: use adapter.set_parameter()
        For SERUM_BODY_STATE: update preset body (TODO Phase 3B.3)

        Returns: {status, parameter, value_set, adapter_evidence, ...}

        Raises: RuntimeError if adapter fails or route unsupported
        """
        if candidate.route_type == RouteType.VST3_HOST_PARAMETER:
            param_name = candidate.binding.host_parameter_name if candidate.binding else None
            if not param_name:
                raise ValueError("No parameter name in binding")

            # Phase 3B.2: use real adapter to set parameter, no stubs
            try:
                evidence = self._adapter.set_parameter(param_name, mutation.value)
                return {
                    "status": "MUTATED",
                    "parameter": param_name,
                    "value_set": mutation.value,
                    "operation": mutation.operation,
                    "adapter_evidence": evidence,
                }
            except Exception as e:
                raise RuntimeError(f"Failed to set parameter '{param_name}' to {mutation.value}: {e}")

        elif candidate.route_type == RouteType.SERUM_BODY_STATE:
            body_path = candidate.binding.body_path if candidate.binding else None
            if not body_path or not self._current_preset:
                raise ValueError("No body path or preset loaded")

            # TODO Phase 3B.3: Update preset body at body_path
            raise NotImplementedError("SERUM_BODY_STATE mutate not yet implemented")

        raise ValueError(f"Unsupported route type: {candidate.route_type}")

    def persist(self, candidate: BindingCandidate) -> Mapping[str, Any]:
        """Save preset to disk.

        Returns: {persisted: bool, preset_path: str, file_size: int}
        """
        if not self._current_preset or not self._preset_path:
            return {"error": "No preset loaded"}

        meta, body = self._current_preset
        dump_preset_file(str(self._preset_path), meta, body)

        return {
            "persisted": True,
            "preset_path": str(self._preset_path),
            "file_size": self._preset_path.stat().st_size,
            "target": candidate.target,
        }

    def reload(self, candidate: BindingCandidate) -> Mapping[str, Any]:
        """Reload preset from disk to verify persistence.

        Returns: {reloaded: bool, preset_path: str, file_size: int}
        """
        if not self._preset_path:
            return {"error": "No preset path"}

        # Reload from disk
        self._current_preset = load_preset_file(str(self._preset_path))

        return {
            "reloaded": True,
            "preset_path": str(self._preset_path),
            "file_size": self._preset_path.stat().st_size,
            "target": candidate.target,
        }
