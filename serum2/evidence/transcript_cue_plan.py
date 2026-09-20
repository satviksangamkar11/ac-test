"""Transcript Cue Plan: Temporal evidence guidance for frame extraction.

Schema for Claude Code → Python pipeline:
  Claude Code identifies where in the transcript visual inspection is useful.
  Python validates the plan and uses it to guide frame extraction.

Frozen properties:
  - Cue plan is advisory only (temporal guidance)
  - No semantic targets, operations, or capability inference
  - No Anthropic SDK used in generation or validation
  - Immutable, hashable, serializable to JSON
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
import hashlib
import json


class TranscriptCueKind(StrEnum):
    """Generic linguistic cue categories (no semantic interpretation)."""
    ACTION = "ACTION"
    STATE_CHANGE = "STATE_CHANGE"
    VALUE_MENTION = "VALUE_MENTION"
    NAVIGATION = "NAVIGATION"
    TRANSITION = "TRANSITION"
    EXPLANATION = "EXPLANATION"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TranscriptCue:
    """Single temporal cue from transcript analysis.

    References one or more normalized transcript segments.
    Provides time range and optional preferred timestamps for frame extraction.
    Contains no semantic interpretation or capability inference.
    """

    cue_id: str

    # References normalized transcript segments by ID
    segment_ids: tuple[str, ...]

    # Time range derived from transcript segment timestamps
    start_s: float
    end_s: float

    # Optional preferred moments within the spoken region.
    # Must be either exact transcript segment boundaries or deterministic
    # functions of transcript boundaries (e.g., midpoint, segment_start + offset).
    # Never model-estimated or arbitrary moments (no semantic inference).
    preferred_timestamps_s: tuple[float, ...]

    # Linguistic category (not semantic target)
    kind: TranscriptCueKind

    # Raw language terms from the transcript (no control mapping)
    focus_terms: tuple[str, ...]

    # Why visual verification is useful at this moment
    verification_reason: str

    # Confidence in this cue's importance (0-1)
    confidence: float


@dataclass(frozen=True)
class TranscriptCuePlan:
    """Complete transcript analysis output: ready for frame extraction guidance.

    Immutable, serializable to JSON.
    Contains NO semantic reasoning, NO capability inference.

    Frozen properties:
      - runtime: "claude-code" (not SDK, not API key)
      - direct_anthropic_sdk: false (never used)
      - api_key_used: false (subscription auth only)
      - transcript_sha256: guard against stale plans
    """

    schema_version: str

    # Metadata about the analysis runtime
    runtime: str
    direct_anthropic_sdk: bool
    api_key_used: bool

    # Source identifiers
    source_id: str
    video_id: str
    source_url: str | None

    # Integrity guard: reject if transcript changes
    transcript_sha256: str
    transcript_language: str | None

    # The cues themselves
    cues: tuple[TranscriptCue, ...] = field(default_factory=tuple)

    # Fully immutable provenance metadata: tuple of (key, scalar_value) pairs.
    # Values must be immutable scalars (str, int, float, bool, None).
    # No nested mutable structures (dicts, lists). Frozen dataclass +
    # tuple structure + scalar-only values = true deep immutability.
    provenance: tuple[tuple[str, str | int | float | bool | None], ...] = field(
        default_factory=tuple
    )


def transcript_sha256(transcript_text: str) -> str:
    """SHA256 of transcript text for integrity checking.

    DEPRECATED: Use canonical_normalized_transcript_sha256() instead.
    This function only hashes text, not timestamps/structure.
    """
    return hashlib.sha256(
        transcript_text.encode("utf-8")
    ).hexdigest()


def canonical_normalized_transcript_sha256(
    transcript_json: dict
) -> str:
    """SHA256 of complete normalized transcript artifact.

    Covers: segments, timestamps, IDs, metadata, text.
    Ensures stale plans cannot be accepted against temporally different transcripts.
    """
    raw = json.dumps(
        transcript_json,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def canonical_json_sha256(payload: dict[str, Any]) -> str:
    """Canonical JSON hash (sorted keys, compact format)."""
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
