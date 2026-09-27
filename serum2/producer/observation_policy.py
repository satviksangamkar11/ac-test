"""Evidence policy: how VLM / OCR readings become terminal observations.

A numeric reading becomes OBSERVED only when MULTIPLE independent sources agree
(within a tolerance). A single source, regardless of its reported confidence,
is NOT sufficient — it becomes AMBIGUOUS with single_source=True, indicating
corroboration is required before this observation can be treated as authoritative.

Rationale for corroboration requirement:
  A single overconfident-but-wrong source is indistinguishable from a correct
  one at adjudication time (the policy has no ground truth). Requiring >=2
  independent agreeing sources eliminates the single-source confident-wrong
  failure mode demonstrated in the C3 benchmark. The trade-off is higher
  abstention on single-modality evidence; this is intentional — abstention
  is always preferred over a confident wrong read.

Enforced HERE, not inside individual strategies.

The confident-wrong rate (confident reading that contradicts ground truth)
is the gating metric (target ~= 0). Abstention is always preferred over
a wrong confident read.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

OUTCOME_CANDIDATE = "CANDIDATE"
OUTCOME_OBSERVED = "OBSERVED"
OUTCOME_AMBIGUOUS = "AMBIGUOUS"
OUTCOME_UNREADABLE = "UNREADABLE"
OUTCOME_IDENTITY_UNRESOLVED = "IDENTITY_UNRESOLVED"

CONFIDENT_THRESHOLD = 0.9


@dataclass
class ObservationCandidate:
    outcome: str
    value: Any = None
    confidence: float = 0.0
    source: str = ""
    single_source: bool = False
    detail: Optional[str] = None
    # Identity binding (GAP A): which control this candidate claims to describe.
    # Empty string means no identity asserted by the source; non-empty must match
    # requested_control_id passed to adjudicate() or the candidate is excluded.
    control_id: str = ""
    # Evidence provenance (GAP C): SHA-256 or hash of the crop/ROI from which
    # this value was extracted. Empty means no crop provenance recorded.
    evidence_hash: Optional[str] = None


def _values_agree(a: Any, b: Any, numeric_tol: float) -> bool:
    if a is None or b is None:
        return False
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= numeric_tol
    return a == b


def adjudicate(
    candidates: List[ObservationCandidate],
    *,
    numeric_tol: float = 1e-3,
    requested_control_id: str = "",
) -> ObservationCandidate:
    """Given N candidates from independent sources (VLM, OCR, multiple frames),
    return the adjudicated result.

    Identity filtering (GAP A): if requested_control_id is non-empty, any
    candidate whose own control_id is also non-empty and does not match is
    excluded before adjudication. If all candidates are filtered out this way,
    IDENTITY_UNRESOLVED is returned instead of UNREADABLE, so callers can
    distinguish "no readable data" from "data present but identity cannot be
    confirmed."

    Corroboration requirement (GAP B): a single source, even one above
    CONFIDENT_THRESHOLD, returns AMBIGUOUS (with single_source=True) rather
    than OBSERVED. Only multi-source agreement produces OBSERVED. This
    eliminates the single-source confident-wrong failure mode.

    Evidence hash (GAP C): the evidence_hash of the highest-confidence
    agreeing candidate is propagated to the OBSERVED result.
    """
    # --- GAP A: identity filtering ---
    if requested_control_id:
        identity_filtered = [
            c for c in candidates
            if c.outcome == OUTCOME_CANDIDATE
            and c.control_id
            and c.control_id != requested_control_id
        ]
        live = [
            c for c in candidates
            if c.outcome == OUTCOME_CANDIDATE
            and not (c.control_id and c.control_id != requested_control_id)
        ]
        if not live and identity_filtered:
            return ObservationCandidate(
                outcome=OUTCOME_IDENTITY_UNRESOLVED,
                detail="all %d candidate(s) had mismatched control_id (expected %r)" % (
                    len(identity_filtered), requested_control_id),
                control_id=requested_control_id,
            )
    else:
        live = [c for c in candidates if c.outcome == OUTCOME_CANDIDATE]

    if not live:
        return ObservationCandidate(outcome=OUTCOME_UNREADABLE, detail="all candidates unreadable")

    # --- GAP B: single source is never sufficient regardless of confidence ---
    if len(live) == 1:
        c = live[0]
        if c.confidence >= CONFIDENT_THRESHOLD:
            return ObservationCandidate(
                outcome=OUTCOME_AMBIGUOUS,
                value=c.value,
                confidence=c.confidence,
                source=c.source,
                single_source=True,
                detail="single source: corroboration required (confidence %.3f >= %.2f but no independent source)" % (
                    c.confidence, CONFIDENT_THRESHOLD),
                control_id=c.control_id,
                evidence_hash=c.evidence_hash,
            )
        return ObservationCandidate(
            outcome=OUTCOME_AMBIGUOUS,
            value=c.value,
            confidence=c.confidence,
            source=c.source,
            single_source=True,
            detail="single source below confidence threshold (%.3f < %.2f)" % (c.confidence, CONFIDENT_THRESHOLD),
            control_id=c.control_id,
            evidence_hash=c.evidence_hash,
        )

    ref = live[0]
    all_agree = all(_values_agree(c.value, ref.value, numeric_tol) for c in live[1:])
    if all_agree:
        # --- GAP C: propagate evidence_hash from highest-confidence candidate ---
        best = max(live, key=lambda c: c.confidence)
        return ObservationCandidate(
            outcome=OUTCOME_OBSERVED,
            value=ref.value,
            confidence=max(c.confidence for c in live),
            source=";".join(c.source for c in live if c.source),
            single_source=False,
            detail="multi-source agreement (%d candidates)" % len(live),
            control_id=ref.control_id or requested_control_id,
            evidence_hash=best.evidence_hash,
        )

    return ObservationCandidate(
        outcome=OUTCOME_AMBIGUOUS,
        value=None,
        confidence=0.0,
        source=";".join(c.source for c in live if c.source),
        detail="split: %r" % [c.value for c in live],
    )
