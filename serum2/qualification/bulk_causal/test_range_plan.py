"""Range Test Plan generation + range characterization are pure and generic (no per-parameter code)."""
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from classify import classify  # noqa: E402
from range_plan import characterize, plan  # noqa: E402

RANGE_EVID = HERE.parents[2] / "parameter_characterization" / "bulk_causal_evidence" / "fx_range_v1.json"


def test_plans_per_kind():
    assert plan({"kind": "bool"})["values"] == [0.0, 1.0]
    e = plan({"kind": "enum", "values": [0, 1, 2]})
    assert e["values"] == [0.0, 1.0, 2.0] and e["probes"] == [3.0]
    i = plan({"kind": "int", "min": 0, "max": 127})
    assert i["values"][0] == 0 and i["values"][-1] == 127 and 128.0 in i["probes"]
    c = plan({"kind": "continuous", "min": 0.0, "max": 1.0})
    assert c["values"] == [0.0, .25, .5, .75, 1.0]
    s = plan({"kind": "signed", "min": -1.0, "max": 1.0})
    assert s["values"] == [-1.0, -.5, 0.0, .5, 1.0]


def test_log_domain_is_geometric_not_arithmetic():
    v = plan({"kind": "log", "min": 20.0, "max": 20000.0})["values"]
    assert v[0] == 20.0 and v[-1] == 20000.0
    ratios = [b / a for a, b in zip(v, v[1:])]
    assert max(ratios) - min(ratios) < 1e-9          # constant ratio
    assert v[2] == pytest.approx(632.4555, rel=1e-4)  # geometric midpoint, not 10010
    with pytest.raises(ValueError):
        plan({"kind": "log", "min": 0.0, "max": 10.0})


def obs(pairs, probe_from):
    return {str(w): {"written": w, "state_value": s, "probe": w >= probe_from} for w, s in pairs}


def test_characterize_separates_declared_from_reachable_and_finds_default():
    # declared [0,10]; Serum clamps 12->10, omits 5 (=> default 5)
    r = characterize({"kind": "continuous", "min": 0.0, "max": 10.0}, obs([(0.0, 0.0), (5.0, None), (10.0, 10.0), (12.0, 10.0)], 12.0))
    assert r["discovered_default"] == 5.0 and r["clamp_high_at"] == 10.0 and r["declared_matches_reachable"]


def test_characterize_flags_schema_narrower_than_serum():
    r = characterize({"kind": "continuous", "min": 0.0, "max": 95.0}, obs([(0.0, 0.0), (95.0, 95.0), (104.5, 100.0)], 104.5))
    assert r["clamp_high_at"] == 100.0 and not r["declared_matches_reachable"]


def test_probe_absent_on_default_boundary_is_a_clamp_not_a_drop():
    r = characterize({"kind": "continuous", "min": 1.0, "max": 32.0}, obs([(1.0, None), (32.0, 31.0), (0.9, None)], 32.0))
    assert r["discovered_default"] == 1.0 and r["probes_dropped"] == []


def test_range_purpose_status_and_restore_gate():
    base = {"purpose": "range", "baseline": {"band_db": [0]}, "file_roundtrip": {"ok": True},
            "observations": {"1.0": {"state_retained": True, "band_db": [0]}}}
    assert classify({**base, "restoration": {"ok": True}})["status"] == "RANGE_CHARACTERIZED"
    assert classify({**base, "restoration": {"ok": False, "detail": "x"}})["status"] == "RESTORE_FAILED"


@pytest.mark.skipif(not RANGE_EVID.exists(), reason="range evidence not present")
def test_fx_range_evidence_is_restored_and_rederivable():
    d = json.loads(RANGE_EVID.read_text())
    assert len(d["records"]) == 18
    for r in d["records"]:
        assert r["status"] == "RANGE_CHARACTERIZED" and r["restoration"]["ok"], r["id"]
        assert characterize(r["domain"], r["observations"]) == r["range"], r["id"]  # stored fingerprint re-derives from raw observations
    by = {r["id"]: r["range"] for r in d["records"]}
    assert by["range_eq_type1"]["clamp_high_at"] == 2.0                       # 3.0 clamps to 2.0 (three states)
    assert by["range_eq_freq1"]["clamp_high_at"] == 20000.0                   # schema said 10000
    assert by["range_eq_reso2"]["clamp_high_at"] == 100.0                     # schema said 95
    assert by["range_dist_drive"]["discovered_default"] == 25.0               # schema default said 50
