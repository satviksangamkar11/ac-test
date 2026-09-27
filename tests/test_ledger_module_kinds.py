"""A5 Ledger Safety: all 9 module kinds coerce without crash.

Proves that _coerce() handles osc, env, lfo, filter, macro, and singleton_field
(arp, global_, voice_unison) without KeyError, and that unknown kinds produce
an UNSUPPORTED terminal rather than raising.
"""
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT), str(ROOT / "serum2" / "knowledge")):
    if p not in sys.path:
        sys.path.insert(0, p)

from serum2.producer.state_ledger import Row, DERIVED, UNSUPPORTED, _coerce, derive


def _row(value: Any, unit: Optional[str] = None, context: Optional[Dict] = None) -> Row:
    return Row(
        control_id="test.control", value=value, unit=unit, status="OBSERVED",
        control_type="continuous", source_ts=0.0, n_readings=1, changed_from_previous=False,
        context=context or {},
    )


# (kind, target dict, value, unit) — should all produce DERIVED (no error)
FIELD_CASES = [
    ("osc",    {"kind": "field", "module": "osc",    "list": "oscillators", "index": 0, "field": "octave",  "operation": "SET", "basis": "exact_normalized"}, "0",    None),
    ("env",    {"kind": "field", "module": "env",    "list": "envelopes",   "index": 0, "field": "attack",  "operation": "SET", "basis": "exact_normalized"}, "10",   "ms"),
    ("lfo",    {"kind": "field", "module": "lfo",    "list": "lfos",        "index": 0, "field": "rate",    "operation": "SET", "basis": "exact_normalized"}, "1.0",  None),
    ("filter", {"kind": "field", "module": "filter", "list": "filters",     "index": 0, "field": "cutoff",  "operation": "SET", "basis": "exact_normalized"}, "0.5",  None),
    ("macro",  {"kind": "field", "module": "macro",  "list": "macros",      "index": 0, "field": "value",   "operation": "SET", "basis": "exact_normalized"}, "50.0", None),
]

SINGLETON_CASES = [
    ("arp",         {"kind": "singleton_field", "attr": "arp",         "field": "rate",       "operation": "SET", "basis": "exact_normalized"}, "0.5",  None),
    ("global_",     {"kind": "singleton_field", "attr": "global_",     "field": "poly_count", "operation": "SET", "basis": "exact_normalized"}, "8",    None),
    ("voice_unison",{"kind": "singleton_field", "attr": "voice_unison","field": "detune",     "operation": "SET", "basis": "exact_normalized"}, "0.3",  None),
]


@pytest.mark.parametrize("kind,target,value,unit", FIELD_CASES)
def test_field_kind_no_keyerror(kind, target, value, unit):
    row = _row(value, unit)
    import copy
    t = copy.deepcopy(target)
    err = _coerce(row, t, "test.control", None)
    assert err is None, "kind=%r gave coerce error: %r" % (kind, err)
    assert t.get("value") is not None, "value not set for kind=%r" % kind


@pytest.mark.parametrize("kind,target,value,unit", SINGLETON_CASES)
def test_singleton_field_no_keyerror(kind, target, value, unit):
    row = _row(value, unit)
    import copy
    t = copy.deepcopy(target)
    err = _coerce(row, t, "test.control", None)
    assert err is None, "singleton_field attr=%r gave coerce error: %r" % (kind, err)
    assert t.get("value") is not None, "value not set for attr=%r" % kind


def test_unknown_kind_gives_unsupported_not_raise():
    """An unrecognized kind must produce an error string (leading to UNSUPPORTED), never raise."""
    row = _row("1.0")
    t = {"kind": "totally_unknown_kind", "operation": "SET"}
    err = _coerce(row, t, "test.control", None)
    assert err is not None, "expected non-None error for unknown kind"
    assert isinstance(err, str)


def test_macro_field_value_is_set():
    """Macro value field should accept a float and set it."""
    row = _row("75.0")
    t = {"kind": "field", "module": "macro", "list": "macros", "index": 0, "field": "value", "operation": "SET", "basis": "exact_normalized"}
    err = _coerce(row, t, "macro1", None)
    assert err is None
    assert t.get("value") is not None


def test_singleton_field_unknown_attr():
    """Unknown attr should return error string, not raise."""
    row = _row("1.0")
    t = {"kind": "singleton_field", "attr": "totally_unknown", "field": "rate", "operation": "SET"}
    err = _coerce(row, t, "test.control", None)
    assert err is not None
    assert isinstance(err, str)
