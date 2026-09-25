"""merge_range is pure: it must flag GUI-vs-state disagreements and stay quiet when they agree."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from merge_range import analyse  # noqa: E402

ED = HERE.parents[2] / "parameter_characterization" / "bulk_causal_evidence"


def rec(pairs):
    return {"observations": {str(w): {"written": w, "state_value": s} for w, s in pairs}}


def rows(triples):
    return [{"written": w, "kind": k, "displayed_value": d, "unit": "u"} for w, k, d in triples]


def test_clamp_that_the_ui_shows_is_consistent():
    r = analyse(rec([(0.0, 0.0), (1.0, 1.0), (1.5, 1.0)]), rows([(None, "reference", 5), (0.0, "value", 0), (1.0, "value", 10), (1.5, "probe", 10)]))
    assert r["status"] == "DISPLAY_CONSISTENT" and r["default_display"] == 5 and r["effective_display_range"] == [0, 10]


def test_ui_beyond_state_clamp_is_flagged_R1():
    r = analyse(rec([(0.0, 0.0), (1.0, 1.0), (1.5, 1.0)]), rows([(0.0, "value", 0), (1.0, "value", 10), (1.5, "probe", 15)]))
    assert r["status"] == "GUI_DISAGREES_WITH_STATE_READBACK" and r["violations"][0]["rule"] == "R1"


def test_non_monotonic_display_is_flagged_R2():
    r = analyse(rec([(0.5, None), (1.0, None), (5.0, 5.0)]), rows([(0.5, "probe", 30), (1.0, "value", 0), (5.0, "value", 30)]))
    assert any(v["rule"] == "R2" for v in r["violations"])


@pytest.mark.skipif(not (ED / "gui_range_merge_v1.json").exists(), reason="range merge not present")
def test_fx_range_merge_findings():
    d = json.loads((ED / "gui_range_merge_v1.json").read_text())["tests"]
    assert d["range_eq_freq1"]["effective_display_range"] == [22, 20000]      # schema said max 10000
    assert d["range_eq_reso2"]["effective_display_range"] == [0, 100] and d["range_eq_reso2"]["default_display"] == 60
    assert d["range_dist_freq"]["status"] == "GUI_DISAGREES_WITH_STATE_READBACK" and d["range_dist_freq"]["effective_display_range"] == [8, 22050]
    assert d["range_comp_makeup"]["status"] == "GUI_DISAGREES_WITH_STATE_READBACK"
    assert d["range_dist_numstages"]["default_display"] == 1                   # schema said default/min 2


@pytest.mark.skipif(not (ED / "gui_osc_merge_v1.json").exists(), reason="osc GUI merge not present")
def test_oscillator_gui_agrees_with_state_readback_and_confirms_ranges():
    d = json.loads((ED / "gui_osc_merge_v1.json").read_text())["tests"]
    assert len(d) == 8 and all(v["status"] == "DISPLAY_CONSISTENT" for v in d.values())
    assert d["oscA.coarse_pitch"]["effective_display_range"] == [-64, 64]        # schema declared +-72
    assert d["oscA.fine"]["effective_display_range"][1] == 100                   # schema declared 80
    assert d["oscA.initial_phase"]["default_display"] == 180 and d["oscA.random_phase"]["default_display"] == 100  # schema defaults said 0
    assert d["oscA.unison"]["default_display"] == 1 and d["oscA.enabled"]["default_display"] == 1
