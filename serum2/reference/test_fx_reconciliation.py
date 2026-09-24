"""FX reconciliation pass: 29/29 accounted for, nothing silently promoted, existing bindings untouched."""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "parameter_characterization" / "fx_reconciliation_pass.json"
BINDINGS = Path(__file__).parent / "serum_mcp_binding_table.json"
ALLOWED = {"DIRECT_BIND", "STRUCTURAL", "UI_ONLY", "BROWSER_EXTERNAL", "UNRESOLVED"}

pytestmark = pytest.mark.skipif(not ART.exists(), reason="fx reconciliation artifact not generated")


@pytest.fixture(scope="module")
def art():
    return json.loads(ART.read_text())


def test_all_29_accounted_for_with_one_allowed_disposition(art):
    assert art["total"] == 29 == len(art["controls"])
    assert {r["disposition"] for r in art["controls"].values()} <= ALLOWED
    assert sum(art["counts"].values()) == 29


def test_scope_is_exactly_the_registry_fx_unknowns(art):
    reg = json.loads((ROOT / "parameter_characterization" / "serum2_master_parameter_registry.json").read_text())
    want = {k for k, v in reg["canonical_registry"].items() if v["section"] == "FX" and v["disposition"] == "UNKNOWN"}
    assert set(art["controls"]) == want


def test_no_new_bindings_and_binding_table_unchanged(art):
    bt = json.loads(BINDINGS.read_text())
    assert art["newly_direct_bound"] == 0
    assert len(bt["controls"]) == 330 and bt["unbound_atlas_ids"] == 567
    fx = [c for c in bt["controls"] if c.startswith("fx.")]
    assert len(fx) == 59
    for cid, r in art["controls"].items():
        assert r["newly_bound"] is False
        if r["disposition"] != "DIRECT_BIND":
            assert cid not in bt["controls"], cid  # nothing silently supported


def test_unresolved_controls_state_exact_missing_evidence(art):
    for cid, r in art["controls"].items():
        if r["disposition"] == "UNRESOLVED":
            assert r["missing_evidence"], cid


def test_offline_write_checks_are_transport_only_and_restore_cleanly(art):
    for c in art["offline_write_introspection_checks"]:
        assert c["raw_keys_changed"] == [c["kparam"]]
        assert c["survives_pack_unpack_introspect"] and c["restoration_matches_baseline"]
