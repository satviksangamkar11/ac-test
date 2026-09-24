import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "vendor" / "serum-mcp" / "src"))

from serum2.producer.state_ledger import _display_curve, _to_target_unit  # noqa: E402
from serum_mcp.generation.spec import EnvelopeSpec, FilterSpec, OscillatorSpec  # noqa: E402

LINEAR = {"kind": "power", "exponent": 1}
SQUARE = {"kind": "power", "exponent": 2}


def _displayed_percent(raw, curve):
    return raw ** curve["exponent"] * 100.0


@pytest.mark.parametrize("pct", [0, 25, 50, 60, 100])
def test_linear_curve_is_plain_percent(pct):
    assert _to_target_unit(pct, "%", "", 0.0, 1.0, LINEAR) == (pct / 100.0, "")


@pytest.mark.parametrize("exponent", [1, 2, 3, 0.5])
@pytest.mark.parametrize("pct", [0, 25, 50, 60, 81, 100])
def test_any_power_curve_round_trips_to_the_requested_display(exponent, pct):
    curve = {"kind": "power", "exponent": exponent}
    raw, why = _to_target_unit(pct, "%", "", 0.0, 1.0, curve)
    assert why == "" and 0.0 <= raw <= 1.0
    assert math.isclose(_displayed_percent(raw, curve), pct, abs_tol=1e-9)


def test_square_curve_differs_from_linear_off_the_endpoints():
    raw_sq, _ = _to_target_unit(60, "%", "", 0.0, 1.0, SQUARE)
    raw_lin, _ = _to_target_unit(60, "%", "", 0.0, 1.0, LINEAR)
    assert raw_sq > raw_lin
    assert round(_displayed_percent(raw_lin, SQUARE)) != 60  # the pre-fix live mismatch shape


@pytest.mark.parametrize("raw,shown", [(0.25, 6), (0.50, 25), (0.81, 66)])
def test_square_curve_matches_live_serum_readings(raw, shown):
    assert round(_displayed_percent(raw, SQUARE)) == shown


@pytest.mark.parametrize("curve", [None, "power2", {}, {"kind": "log"}, {"kind": "power"},
                                   {"kind": "power", "exponent": 0}, {"kind": "power", "exponent": True}])
def test_undeclared_or_invalid_curve_is_refused_not_guessed(curve):
    raw, why = _to_target_unit(60, "%", "", 0.0, 1.0, curve)
    assert raw is None and "display_curve" in why


def test_non_normalized_percent_target_unaffected():
    assert _to_target_unit(60, "%", "", 0.0, 100.0, None) == (60, "")


def test_db_and_time_conversions_unaffected():
    assert _to_target_unit(0.0, "db", "", 0.0, 1.0, None) == (1.0, "")
    assert _to_target_unit(600, "ms", "seconds", 0.0, 10.0, None) == (0.6, "")
    assert _to_target_unit(1.0, "s", "seconds", 0.0, 10.0, None) == (1.0, "")


def test_curve_is_read_from_field_metadata_only():
    assert _display_curve(EnvelopeSpec.model_fields["sustain"]) == SQUARE
    for f in ("attack", "decay", "release"):
        assert _display_curve(EnvelopeSpec.model_fields[f]) is None
    assert _display_curve(FilterSpec.model_fields["cutoff"]) is None
    assert _display_curve(OscillatorSpec.model_fields["volume"]) is None
