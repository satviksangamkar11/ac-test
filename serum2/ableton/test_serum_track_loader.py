"""The bridge wrapper fails closed everywhere it isn't Windows+Ableton+Serum, and never fakes a result. These tests
run on this actual container (Linux, no Ableton) -- they ARE the fail-closed proof, not a mock of it."""
import platform

import pytest

from serum2.ableton.serum_track_loader import (
    BridgeUnavailable, DEFAULT_PORT, bridge_status, build_ui_readback_request, load_and_verify,
)


def test_load_and_verify_fails_closed_on_this_machine():
    """This container is not Windows; the wrapper must refuse, never return a fake LOADED_VISUAL."""
    with pytest.raises(BridgeUnavailable):
        load_and_verify("/tmp/does_not_matter.SerumPreset")


def test_failure_message_names_the_exact_remedy():
    try:
        load_and_verify("/tmp/does_not_matter.SerumPreset")
        assert False, "expected BridgeUnavailable"
    except BridgeUnavailable as e:
        msg = str(e)
        assert "Windows" in msg or "AbletonMCP" in msg
        assert str(DEFAULT_PORT) in msg or "port" in msg.lower()


def test_bridge_status_reports_unavailable_without_raising():
    status = bridge_status()
    assert status["available"] is False
    assert status["reason"]


def test_ui_readback_request_shape_matches_state_comparator_contract():
    req = build_ui_readback_request(["oscA.wavetable", "filter1.cutoff"])
    assert req["route"] == "DIRECT_UI"
    assert set(req["values"]) == {"oscA.wavetable", "filter1.cutoff"}
    assert all(v is None for v in req["values"].values())   # nothing is ever pre-filled/guessed


def test_never_returns_a_result_without_a_real_connection(monkeypatch):
    """Even if a test forces past the platform check, no socket connection means no result -- still closed."""
    monkeypatch.setattr(platform, "system", lambda: "Windows")
    with pytest.raises(BridgeUnavailable):
        load_and_verify("/tmp/does_not_matter.SerumPreset")
