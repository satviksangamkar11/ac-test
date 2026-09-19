"""U8: every observed change ends at an explicit terminal layer -- nothing is silently dropped."""
from types import SimpleNamespace

from serum2.producer.u8_event_audit import ADMITTED, NO_OPERATION, audit_events


def ev(changes=(), new_routes=()):
    diff = {"changed_controls": [{"control_id": c, "before": b, "after": a} for c, b, a in changes],
            "added_routes": [], "newly_observed_routes": list(new_routes)}
    return SimpleNamespace(event_id="e", start_timestamp_sec=0.0, end_timestamp_sec=1.0, fusion_status="VISUAL_ONLY", snapshot_diff=diff)


def terminal(cid, before, after):
    (r,) = audit_events([ev([(cid, before, after)])])
    return r["terminal"], r["layer"]


def test_unknown_reference_is_refused_at_reference_layer():
    assert terminal("noise.enabled", "off", "on") == ("REFUSED_UNRESOLVED_REFERENCE", "REFERENCE_RESOLUTION")


def test_known_control_without_increase_decrease_terminates_at_operation():
    assert terminal("oscB.enabled", "off", "on") == (NO_OPERATION, "OPERATION")


def test_atlas_known_but_brain_unknown_is_a_brain_gap_not_a_reference_failure():
    assert terminal("fx.hyper.unison", "4", "7") == ("REFUSED_NO_BRAIN_CONCEPT", "PRODUCER_BRAIN")


def test_known_target_without_qualified_capability_is_refused_no_capability():
    assert terminal("env2.release", "15 ms", "267 ms") == ("REFUSED_NO_CAPABILITY", "CAPABILITY_RESOLUTION")


def test_qualified_admitted_control_reaches_authorized_execution():
    assert terminal("env1.release", "15 ms", "838 ms") == (ADMITTED, "AUTHORIZED_EXECUTION")


def test_route_without_baseline_is_reported_not_dropped():
    (r,) = audit_events([ev(new_routes=[{"source": "env2", "destination": "filter1.cutoff"}])])
    assert r["terminal"] == "NEWLY_OBSERVED_ROUTE_NO_BASELINE" and r["layer"] == "OBSERVATION"


def test_row_count_equals_observed_item_count():
    rows = audit_events([ev([("env1.release", "15 ms", "838 ms"), ("noise.enabled", "off", "on"), ("oscB.enabled", "off", "on")])])
    assert len(rows) == 3
