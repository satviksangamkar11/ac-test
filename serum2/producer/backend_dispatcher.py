"""Phase E: backend dispatch -- naming, not routing.

The actual routing DECISION (which backend an admitted operation uses)
already lives in producer_brain.py's route_decision/RouteSelector logic and
the SERUM_PRESET_PLAN_READY / MCP_PLAN_READY / MODULATION_ROUTE_PLAN_READY
execution_status values it produces. This module does NOT reimplement that
-- doing so would be exactly the "second execution path" the architecture
explicitly forbids. It exists because nothing currently gives episode-
recording code ONE place to ask "which backend did this admitted operation
actually use", uniformly across all three plan shapes -- that fact is
otherwise implicit in which status string/plan attribute happens to be set.

SERUM  -> serum-mcp -> .SerumPreset -> Serum's own UI -> UI readback
ABLETON -> Ableton MCP -> DAW/session state -> readback
NONE   -> not admitted / no plan produced
"""
from __future__ import annotations

from typing import Optional

SERUM = "SERUM_MCP"
ABLETON = "ABLETON_MCP"
NONE = "NONE"

_SERUM_PLAN_ATTRS = ("_serum_preset_plan", "_modulation_route_plan")
_ABLETON_PLAN_ATTRS = ("_mcp_plan",)


def dispatched_backend(result) -> str:
    """Given a ProducerResult, return which backend its admitted plan (if
    any) targets. Pure inspection -- never decides routing, only reports
    what producer_brain.py already decided."""
    for attr in _SERUM_PLAN_ATTRS:
        if getattr(result, attr, None) is not None:
            return SERUM
    for attr in _ABLETON_PLAN_ATTRS:
        if getattr(result, attr, None) is not None:
            return ABLETON
    return NONE


def backend_execution_chain(backend: str) -> list:
    """Documents the fixed, single chain for each backend -- for episode
    provenance strings, not a runtime decision."""
    if backend == SERUM:
        return ["serum-mcp", ".SerumPreset", "Serum's own in-plugin UI", "UI readback"]
    if backend == ABLETON:
        return ["Ableton MCP", "DAW/session state", "readback"]
    return []
