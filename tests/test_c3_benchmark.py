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


def test_real_high_confidence_correct_vlm_is_now_ambiguous_single_source():
    """GAP B remediation: the real case where Qwen was correct and confident (CAL_06,
    0.944 confidence) now returns AMBIGUOUS because it is a single source with no
    independent corroboration (OCR unavailable). The value is preserved in the result
    (value=1.0) but the outcome is AMBIGUOUS, not OBSERVED.
    Correctness + high confidence is necessary but not sufficient; corroboration is
    required before a reading can be mutation-authorizing."""
    cases = {c["case_id"]: c for c in build_real_cases()}
    row = run_real_case(cases["real_cal06_env1_decay"], ObservationEngine())
    assert row["adjudicated_outcome"] == OUTCOME_AMBIGUOUS
    assert row["confident_wrong"] is False
    assert row["abstained"] is True


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


def test_synthetic_single_confident_wrong_source_is_now_ambiguous():
    """GAP B remediation: a single source above CONFIDENT_THRESHOLD now returns
    AMBIGUOUS (corroboration required), not OBSERVED. The confident-wrong outcome
    no longer occurs for single-source cases -- multi-source agreement is required
    for OBSERVED. This is the C3 remediation fix for the single-source gap.
    See c3_report.md for the original gap description."""
    cases = {c["case_id"]: c for c in build_synthetic_cases()}
    row = run_synthetic_case(cases["synthetic_wrong_vlm_high_confidence"])
    assert row["adjudicated_outcome"] == OUTCOME_AMBIGUOUS
    assert row["confident_wrong"] is False
    assert row["abstained"] is True


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
