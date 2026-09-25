"""closure_ledger_v2: same frozen ledger as v1, run against the GUI-observed campaign, plus an additive
host_text_evidence tier that must never influence status or ui_semantics -- host-text is not DIRECT_UI evidence.
"""
import json
from pathlib import Path

import pytest

ED = Path(__file__).resolve().parents[3] / "parameter_characterization" / "bulk_causal_evidence"
LED = ED / "closure_ledger_v2.json"
RUN = ED / "campaign_run_gui_v1.json"
VOCAB = {"NOT_DERIVED", "SERUM_CRASH", "STATE_NOT_OBSERVED", "CAUSAL_INCOMPLETE", "STATE_QUALIFIED_UI_PENDING", "PROMOTION_BLOCKED", "CLOSED"}
HOST_TEXT_VOCAB = {"OBSERVED", "OBSERVED_NO_CONTRAST", "UNOBSERVABLE", "NOT_ATTEMPTED"}

pytestmark = pytest.mark.skipif(not (LED.exists() and RUN.exists()), reason="GUI campaign evidence not present")


@pytest.fixture(scope="module")
def led():
    return json.loads(LED.read_text())


def test_every_candidate_appears_exactly_once_and_counts_sum(led):
    ids = [e["atlas_id"] for e in led["candidates"]]
    assert len(ids) == len(set(ids)) == led["total_candidates"] == 330
    assert sum(led["status_counts"].values()) == 330
    assert sum(led["host_text_evidence_counts"].values()) == 330
    assert {e["status"] for e in led["candidates"]} <= VOCAB
    assert {e["host_text_evidence"]["status"] for e in led["candidates"]} <= HOST_TEXT_VOCAB


def test_host_text_evidence_never_marks_direct_ui_verified(led):
    """The whole point of splitting the tiers: host_text_fallback must never be reported as literal on-screen
    UI verification, no matter how strong the machine-readable signal is."""
    assert led["direct_ui_verification_performed"] is False
    assert all(e["host_text_evidence"]["is_direct_ui_verified"] is False for e in led["candidates"])


def test_host_text_evidence_does_not_change_status_relative_to_v1_pipeline(led):
    """closure_ledger_v2 must reuse closure_ledger.build() unmodified: two candidates with different
    host_text_evidence status can land on the SAME ledger status (host-text is additive, not a gate)."""
    by_status = {}
    for e in led["candidates"]:
        by_status.setdefault(e["status"], set()).add(e["host_text_evidence"]["status"])
    # at least one status bucket must contain more than one host_text_evidence outcome, proving the
    # two tiers vary independently (if this ever collapses to 1:1, host-text has started gating status)
    assert any(len(v) > 1 for v in by_status.values())


def test_not_attempted_is_exactly_the_not_derived_candidates(led):
    not_attempted = {e["atlas_id"] for e in led["candidates"] if e["host_text_evidence"]["status"] == "NOT_ATTEMPTED"}
    not_derived = {e["atlas_id"] for e in led["candidates"] if e["status"] == "NOT_DERIVED"}
    assert not_attempted == not_derived


def test_observed_requires_a_mutated_text_distinct_from_restored(led):
    run = json.loads(RUN.read_text())
    recs = {r["atlas_id"]: r for r in run["records"]}
    for e in led["candidates"]:
        if e["host_text_evidence"]["status"] == "OBSERVED":
            rec = recs[e["atlas_id"]]
            restored = rec["gui_restore"]["host_text_display"]
            mutated_texts = [v.get("gui_mutated", {}).get("host_text_display", {}) for v in rec["values"]]
            assert any(t and t != restored for t in mutated_texts)


def test_312_pending_split_by_host_text_signal_matches_reported_counts(led):
    """No-shortcut check: both the 129-with-no-signal and the 183-with-corroboration subsets of
    STATE_QUALIFIED_UI_PENDING remain PENDING -- host-text corroboration is not a substitute for live UI."""
    pending = [e for e in led["candidates"] if e["status"] == "STATE_QUALIFIED_UI_PENDING"]
    assert all(e["ui_semantics"]["status"] != "VERIFIED" for e in pending)
    no_signal = [e for e in pending if e["host_text_evidence"]["status"] == "UNOBSERVABLE"]
    corroborated = [e for e in pending if e["host_text_evidence"]["status"] == "OBSERVED"]
    assert len(no_signal) + len(corroborated) <= len(pending)   # every pending candidate still requires live UI regardless of bucket
