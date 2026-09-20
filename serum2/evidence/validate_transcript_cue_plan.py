"""Transcript Cue Plan validation: guards against semantic reasoning leakage.

Rejects any plan containing:
  - semantic_target, canonical_target (target identity)
  - operation (operation type)
  - capability, contract (capability inference)
  - route, binding, admission (authority layer)
  - execution, mcp, tool_call (execution)
  - parameter_value (control mapping)

These fields would make Claude Code a second reasoning layer.
Transcript layer is ONLY temporal guidance.
"""

from __future__ import annotations

from typing import Any

# Required fields in every TranscriptCue
REQUIRED_CUE_FIELDS = {
    "cue_id",
    "segment_ids",
    "start_s",
    "end_s",
    "preferred_timestamps_s",
    "kind",
    "focus_terms",
    "verification_reason",
    "confidence",
}

FORBIDDEN_FIELDS = {
    "semantic_target",
    "canonical_target",
    "operation",
    "capability",
    "contract",
    "route",
    "binding",
    "admission",
    "execution",
    "mcp",
    "mcp_call",
    "tool_call",
    "parameter_value",
    "control_identity",
    "target_id",
}


def validate_transcript_cue_plan(
    payload: dict[str, Any],
    *,
    transcript_sha256: str,
    duration_s: float,
    transcript_segment_ids: set[str] | None = None,
    transcript_segment_timestamps: dict[str, tuple[float, float]] | None = None,
) -> None:
    """Validate a TranscriptCuePlan JSON payload.

    Args:
        payload: The plan as a dict
        transcript_sha256: Expected transcript hash (canonical normalized artifact)
        duration_s: Video duration for timestamp validation
        transcript_segment_ids: Known segment IDs from transcript (for provenance check)
        transcript_segment_timestamps: Map of segment_id → (start_s, end_s) for
            preferred_timestamps validation. Required for enforcing that preferred
            timestamps are exact boundaries or deterministic functions thereof.

    Raises:
        ValueError: If the plan violates frozen properties
    """

    # Check required fields
    required = {
        "schema_version",
        "runtime",
        "direct_anthropic_sdk",
        "api_key_used",
        "source_id",
        "video_id",
        "transcript_sha256",
        "cues",
    }

    missing = required - payload.keys()
    if missing:
        raise ValueError(
            f"Transcript cue plan missing fields: {sorted(missing)}"
        )

    # Runtime must be claude-code (not SDK)
    if payload["runtime"] != "claude-code":
        raise ValueError(
            f"Unexpected transcript planning runtime: {payload['runtime']}"
        )

    # Must not use Anthropic SDK
    if payload["direct_anthropic_sdk"] is not False:
        raise ValueError(
            "Transcript planner must not use Anthropic SDK"
        )

    # Must not use API key (subscription auth only)
    if payload["api_key_used"] is not False:
        raise ValueError(
            "Transcript planner must not use an API key"
        )

    # Transcript hash guard (detect stale plans)
    if payload["transcript_sha256"] != transcript_sha256:
        raise ValueError(
            f"Transcript cue plan does not match current transcript "
            f"(plan: {payload['transcript_sha256'][:8]}..., "
            f"current: {transcript_sha256[:8]}...)"
        )

    # Validate each cue
    cues = payload.get("cues", [])
    if not isinstance(cues, list):
        raise ValueError("Cues must be a list")

    for i, cue in enumerate(cues):
        if not isinstance(cue, dict):
            raise ValueError(f"Cue {i} is not a dict")

        # Validate all required cue fields exist
        missing_cue_fields = REQUIRED_CUE_FIELDS - cue.keys()
        if missing_cue_fields:
            raise ValueError(
                f"Cue {i} missing fields: {sorted(missing_cue_fields)}"
            )

        # Guard against semantic reasoning fields
        forbidden = FORBIDDEN_FIELDS & cue.keys()
        if forbidden:
            raise ValueError(
                f"Cue {i} contains forbidden reasoning fields: "
                f"{sorted(forbidden)}"
            )

        # Validate segment provenance (if transcript segments provided)
        if transcript_segment_ids is not None:
            cue_segment_ids = cue.get("segment_ids", [])
            if not isinstance(cue_segment_ids, (list, tuple)):
                raise ValueError(
                    f"Cue {i} segment_ids must be a list/tuple"
                )

            unknown_segments = set(cue_segment_ids) - transcript_segment_ids
            if unknown_segments:
                raise ValueError(
                    f"Cue {i} references unknown transcript segments: "
                    f"{sorted(unknown_segments)}"
                )

        # Validate timestamps
        try:
            start = float(cue["start_s"])
            end = float(cue["end_s"])
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"Cue {i} has invalid timestamps: {e}")

        if start < 0:
            raise ValueError(f"Cue {i} start cannot be negative: {start}")

        if end < start:
            raise ValueError(
                f"Cue {i} end precedes start: {start} → {end}"
            )

        if end > duration_s:
            raise ValueError(
                f"Cue {i} exceeds video duration: {end} > {duration_s}"
            )

        # Validate confidence
        try:
            confidence = float(cue["confidence"])
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"Cue {i} has invalid confidence: {e}")

        if not (0.0 <= confidence <= 1.0):
            raise ValueError(
                f"Cue {i} confidence out of range: {confidence}"
            )

        # Validate preferred timestamps
        preferred = cue.get("preferred_timestamps_s", [])
        if not isinstance(preferred, (list, tuple)):
            raise ValueError(
                f"Cue {i} preferred_timestamps_s must be a list"
            )

        for j, timestamp in enumerate(preferred):
            try:
                ts = float(timestamp)
            except (ValueError, TypeError) as e:
                raise ValueError(
                    f"Cue {i} preferred timestamp {j} is invalid: {e}"
                )

            if ts < start or ts > end:
                raise ValueError(
                    f"Cue {i} preferred timestamp {j} ({ts}) "
                    f"is outside cue window [{start}, {end}]"
                )

            # Enforce that preferred timestamp is exact boundary or deterministic
            if transcript_segment_timestamps is not None:
                segment_ids = cue.get("segment_ids", [])
                is_allowed = False

                # Check if ts is an exact segment boundary
                for seg_id in segment_ids:
                    if seg_id in transcript_segment_timestamps:
                        seg_start, seg_end = transcript_segment_timestamps[seg_id]
                        # Allow exact boundaries or midpoint (deterministic)
                        tolerance = 0.001  # 1ms tolerance for float rounding
                        if (
                            abs(ts - seg_start) < tolerance
                            or abs(ts - seg_end) < tolerance
                            or abs(ts - (seg_start + seg_end) / 2) < tolerance
                        ):
                            is_allowed = True
                            break

                if not is_allowed and segment_ids:
                    raise ValueError(
                        f"Cue {i} preferred timestamp {j} ({ts}) is not an "
                        f"exact segment boundary or deterministic function "
                        f"(segments: {segment_ids})"
                    )
