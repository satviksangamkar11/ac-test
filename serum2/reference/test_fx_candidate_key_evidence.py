"""The FX candidate-key evidence survey is read-only: it must never leak a candidate into the binding table."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "parameter_characterization" / "fx_candidate_key_evidence.json"
BINDINGS = Path(__file__).parent / "serum_mcp_binding_table.json"
TIERS = {"T1_RULE_GAP", "T2_EXACT_UNCATALOGUED", "T3_STRONG", "T4_WEAK", "T5_NO_KEY", "NOT_A_PARAM"}

pytestmark = pytest.mark.skipif(not ART.exists(), reason="evidence artifact not generated")


@pytest.fixture(scope="module")
def art():
    return json.loads(ART.read_text())


def test_binds_nothing_and_binding_table_unchanged(art):
    bt = json.loads(BINDINGS.read_text())["controls"]
    assert art["binds_nothing"] is True and len(bt) == 330
    assert not set(art["controls"]) & set(bt)  # every reviewed control is still unbound


def test_tiers_are_valid_and_no_key_rows_have_no_candidate(art):
    for cid, r in art["controls"].items():
        assert r["tier"] in TIERS, cid
        if r["tier"] in ("T5_NO_KEY", "NOT_A_PARAM"):
            assert not r["candidate_kparam"], cid
        else:
            assert r["candidate_kparam"] and r["evidence_or_gap"], cid


def test_corpus_counts_are_consistent(art):
    for cid, r in art["controls"].items():
        n, tot = r["corpus_units_with_key"], r["corpus_units_of_type"]
        if n is not None and tot:
            assert 0 <= n <= tot, cid
