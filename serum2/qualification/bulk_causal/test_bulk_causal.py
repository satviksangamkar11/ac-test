"""classify.py is pure; the FX evidence artifact must be internally consistent and the harness controls must behave."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from classify import classify  # noqa: E402

EVID = HERE.parents[2] / "parameter_characterization" / "bulk_causal_evidence" / "fx_verify_v1.json"


def rec(deltas, retained=True, restored=True, rt=True, expect=(), floor=0.5, probe=False):
    base = [50.0] * 5
    return {"baseline": {"band_db": base}, "noise_floor_db": floor, "expect": list(expect),
            "restoration": {"ok": restored, "detail": "x"}, "file_roundtrip": {"ok": rt},
            "observations": {"1.0": {"state_retained": retained, "probe": probe, "band_db": [b + d for b, d in zip(base, deltas)]}}}


E1 = {"value": "1.0", "band": 0, "relation": "increase_db", "threshold": 6}


def test_every_status_is_reachable():
    assert classify(rec([9, 0, 0, 0, 0], expect=[E1]))["status"] == "PROVEN"
    assert classify(rec([1, 0, 0, 0, 0], expect=[E1]))["status"] == "FAILED"
    assert classify(rec([9, 0, 0, 0, 0]))["status"] == "AMBIGUOUS"
    assert classify(rec([0.1, 0, 0, 0, 0]))["status"] == "NOT_OBSERVED"
    assert classify(rec([9, 0, 0, 0, 0], retained=False, expect=[E1]))["status"] == "REJECTED"
    assert classify(rec([9, 0, 0, 0, 0], restored=False, expect=[E1]))["status"] == "RESTORE_FAILED"


def test_lost_file_roundtrip_blocks_proven():
    assert classify(rec([9, 0, 0, 0, 0], rt=False, expect=[E1]))["status"] == "FAILED"


def test_vs_compares_two_written_values():
    r = rec([0, 0, 0, 0, 0])
    r["observations"]["2.0"] = {"state_retained": True, "band_db": [50.0, 50.0, 50.0, 50.0, 30.0]}
    e = {"value": "2.0", "vs": "1.0", "band": 4, "relation": "decrease_db", "threshold": 10}
    assert classify({**r, "expect": [e]})["status"] == "PROVEN"


@pytest.mark.skipif(not EVID.exists(), reason="FX evidence not present")
def test_fx_evidence_is_consistent_and_controls_behave():
    d = json.loads(EVID.read_text())
    assert d["harness"]["authorizes_nothing"] is True and d["harness"]["product_version"] == "2.0.23"
    by = {r["id"]: r for r in d["records"]}
    assert by["ctl_positive_filter_cutoff"]["status"] == "PROVEN"      # harness can say yes
    assert by["ctl_negative_bogus_key"]["status"] == "REJECTED"        # ...and no
    for r in d["records"]:
        assert r["restoration"]["ok"], r["id"]                          # no contaminated session
        assert classify(r)["status"] == r["status"], r["id"]           # stored status re-derives from raw observations
    for cid in ("eq_left_type", "eq_right_type", "comp_multiband_mode", "dist_prepost_lowpass_drive80", "dist_prepost_lowpass_drive0"):
        assert by[cid]["status"] == "PROVEN", cid
