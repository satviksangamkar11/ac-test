"""Evidence policy: how VLM / OCR readings become terminal observations.

A numeric reading becomes OBSERVED only when:
  - Both VLM and OCR agree (within a tolerance), OR
  - >= 2 independent frame-group agreements exist.
Otherwise it stays AMBIGUOUS or UNREADABLE.
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

CONFIDENT_THRESHOLD = 0.9


@dataclass
class ObservationCandidate:
    outcome: str
    value: Any = None
    confidence: float = 0.0
    source: str = ""
    single_source: bool = False
    detail: Optional[str] = None


def _values_agree(a: Any, b: Any, numeric_tol: float) -> bool:
    if a is None or b is None:
        return False
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= numeric_tol
    return a == b


def adjudicate(candidates: List[ObservationCandidate], *, numeric_tol: float = 1e-3) -> ObservationCandidate:
    """Given N candidates from independent sources (VLM, OCR, multiple frames),
    return the adjudicated result: OBSERVED if agreement, AMBIGUOUS if split,
    UNREADABLE if all failed."""
    live = [c for c in candidates if c.outcome == OUTCOME_CANDIDATE]

    if not live:
        return ObservationCandidate(outcome=OUTCOME_UNREADABLE, detail="all candidates unreadable")

    if len(live) == 1:
        c = live[0]
        if c.confidence >= CONFIDENT_THRESHOLD:
            return ObservationCandidate(
                outcome=OUTCOME_OBSERVED,
                value=c.value,
                confidence=c.confidence,
                source=c.source,
                single_source=True,
                detail="single source admitted (confidence >= %.2f)" % CONFIDENT_THRESHOLD,
            )
        return ObservationCandidate(
            outcome=OUTCOME_AMBIGUOUS,
            value=c.value,
            confidence=c.confidence,
            source=c.source,
            detail="single source below confidence threshold (%.3f < %.2f)" % (c.confidence, CONFIDENT_THRESHOLD),
        )

    ref = live[0]
    all_agree = all(_values_agree(c.value, ref.value, numeric_tol) for c in live[1:])
    if all_agree:
        return ObservationCandidate(
            outcome=OUTCOME_OBSERVED,
            value=ref.value,
            confidence=max(c.confidence for c in live),
            source=";".join(c.source for c in live if c.source),
            single_source=False,
            detail="multi-source agreement (%d candidates)" % len(live),
        )

    return ObservationCandidate(
        outcome=OUTCOME_AMBIGUOUS,
        value=None,
        confidence=0.0,
        source=";".join(c.source for c in live if c.source),
        detail="split: %r" % [c.value for c in live],
    )
