"""Generic value selection: type/bounds come from the schema (Atlas + serum-mcp), never from a control name."""
import pytest
from serum2.qualification.candidate_binding_qualifier import field_domain, value_domain, domain_value
from serum2.reference.serum_atlas import get_control

def _pick(cid, lst, fld, baseline):
    d = value_domain(get_control(cid), field_domain(lst, fld))
    return d, domain_value(get_control(cid), baseline, d)

def test_integer_control_gets_integer_value():
    d, v = _pick("oscA.unison", "oscillators", "unison", 1.0)
    assert d["kind"] == "integer" and v == int(v) and 1 <= v <= 16 and v != 1.0

def test_integer_octave_not_fractional():
    d, v = _pick("oscA.octave", "oscillators", "octave", 0.0)
    assert d["kind"] == "integer" and v == int(v) and -4 <= v <= 4

def test_schema_bounds_intersect_atlas_bounds():
    d, v = _pick("oscA.semitone", "oscillators", "semitone", 0.0)   # atlas +-72, schema +-12
    assert (d["lo"], d["hi"]) == (-12.0, 12.0) and -12 <= v <= 12

def test_float_and_toggle():
    d, v = _pick("env1.hold", "envelopes", "hold", 0.0)
    assert d["kind"] == "float" and 0 < v <= 5.2
    assert _pick("filter1.enabled", "filters", "enabled", False)[1] is True

def test_enum_is_blocked_not_guessed():
    with pytest.raises(NotImplementedError):
        value_domain(get_control("lfo1.mode"), field_domain("lfos", "mode"))
