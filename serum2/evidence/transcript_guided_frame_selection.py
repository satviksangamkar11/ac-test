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
    Priority (enforced via slot allocation under budget):
      TRANSCRIPT_CUE > VISUAL_CHANGE > UNIFORM_FALLBACK

    Allocation strategy: reserve frame slots for transcript and visual,
    fill remainder with uniform fallback. Ensures transcript cues are not
    starved when under frame budget.

    Args:
        transcript_candidates: From Claude Code cue plan
        visual_change_candidates: From existing visual detector
        uniform_candidates: From regular interval fallback
        max_frames: Maximum frames to return
        duration_s: Video duration (for clamping)

    Returns:
        Sorted list of merged candidates (deduplicated, priority-allocated)
    """

    merged: dict[int, FrameCandidate] = {}

    # Deduplicate within 100ms buckets
    # ponytail: allocation strategy is deterministic but simple (60/30/10 split)
    # upgrade if workload demands more sophisticated distribution
    def add_to_merged(candidate: FrameCandidate) -> None:
        timestamp = clamp_timestamp(candidate.timestamp_s, duration_s)
        key = round(timestamp * 10)  # 100ms bucket

        if key not in merged:
            merged[key] = FrameCandidate(
                timestamp_s=timestamp,
                basis=candidate.basis,
                cue_ids=candidate.cue_ids,
                selection_reason=candidate.selection_reason,
            )
        else:
            current = merged[key]
            # Merge: prefer stronger provenance, combine cue_ids
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

    # Add all candidates in priority order
    for candidate in transcript_candidates:
        add_to_merged(candidate)

    for candidate in visual_change_candidates:
        add_to_merged(candidate)

    for candidate in uniform_candidates:
        add_to_merged(candidate)

    # Sort by timestamp
    all_candidates = sorted(merged.values(), key=lambda c: c.timestamp_s)

    if len(all_candidates) <= max_frames:
        return all_candidates

    # Over budget: per-cue allocation guarantees each transcript cue gets coverage
    # Separate by basis
    transcript = [c for c in all_candidates if c.basis == FrameSelectionBasis.TRANSCRIPT_CUE]
    visual = [c for c in all_candidates if c.basis == FrameSelectionBasis.VISUAL_CHANGE]
    uniform = [c for c in all_candidates if c.basis == FrameSelectionBasis.UNIFORM_FALLBACK]

    num_categories = sum(1 for g in [transcript, visual, uniform] if g)

    if num_categories == 1:
        # Single category: just take the top max_frames
        return all_candidates[:max_frames]
    elif transcript:
        # Per-cue allocation: ensure each unique transcript cue gets at least one frame
        # Group by cue_id
        cues_by_id = {}
        for c in transcript:
            for cue_id in c.cue_ids:
                if cue_id not in cues_by_id:
                    cues_by_id[cue_id] = []
                cues_by_id[cue_id].append(c)

        num_unique_cues = len(cues_by_id)
        cue_slots = min(num_unique_cues, max_frames // 2)  # Reserve at least one per cue

        # Take first candidate from each cue
        transcript_selected = []
        for cue_id in sorted(cues_by_id.keys()):
            if transcript_selected and len(transcript_selected) >= cue_slots:
                break
            transcript_selected.append(cues_by_id[cue_id][0])

        # Fill remaining slots with additional transcript candidates
        remaining_t = (
            max_frames
            - len(transcript_selected)
            - (1 if visual else 0)
            - (1 if uniform else 0)
        )
        transcript_selected.extend(
            transcript[len(transcript_selected) : len(transcript_selected) + remaining_t]
        )

        # Add visual and uniform to fill budget
        v_slots = 1 if visual else 0
        u_slots = (
            max(1, max_frames - len(transcript_selected) - v_slots) if uniform else 0
        )

        result = transcript_selected + visual[:v_slots] + uniform[:u_slots]
        return sorted(result, key=lambda c: c.timestamp_s)[:max_frames]
    else:
        # No transcript: split visual and uniform
        num_categories = sum(1 for g in [visual, uniform] if g)
        if num_categories == 1:
            return all_candidates[:max_frames]
        else:
            v_slots = int(max_frames * 0.7)
            u_slots = max_frames - v_slots
            return sorted(
                visual[:v_slots] + uniform[:u_slots],
                key=lambda c: c.timestamp_s
            )


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
