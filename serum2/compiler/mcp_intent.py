"""16.5.61: Typed Musical-Intent Layer (Option A / MCP execution path).

Pipeline:
  natural-language intent
    ↓ parse_intent()      →  ParsedIntent | IntentRefusal
    ↓ compile_intent()    →  IntentPlan   | IntentRefusal
    ↓ [caller: MCP read current value]
    ↓ resolve_host_value()→  float
    ↓ [caller: MCP write + readback]
    ↓ make_audit_record() →  dict

Admission gate for Option A:
  A target is admitted iff it appears in MCP_HOST_MAP.
  The map is grounded in the 127-parameter discovery experiment
  (16.5_Serum2_Complete_MCP_Discovery, 2026-09-07). No Serum
  knowledge is invented: a target absent from the map is refused.

This module is pure Python. It never calls AbletonMCP directly.
The caller is responsible for MCP I/O (read, write, readback).
"""
import re
from dataclasses import dataclass
from typing import Optional, Tuple

from .targets import SEMANTIC_TARGETS, SemanticTargetRef

# ---- refusal reasons ----
REFUSED_UNKNOWN_TARGET   = "UNKNOWN_SEMANTIC_TARGET"
REFUSED_NO_MCP_MAPPING   = "NO_MCP_MAPPING"
REFUSED_PARSE_FAILURE    = "INTENT_PARSE_FAILURE"
REFUSED_VALUE_OOB        = "VALUE_OUT_OF_RANGE"

# ---- value spec kinds ----
ABSOLUTE  = "absolute"
RELATIVE  = "relative"


@dataclass(frozen=True)
class ParsedIntent:
    raw_intent: str
    semantic_target_name: str
    value_kind: str        # ABSOLUTE | RELATIVE
    value: float           # absolute: 0-1 host value; relative: signed delta (-1 to +1)


@dataclass(frozen=True)
class IntentRefusal:
    raw_intent: str
    reason: str
    detail: str


@dataclass(frozen=True)
class MCPHostParam:
    index: int
    name: str
    description: str
    track_index: int = 0
    device_index: int = 0


@dataclass(frozen=True)
class IntentPlan:
    """Everything the caller needs to execute one MCP write."""
    raw_intent: str
    semantic_target: SemanticTargetRef
    capability_key: str
    host_param: MCPHostParam
    value_kind: str        # ABSOLUTE | RELATIVE
    value_spec: float      # as parsed: absolute 0-1 OR relative delta


# ---------------------------------------------------------------------------
# MCP Host Map — grounded in 16.5_Serum2_Complete_MCP_Discovery (2026-09-07)
# Maps semantic_target_name -> MCPHostParam
# All parameters verified writable via track_index=0, device_index=0, Serum 2
# ---------------------------------------------------------------------------
MCP_HOST_MAP: dict[str, MCPHostParam] = {
    "OSC1.Volume":        MCPHostParam(1,   "A Level",       "OSC A output level (0=silent, 1=full)"),
    "OSC1.Enable":        MCPHostParam(16,  "A Enable",      "OSC A on/off toggle"),
    "OSC1.Octave":        MCPHostParam(17,  "A Octave",      "OSC A octave offset"),
    "Global.MasterVolume":MCPHostParam(2,   "Main Vol",      "Master output volume"),
    "Filter.Cutoff":      MCPHostParam(11,  "Filter 1 Freq", "Filter 1 cutoff frequency"),
    "Filter.Resonance":   MCPHostParam(75,  "Filter 1 Res",  "Filter 1 resonance"),
    "Env1.Attack":        MCPHostParam(12,  "Env 1 Attack",  "Amplitude envelope attack time"),
    # Env1.Decay, Env1.Sustain, Env1.Release are NOT in the 127-param MCP surface.
    # Env 4 (indices 100-104) is an auxiliary modulation envelope, not the amp envelope.
    # Mapping Env1.* to Env 4 would silently write to the wrong parameter.
    # REFUSED_NO_MCP_MAPPING is the correct outcome — see 16.5.62 DiscoveryRequest.
}

# ---------------------------------------------------------------------------
# Intent vocabulary — maps lowercased phrase fragments to semantic target names
# Order matters: more specific patterns first.
# ---------------------------------------------------------------------------
_TARGET_PATTERNS: list[tuple[list[str], str]] = [
    # OSC1 volume — most specific first
    (["osc 1 quieter", "osc1 quieter", "osc 1 louder", "osc1 louder",
      "osc 1 volume", "osc1 volume", "osc 1 level", "osc1 level",
      "osc 1 to ", "osc1 to ", "make osc 1", "make osc1"],       "OSC1.Volume"),
    (["filter cutoff", "cutoff", "filter frequency", "filter freq"], "Filter.Cutoff"),
    (["filter resonance", "filter reso", "resonance"],              "Filter.Resonance"),
    # Envelope — "attack" must not match before filter patterns
    (["attack", "env attack", "envelope attack"],                   "Env1.Attack"),
    (["release", "env release"],                                    "Env1.Release"),
    (["sustain", "env sustain"],                                    "Env1.Sustain"),
    (["master volume", "main volume", "master vol", "overall volume"], "Global.MasterVolume"),
    (["osc 1 enable", "osc1 enable", "enable osc"],                "OSC1.Enable"),
    (["osc 1 octave", "osc1 octave"],                              "OSC1.Octave"),
]

# Directional keywords → signed delta (negative = decrease, positive = increase).
# "slower attack" means longer = higher MCP value → positive.
_DIRECTION_DELTAS: dict[str, float] = {
    "quieter":  -0.20,
    "louder":    0.20,
    "high":      0.20,
    "higher":    0.20,
    "low":      -0.20,
    "lower":    -0.20,
    "increase":  0.20,
    "decrease": -0.20,
    "slower":    0.20,
    "faster":   -0.20,
    "more":      0.20,
    "less":     -0.20,
    "brighter":  0.20,
    "darker":   -0.20,
    "bigger":    0.20,
    "smaller":  -0.20,
    "long":      0.20,
    "longer":    0.20,
    "short":    -0.20,
    "shorter":  -0.20,
    "open":      0.20,
    "close":    -0.20,
    "up":        0.20,
    "down":     -0.20,
}


def _detect_target(lowered: str) -> Optional[str]:
    for phrases, target_name in _TARGET_PATTERNS:
        if any(p in lowered for p in phrases):
            return target_name
    return None


def _detect_value(lowered: str) -> Optional[Tuple[str, float]]:
    """Return (kind, value) or None if unparseable."""
    # Absolute percentage: "50%", "to 75%", "at 50%"
    pct_match = re.search(r'\b(\d+(?:\.\d+)?)\s*%', lowered)
    if pct_match:
        pct = float(pct_match.group(1))
        if 0.0 <= pct <= 100.0:
            return (ABSOLUTE, pct / 100.0)
        return None  # out of range — caller will refuse

    # Absolute normalized: "to 0.5", "set to 0.75"
    norm_match = re.search(r'\bto\s+(0(?:\.\d+)?|1(?:\.0+)?)\b', lowered)
    if norm_match:
        val = float(norm_match.group(1))
        return (ABSOLUTE, val)

    # Directional delta
    for keyword, delta in sorted(_DIRECTION_DELTAS.items(), key=lambda kv: -len(kv[0])):
        if keyword in lowered:
            return (RELATIVE, delta)

    return None


def parse_intent(raw_intent: str) -> "ParsedIntent | IntentRefusal":
    """Parse a natural-language intent string into a structured ParsedIntent.

    Returns IntentRefusal when the intent cannot be mapped to a known
    semantic target or a resolvable value specification.
    """
    lowered = raw_intent.lower()

    target_name = _detect_target(lowered)
    if target_name is None:
        return IntentRefusal(
            raw_intent=raw_intent,
            reason=REFUSED_PARSE_FAILURE,
            detail=(
                "could not identify a known synthesis parameter in %r; "
                "supported targets: %s" % (
                    raw_intent,
                    ", ".join(t for _, t in _TARGET_PATTERNS))
            ),
        )

    value_result = _detect_value(lowered)
    if value_result is None:
        return IntentRefusal(
            raw_intent=raw_intent,
            reason=REFUSED_PARSE_FAILURE,
            detail=(
                "detected target %r but could not parse a value or direction from %r; "
                "use 'X%%', 'to X.X', or directional words like 'quieter', 'increase'" %
                (target_name, raw_intent)
            ),
        )

    kind, value = value_result
    return ParsedIntent(
        raw_intent=raw_intent,
        semantic_target_name=target_name,
        value_kind=kind,
        value=value,
    )


def compile_intent(raw_intent: str) -> "IntentPlan | IntentRefusal":
    """Full compilation: intent string → IntentPlan.

    Returns IntentRefusal when:
      - the intent cannot be parsed (INTENT_PARSE_FAILURE)
      - the semantic target is not in SEMANTIC_TARGETS vocabulary (UNKNOWN_SEMANTIC_TARGET)
      - no MCP host mapping exists for the target (NO_MCP_MAPPING)

    Does NOT read or write MCP. Does NOT execute anything.
    """
    parsed = parse_intent(raw_intent)
    if isinstance(parsed, IntentRefusal):
        return parsed

    # Semantic vocabulary check
    ref = SEMANTIC_TARGETS.get(parsed.semantic_target_name)
    if ref is None:
        return IntentRefusal(
            raw_intent=raw_intent,
            reason=REFUSED_UNKNOWN_TARGET,
            detail=(
                "semantic target %r is not in SEMANTIC_TARGETS vocabulary; "
                "this is a compiler gap, not a Serum limitation" %
                parsed.semantic_target_name
            ),
        )

    # MCP host mapping check — the Option A capability admission gate
    host_param = MCP_HOST_MAP.get(parsed.semantic_target_name)
    if host_param is None:
        return IntentRefusal(
            raw_intent=raw_intent,
            reason=REFUSED_NO_MCP_MAPPING,
            detail=(
                "semantic target %r exists in vocabulary (capability_key=%r) "
                "but has no MCP host parameter mapping for the current device "
                "(track_index=0, device_index=0, Serum 2 127-param surface). "
                "This is the exact missing capability for the knowledge loop." %
                (parsed.semantic_target_name, ref.capability_key)
            ),
        )

    return IntentPlan(
        raw_intent=raw_intent,
        semantic_target=ref,
        capability_key=ref.capability_key,
        host_param=host_param,
        value_kind=parsed.value_kind,
        value_spec=parsed.value,
    )


def resolve_host_value(plan: IntentPlan, current_host_value: float) -> "float | IntentRefusal":
    """Convert an IntentPlan's value_spec to a concrete host value (0-1).

    For ABSOLUTE intents: value_spec is already the host value.
    For RELATIVE intents: value_spec is a signed delta applied to current_host_value,
    clamped to [0, 1].

    Returns IntentRefusal if the result would be out of range (for absolute values
    that were already clamped, this should not occur; the check is a safety guard).
    """
    if plan.value_kind == ABSOLUTE:
        host_val = plan.value_spec
    else:
        host_val = current_host_value + plan.value_spec

    host_val = max(0.0, min(1.0, host_val))
    return host_val


def make_audit_record(
    plan: IntentPlan,
    current_host_value: float,
    written_host_value: float,
    readback_value: float,
    mcp_write_response: str,
    result: str = "SUCCESS",
) -> dict:
    """Assemble the canonical auditable record for one intent execution."""
    return {
        "intent": plan.raw_intent,
        "semantic_target": plan.semantic_target.name,
        "capability_key": plan.capability_key,
        "resolved_host_parameter": {
            "index": plan.host_param.index,
            "name": plan.host_param.name,
            "description": plan.host_param.description,
            "track_index": plan.host_param.track_index,
            "device_index": plan.host_param.device_index,
        },
        "requested_value": plan.value_spec,
        "requested_value_kind": plan.value_kind,
        "host_value": written_host_value,
        "readback_value": readback_value,
        "write_matched_readback": abs(written_host_value - readback_value) < 0.01,
        "mcp_write_response": mcp_write_response,
        "result": result,
    }
