"""The final producer-facing execution contract: rebuilt from committed evidence it must equal the committed file,
hold exactly 330 rows with the live v3 outcome verbatim, and keep raw-field vs host-parameter execution distinct."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_final_execution_contract_v1 as b  # noqa: E402

pytestmark = pytest.mark.skipif(not b.OUT_JSON.exists(), reason="final contract not present")


@pytest.fixture(scope="module")
def doc():
    return json.loads(b.OUT_JSON.read_text())


@pytest.fixture(scope="module")
def v3():
    return {r["atlas_id"]: r for r in b.load_jsonl(b.V3)}


def test_committed_file_matches_rebuild(doc):
    assert json.loads(json.dumps(b.build())) == doc
    assert b.report(doc) == b.OUT_MD.read_text()


def test_counts(doc):
    s = doc["summary"]
    assert s["total_controls"] == 330 and s["conforming_executable"] == 310
    assert (s[b.HOST], s[b.RAW], s[b.EXC]) == (183, 127, 20)
    assert s[b.FAILED] == 0 and s[b.NOOP] == 0
    assert s["restoration_verified"] == 330 and s["v3_vs_v2_identical"]


def test_rows_are_exactly_the_live_rows(doc, v3):
    ids = [r["atlas_id"] for r in doc["rows"]]
    assert len(ids) == len(set(ids)) == 330
    assert set(ids) == set(v3) == set(doc["producer_lookup"])
    for r in doc["rows"]:
        L = v3[r["atlas_id"]]
        assert r["final_execution_classification"] == L["outcome"]
        assert r["live_execution"]["leaves"] == L["q3_leaves"] and r["live_execution"]["q4"] == L["q4"]
        assert r["serum_binary_sha256"] == b.SERUM_SHA256 and r["serum_version"] == "2.0.23"
        assert r["restoration_verified"] is True


def test_cross_checks_against_contract_and_map(doc):
    c = {r["atlas_id"]: r for r in json.loads(b.CONTRACT.read_text())["rows"]}
    m = {r["atlas_id"]: r for r in json.loads(b.MAP_V8.read_text())["controls"]}
    for r in doc["rows"]:
        assert r["mcp_operation"]["edit"] == c[r["atlas_id"]]["mcp_edit"]
        assert r["expected_raw"] == c[r["atlas_id"]]["expected_raw"]
        assert r["semantic_identity"] == m[r["atlas_id"]]["semantic_field"]
        assert r["reference_conclusion"] == m[r["atlas_id"]]["final_conclusion"]


def test_raw_vs_host_distinction(doc):
    for r in doc["rows"]:
        cls = r["final_execution_classification"]
        if cls == b.RAW:
            assert not r["host_parameter_present"] and r["host_parameter_name"] is None
        if cls != b.HOST:
            assert r["execution_kind"] == "RAW_FIELD"
        if r["host_parameter_name"] is not None:
            assert r["host_parameter_name"] in r["live_execution"]["q4"]["changed_hosts"]


def test_exceptions_never_success(doc):
    exc = [r for r in doc["rows"] if r["final_execution_classification"] == b.EXC]
    assert sorted(r["atlas_id"] for r in exc) == doc["exceptions"] and len(exc) == 20
    for r in exc:
        assert r["exception"] and doc["producer_lookup"][r["atlas_id"]]["exception_policy"] != "NONE"
    for r in doc["rows"]:
        if r["final_execution_classification"] != b.EXC:
            assert r["exception"] is None
