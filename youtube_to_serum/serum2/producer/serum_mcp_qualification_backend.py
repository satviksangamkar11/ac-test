"""Backend for SERUM_PRESET_STRUCTURAL_BINDING qualification.

Executes through serum-mcp's public tool implementations
(`serum_mcp.tools.describe_preset` / `serum_mcp.tools.edit_preset` -- the same
functions its MCP server registers as tools, minus the stdio transport, which a
pytest process cannot speak). The .SerumPreset file on disk is the only state:
this class caches nothing, so every read() is a fresh describe_preset call.

If serum-mcp cannot be imported, or the file/resolver is unusable, every method
raises -- the runner turns that into FAILED_BACKEND_ERROR. There is no fallback.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import Any, Mapping

from serum2.producer.batch_qualification_system import (
    BindingCandidate,
    MutationSpec,
    RouteType,
)

SERUM_MCP_SRC = Path(__file__).resolve().parents[2] / "vendor" / "serum-mcp" / "src"
_OSC_LABELS = ("A", "B", "C", "Noise", "Sub")
_OSC_ENABLED = re.compile(r"^oscillators\[(\d+)\]\.enabled$")


class SerumMCPIntegrationError(RuntimeError):
    pass


def _oscillator_index(candidate: BindingCandidate) -> int:
    op = candidate.binding.resolver_operation_id if candidate.binding else None
    m = _OSC_ENABLED.match(op or "")
    if not m or int(m.group(1)) >= len(_OSC_LABELS):
        raise SerumMCPIntegrationError(f"unsupported resolver_operation_id: {op!r}")
    return int(m.group(1))


class SerumMCPPresetBackend:
    def __init__(self, preset_path: str, serum_mcp_src: Path = SERUM_MCP_SRC):
        self._path = str(preset_path)
        if not Path(serum_mcp_src).exists():
            raise SerumMCPIntegrationError(f"serum-mcp source not found: {serum_mcp_src}")
        if str(serum_mcp_src) not in sys.path:
            sys.path.insert(0, str(serum_mcp_src))
        try:
            from serum_mcp.tools.describe_preset import describe_preset
            from serum_mcp.tools.edit_preset import edit_preset
            from serum_mcp.preset.introspect import extract_spec
            from serum_mcp.preset.packer import unpack_file
            from serum_mcp.generation.spec import PresetSpec
        except ImportError as exc:
            raise SerumMCPIntegrationError(f"cannot import serum-mcp tools: {exc}") from exc
        self._describe, self._edit = describe_preset, edit_preset
        self._extract, self._unpack, self._PresetSpec = extract_spec, unpack_file, PresetSpec

    def load(self, candidate: BindingCandidate) -> Mapping[str, Any]:
        if candidate.route_type != RouteType.SERUM_PRESET_STRUCTURAL_BINDING:
            raise SerumMCPIntegrationError(f"unsupported route: {candidate.route_type}")
        _oscillator_index(candidate)
        if not Path(self._path).is_file():
            raise SerumMCPIntegrationError(f"preset not found: {self._path}")
        self._describe(self._path)
        return {"preset_path": self._path, "tool": "serum_mcp.tools.describe_preset"}

    def read(self, candidate: BindingCandidate) -> bool:
        label = _OSC_LABELS[_oscillator_index(candidate)]
        for line in self._describe(self._path).splitlines():
            if line.startswith(f"Osc {label}:"):
                return line.split(":", 1)[1].split()[0].upper() == "ON"
        raise SerumMCPIntegrationError(f"describe_preset has no 'Osc {label}' line")

    def mutate(self, candidate: BindingCandidate, mutation: MutationSpec) -> Mapping[str, Any]:
        idx = _oscillator_index(candidate)
        current = self._extract(self._unpack(self._path).data).oscillators
        # edit_preset needs every oscillator up to idx; round-trip the earlier ones untouched.
        oscs = list(current[:idx]) + [current[idx].model_copy(update={"enabled": bool(mutation.value)})]
        spec = self._PresetSpec(name="", description="", oscillators=oscs)
        written = self._edit(self._path, spec)
        return {"tool": "serum_mcp.tools.edit_preset", "value": bool(mutation.value),
                "written_path": written.splitlines()[0]}

    def persist(self, candidate: BindingCandidate) -> Mapping[str, Any]:
        p = Path(self._path)
        return {"path": str(p), "size_bytes": p.stat().st_size,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest().upper()}

    def reload(self, candidate: BindingCandidate) -> Mapping[str, Any]:
        return {"path": self._path, "tool": "serum_mcp.tools.describe_preset"}
