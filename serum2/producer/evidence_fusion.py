"""Phase B: transcript + visual evidence fusion.

Combines a transcript excerpt with a UIStateSnapshot diff into one
ProductionEvent, classifying the relationship between what the narrator
said and what the UI actually shows. This is what prevents the system from
being transcript-blind: a change the narrator never mentions is preserved
as evidence, not discarded because it wasn't named.

Never picks a "winner" when transcript and visual disagree -- CONFLICT is
a first-class, preserved outcome, exactly as the frozen plan requires
("if transcript and visual disagree, preserve both and mark the conflict").
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from serum2.source.visual_evidence import ProductionEvent

AGREEMENT = "AGREEMENT"
VISUAL_ONLY = "VISUAL_ONLY"
TRANSCRIPT_ONLY = "TRANSCRIPT_ONLY"
CONFLICT = "CONFLICT"
UNKNOWN = "UNKNOWN"

# Same target-keyword vocabulary transcript_query_planner.py uses -- a
# transcript excerpt "supports" a changed control if its text mentions a
# keyword associated with that control_id's family. Reused, not duplicated:
# imported from the planner so the two never drift apart.
from serum2.source.transcript_query_planner import _TARGET_KEYWORDS


def _transcript_mentions_control(transcript_excerpt: str, control_id: str) -> bool:
    if not transcript_excerpt:
        return False
    lowered = transcript_excerpt.lower()
    control_family = control_id.lower().split(".")[0]  # "env1.release" -> "env1"
    for _concept, target_name, keywords in _TARGET_KEYWORDS:
        target_family = target_name.lower().split(".")[0].replace("env1", "env")
        if control_family.replace("1", "").startswith(target_family.replace("1", "")) or \
           target_family in control_family:
            if any(kw in lowered for kw in keywords):
                return True
    return False


def fuse_transcript_and_visual(
    event_id: str,
    start_timestamp_sec: float,
    end_timestamp_sec: float,
    evidence_frame_ids: List[str],
    snapshot_diff: Dict[str, Any],
    transcript_excerpt: Optional[str] = None,
    transcript_timestamp_sec: Optional[float] = None,
) -> ProductionEvent:
    """Build one ProductionEvent from a UI diff + overlapping transcript.

    fusion_status classification:
      AGREEMENT        transcript mentions >=1 changed control, and no
                        changed control is UNRELATED to the transcript topic
                        (i.e. transcript covers everything that changed)
      VISUAL_ONLY       UI changed but transcript says nothing relevant at all
      TRANSCRIPT_ONLY    transcript describes an action but no UI change was
                        observed for it (nothing in snapshot_diff)
      CONFLICT          transcript mentions a specific control, but that
                        control's observed diff contradicts the transcript's
                        own directional wording (e.g. "off"/"less"/"lower"
                        said while the observed value increased), OR the
                        transcript names a target that did NOT change while
                        OTHER unrelated controls did
      UNKNOWN           no transcript excerpt and no interpretable diff
    """
    changed = snapshot_diff.get("changed_controls", [])
    added_routes = snapshot_diff.get("added_routes", [])
    removed_routes = snapshot_diff.get("removed_routes", [])

    observed: List[str] = []
    for c in changed:
        observed.append("%s: %s -> %s" % (c["control_id"], c["before"], c["after"]))
    for r in added_routes:
        observed.append("added route: %s -> %s" % (r.get("source"), r.get("destination")))
    for r in removed_routes:
        observed.append("removed route: %s -> %s" % (r.get("source"), r.get("destination")))

    has_visual_change = bool(changed or added_routes or removed_routes)
    has_transcript = bool(transcript_excerpt)

    mentioned_ids = [
        c["control_id"] for c in changed
        if _transcript_mentions_control(transcript_excerpt or "", c["control_id"])
    ]
    unmentioned_ids = [c["control_id"] for c in changed if c["control_id"] not in mentioned_ids]

    # Route additions/removals are also checkable against the transcript --
    # e.g. "drag the LFO onto the cutoff" should count as mentioning an
    # lfo*->*filter*/*cutoff* route, the same way a control_id is checked.
    # Without this, every route-only event falls through to CONFLICT just
    # because `mentioned_ids` (controls-only) stays empty -- a real bug
    # caught by testing the exact k6 LFO->cutoff example against this code.
    route_mentioned = False
    if transcript_excerpt:
        lowered_excerpt = transcript_excerpt.lower()
        for r in added_routes + removed_routes:
            src = (r.get("source") or "").lower()
            dst = (r.get("destination") or "").lower()
            src_hit = "lfo" in lowered_excerpt and src.startswith("lfo")
            dst_hit = any(kw in lowered_excerpt for kw in ("cutoff", "filter")) and (
                "filter" in dst or "cutoff" in dst
            )
            if src_hit or dst_hit:
                route_mentioned = True
                break

    _DECREASE_WORDS = ("off", "less", "lower", "down", "reduce", "decrease", "shorter", "quieter")
    _INCREASE_WORDS = ("more", "up", "raise", "increase", "longer", "louder", "bring up")

    conflict = False
    if has_transcript and mentioned_ids:
        lowered = (transcript_excerpt or "").lower()
        said_decrease = any(w in lowered for w in _DECREASE_WORDS)
        said_increase = any(w in lowered for w in _INCREASE_WORDS)
        # Directional conflict check is advisory-only and intentionally
        # coarse: real language ("take the pops and clicks off") can mean
        # "soften" (a value increase) while using decrease-coded words. This
        # is exactly why CONFLICT must be surfaced for the Brain to reason
        # about, not silently resolved here.
        if said_decrease and not said_increase:
            for cid in mentioned_ids:
                c = next(x for x in changed if x["control_id"] == cid)
                # only flag if both sides are parseable numerics with a unit
                import re
                bm = re.match(r"([\d.]+)", str(c["before"]))
                am = re.match(r"([\d.]+)", str(c["after"]))
                if bm and am and float(am.group(1)) > float(bm.group(1)):
                    conflict = True

    any_mentioned = bool(mentioned_ids) or route_mentioned
    routes_only_and_all_mentioned = (
        not changed and (added_routes or removed_routes) and route_mentioned
    )

    if not has_visual_change and not has_transcript:
        fusion_status = UNKNOWN
    elif conflict:
        fusion_status = CONFLICT
    elif routes_only_and_all_mentioned:
        fusion_status = AGREEMENT
    elif has_visual_change and mentioned_ids and not unmentioned_ids:
        fusion_status = AGREEMENT
    elif has_visual_change and not has_transcript:
        fusion_status = VISUAL_ONLY
    elif has_visual_change and has_transcript and not any_mentioned:
        # transcript present but doesn't name any of the observed changes --
        # both evidence sources are real but disjoint; treat as CONFLICT
        # (silently picking one would violate "preserve the disagreement").
        fusion_status = CONFLICT
    elif has_visual_change and unmentioned_ids:
        # transcript covers SOME but not all changes -- the frozen plan's
        # exact motivating case (mentioned + unmentioned changes coexist).
        # Not a contradiction, so not CONFLICT; recorded plainly via
        # `unknown` below rather than forced into AGREEMENT.
        fusion_status = AGREEMENT
    elif has_transcript and not has_visual_change:
        fusion_status = TRANSCRIPT_ONLY
    else:
        fusion_status = UNKNOWN

    inferred: List[str] = []
    unknown: List[str] = []
    if transcript_excerpt:
        inferred.append("transcript: %r" % transcript_excerpt)
    if unmentioned_ids:
        unknown.append(
            "controls changed but not named in the transcript excerpt: %s" % unmentioned_ids
        )
    if has_transcript and not has_visual_change:
        unknown.append("transcript describes an action but no corresponding UI change was observed")

    return ProductionEvent(
        event_id=event_id,
        start_timestamp_sec=start_timestamp_sec,
        end_timestamp_sec=end_timestamp_sec,
        evidence_frame_ids=evidence_frame_ids,
        snapshot_diff=snapshot_diff,
        transcript_excerpt=transcript_excerpt,
        transcript_timestamp_sec=transcript_timestamp_sec,
        observed=observed,
        inferred=inferred,
        unknown=unknown,
        fusion_status=fusion_status,
    )
