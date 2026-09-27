"""C3 regression tests.

Locks in adjudication behavior for the C3 benchmark's synthetic adversarial cases
(deterministic, no GPU/model needed) and re-derives the real-case rows from the
already-committed W1 ground truth + stored real VLM outputs (no model re-invocation,
no Serum interaction). Does not touch the mutation pipeline -- this is diagnostic-only
coverage for serum2/producer/c3_benchmark/run_c3_benchmark.py.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from serum2.producer.c3_benchmark.run_c3_benchmark import (
    build_real_cases, build_synthetic_cases, run_real_case, run_synthetic_case,
)
from serum2.producer.observation_engine import ObservationEngine
from serum2.producer.observation_policy import OUTCOME_OBSERVED, OUTCOME_AMBIGUOUS, OUTCOME_UNREADABLE


def test_real_high_confidence_correct_vlm_is_observed_and_exact():
    """The one real case where Qwen was both correct and confident must be admitted."""
    cases = {c["case_id"]: c for c in build_real_cases()}
    row = run_real_case(cases["real_cal06_env1_decay"], ObservationEngine())
    assert row["adjudicated_outcome"] == OUTCOME_OBSERVED
    assert row["exact_match"] is True
    assert row["confident_wrong"] is False


def test_real_low_confidence_wrong_vlm_abstains_not_confident_wrong():
    """The real case where Qwen was wrong AND appropriately low-confidence must abstain,
    not become a confident-wrong observation -- this is the core safety property."""
    cases = {c["case_id"]: c for c in build_real_cases()}
    row = run_real_case(cases["real_bulk01_env1_decay"], ObservationEngine())
    assert row["adjudicated_outcome"] in (OUTCOME_AMBIGUOUS, OUTCOME_UNREADABLE)
    assert row["confident_wrong"] is False
    assert row["exact_match"] is False


def test_real_missing_evidence_case_is_unreadable_not_fabricated():
    cases = {c["case_id"]: c for c in build_real_cases()}
    row = run_real_case(cases["real_missing_filter1_cutoff_tooltip"], ObservationEngine())
    assert row["ground_truth_readable"] is False
    assert row["adjudicated_outcome"] == OUTCOME_UNREADABLE
    assert row["adjudicated_value"] is None
    assert row["abstained"] is True


def test_synthetic_ambiguous_split_sources_abstain():
    cases = {c["case_id"]: c for c in build_synthetic_cases()}
    row = run_synthetic_case(cases["synthetic_ambiguous_numeric_split"])
    assert row["adjudicated_outcome"] == OUTCOME_AMBIGUOUS
    assert row["exact_match"] is False
    assert row["confident_wrong"] is False


def test_synthetic_disagreeing_sources_never_silently_pick_one():
    cases = {c["case_id"]: c for c in build_synthetic_cases()}
    row = run_synthetic_case(cases["synthetic_wrong_ocr_correct_vlm_agree_fails"])
    assert row["adjudicated_outcome"] == OUTCOME_AMBIGUOUS


def test_synthetic_single_confident_wrong_source_IS_admitted_known_gap():
    """Documents a real, unresolved gap: a single source above CONFIDENT_THRESHOLD is
    admitted as OBSERVED regardless of correctness -- the policy has no independent way
    to detect it's wrong. This is why C3 is NOT integrated into the mutation pipeline.
    If this test starts failing (i.e. the policy starts abstaining here), the integration
    decision in c3_report.md should be revisited -- it would mean the risk got smaller,
    not that it's automatically now safe to wire in."""
    cases = {c["case_id"]: c for c in build_synthetic_cases()}
    row = run_synthetic_case(cases["synthetic_wrong_vlm_high_confidence"])
    assert row["adjudicated_outcome"] == OUTCOME_OBSERVED
    assert row["confident_wrong"] is True


def test_synthetic_agreeing_correct_sources_observed():
    cases = {c["case_id"]: c for c in build_synthetic_cases()}
    row = run_synthetic_case(cases["synthetic_correct_unit_format_difference"])
    assert row["adjudicated_outcome"] == OUTCOME_OBSERVED
    assert row["exact_match"] is True


def test_synthetic_boolean_state_agreement_observed():
    cases = {c["case_id"]: c for c in build_synthetic_cases()}
    row = run_synthetic_case(cases["synthetic_boolean_state_agree"])
    assert row["adjudicated_outcome"] == OUTCOME_OBSERVED
    assert row["adjudicated_value"] == "ON"


def test_synthetic_all_unreadable_sources_stay_unreadable_never_fabricated():
    cases = {c["case_id"]: c for c in build_synthetic_cases()}
    row = run_synthetic_case(cases["synthetic_all_sources_unreadable"])
    assert row["adjudicated_outcome"] == OUTCOME_UNREADABLE
    assert row["adjudicated_value"] is None


def test_synthetic_low_confidence_correct_value_still_abstains():
    """Correctness alone is not sufficient -- low confidence must still abstain."""
    cases = {c["case_id"]: c for c in build_synthetic_cases()}
    row = run_synthetic_case(cases["synthetic_low_confidence_single_source_correct_value"])
    assert row["adjudicated_outcome"] == OUTCOME_AMBIGUOUS
    assert row["exact_match"] is False


def test_pass_fail_never_keyed_on_literal_unreadable_string():
    """Regression for the known benchmark-design flaw: correctness must derive from
    structured outcome + value comparison, never from the mere presence of the word
    'UNREADABLE' anywhere in a result."""
    cases = {c["case_id"]: c for c in build_synthetic_cases()}
    row = run_synthetic_case(cases["synthetic_all_sources_unreadable"])
    # A case being UNREADABLE must not, by itself, count as exact_match or count as "safe".
    assert row["exact_match"] is False
    assert "UNREADABLE" not in str(row["exact_match"])
