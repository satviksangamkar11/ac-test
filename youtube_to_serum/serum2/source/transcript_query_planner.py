"""Transcript-first visual query planning (VLP-1 correction).

The transcript does not tell Vision what the answer is. It tells Vision
WHERE to look and WHAT production event is being discussed. This module
scans transcript segments for action-bearing language (a parameter name
plus a change verb), and turns each hit into a small set of targeted
timestamps — a BEFORE reading and an AFTER reading around the mention —
instead of blindly sampling frames on a fixed cadence.

Blind fixed-cadence sampling (the old acquire_visual_evidence.py default)
forces the vision step to search the whole video and guess what mattered,
which is exactly what produced the invalidated k6OBzXdcFtA episode (a
destination inferred from genre/title convention because no transcript
anchor narrowed the search). Planning first, then asking Vision only
"what changed here" removes that failure mode.

This module does not call any MCP tool and does not touch Serum/Ableton.
It is pure text analysis over already-fetched transcript segments.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

# concept -> (canonical target name, keyword phrases to match in transcript text)
# Mirrors producer_brain._INTENT_TO_CONCEPT's vocabulary so a planned target
# lands on a concept the brain can already resolve.
_TARGET_KEYWORDS: List[Tuple[str, str, List[str]]] = [
    ("note-release", "Env1.Release", [
        "release time", "release envelope", "the release", "env release",
        "envelope release", "release knob", "release to",
    ]),
    ("envelope-attack", "Env1.Attack", [
        "attack time", "the attack", "env attack", "envelope attack",
        "attack knob",
    ]),
    ("filter-cutoff", "Filter.Cutoff", [
        "filter cutoff", "cutoff frequency", "the cutoff", "filter frequency",
    ]),
    ("filter-resonance", "Filter.Resonance", [
        "filter resonance", "the resonance", "reso knob",
    ]),
]


@dataclass
class TranscriptSegment:
    """One timed transcript chunk, as returned by a transcript source."""
    timestamp_sec: float
    text: str


@dataclass
class VisualQueryTarget:
    """One timestamp Vision should look at, and why."""
    timestamp_sec: float
    role: str
    """'before' | 'after' | 'context' — before/after must bracket the same
    mention so the resulting frames form a genuine before/after pair."""
    reason: str
    """Human-readable justification, e.g. transcript excerpt that triggered
    this target."""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VisualQueryPlan:
    """The output of transcript analysis: what to look at and why.

    empty (targets == []) is a valid, honest result — it means the
    transcript contained no action-bearing mention of a known target, and
    callers must NOT fall back to blind fixed-cadence sampling silently;
    that decision belongs to the caller (e.g. fall back to
    TranscriptSufficiency-triggered legacy acquisition and say so).
    """
    concept_hint: Optional[str]
    target_name_hint: Optional[str]
    targets: List[VisualQueryTarget] = field(default_factory=list)
    trigger_excerpt: Optional[str] = None
    trigger_timestamp_sec: Optional[float] = None

    def timestamps(self) -> List[float]:
        return [t.timestamp_sec for t in self.targets]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concept_hint": self.concept_hint,
            "target_name_hint": self.target_name_hint,
            "targets": [t.to_dict() for t in self.targets],
            "trigger_excerpt": self.trigger_excerpt,
            "trigger_timestamp_sec": self.trigger_timestamp_sec,
        }


def _find_first_mention(
    segments: List[TranscriptSegment],
) -> Optional[Tuple[TranscriptSegment, str, str, List[str]]]:
    """Return (segment, concept, target_name, matched_keywords) for the
    first mention of a known target anywhere in the transcript, or None.

    Auto-generated YouTube transcripts routinely split a single word across
    two adjacent segments (e.g. one real segment ending "...the cut" and
    the next starting "off to introduce..." — genuinely observed scanning
    a real video's transcript this way: per-segment matching silently
    missed a real "cutoff" mention because of exactly this split). Matching
    is therefore done against the WHOLE transcript joined into one string
    with a single space between segments, never segment-by-segment, so a
    keyword phrase split across a segment boundary is still found. The
    match's character offset is mapped back to the segment whose text
    contains it, for the mention's timestamp.
    """
    def _build_joined(separator: str) -> Tuple[str, List[Tuple[int, TranscriptSegment]]]:
        parts: List[str] = []
        offsets: List[Tuple[int, TranscriptSegment]] = []
        cursor = 0
        for seg in segments:
            offsets.append((cursor, seg))
            parts.append(seg.text)
            cursor += len(seg.text) + len(separator)
        return separator.join(parts).lower(), offsets

    def _segment_at(offsets: List[Tuple[int, TranscriptSegment]], offset: int) -> TranscriptSegment:
        result = offsets[0][1]
        for start, seg in offsets:
            if start > offset:
                break
            result = seg
        return result

    # Two joins: space-separated (normal cross-boundary phrase matching, e.g.
    # a phrase split as "...the release" | "time was..." mid-sentence) and
    # separator-less (mid-WORD splits, e.g. a real transcript observed
    # ending one segment "...the cut" and starting the next "off to..." —
    # "the cutoff" only appears in the space-less join). Whichever join
    # finds an earlier match wins; both are searched for every keyword so
    # neither split style is preferred a priori.
    joined_spaced, offsets_spaced = _build_joined(" ")
    joined_tight, offsets_tight = _build_joined("")

    for concept, target_name, keywords in _TARGET_KEYWORDS:
        for kw in keywords:
            idx_spaced = joined_spaced.find(kw)
            idx_tight = joined_tight.find(kw)
            if idx_spaced == -1 and idx_tight == -1:
                continue
            if idx_tight != -1 and (idx_spaced == -1 or idx_tight <= idx_spaced):
                return _segment_at(offsets_tight, idx_tight), concept, target_name, [kw]
            return _segment_at(offsets_spaced, idx_spaced), concept, target_name, [kw]
    return None


def plan_visual_queries(
    segments: List[TranscriptSegment],
    before_offset_sec: float = 4.0,
    after_offset_sec: float = 4.0,
    extra_after_offset_sec: float = 10.0,
) -> VisualQueryPlan:
    """Scan transcript segments for the first action-bearing mention of a
    known production target and build a before/after visual query plan
    around it.

    Three targets are produced around the mention at t:
      before  = max(0, t - before_offset_sec)   — state prior to the change
      after   = t + after_offset_sec            — state right after
      after2  = t + extra_after_offset_sec       — a second, later after
                reading, since a producer often keeps adjusting for a few
                seconds past the sentence that names the parameter (this
                mirrors the real VLP-1 candidate: mention ~0:34, settled
                value only legible by ~0:38-0:44).

    Returns an empty-targets plan (not an exception, not a guess) when no
    known target is mentioned anywhere in the transcript.
    """
    hit = _find_first_mention(segments)
    if hit is None:
        return VisualQueryPlan(concept_hint=None, target_name_hint=None, targets=[])

    seg, concept, target_name, matched_keywords = hit
    t = seg.timestamp_sec

    targets = [
        VisualQueryTarget(
            timestamp_sec=max(0.0, t - before_offset_sec),
            role="before",
            reason="%.1fs before transcript mention of %r (matched: %s)"
            % (before_offset_sec, target_name, matched_keywords),
        ),
        VisualQueryTarget(
            timestamp_sec=t + after_offset_sec,
            role="after",
            reason="%.1fs after transcript mention of %r" % (after_offset_sec, target_name),
        ),
        VisualQueryTarget(
            timestamp_sec=t + extra_after_offset_sec,
            role="after",
            reason="%.1fs after transcript mention of %r (settled-value check)"
            % (extra_after_offset_sec, target_name),
        ),
    ]

    return VisualQueryPlan(
        concept_hint=concept,
        target_name_hint=target_name,
        targets=targets,
        trigger_excerpt=seg.text,
        trigger_timestamp_sec=t,
    )
