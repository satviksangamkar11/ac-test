"""Transcript-guided frame selection: merge cues with visual detection & uniform fallback.

Three sources of frame candidates:
  1. TRANSCRIPT_CUE: Claude Code identified important moments
  2. VISUAL_CHANGE: Existing detector found scene changes
  3. UNIFORM_FALLBACK: Regular intervals for baseline coverage

Priority (provenance only, not truth):
  TRANSCRIPT_CUE > VISUAL_CHANGE > UNIFORM_FALLBACK

Merges candidates within 100ms buckets.
Returns deterministic, deduplicated, sorted by timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FrameSelectionBasis(StrEnum):
    """Why a particular frame was selected."""
    TRANSCRIPT_CUE = "TRANSCRIPT_CUE"
    VISUAL_CHANGE = "VISUAL_CHANGE"
    UNIFORM_FALLBACK = "UNIFORM_FALLBACK"


@dataclass(frozen=True)
class FrameCandidate:
    """Single frame timestamp candidate for extraction."""

    timestamp_s: float
    basis: FrameSelectionBasis

    # Which transcript cue(s) this came from (empty if not transcript-based)
    cue_ids: tuple[str, ...] = ()

    # Human-readable reason why this timestamp was selected
    selection_reason: str | None = None


@dataclass(frozen=True)
class FrameSelectionConfig:
    """Parameters for frame candidate generation."""

    # Maximum frames to return
    max_frames: int = 64

    # Temporal window around transcript cues (for fallback when no preferred_timestamps)
    pre_roll_s: float = 2.0
    post_roll_s: float = 2.0

    # Uniform fallback interval (e.g., one frame every 10 seconds)
    uniform_interval_s: float = 10.0

    # Prevent one transcript cue from exploding frame count
    max_preferred_per_cue: int = 3


def clamp_timestamp(timestamp_s: float, duration_s: float) -> float:
    """Clamp timestamp to [0, duration_s]."""
    return max(0.0, min(timestamp_s, duration_s))


def build_transcript_candidates(
    cue_plan: dict,
    duration_s: float,
    config: FrameSelectionConfig,
) -> list[FrameCandidate]:
    """Generate frame candidates from transcript cues.

    For each cue:
    - Use preferred_timestamps_s if provided
    - Otherwise, use start, midpoint, end of the cue window

    Args:
        cue_plan: TranscriptCuePlan as dict
        duration_s: Video duration
        config: Selection configuration

    Returns:
        List of FrameCandidate with basis=TRANSCRIPT_CUE
    """

    candidates: list[FrameCandidate] = []

    for cue in cue_plan.get("cues", []):
        cue_id = str(cue["cue_id"])
        preferred = cue.get("preferred_timestamps_s", [])

        # Use preferred timestamps if available
        for timestamp in preferred[: config.max_preferred_per_cue]:
            timestamp = clamp_timestamp(float(timestamp), duration_s)

            candidates.append(
                FrameCandidate(
                    timestamp_s=timestamp,
                    basis=FrameSelectionBasis.TRANSCRIPT_CUE,
                    cue_ids=(cue_id,),
                    selection_reason=cue.get("verification_reason"),
                )
            )

        # If no preferred timestamps, use cue boundaries
        if not preferred:
            start = clamp_timestamp(float(cue["start_s"]), duration_s)
            end = clamp_timestamp(float(cue["end_s"]), duration_s)
            midpoint = (start + end) / 2.0

            candidates.extend(
                [
                    FrameCandidate(
                        timestamp_s=start,
                        basis=FrameSelectionBasis.TRANSCRIPT_CUE,
                        cue_ids=(cue_id,),
                        selection_reason=cue.get("verification_reason"),
                    ),
                    FrameCandidate(
                        timestamp_s=midpoint,
                        basis=FrameSelectionBasis.TRANSCRIPT_CUE,
                        cue_ids=(cue_id,),
                        selection_reason=cue.get("verification_reason"),
                    ),
                    FrameCandidate(
                        timestamp_s=end,
                        basis=FrameSelectionBasis.TRANSCRIPT_CUE,
                        cue_ids=(cue_id,),
                        selection_reason=cue.get("verification_reason"),
                    ),
                ]
            )

    return candidates


def merge_frame_candidates(
    transcript_candidates: list[FrameCandidate],
    visual_change_candidates: list[FrameCandidate],
    uniform_candidates: list[FrameCandidate],
    *,
    max_frames: int,
    duration_s: float,
) -> list[FrameCandidate]:
    """Merge three sources of frame candidates into deduplicated list.

    Deduplication: 100ms bucket (±50ms).
    Priority (for provenance field only):
      TRANSCRIPT_CUE > VISUAL_CHANGE > UNIFORM_FALLBACK

    Args:
        transcript_candidates: From Claude Code cue plan
        visual_change_candidates: From existing visual detector
        uniform_candidates: From regular interval fallback
        max_frames: Maximum frames to return
        duration_s: Video duration (for clamping)

    Returns:
        Sorted list of merged candidates
    """

    merged: dict[int, FrameCandidate] = {}

    # Process in priority order
    ordered = (
        transcript_candidates
        + visual_change_candidates
        + uniform_candidates
    )

    for candidate in ordered:
        timestamp = clamp_timestamp(candidate.timestamp_s, duration_s)

        # 100ms bucket (±50ms) for deduplication
        key = round(timestamp * 10)

        if key not in merged:
            merged[key] = FrameCandidate(
                timestamp_s=timestamp,
                basis=candidate.basis,
                cue_ids=candidate.cue_ids,
                selection_reason=candidate.selection_reason,
            )
        else:
            current = merged[key]

            # Merge: prefer stronger provenance, combine cue_ids, preserve reason
            merged[key] = FrameCandidate(
                timestamp_s=current.timestamp_s,
                basis=(
                    FrameSelectionBasis.TRANSCRIPT_CUE
                    if (
                        current.basis
                        == FrameSelectionBasis.TRANSCRIPT_CUE
                        or candidate.basis
                        == FrameSelectionBasis.TRANSCRIPT_CUE
                    )
                    else (
                        FrameSelectionBasis.VISUAL_CHANGE
                        if (
                            current.basis
                            == FrameSelectionBasis.VISUAL_CHANGE
                            or candidate.basis
                            == FrameSelectionBasis.VISUAL_CHANGE
                        )
                        else FrameSelectionBasis.UNIFORM_FALLBACK
                    )
                ),
                cue_ids=tuple(
                    sorted(
                        set(current.cue_ids) | set(candidate.cue_ids)
                    )
                ),
                selection_reason=(
                    current.selection_reason
                    or candidate.selection_reason
                ),
            )

    # Sort by timestamp, limit to max_frames
    result = sorted(merged.values(), key=lambda c: c.timestamp_s)
    return result[:max_frames]


def build_uniform_candidates(
    duration_s: float,
    interval_s: float,
) -> list[FrameCandidate]:
    """Generate uniform baseline coverage.

    One frame every interval_s seconds, starting at interval_s.

    Args:
        duration_s: Video duration
        interval_s: Interval between frames

    Returns:
        List of FrameCandidate with basis=UNIFORM_FALLBACK
    """

    candidates: list[FrameCandidate] = []
    timestamp = interval_s

    while timestamp < duration_s:
        candidates.append(
            FrameCandidate(
                timestamp_s=timestamp,
                basis=FrameSelectionBasis.UNIFORM_FALLBACK,
                selection_reason=f"Uniform baseline coverage ({interval_s}s intervals)",
            )
        )
        timestamp += interval_s

    return candidates
