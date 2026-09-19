"""Phase G (smallest missing deterministic layer): timestamped evidence ->
an ordered ProductionEvent timeline.

Pure glue over machinery that already exists and is fully reused, never
reimplemented:
  - visual_evidence.diff_snapshots()          -- the diff between two frames
  - evidence_fusion.fuse_transcript_and_visual() -- the fusion classification
    (AGREEMENT/VISUAL_ONLY/TRANSCRIPT_ONLY/CONFLICT/UNKNOWN)
  - transcript_query_planner.TranscriptSegment -- the transcript unit type

This module adds exactly one new piece of logic: given N timestamp-ordered
snapshots and M timestamp-ordered transcript segments, which pairs of
consecutive snapshots form an interval, and which transcript segments fall
inside each interval. Everything else (diffing, fusion classification) is
delegated, not duplicated.
"""
from __future__ import annotations

import dataclasses
from typing import Dict, List, Optional, Tuple

from serum2.source.visual_evidence import UIStateSnapshot, ProductionEvent, diff_snapshots, OBSERVED
from serum2.source.transcript_query_planner import TranscriptSegment
from serum2.producer.evidence_fusion import fuse_transcript_and_visual


def _diff_has_evidence_backed_change(diff: dict) -> bool:
    """A diff carries an actual, comparable change -- not merely a control
    that became newly observed or went unobserved between the two frames.
    newly_observed_controls/not_observed_controls are explicitly NOT
    treated as changes here (see visual_evidence.diff_snapshots()'s own
    invariants) -- this function exists only to decide whether an interval
    is worth an event at all, it does not reclassify anything diff_snapshots
    already classified."""
    return bool(
        diff.get("changed_controls") or diff.get("added_routes") or diff.get("removed_routes")
    )


def _baseline_view(prev: UIStateSnapshot, cur: UIStateSnapshot, history: Dict[str, Tuple]):
    """`prev` with, for every control that is OBSERVED in `cur` but not OBSERVED
    in `prev`, that control's most recent earlier OBSERVED reading.

    Why: a Serum panel shows one entity at a time (e.g. the ENV panel shows
    ENV2 for a few frames between two ENV1 readings), so a consecutive-pair
    diff never pairs the two ENV1 readings and a real, two-sided-observed
    change is lost as 'newly observed'. Nothing is invented: every carried
    value is a real earlier OBSERVED reading, and its frame/time is returned
    so the event interval and provenance say exactly where the baseline came
    from. Controls never observed before are left alone (still 'newly observed')."""
    prev_ok = {c.control_id for c in prev.controls if c.status == OBSERVED}
    carried = {}
    for c in cur.controls:
        if c.status == OBSERVED and c.control_id not in prev_ok and c.control_id in history:
            carried[c.control_id] = history[c.control_id]
    if not carried:
        return prev, {}
    kept = [c for c in prev.controls if c.control_id not in carried]
    view = dataclasses.replace(prev, controls=kept + [v[0] for v in carried.values()])
    return view, {cid: {"frame_id": v[2], "timestamp_sec": v[1]} for cid, v in carried.items()}


def build_production_timeline(
    snapshots: List[UIStateSnapshot],
    transcript_segments: List[TranscriptSegment],
) -> List[ProductionEvent]:
    """Walk consecutive snapshot pairs, diff each pair with the existing
    diff_snapshots(), align overlapping transcript segments, and fuse each
    evidence-backed (or transcript-backed) interval into one ProductionEvent
    via the existing fuse_transcript_and_visual(). Returns events ordered by
    start_timestamp_sec.

    Does not mutate `snapshots` or `transcript_segments` -- both are sorted
    into new lists.

    An interval with neither an evidence-backed visual change (per
    diff_snapshots()'s changed_controls/added_routes/removed_routes -- NOT
    newly_observed_controls/not_observed_controls, which are never changes)
    nor any overlapping transcript segment produces NO event: a no-change,
    no-mention interval is not evidence of anything happening, so it is not
    timeline-worthy. This is the one deliberate filtering decision this
    layer makes; every other judgment (what changed, whether transcript and
    visual agree) is delegated to diff_snapshots()/fuse_transcript_and_visual().
    """
    ordered_snapshots = sorted(snapshots, key=lambda s: s.timestamp_sec)
    ordered_segments = sorted(transcript_segments, key=lambda s: s.timestamp_sec)

    events: List[ProductionEvent] = []
    history: Dict[str, Tuple] = {}
    for snap in ordered_snapshots[:1]:
        for c in snap.controls:
            if c.status == OBSERVED:
                history[c.control_id] = (c, snap.timestamp_sec, snap.frame_id)
    for before, after in zip(ordered_snapshots, ordered_snapshots[1:]):
        view, carried = _baseline_view(before, after, history)
        diff = diff_snapshots(view, after)
        diff["baseline_carried"] = carried  # {control_id: {frame_id, timestamp_sec}} of the earlier reading used
        for c in after.controls:
            if c.status == OBSERVED:
                history[c.control_id] = (c, after.timestamp_sec, after.frame_id)
        start_ts = min([before.timestamp_sec] + [v["timestamp_sec"] for v in carried.values()])
        base_frames = sorted({v["frame_id"] for v in carried.values()} - {before.frame_id})

        segs_in_window = [
            s for s in ordered_segments
            if start_ts <= s.timestamp_sec <= after.timestamp_sec
        ]
        transcript_excerpt: Optional[str] = (
            " ".join(s.text for s in segs_in_window) if segs_in_window else None
        )
        transcript_timestamp_sec: Optional[float] = (
            segs_in_window[0].timestamp_sec if segs_in_window else None
        )

        if not _diff_has_evidence_backed_change(diff) and not transcript_excerpt:
            continue  # no-change, no-mention interval -- not timeline-worthy

        event_id = "evt_%d_%d" % (
            round(start_ts * 1000), round(after.timestamp_sec * 1000),
        )
        event = fuse_transcript_and_visual(
            event_id=event_id,
            start_timestamp_sec=start_ts,
            end_timestamp_sec=after.timestamp_sec,
            evidence_frame_ids=base_frames + [before.frame_id, after.frame_id],
            snapshot_diff=diff,
            transcript_excerpt=transcript_excerpt,
            transcript_timestamp_sec=transcript_timestamp_sec,
        )
        events.append(event)

    events.sort(key=lambda e: e.start_timestamp_sec)
    return events
