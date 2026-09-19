"""Adapter layer between StructuralQualificationBackend and serum-mcp.

Minimal contract:
  - read_parameter(name: str) -> Any (observed value)
  - set_parameter(name: str, value: Any) -> dict (execution evidence)

This adapter is NOT authoritative. It is the observation layer only.
It relays real Serum state changes to the backend, which feeds StructuralQualificationRunner.
"""
from __future__ import annotations

from typing import Any, Dict, Protocol


class SerumMCPAdapter(Protocol):
    """Protocol for serum-mcp parameter read/write operations.

    Implementations must return real observed Serum 2.0.21 state, never stubs.

    If the parameter cannot be read/written, raise an exception rather than
    returning a synthetic value.
    """

    def read_parameter(self, name: str) -> Any:
        """Read current Serum parameter value.

        Args:
            name: VST3 parameter name (e.g., "B Enable")

        Returns:
            Current observed value from Serum 2.0.21

        Raises:
            ValueError: Parameter does not exist
            RuntimeError: Cannot communicate with Serum
        """
        ...

    def set_parameter(self, name: str, value: Any) -> Dict[str, Any]:
        """Set Serum parameter to value.

        Args:
            name: VST3 parameter name (e.g., "B Enable")
            value: New value to set

        Returns:
            Execution evidence dict with at least:
              - status: "SET" or "ERROR"
              - parameter: parameter name
              - value_set: the value we attempted to set
              - error?: if status is ERROR

        Raises:
            ValueError: Parameter does not exist
            RuntimeError: Cannot communicate with Serum
        """
        ...
