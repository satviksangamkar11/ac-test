"""closure_ledger_v3: v2 carried verbatim + an additive direct_ui_evidence tier. DIRECT_UI and host-text stay separate,
and neither changes status."""
import json
from pathlib import Path

import pytest

ED = Path(__file__).resolve().parents[3] / "parameter_characterization" / "bulk_causal_evidence"
V3, V2, UI = ED / "closure_ledger_v3.json", ED / "closure_ledger_v2.json", ED / "direct_ui_evidence_v2.json"
UI_VOCAB = {"UI_CONFIRMED", "UI_PLAUSIBLE", "UI_MISMATCH", "UI_CONTEXT_CONFLICT", "UI_VOCABULARY_MISMATCH", "UI_VOCABULARY_DISCOVERED",
            "UI_NOT_OBSERVABLE_IN_CONTEXT", "UI_CURVE_UNVERIFIED", "UI_OBSERVED_NO_TARGET", "UI_NOT_SCANNED"}

pytestmark = pytest.mark.skipif(not (V3.exists() and V2.exists() and UI.exists()), reason="ledger evidence not present")


@pytest.fixture(scope="module")
def v3():
    return json.loads(V3.read_text())


@pytest.fixture(scope="module")
def ui(v3):
    return {e["atlas_id"]: e["direct_ui_evidence"] for e in v3["candidates"]}


def test_v2_fields_carried_verbatim(v3):
    v2 = {e["atlas_id"]: e for e in json.loads(V2.read_text())["candidates"]}
    assert len(v3["candidates"]) == len(v2) == v3["total_candidates"] == 330
    for e in v3["candidates"]:
        assert {k: v for k, v in e.items() if k != "direct_ui_evidence"} == v2[e["atlas_id"]]
    assert v3["status_changed_by_direct_ui"] is False


def test_tiers_are_separate(v3):
    for e in v3["candidates"]:
        assert e["direct_ui_evidence"]["status"] in UI_VOCAB
        assert e["host_text_evidence"]["is_direct_ui_verified"] is False      # host text never counts as screen evidence
        d = e["direct_ui_evidence"]
        if d["status"] != "UI_NOT_SCANNED":
            assert d["observation_method"] == "direct_ui_screen_scan"
        assert d["is_direct_ui_verified"] == (d["status"] == "UI_CONFIRMED")
    assert sum(v3["direct_ui_evidence_counts"].values()) == 330
    # the two tiers vary independently: some UI outcome co-occurs with more than one host-text outcome
    pairs = {}
    for e in v3["candidates"]:
        pairs.setdefault(e["direct_ui_evidence"]["status"], set()).add(e["host_text_evidence"]["status"])
    assert any(len(s) > 1 for s in pairs.values())


def test_2026_09_26_rescan_findings(ui):
    for i in range(1, 7):
        d = ui["lfo%d.mode" % i]
        assert d["status"] == "UI_CONTEXT_CONFLICT" and d["conflicts_with"] == "lfo%d.shape" % i
        assert [x["verdict"] for x in d["isolation_evidence"]] == ["MATCH", "MATCH"]
    assert ui["fx.compressor.release"]["status"] == "UI_CONFIRMED"
    assert ui["fx.compressor.attack"]["status"] == ui["fx.compressor.gain"]["status"] == "UI_MISMATCH"
    assert ui["fx.reverb.type"]["status"] == "UI_VOCABULARY_MISMATCH"
    assert ui["arp.transpose.shape"]["status"] == "UI_VOCABULARY_DISCOVERED" and len(ui["arp.transpose.shape"]["display_vocabulary"]) == 18
    for o in "ABC":
        for f in ("warp_amount", "warp_mode", "warp_mode2", "warp_var2"):
            assert ui["osc%s.%s" % (o, f)]["status"] == "UI_NOT_OBSERVABLE_IN_CONTEXT"


def test_mismatch_set_is_exactly_the_open_findings(ui):
    assert {a for a, d in ui.items() if d["status"] == "UI_MISMATCH"} == {
        "env1.sustain", "env2.sustain", "env3.sustain", "env4.sustain",
        "fx.compressor.attack", "fx.compressor.gain", "fx.compressor.ratio"}
