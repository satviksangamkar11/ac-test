"""Phase 3.5 Precursor: Row-Detail Identity Formalization

Verify that row-detail observations are properly separated from flat Atlas controls.
This is a prerequisite for Phase 3.5 (Matrix Amount geometric calibration).
"""

import sys
from expected_inventory import (
    ExpectedObservation,
    ExpectedInventoryBuilder,
    EpisodeContextResolver,
)


def test_extract_row_detail_with_bracket_notation():
    """Row-detail extraction: matrix.amount[Env 2 → Filter 1 Freq]"""
    print("\n--- Test A: Row-detail extraction ---")

    atlas = {}
    context = EpisodeContextResolver(reference_id="test", atlas=atlas)

    # Add expected observation with row-detail
    context.add_control_context("matrix.amount[Env 2 → Filter 1 Freq]", {
        "transcript": "Matrix amount slider",
        "procedure": "Set modulation depth",
        "module_context": "MATRIX / Row 1 / Amount",
    })

    builder = ExpectedInventoryBuilder(atlas=atlas, episode_context=context)
    inventory = builder.build()

    # Verify the observation was created
    assert "matrix.amount[Env 2 → Filter 1 Freq]" in inventory
    obs = inventory["matrix.amount[Env 2 → Filter 1 Freq]"]

    # Verify row_detail was extracted
    assert obs.row_detail == "Env 2 → Filter 1 Freq", f"Expected 'Env 2 → Filter 1 Freq', got {obs.row_detail}"
    print(f"[PASS] Row-detail extracted: {obs.row_detail}")
    return True


def test_flat_control_has_no_row_detail():
    """Flat control without brackets has row_detail=None"""
    print("\n--- Test B: Flat control (no row-detail) ---")

    atlas = {}
    context = EpisodeContextResolver(reference_id="test", atlas=atlas)

    context.add_control_context("matrix.amount", {
        "transcript": "Matrix controls",
        "procedure": "Configure routing",
        "module_context": "MATRIX",
    })

    builder = ExpectedInventoryBuilder(atlas=atlas, episode_context=context)
    inventory = builder.build()

    assert "matrix.amount" in inventory
    obs = inventory["matrix.amount"]

    assert obs.row_detail is None, f"Expected None, got {obs.row_detail}"
    print(f"[PASS] Flat control has row_detail=None")
    return True


def test_row_detail_in_to_dict():
    """Verify row_detail is preserved in to_dict serialization"""
    print("\n--- Test C: Row-detail in serialization ---")

    obs = ExpectedObservation(
        canonical_id="matrix.amount[Env 2 → Filter 1 Freq]",
        observation_kind="MATRIX_AMOUNT",
        strategy="SLIDER_PIXEL",
        expectation_basis={"transcript": "test"},
        row_detail="Env 2 → Filter 1 Freq",
    )

    serialized = obs.to_dict()
    assert serialized["row_detail"] == "Env 2 → Filter 1 Freq"
    print(f"[PASS] Row-detail in serialization: {serialized['row_detail']}")
    return True


def test_distinct_observations_per_row():
    """Multiple rows of same control create distinct observations"""
    print("\n--- Test D: Distinct row-specific observations ---")

    atlas = {}
    context = EpisodeContextResolver(reference_id="test", atlas=atlas)

    # Add two different rows of the same matrix.amount control
    context.add_control_context("matrix.amount[Env 2 → Filter 1 Freq]", {
        "transcript": "Row 1 amount",
        "procedure": "Env 2 modulation depth",
        "module_context": "MATRIX / Row 1",
    })
    context.add_control_context("matrix.amount[LFO 1 → OSC A Pitch]", {
        "transcript": "Row 2 amount",
        "procedure": "LFO 1 modulation depth",
        "module_context": "MATRIX / Row 2",
    })

    builder = ExpectedInventoryBuilder(atlas=atlas, episode_context=context)
    inventory = builder.build()

    # Both should be present as separate observations
    assert len(inventory) == 2, f"Expected 2 observations, got {len(inventory)}"
    obs1 = inventory["matrix.amount[Env 2 → Filter 1 Freq]"]
    obs2 = inventory["matrix.amount[LFO 1 → OSC A Pitch]"]

    assert obs1.row_detail == "Env 2 → Filter 1 Freq"
    assert obs2.row_detail == "LFO 1 → OSC A Pitch"
    assert obs1.canonical_id != obs2.canonical_id
    print(f"[PASS] Two row-specific observations created:")
    print(f"   Obs 1: {obs1.canonical_id} → {obs1.row_detail}")
    print(f"   Obs 2: {obs2.canonical_id} → {obs2.row_detail}")
    return True


def run_phase_3_5_precursor_tests():
    """Run row-detail identity tests."""
    print("\n" + "=" * 70)
    print("Phase 3.5 Precursor: Row-Detail Identity Tests")
    print("=" * 70)

    tests = [
        ("Extract row-detail", test_extract_row_detail_with_bracket_notation),
        ("Flat control (no row-detail)", test_flat_control_has_no_row_detail),
        ("Row-detail in serialization", test_row_detail_in_to_dict),
        ("Distinct row-specific observations", test_distinct_observations_per_row),
    ]

    passed = 0
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"[FAIL] {name}: {e}")

    print("\n" + "=" * 70)
    print(f"Phase 3.5 Precursor Results: {passed}/{len(tests)} PASSED")
    print("=" * 70)

    return passed == len(tests)


if __name__ == "__main__":
    success = run_phase_3_5_precursor_tests()
    sys.exit(0 if success else 1)
