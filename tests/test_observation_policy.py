"""C1 Observation Policy: adjudicate() agree/disagree/single-source cases.

No Qwen API calls. Pure logic tests for the adjudication policy.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from serum2.producer.observation_policy import (
    ObservationCandidate, adjudicate,
    OUTCOME_CANDIDATE, OUTCOME_OBSERVED, OUTCOME_AMBIGUOUS, OUTCOME_UNREADABLE,
    CONFIDENT_THRESHOLD,
)


def _cand(value, confidence=0.95, source="vlm", outcome=OUTCOME_CANDIDATE):
    return ObservationCandidate(outcome=outcome, value=value, confidence=confidence, source=source)


def test_empty_candidates_returns_unreadable():
    r = adjudicate([])
    assert r.outcome == OUTCOME_UNREADABLE


def test_all_unreadable_returns_unreadable():
    r = adjudicate([ObservationCandidate(outcome=OUTCOME_UNREADABLE), ObservationCandidate(outcome=OUTCOME_UNREADABLE)])
    assert r.outcome == OUTCOME_UNREADABLE


def test_single_high_confidence_is_ambiguous_not_observed():
    # GAP B fix: single source, even above threshold, requires corroboration.
    r = adjudicate([_cand(1.5, confidence=0.95)])
    assert r.outcome == OUTCOME_AMBIGUOUS
    assert r.value == 1.5
    assert r.single_source is True


def test_single_low_confidence_is_ambiguous():
    r = adjudicate([_cand(1.5, confidence=0.7)])
    assert r.outcome == OUTCOME_AMBIGUOUS
    assert r.single_source is True


def test_two_candidates_agree_numeric():
    r = adjudicate([_cand(300.0, source="vlm"), _cand(300.0, source="ocr")])
    assert r.outcome == OUTCOME_OBSERVED
    assert r.value == 300.0
    assert r.single_source is False


def test_two_candidates_agree_within_tol():
    r = adjudicate([_cand(300.001, source="vlm"), _cand(300.0, source="ocr")], numeric_tol=1e-2)
    assert r.outcome == OUTCOME_OBSERVED


def test_two_candidates_disagree_numeric():
    r = adjudicate([_cand(300.0, source="vlm"), _cand(400.0, source="ocr")])
    assert r.outcome == OUTCOME_AMBIGUOUS
    assert r.value is None


def test_two_candidates_agree_string():
    r = adjudicate([_cand("Saw", source="vlm"), _cand("Saw", source="ocr")])
    assert r.outcome == OUTCOME_OBSERVED
    assert r.value == "Saw"


def test_two_candidates_disagree_string():
    r = adjudicate([_cand("Saw", source="vlm"), _cand("Square", source="ocr")])
    assert r.outcome == OUTCOME_AMBIGUOUS


def test_three_candidates_all_agree():
    r = adjudicate([_cand(1.0, source="vlm"), _cand(1.0, source="ocr"), _cand(1.0, source="frame2")])
    assert r.outcome == OUTCOME_OBSERVED
    assert r.value == 1.0
    assert r.single_source is False


def test_three_candidates_mixed_agreement():
    r = adjudicate([_cand(1.0, source="vlm"), _cand(1.0, source="ocr"), _cand(2.0, source="frame2")])
    assert r.outcome == OUTCOME_AMBIGUOUS


def test_max_confidence_taken_from_agreeing_candidates():
    r = adjudicate([_cand(1.0, confidence=0.8, source="vlm"), _cand(1.0, confidence=0.95, source="ocr")])
    assert r.outcome == OUTCOME_OBSERVED
    assert r.confidence == 0.95


def test_source_string_joins_agreeing_sources():
    r = adjudicate([_cand(1.0, source="vlm"), _cand(1.0, source="ocr")])
    assert "vlm" in r.source and "ocr" in r.source


def test_single_below_threshold_is_ambiguous_not_unreadable():
    r = adjudicate([_cand(1.0, confidence=CONFIDENT_THRESHOLD - 0.01)])
    assert r.outcome == OUTCOME_AMBIGUOUS


def test_single_at_threshold_is_ambiguous_not_observed():
    # GAP B fix: even exactly at threshold, single source is not sufficient.
    r = adjudicate([_cand(1.0, confidence=CONFIDENT_THRESHOLD)])
    assert r.outcome == OUTCOME_AMBIGUOUS
    assert r.single_source is True
