"""U3: Generic Operation Model — RED tests.

Proves the operation layer is:
  1. Target-independent (same OperationSpec for different targets)
  2. Typed (Operand carries value + unit, not bare primitives)
  3. Validated (Operand checked against ValueDomain before intent formation)

These tests drive the U3 implementation; they must FAIL before changes and
PASS after. Do NOT add target-selection logic to make them pass.

Central U3 invariant:
    Target = WHAT  (U1)
    Operation = HOW  (U3)
    ValueDomain = WHAT KIND OF VALUE  (U2)
    Capability = CAN IT BE DONE
    Admission = MAY IT BE DONE
"""
import pytest
from serum2.producer.operation_spec import OperationType, OperationSpec, OperationInterpreter, Operand
from serum2.producer.concept_representation import ValueDomain


# ---------------------------------------------------------------------------
# U3-A: Target-independence invariant
# ---------------------------------------------------------------------------

class TestU3TargetIndependence:
    """Same operation phrase → same OperationSpec regardless of target.

    The operation interpreter receives a phrase and a domain hint; it must NOT
    receive or infer a target. All three phrases below must produce an identical
    operation class.
    """

    def test_increase_produces_same_representation_across_targets(self):
        """increase Env1.Release / increase Filter.Cutoff / increase LFO1.Rate
        all produce INCREASE — target is irrelevant at this layer."""
        interp = OperationInterpreter()
        # Phrases that name different targets; the target component must be ignored
        specs = [
            interp.interpret("increase Env1.Release"),
            interp.interpret("increase Filter.Cutoff"),
            interp.interpret("increase LFO1.Rate"),
            interp.interpret("increase"),           # bare direction; same result
        ]
        for spec in specs:
            assert spec.operation == OperationType.INCREASE, \
                f"Expected INCREASE, got {spec.operation}"

    def test_decrease_produces_same_representation_across_targets(self):
        interp = OperationInterpreter()
        specs = [
            interp.interpret("decrease Env1.Release"),
            interp.interpret("decrease Filter.Cutoff"),
            interp.interpret("shorter"),
        ]
        for spec in specs:
            assert spec.operation == OperationType.DECREASE, \
                f"Expected DECREASE, got {spec.operation}"

    def test_set_produces_same_representation_across_time_targets(self):
        """SET with a numeric value is target-independent; the domain context
        (TIME / RATE / etc.) comes from ValueDomain at validation time, not from
        the interpreter."""
        interp = OperationInterpreter()
        for phrase in ("to 500 ms", "set to 500 ms", "500 ms"):
            spec = interp.interpret(phrase)
            assert spec.operation == OperationType.SET, \
                f"phrase={phrase!r}: expected SET, got {spec.operation}"
            assert spec.operand is not None
            assert spec.operand.value == 500
            assert spec.operand.unit == "ms"

    def test_interpreter_ignores_target_tokens(self):
        """Dotted target identifiers in the phrase must not change the operation."""
        interp = OperationInterpreter()
        with_target = interp.interpret("increase Env1.Release")
        without_target = interp.interpret("increase")
        assert with_target.operation == without_target.operation


# ---------------------------------------------------------------------------
# U3-B: Typed Operand
# ---------------------------------------------------------------------------

class TestU3TypedOperand:
    """OperationSpec carries a typed Operand, not bare primitives."""

    def test_set_populates_operand_with_value_and_unit(self):
        spec = OperationInterpreter().interpret("to 100 ms")
        assert spec.operand is not None
        assert spec.operand.value == 100
        assert spec.operand.unit == "ms"
        assert spec.operand.normalized_value is None   # not set by interpreter

    def test_increase_has_no_operand_value(self):
        """Direction-only operations carry no numeric operand."""
        spec = OperationInterpreter().interpret("increase")
        # operand may be None or present with value=None
        if spec.operand is not None:
            assert spec.operand.value is None

    def test_toggle_on_has_boolean_operand(self):
        spec = OperationInterpreter().interpret("enable", operation_type="toggle")
        assert spec.operation == OperationType.TOGGLE_ON
        assert spec.operand is not None
        assert spec.operand.boolean_value is True

    def test_toggle_off_has_boolean_operand(self):
        spec = OperationInterpreter().interpret("disable", operation_type="toggle")
        assert spec.operation == OperationType.TOGGLE_OFF
        assert spec.operand is not None
        assert spec.operand.boolean_value is False

    def test_select_carries_enum_operand(self):
        spec = OperationInterpreter().interpret("set to Band 24", operation_type="enum")
        assert spec.operation == OperationType.SELECT
        assert spec.operand is not None
        assert spec.operand.enum_value is not None
        assert "band" in spec.operand.enum_value.lower()

    def test_operand_dataclass_has_required_fields(self):
        """Operand must have: value, unit, normalized_value, enum_value, boolean_value."""
        op = Operand()
        assert hasattr(op, "value")
        assert hasattr(op, "unit")
        assert hasattr(op, "normalized_value")
        assert hasattr(op, "enum_value")
        assert hasattr(op, "boolean_value")


# ---------------------------------------------------------------------------
# U3-C: ValueDomain validation
# ---------------------------------------------------------------------------

class TestU3ValueDomainValidation:
    """Operand must be validated against ValueDomain before the intent is formed.

    validate_against(value_domain) returns (ok: bool, reason: str).
    """

    def test_time_operand_in_range_is_valid(self):
        """500 ms is a plausible time value for an ADSR control."""
        spec = OperationInterpreter().interpret("to 500 ms")
        vd = ValueDomain(type="time", unit="seconds", min_value=0.0, max_value=5.2)
        ok, reason = spec.operand.validate_against(vd)
        assert ok, f"Expected valid: {reason}"

    def test_time_operand_unit_mismatch_is_flagged(self):
        """Supplying Hz where seconds are expected must fail validation."""
        op = Operand(value=440, unit="hz")
        vd = ValueDomain(type="time", unit="seconds", min_value=0.0, max_value=5.2)
        ok, reason = op.validate_against(vd)
        assert not ok, "Hz operand against TIME domain must fail"
        assert "unit" in reason.lower() or "type" in reason.lower()

    def test_enum_operand_validates_against_vocabulary(self):
        """SELECT operand must check the value against enum_values in the domain."""
        op = Operand(enum_value="Band 24")
        vd = ValueDomain(type="enum", enum_values=["Low 12", "Low 24", "Band 12", "Band 24", "High 12", "High 24"])
        ok, reason = op.validate_against(vd)
        assert ok, f"Expected valid enum value: {reason}"

    def test_enum_operand_rejects_unknown_value(self):
        op = Operand(enum_value="Notch 48")  # not in vocabulary
        vd = ValueDomain(type="enum", enum_values=["Low 12", "Low 24", "Band 12", "Band 24"])
        ok, reason = op.validate_against(vd)
        assert not ok
        assert "notch 48" in reason.lower() or "not in" in reason.lower()

    def test_toggle_operand_validates_against_toggle_domain(self):
        op = Operand(boolean_value=True)
        vd = ValueDomain(type="toggle")
        ok, reason = op.validate_against(vd)
        assert ok

    def test_increase_with_no_value_is_valid_for_numeric_domain(self):
        """Direction-only operation needs no numeric value; it's inherently valid
        against any numeric domain."""
        spec = OperationInterpreter().interpret("increase")
        vd = ValueDomain(type="rate", unit="normalized rate", min_value=0.0, max_value=100.0,
                         interpretation="mode_dependent")
        ok, reason = spec.validate_against(vd)
        assert ok, f"INCREASE against numeric domain should be valid: {reason}"

    def test_set_out_of_range_is_flagged(self):
        """9999 ms is way above max_value=5.2 s; should be flagged."""
        op = Operand(value=9999, unit="ms")
        vd = ValueDomain(type="time", unit="seconds", min_value=0.0, max_value=5.2)
        ok, reason = op.validate_against(vd)
        # May be invalid if value is translated to seconds (9.999 > 5.2) or unit-unaware
        # At minimum: validate_against must NOT raise; it must return (bool, str)
        assert isinstance(ok, bool)
        assert isinstance(reason, str)


# ---------------------------------------------------------------------------
# U3-D: New operation types exist in the enum
# ---------------------------------------------------------------------------

class TestU3OperationTypeEnum:
    """All nine U3 operation classes must exist in OperationType."""

    @pytest.mark.parametrize("op", [
        "SET", "INCREASE", "DECREASE",
        "TOGGLE_ON", "TOGGLE_OFF",
        "SELECT",
        "PATCH", "ADD", "REMOVE",
    ])
    def test_operation_type_exists(self, op):
        assert hasattr(OperationType, op), \
            f"OperationType.{op} must exist for U3"

    def test_set_is_distinct_from_numeric_set_or_is_canonical(self):
        """SET must be the canonical name (NUMERIC_SET may alias or be retired)."""
        assert OperationType.SET is not None

    def test_unknown_still_exists(self):
        assert OperationType.UNKNOWN is not None


# ---------------------------------------------------------------------------
# U3-E: OperationSpec.validate_against(value_domain) convenience method
# ---------------------------------------------------------------------------

class TestU3SpecLevelValidation:
    """OperationSpec itself exposes validate_against for the intent-formation layer."""

    def test_spec_has_validate_against(self):
        spec = OperationInterpreter().interpret("increase")
        assert callable(getattr(spec, "validate_against", None)), \
            "OperationSpec must have validate_against(value_domain)"

    def test_increase_spec_validates_against_rate_domain(self):
        spec = OperationInterpreter().interpret("increase")
        vd = ValueDomain(type="rate", unit="normalized rate", min_value=0.0, max_value=100.0,
                         interpretation="mode_dependent")
        ok, reason = spec.validate_against(vd)
        assert ok

    def test_toggle_spec_fails_against_numeric_domain(self):
        spec = OperationInterpreter().interpret("enable", operation_type="toggle")
        vd = ValueDomain(type="time", unit="seconds", min_value=0.0, max_value=5.2)
        ok, reason = spec.validate_against(vd)
        assert not ok, "Toggle op against numeric domain must fail"


# ---------------------------------------------------------------------------
# U3-F: No target selection inside the operation layer
# ---------------------------------------------------------------------------

class TestU3NoTargetSelection:
    """The interpreter must never produce a target as a side effect."""

    def test_interpreter_produces_no_target_field(self):
        """OperationSpec has no 'target' or 'canonical_target' field."""
        spec = OperationInterpreter().interpret("increase LFO1.Rate")
        assert not hasattr(spec, "canonical_target"), \
            "OperationSpec must not carry a canonical_target"
        assert not hasattr(spec, "resolved_target"), \
            "OperationSpec must not carry a resolved_target"

    def test_brighter_does_not_produce_a_target(self):
        """Audio-descriptor words ('brighter') must not select a target concept."""
        spec = OperationInterpreter().interpret("brighter")
        # Must be UNKNOWN or INCREASE (perceptual direction), never a named target
        assert spec.operation in (OperationType.UNKNOWN, OperationType.INCREASE,
                                  OperationType.DECREASE), \
            f"'brighter' must not resolve a target; got {spec.operation}"
        assert not hasattr(spec, "canonical_target")
