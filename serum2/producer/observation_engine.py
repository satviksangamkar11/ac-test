"""Unified Observation Engine — converts raw evidence into validated candidates.

One abstraction for all observation modalities:
  - TEXT (literal transcription)
  - ENUM (resolve to canonical vocabulary)
  - NUMERIC (parse, unit convert, clamp)
  - ENABLE_STATE (checkbox/visual state)
  - ROUTE_TEXT (modulation source/destination)
  - GRAPH_DERIVED (shapes known from Phase 1 schema: Lorenz curve, wavetable shape)
  - RUNTIME_STATE (explicitly excluded from preset reproduction)
  - SLIDER_PIXEL (interface only; currently unsupported)

Each strategy normalizes raw evidence into a candidate, which state_ledger
then validates through existing _coerce() logic. Keeps validation centralized,
observation modalities decoupled.

Qwen output remains UNTRUSTED_CANDIDATE. No VLM output becomes terminal
observation without deterministic validation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional, Dict, List
import re


@dataclass
class ObservationCandidate:
    """Result of an observation strategy; input to state_ledger.derive()."""
    control_id: str
    raw_value: Any
    normalized_value: Any
    strategy: str  # "TEXT", "ENUM", "NUMERIC", "ENABLE_STATE", "ROUTE_TEXT", "GRAPH_DERIVED", "RUNTIME_STATE", "SLIDER_PIXEL"
    confidence: float  # 0.0-1.0
    evidence_hash: Optional[str] = None  # crop SHA256 or frame hash if available
    modality_notes: str = ""
    vlm_source: bool = False  # True if this came from Qwen, False if deterministic extraction


class ObservationStrategy(ABC):
    """Base class for observation strategies."""

    @abstractmethod
    def observe(self, raw_value: Any, context: Dict[str, Any]) -> ObservationCandidate:
        """Normalize raw value into a candidate.

        context may include:
          - control_id, control_type, unit
          - atlas_entry (from serum_atlas.py)
          - element_kind (from atlas: CONTROL, SELECTOR, TEXT_IDENTITY, ENABLE_STATE, ROUTE, etc.)
          - roi_hash, frame_hash (evidence provenance)
          - vlm_source (True if value came from Qwen)
        """
        pass


class TextObservationStrategy(ObservationStrategy):
    """Raw text transcription — minimal normalization, maximum fidelity."""

    def observe(self, raw_value: Any, context: Dict[str, Any]) -> ObservationCandidate:
        s = str(raw_value or "").strip()
        return ObservationCandidate(
            control_id=context.get("control_id", ""),
            raw_value=raw_value,
            normalized_value=s,
            strategy="TEXT",
            confidence=1.0 if s else 0.0,
            evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
            vlm_source=context.get("vlm_source", False),
        )


class EnumObservationStrategy(ObservationStrategy):
    """Enum/selector value — resolve to canonical domain entry."""

    def observe(self, raw_value: Any, context: Dict[str, Any]) -> ObservationCandidate:
        s = str(raw_value or "").strip()
        domain = context.get("enum_values", [])

        if not s:
            return ObservationCandidate(
                control_id=context.get("control_id", ""),
                raw_value=raw_value,
                normalized_value=None,
                strategy="ENUM",
                confidence=0.0,
                evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
                modality_notes="empty enum value",
                vlm_source=context.get("vlm_source", False),
            )

        # Exact match first
        if s in domain:
            return ObservationCandidate(
                control_id=context.get("control_id", ""),
                raw_value=raw_value,
                normalized_value=s,
                strategy="ENUM",
                confidence=1.0,
                evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
                vlm_source=context.get("vlm_source", False),
            )

        # Case-insensitive exact match
        norm_s = s.lower()
        for d in domain:
            if d.lower() == norm_s:
                return ObservationCandidate(
                    control_id=context.get("control_id", ""),
                    raw_value=raw_value,
                    normalized_value=d,
                    strategy="ENUM",
                    confidence=0.95,
                    evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
                    modality_notes=f"case-normalized {s} → {d}",
                    vlm_source=context.get("vlm_source", False),
                )

        # No match
        return ObservationCandidate(
            control_id=context.get("control_id", ""),
            raw_value=raw_value,
            normalized_value=s,
            strategy="ENUM",
            confidence=0.0,
            evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
            modality_notes=f"enum {s} not in domain {domain}",
            vlm_source=context.get("vlm_source", False),
        )


class NumericObservationStrategy(ObservationStrategy):
    """Numeric value with optional unit."""

    _NUM_PATTERN = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*(ms|s|hz|khz|db|%|:1)?\s*$", re.I)

    def observe(self, raw_value: Any, context: Dict[str, Any]) -> ObservationCandidate:
        s = str(raw_value or "").strip()
        m = self._NUM_PATTERN.match(s)

        if not m:
            return ObservationCandidate(
                control_id=context.get("control_id", ""),
                raw_value=raw_value,
                normalized_value=None,
                strategy="NUMERIC",
                confidence=0.0,
                evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
                modality_notes=f"non-numeric value: {s}",
                vlm_source=context.get("vlm_source", False),
            )

        num = float(m.group(1))
        unit = (m.group(2) or (context.get("unit") or "")).lower()

        return ObservationCandidate(
            control_id=context.get("control_id", ""),
            raw_value=raw_value,
            normalized_value=(num, unit),
            strategy="NUMERIC",
            confidence=1.0,
            evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
            vlm_source=context.get("vlm_source", False),
        )


class EnableStateObservationStrategy(ObservationStrategy):
    """Checkbox/toggle state — visual classification."""

    def observe(self, raw_value: Any, context: Dict[str, Any]) -> ObservationCandidate:
        s = str(raw_value or "").strip().lower()

        if s in ("on", "true", "checked", "enabled"):
            result = "ON"
            conf = 1.0
        elif s in ("off", "false", "unchecked", "disabled"):
            result = "OFF"
            conf = 1.0
        else:
            return ObservationCandidate(
                control_id=context.get("control_id", ""),
                raw_value=raw_value,
                normalized_value=None,
                strategy="ENABLE_STATE",
                confidence=0.0,
                evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
                modality_notes=f"unrecognized enable/disable state: {s}",
                vlm_source=context.get("vlm_source", False),
            )

        return ObservationCandidate(
            control_id=context.get("control_id", ""),
            raw_value=raw_value,
            normalized_value=result,
            strategy="ENABLE_STATE",
            confidence=conf,
            evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
            vlm_source=context.get("vlm_source", False),
        )


class RouteTextObservationStrategy(ObservationStrategy):
    """Modulation route source/destination — text validation."""

    def observe(self, raw_value: Any, context: Dict[str, Any]) -> ObservationCandidate:
        s = str(raw_value or "").strip()
        route_type = context.get("route_element", "")  # "source" or "destination"

        return ObservationCandidate(
            control_id=context.get("control_id", ""),
            raw_value=raw_value,
            normalized_value=s,
            strategy="ROUTE_TEXT",
            confidence=1.0 if s else 0.0,
            evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
            modality_notes=f"route {route_type}",
            vlm_source=context.get("vlm_source", False),
        )


class GraphDerivedObservationStrategy(ObservationStrategy):
    """Graph/curve shapes known to be derived from stored fields (Phase 1 schema closure).

    Per Phase 1:
      - LFO Chaos: Lorenz curve is runtime animation derived from kParamType enum
      - OSC waveform shape is derived from wavetable name + wt_position

    These don't get their own observation; they're marked as derived from other stored fields.
    """

    def observe(self, raw_value: Any, context: Dict[str, Any]) -> ObservationCandidate:
        graph_type = context.get("graph_type", "")  # "lorenz_curve", "waveform_shape", etc.
        source_field = context.get("derived_from", "")

        return ObservationCandidate(
            control_id=context.get("control_id", ""),
            raw_value=raw_value,
            normalized_value=None,
            strategy="GRAPH_DERIVED",
            confidence=1.0,
            evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
            modality_notes=f"derived visualization ({graph_type}) from {source_field}; not independent preset state",
            vlm_source=False,
        )


class RuntimeStateObservationStrategy(ObservationStrategy):
    """Runtime/transient state — explicitly excluded from preset reproduction.

    Example: voice-count meter (0/8) is live playhead state, not a stored parameter.
    These get terminal status NOT_APPLICABLE rather than becoming preset evidence.
    """

    def observe(self, raw_value: Any, context: Dict[str, Any]) -> ObservationCandidate:
        runtime_type = context.get("runtime_type", "")  # "voice_meter", "level_meter", etc.

        return ObservationCandidate(
            control_id=context.get("control_id", ""),
            raw_value=raw_value,
            normalized_value=None,
            strategy="RUNTIME_STATE",
            confidence=1.0,
            evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
            modality_notes=f"runtime/transient state ({runtime_type}); must not be treated as preset parameter",
            vlm_source=False,
        )


class SliderPixelObservationStrategy(ObservationStrategy):
    """Slider pixel-position calibration — interface only; not yet implemented.

    This strategy is reserved for Matrix Amount and similar pixel-position-to-value
    conversions. Currently always returns UNOBSERVED_UNSUPPORTED_MODALITY to indicate
    the modality exists but implementation is Phase 3 work.
    """

    def observe(self, raw_value: Any, context: Dict[str, Any]) -> ObservationCandidate:
        return ObservationCandidate(
            control_id=context.get("control_id", ""),
            raw_value=raw_value,
            normalized_value=None,
            strategy="SLIDER_PIXEL",
            confidence=0.0,
            evidence_hash=context.get("roi_hash") or context.get("frame_hash"),
            modality_notes="UNOBSERVED_UNSUPPORTED_MODALITY: slider pixel calibration not implemented yet (Phase 3)",
            vlm_source=context.get("vlm_source", False),
        )


# Strategy registry
_STRATEGIES: Dict[str, ObservationStrategy] = {
    "TEXT": TextObservationStrategy(),
    "ENUM": EnumObservationStrategy(),
    "NUMERIC": NumericObservationStrategy(),
    "ENABLE_STATE": EnableStateObservationStrategy(),
    "ROUTE_TEXT": RouteTextObservationStrategy(),
    "GRAPH_DERIVED": GraphDerivedObservationStrategy(),
    "RUNTIME_STATE": RuntimeStateObservationStrategy(),
    "SLIDER_PIXEL": SliderPixelObservationStrategy(),
}


def get_strategy(strategy_name: str) -> ObservationStrategy:
    """Get a strategy by name."""
    if strategy_name not in _STRATEGIES:
        raise ValueError(f"Unknown observation strategy: {strategy_name}")
    return _STRATEGIES[strategy_name]


class ObservationEngine:
    """Main entry point for observation normalization.

    Takes a raw observation and context, selects the appropriate strategy,
    and returns a candidate ready for state_ledger validation.
    """

    def observe(self, raw_value: Any, context: Dict[str, Any]) -> ObservationCandidate:
        """Select strategy and normalize observation.

        context keys:
          - control_id (required)
          - element_kind: one of CONTROL, SELECTOR, TEXT_IDENTITY, ENABLE_STATE, ROUTE, TOPOLOGY, GRAPH, CURVE, REGION
          - control_type: "continuous", "enum", "toggle", "topology", "module_identity", "route"
          - enum_values: list of valid enum options (for ENUM strategy)
          - unit: unit string (for NUMERIC strategy)
          - roi_hash, frame_hash: evidence provenance
          - vlm_source: True if value came from Qwen
        """
        control_id = context.get("control_id", "")
        element_kind = context.get("element_kind")
        control_type = context.get("control_type")

        # Select strategy based on element_kind first, fall back to control_type
        strategy_name = self._select_strategy(element_kind, control_type, context)
        strategy = get_strategy(strategy_name)

        return strategy.observe(raw_value, context)

    def _select_strategy(self, element_kind: Optional[str], control_type: Optional[str], context: Dict[str, Any]) -> str:
        """Determine which strategy to use based on control metadata."""

        # Explicit strategy requests
        if context.get("force_strategy"):
            return context["force_strategy"]

        # Element kind has priority (more specific)
        if element_kind == "ENABLE_STATE":
            return "ENABLE_STATE"
        elif element_kind == "TEXT_IDENTITY":
            return "TEXT"
        elif element_kind == "SELECTOR":
            return "ENUM"
        elif element_kind == "CONTROL":
            return "NUMERIC"
        elif element_kind == "ROUTE":
            return "ROUTE_TEXT"
        elif element_kind in ("GRAPH", "CURVE"):
            return "GRAPH_DERIVED"

        # Fall back to control_type
        if control_type == "enum":
            return "ENUM"
        elif control_type == "toggle":
            return "ENABLE_STATE"
        elif control_type == "continuous":
            return "NUMERIC"
        elif control_type == "route":
            return "ROUTE_TEXT"

        # Default to TEXT (safest fallback)
        return "TEXT"
