"""Phase 3.4: Completeness Invariant Validation

Enforce the critical invariant:
EPISODE_EXPECTED_SET == TERMINAL_OBSERVATION_SET

Three failure conditions, one success condition.
"""

import sys
from expected_inventory import CompletenessValidator, ExpectedObservation, TerminalObservation, ObservationOutcome


def test_missing_expected_item_fails():
    """Condition A: Expected item with no terminal outcome -> FAIL"""
    print("\n--- Test A: Missing terminal outcome for expected item ---")

    validator = CompletenessValidator(
        expected_inventory={
            "control_A": ExpectedObservation("control_A", "TEXT", "TEXT"),
            "control_B": ExpectedObservation("control_B", "NUMERIC", "NUMERIC"),
            "control_C": ExpectedObservation("control_C", "ENUM", "ENUM"),
        }
    )

    # Add terminal observations for A and B only (C is missing)
    validator.add_terminal_observation(TerminalObservation("control_A", ObservationOutcome.OBSERVED))
    validator.add_terminal_observation(TerminalObservation("control_B", ObservationOutcome.OBSERVED))
    # Control C has NO terminal outcome

    result = validator.validate()

    assert not result["valid"], "Should fail when expected item missing terminal outcome"
    assert "control_C" in result["missing"], "Missing control must be identified"
    print(f"[PASS] Correctly FAILED: missing terminal for control_C")
    print(f"   Missing: {result['missing']}")
    return True


def test_source_insufficient_passes():
    """Condition B: Expected item with SOURCE_INSUFFICIENT -> PASS"""
    print("\n--- Test B: SOURCE_INSUFFICIENT counts as valid terminal outcome ---")

    validator = CompletenessValidator(
        expected_inventory={
            "control_A": ExpectedObservation("control_A", "TEXT", "TEXT"),
            "control_B": ExpectedObservation("control_B", "NUMERIC", "NUMERIC"),
            "control_C": ExpectedObservation("control_C", "NUMERIC", "NUMERIC"),  # Drive=1.9
        }
    )

    # Add terminal observations
    validator.add_terminal_observation(TerminalObservation("control_A", ObservationOutcome.OBSERVED))
    validator.add_terminal_observation(TerminalObservation("control_B", ObservationOutcome.OBSERVED))
    validator.add_terminal_observation(
        TerminalObservation("control_C", ObservationOutcome.SOURCE_INSUFFICIENT)
    )

    result = validator.validate()

    assert result["valid"], "Should PASS when all expected items have terminal outcomes (including SOURCE_INSUFFICIENT)"
    assert len(result["missing"]) == 0, "No items should be reported as missing"
    print(f"[PASS] Correctly PASSED: all expected items accounted for")
    print(f"   Missing: {result['missing']} (empty)")
    print(f"   control_C with SOURCE_INSUFFICIENT is a valid terminal outcome")
    return True


def test_extra_unexpected_item_fails():
    """Condition C: Terminal observation for unexpected item -> FAIL"""
    print("\n--- Test C: Extra terminal observation not in expected set ---")

    validator = CompletenessValidator(
        expected_inventory={
            "control_A": ExpectedObservation("control_A", "TEXT", "TEXT"),
            "control_B": ExpectedObservation("control_B", "NUMERIC", "NUMERIC"),
        }
    )

    # Add terminal observations including an unexpected one
    validator.add_terminal_observation(TerminalObservation("control_A", ObservationOutcome.OBSERVED))
    validator.add_terminal_observation(TerminalObservation("control_B", ObservationOutcome.OBSERVED))
    validator.add_terminal_observation(TerminalObservation("control_X", ObservationOutcome.OBSERVED))  # ← unexpected

    result = validator.validate()

    assert not result["valid"], "Should fail when extra terminal observation exists"
    assert "control_X" in result["extra"], "Extra control must be identified"
    print(f"[PASS] Correctly FAILED: extra terminal for control_X")
    print(f"   Extra: {result['extra']}")
    return True


def test_duplicate_terminal_fails():
    """Invariant: Duplicate terminal outcome for same canonical_id -> FAIL

    This prevents accidental double-accounting of the same observation.
    """
    print("\n--- Test D: Duplicate terminal outcome for same canonical_id ---")

    validator = CompletenessValidator(
        expected_inventory={
            "control_A": ExpectedObservation("control_A", "TEXT", "TEXT"),
            "control_B": ExpectedObservation("control_B", "NUMERIC", "NUMERIC"),
        }
    )

    # Add first terminal for control_A
    validator.add_terminal_observation(TerminalObservation("control_A", ObservationOutcome.OBSERVED))

    # Try to add duplicate terminal for control_A
    initial_count = len(validator.terminal_ids)
    validator.add_terminal_observation(TerminalObservation("control_A", ObservationOutcome.OBSERVED))

    # Set-based tracking should prevent duplicates
    assert len(validator.terminal_ids) == initial_count, "Duplicate terminal should not increase count"
    print(f"[PASS] Correctly prevented duplicate: control_A terminal_ids count unchanged")
    return True


def test_real_reference_scenario():
    """Test with actual HEEGN1Xl5o4 scenario: 23 expected, various outcomes"""
    print("\n--- Test E: Real reference scenario (HEEGN1Xl5o4) ---")

    # Simplified subset of HEEGN1Xl5o4 expected controls
    expected = {
        # Gate-A verified controls
        "oscA.unison": ExpectedObservation("oscA.unison", "NUMERIC", "NUMERIC"),
        "lfo1.shape": ExpectedObservation("lfo1.shape", "ENUM", "ENUM"),
        "voicing.legato": ExpectedObservation("voicing.legato", "ENABLE_STATE", "ENABLE_STATE"),
        "route:Env 2->Filter 1 Freq": ExpectedObservation("route:Env 2->Filter 1 Freq", "ROUTE", "ROUTE_TEXT"),

        # Gate-A problematic controls
        "fx.overdrive.drive": ExpectedObservation("fx.overdrive.drive", "NUMERIC", "NUMERIC"),
        "matrix.amount[Env 2->Filter 1 Freq]": ExpectedObservation(
            "matrix.amount[Env 2->Filter 1 Freq]", "MATRIX_AMOUNT", "SLIDER_PIXEL"
        ),

        # Other expected but not visibly changed
        "oscC.enabled": ExpectedObservation("oscC.enabled", "UNKNOWN", "TEXT"),
        "voicing.mono": ExpectedObservation("voicing.mono", "ENABLE_STATE", "ENABLE_STATE"),
    }

    validator = CompletenessValidator(expected_inventory=expected)

    # Add terminal observations
    # Gate-A verified: OBSERVED
    validator.add_terminal_observation(TerminalObservation("oscA.unison", ObservationOutcome.OBSERVED))
    validator.add_terminal_observation(TerminalObservation("lfo1.shape", ObservationOutcome.OBSERVED))
    validator.add_terminal_observation(TerminalObservation("voicing.legato", ObservationOutcome.OBSERVED))
    validator.add_terminal_observation(TerminalObservation("route:Env 2->Filter 1 Freq", ObservationOutcome.OBSERVED))

    # Gate-A problematic: SOURCE_INSUFFICIENT or OBSERVABLE_VISUAL_ONLY
    validator.add_terminal_observation(
        TerminalObservation("fx.overdrive.drive", ObservationOutcome.SOURCE_INSUFFICIENT)
    )
    validator.add_terminal_observation(
        TerminalObservation("matrix.amount[Env 2->Filter 1 Freq]", ObservationOutcome.OBSERVED)
    )

    # Other expected controls: NOT_VISIBLE_IN_FRAME
    validator.add_terminal_observation(
        TerminalObservation("oscC.enabled", ObservationOutcome.NOT_VISIBLE_IN_FRAME)
    )
    validator.add_terminal_observation(
        TerminalObservation("voicing.mono", ObservationOutcome.OBSERVED)
    )

    result = validator.validate()

    assert result["valid"], "Real scenario should pass despite SOURCE_INSUFFICIENT items"
    assert len(result["missing"]) == 0, "No items should be missing"
    assert len(result["extra"]) == 0, "No extra items"
    print(f"[PASS] Real reference scenario PASSED")
    print(f"   Expected: {len(expected)} controls")
    print(f"   Terminal outcomes: {len(validator.terminal_ids)}")
    print(f"   All accounted for (including SOURCE_INSUFFICIENT)")
    return True


def run_phase_3_4_tests():
    """Run all Phase 3.4 completeness invariant tests."""
    print("\n" + "=" * 70)
    print("Phase 3.4: Completeness Invariant Tests")
    print("=" * 70)

    tests = [
        ("Missing expected item -> FAIL", test_missing_expected_item_fails),
        ("SOURCE_INSUFFICIENT -> PASS", test_source_insufficient_passes),
        ("Extra unexpected item -> FAIL", test_extra_unexpected_item_fails),
        ("Duplicate terminal -> prevented", test_duplicate_terminal_fails),
        ("Real reference scenario", test_real_reference_scenario),
    ]

    passed = 0
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"[FAIL] {name}: {e}")

    print("\n" + "=" * 70)
    print(f"Phase 3.4 Results: {passed}/{len(tests)} PASSED")
    print("=" * 70)

    return passed == len(tests)


if __name__ == "__main__":
    success = run_phase_3_4_tests()
    sys.exit(0 if success else 1)
