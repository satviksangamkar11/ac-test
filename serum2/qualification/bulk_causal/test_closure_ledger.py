"""The 330-candidate closure ledger: every candidate exactly once, statuses only move up on evidence, crashes are never hidden."""
import json
from pathlib import Path

import pytest

ED = Path(__file__).resolve().parents[3] / "parameter_characterization" / "bulk_causal_evidence"
LED = ED / "closure_ledger_v1.json"
RUN = ED / "campaign_run_v1.json"
VOCAB = {"NOT_DERIVED", "SERUM_CRASH", "STATE_NOT_OBSERVED", "CAUSAL_INCOMPLETE", "STATE_QUALIFIED_UI_PENDING", "PROMOTION_BLOCKED", "CLOSED"}

pytestmark = pytest.mark.skipif(not (LED.exists() and RUN.exists()), reason="campaign evidence not present")


@pytest.fixture(scope="module")
def led():
    return json.loads(LED.read_text())


def test_every_candidate_appears_exactly_once_and_counts_sum(led):
    ids = [e["atlas_id"] for e in led["candidates"]]
    assert len(ids) == len(set(ids)) == led["total_candidates"] == 330
    assert sum(led["status_counts"].values()) == 330
    assert {e["status"] for e in led["candidates"]} <= VOCAB


def test_closed_requires_every_gate(led):
    for e in led["candidates"]:
        if e["status"] == "CLOSED":
            assert e["ui_semantics"]["status"] == "VERIFIED" and e["promotion_dry_run"]["promoted"] and not e["blocked_by"]
            assert e["causal"]["restoration"] and e["causal"]["file_roundtrip"]
        if e["status"] == "STATE_QUALIFIED_UI_PENDING":
            assert e["ui_semantics"]["status"] != "VERIFIED"      # never pending once the UI is verified, never closed without it
        if e["status"] in ("NOT_DERIVED", "SERUM_CRASH", "STATE_NOT_OBSERVED"):
            assert e.get("reason")


def test_serum_crashes_are_recorded_not_hidden(led):
    run = json.loads(RUN.read_text())
    crashes = {c["atlas_id"] for c in run["harness"]["serum_crashes"]}
    assert crashes and crashes == {e["atlas_id"] for e in led["candidates"] if e["status"] == "SERUM_CRASH"}
    assert all(e["needs"] for e in led["candidates"] if e["status"] == "SERUM_CRASH")


def test_run_accounts_for_every_derived_parameter():
    run = json.loads(RUN.read_text())
    accounted = {r["atlas_id"] for r in run["records"]} | {c["atlas_id"] for c in run["harness"]["serum_crashes"]}
    manifest = json.loads((Path(__file__).resolve().parent / "manifest_campaign_v1.json").read_text())
    assert accounted == {p["atlas_id"] for p in manifest["parameters"]}
    assert all(r["restoration"]["ok"] for r in run["records"])          # no contaminated session anywhere in the run
