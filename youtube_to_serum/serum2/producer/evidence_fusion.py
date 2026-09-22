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

import re
from typing import Any, Dict, List, Optional, Tuple

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


# ---------------------------------------------------------------------------------------------
# Per-control direction evaluation (architecture section 22).
#
# Direction is evaluated for EACH changed control, from the transcript language that is LOCAL to
# that control -- never from the excerpt as a whole. A control's mention keywords come from the
# reference Atlas (aliases + names of its canonical id: data, not a list kept here). The English
# direction vocabulary below is generic language, not a control or tutorial mapping.
# ---------------------------------------------------------------------------------------------
_DECREASE_WORDS = frozenset(("off", "less", "lower", "down", "reduce", "decrease", "shorter", "shorten",
                             "quieter", "smaller", "tighter"))
_INCREASE_WORDS = frozenset(("more", "up", "raise", "increase", "longer", "louder", "higher", "bigger",
                             "larger", "extend", "boost"))
_CLAUSE_BOUNDARY = frozenset(("and", "but", "then", "so", "also", "while", "because", "although"))
_MAX_TOKENS_BETWEEN = 3     # a direction word belongs to a control only if it sits this close to a mention

_UNITS_TO_BASE = {"ms": ("time", 1.0), "s": ("time", 1000.0), "hz": ("freq", 1.0), "khz": ("freq", 1000.0),
                  "db": ("db", 1.0), "%": ("pct", 1.0), "": ("num", 1.0)}


def _tokens(text: str) -> List[str]:
    """Lower-cased word tokens. Bracketed captions such as [music] are not speech and are dropped."""
    return re.findall(r"[a-z0-9']+", re.sub(r"\[[^\]]*\]", " ", (text or "").lower()))


def _mention_sequences(control_id: str) -> List[List[str]]:
    """Token sequences that name this control, derived from the Atlas entry its id resolves to."""
    from serum2.reference.serum_atlas import normalize_control, get_control
    seqs: List[List[str]] = []
    r = normalize_control(control_id)
    if r.status in ("EXACT", "ALIAS") and r.canonical_id:
        e = get_control(r.canonical_id)
        names = list(e.aliases) + [e.display_name.lower(), r.canonical_id.split(".", 1)[1].replace("_", " ")]
        for n in names:
            t = _tokens(n)
            if t and len(" ".join(t)) > 1 and not (set(t) & (_DECREASE_WORDS | _INCREASE_WORDS)) and t not in seqs:
                seqs.append(t)
    return seqs


_NAME_TOKENS: Optional[frozenset] = None


def _atlas_name_tokens() -> frozenset:
    """Single-word control names known to the reference Atlas (aliases and canonical field names).
    Used only to let OTHER controls compete for a direction word, so 'blend a bit down' is not read as
    a statement about a neighbouring control. Data-derived; biases toward UNKNOWN, never toward CONFLICT."""
    global _NAME_TOKENS
    if _NAME_TOKENS is None:
        from serum2.reference.serum_atlas import all_control_ids, get_control
        names = set()
        for cid in all_control_ids():
            e = get_control(cid)
            for n in list(e.aliases) + [cid.split(".", 1)[1].replace("_", " ")]:
                t = _tokens(n)
                if len(t) == 1 and len(t[0]) >= 3 and t[0] not in _DECREASE_WORDS | _INCREASE_WORDS:
                    names.add(t[0])
        _NAME_TOKENS = frozenset(names)
    return _NAME_TOKENS


_NUMBER_WORDS = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8"}


def _named_slots(text: str) -> set:
    """Slots the transcript names explicitly ('envelope one', 'env 2', 'filter number two'), as Atlas slot
    ids. Reuses the Atlas's own slot recognizer on a lightly normalized copy of the text."""
    from serum2.reference.serum_atlas import _slots_in
    t = re.sub(r"\[[^\]]*\]", " ", (text or "").lower())
    t = re.sub(r"\b(envelope|envelopes)\b", "env", t)
    t = re.sub(r"\b(number|no)\b", " ", t)
    t = re.sub(r"\b(%s)\b" % "|".join(_NUMBER_WORDS), lambda m: _NUMBER_WORDS[m.group(1)], t)
    return set(_slots_in(t))


def _slot_of(control_id: str) -> Optional[str]:
    from serum2.reference.serum_atlas import normalize_control
    r = normalize_control(control_id)
    return r.canonical_id.split(".", 1)[0] if r.status in ("EXACT", "ALIAS") and r.canonical_id else None


def _excluded_by_named_slots(control_id: str, named: set) -> bool:
    """True if the excerpt names slots of this control's family but not this control's slot: a bare
    alias then cannot be about this control."""
    slot = _slot_of(control_id)
    if not slot:
        return False
    fam = re.sub(r"\d+$", "", slot)
    same_family = {n for n in named if re.sub(r"\d+$", "", n) == fam}
    return bool(same_family) and slot not in same_family


def _mention_spans(tokens: List[str], seqs: List[List[str]]) -> List[Tuple[int, int]]:
    spans = []
    for seq in seqs:
        n = len(seq)
        for i in range(len(tokens) - n + 1):
            if tokens[i:i + n] == seq:
                spans.append((i, i + n))
    return spans


def _to_number(v: Any) -> Optional[Tuple[str, float]]:
    """('time'|'freq'|'db'|'pct'|'num'|'onoff', value in the family's base unit), or None if not comparable."""
    sv = str(v).strip().lower()
    if sv in ("on", "off"):
        return "onoff", 1.0 if sv == "on" else 0.0
    m = re.fullmatch(r"(-?inf|-?\d+(?:\.\d+)?)\s*(ms|s|hz|khz|db|%)?", sv)
    if not m:
        return None
    fam, mult = _UNITS_TO_BASE[m.group(2) or ""]
    return fam, float(m.group(1).replace("inf", "inf")) * mult


def _visual_direction(before: Any, after: Any) -> Optional[str]:
    b, a = _to_number(before), _to_number(after)
    if b is None or a is None or b[0] != a[0]:
        return None
    return "increase" if a[1] > b[1] else ("decrease" if a[1] < b[1] else None)


def _transcript_directions(tokens: List[str], spans_by_control: Dict[str, List[Tuple[int, int]]]) -> Dict[str, Optional[str]]:
    """Assign each direction word to the NEAREST control mention within reach; a word equidistant from
    two different controls, or far from every mention, belongs to none. A control that receives both
    increase and decrease words is indeterminate (None)."""
    got: Dict[str, set] = {cid: set() for cid in spans_by_control}
    for j, tok in enumerate(tokens):
        kind = "increase" if tok in _INCREASE_WORDS else ("decrease" if tok in _DECREASE_WORDS else None)
        if kind is None:
            continue
        best: List[Tuple[int, str]] = []
        for cid, spans in spans_by_control.items():
            for (a, b) in spans:
                gap = (a - j - 1) if j < a else (j - b)          # tokens between the word and the mention
                lo, hi = (j + 1, a) if j < a else (b, j)
                if 0 <= gap <= _MAX_TOKENS_BETWEEN and not (_CLAUSE_BOUNDARY & set(tokens[lo:hi])):
                    best.append((gap, cid))                       # never across a clause boundary
        if not best:
            continue
        best.sort()
        if len(best) > 1 and best[0][0] == best[1][0] and best[0][1] != best[1][1]:
            continue                                             # equidistant from two controls: ambiguous
        got[best[0][1]].add(kind)
    return {cid: (next(iter(k)) if len(k) == 1 else None) for cid, k in got.items()}


def classify_controls(changed: List[Dict[str, Any]], transcript_excerpt: Optional[str]) -> Dict[str, Dict[str, Any]]:
    """Per changed control: {mentioned, visual, transcript, classification}. CONFLICT needs a positive
    contradiction for THAT control; anything not reliably evaluable is UNKNOWN, never CONFLICT."""
    tokens = _tokens(transcript_excerpt or "")
    seqs = {c["control_id"]: _mention_sequences(c["control_id"]) for c in changed}
    named = _named_slots(transcript_excerpt or "")
    spans = {cid: ([] if _excluded_by_named_slots(cid, named) else _mention_spans(tokens, sq)) for cid, sq in seqs.items()}
    # legacy planner phrases still count as a mention (kept for compatibility, never as direction evidence)
    own = {cid: sp for cid, sp in spans.items() if sp}
    covered = {i for sp in own.values() for (a, b) in sp for i in range(a, b)}
    competing = {"~other:%d" % i: [(i, i + 1)] for i, tok in enumerate(tokens) if tok in _atlas_name_tokens() and i not in covered}
    t_dirs = _transcript_directions(tokens, {**own, **competing})
    out: Dict[str, Dict[str, Any]] = {}
    for c in changed:
        cid = c["control_id"]
        mentioned = bool(spans[cid]) or (not _excluded_by_named_slots(cid, named) and _transcript_mentions_control(transcript_excerpt or "", cid))
        v = _visual_direction(c["before"], c["after"])
        t = t_dirs.get(cid) if spans[cid] else None
        if t and v:
            cls = AGREEMENT if t == v else CONFLICT
        else:
            cls = UNKNOWN
        out[cid] = {"mentioned": mentioned, "visual": v, "transcript": t, "classification": cls}
    return out


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

    fusion_status classification (architecture 22 -- direction is evaluated PER CHANGED CONTROL):
      per control   AGREEMENT  transcript direction (from language local to that control) and visual
                                direction are both present and equal
                    CONFLICT   both present and opposite -- a positive contradiction for that control
                    UNKNOWN    either is absent or indeterminate (never CONFLICT)
      event         CONFLICT   any per-control CONFLICT
                    AGREEMENT  no CONFLICT and >=1 per-control AGREEMENT (or a mentioned route change)
                    VISUAL_ONLY  UI changed and the transcript, if any, does not cover it
                    TRANSCRIPT_ONLY  transcript present, no UI change
                    UNKNOWN    otherwise (covered, direction not reliably evaluable; or no evidence)
    Per-control detail is returned in snapshot_diff["control_fusion"].
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

    per_control = classify_controls(changed, transcript_excerpt)
    mentioned_ids = [cid for cid, d in per_control.items() if d["mentioned"]]
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

    any_conflict = any(d["classification"] == CONFLICT for d in per_control.values())
    any_agreement = any(d["classification"] == AGREEMENT for d in per_control.values())
    any_mentioned = bool(mentioned_ids) or route_mentioned

    # Event level (architecture 22): CONFLICT only from a per-control positive contradiction; the
    # transcript merely being about something else is NOT a contradiction.
    if not has_visual_change and not has_transcript:
        fusion_status = UNKNOWN
    elif any_conflict:
        fusion_status = CONFLICT
    elif any_agreement or route_mentioned:
        fusion_status = AGREEMENT
    elif has_visual_change and not any_mentioned:
        fusion_status = VISUAL_ONLY          # UI changed; the transcript (if any) does not cover it
    elif has_transcript and not has_visual_change:
        fusion_status = TRANSCRIPT_ONLY
    else:
        fusion_status = UNKNOWN              # covered but direction not reliably evaluable

    snapshot_diff = dict(snapshot_diff)
    snapshot_diff["control_fusion"] = per_control

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
