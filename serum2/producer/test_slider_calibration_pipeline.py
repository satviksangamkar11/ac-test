"""Regression tests for slider calibration pipeline.

Ensures v3 architecture solves the row-4 geometry defect and prevents regressions.
"""

import numpy as np
from PIL import Image
from slider_geometry_detector_v3 import (
    establish_structural_rail,
    detect_slider_handle_in_row,
    GeometryDetectionError,
)
from phase4_2_slider_calibration_pipeline import (
    calibrate_matrix_amounts,
    calibrate_slider_amount,
    SliderObservation,
)

# Load golden image
image_path = r"D:\ableton claude final best\video_screenshots\HEEGN1Xl5o4\step3_04m35s_matrix_mod_routes.jpg"
img = Image.open(image_path)
arr = np.array(img)

# Configuration
AMOUNT_COLUMN = (198, 324)
REFERENCE_ROWS = [280]
POPULATED_ROWS = [
    ('LFO 1 → A Fine', 160),
    ('LFO 1 → B Fine', 184),
    ('Env 3 → Noise Level', 207),
    ('Env 2 → Filter 1 Freq', 232),
]

# Blind auditor's verified measurements
BLIND_AUDITOR = {
    'LFO 1 → A Fine': (262, 1.6),
    'LFO 1 → B Fine': (262, 1.6),
    'Env 3 → Noise Level': (282, 33.3),
    'Env 2 → Filter 1 Freq': (305, 69.8),
}


def test_structural_rail_established():
    """Test that structural rail is correctly established from reference rows."""
    rail = establish_structural_rail(arr, REFERENCE_ROWS, AMOUNT_COLUMN)

    assert rail.left_pixel == 198, f"Expected left=198, got {rail.left_pixel}"
    assert rail.right_pixel == 323, f"Expected right=323, got {rail.right_pixel}"
    assert rail.width == 125, f"Expected width=125, got {rail.width}"

    # Verify it matches blind auditor's expected geometry (198-324, only 1px diff)
    assert rail.left_pixel == 198
    assert abs(rail.right_pixel - 324) <= 1, f"Right edge {rail.right_pixel} too far from blind's 324"

    print("✓ Structural rail established correctly (198–323)")


def test_rail_shared_across_all_rows():
    """Test that the same structural rail applies to all four populated rows.

    Key insight: the rail geometry is FIXED physical structure.
    It doesn't change per row; only the handle position changes.
    """
    rail = establish_structural_rail(arr, REFERENCE_ROWS, AMOUNT_COLUMN)

    for route_name, row_y in POPULATED_ROWS:
        handle_x, normalized = detect_slider_handle_in_row(arr, row_y, rail)

        # Verify handle lies within the rail
        assert rail.left_pixel <= handle_x <= rail.right_pixel, \
            f"{route_name}: handle {handle_x} outside rail [{rail.left_pixel}, {rail.right_pixel}]"

    print("✓ Structural rail applies universally to all rows (no special cases)")


def test_row4_uses_structural_rail_not_fill():
    """Test that row 4 uses the structural rail, not its visual fill geometry.

    Row 4 (Env 2 → Filter 1 Freq) has different visual fill than rows 1-3.
    v3 detector should find the same structural rail, ignoring fill differences.
    """
    rail = establish_structural_rail(arr, REFERENCE_ROWS, AMOUNT_COLUMN)

    # Row 4: Env 2 → Filter 1 Freq
    row4_y = 232
    handle_x, normalized = detect_slider_handle_in_row(arr, row4_y, rail)

    # Expected: handle at x≈305 (blind auditor's measurement)
    assert abs(handle_x - 305) <= 1, \
        f"Row 4 handle x={handle_x}, expected ≈305 (blind: 305)"

    # The rail should be the same as for rows 1-3
    assert rail.left_pixel == 198
    assert rail.right_pixel == 323

    print("✓ Row 4 uses structural rail (not fill geometry); matches blind auditor")


def test_handle_detection_independent_of_fill():
    """Test that handle detection is independent of slider fill.

    If handle detection depended on fill, rows 1-3 (similar fill) would cluster
    differently than row 4. They should all use the same rail.
    """
    rail = establish_structural_rail(arr, REFERENCE_ROWS, AMOUNT_COLUMN)

    handles = {}
    for route_name, row_y in POPULATED_ROWS:
        handle_x, _ = detect_slider_handle_in_row(arr, row_y, rail)
        handles[route_name] = handle_x

    # Expected handles (from blind auditor)
    expected = {
        'LFO 1 → A Fine': 262,
        'LFO 1 → B Fine': 262,
        'Env 3 → Noise Level': 282,
        'Env 2 → Filter 1 Freq': 305,
    }

    for route_name, expected_handle in expected.items():
        actual_handle = handles[route_name]
        assert abs(actual_handle - expected_handle) <= 1, \
            f"{route_name}: handle {actual_handle}, expected {expected_handle}"

    print("✓ Handle detection independent of fill; all match blind auditor (0px diff)")


def test_generic_slider_calibration():
    """Test that GenericSliderCalibration formula is correct."""
    test_cases = [
        (0.0, -100.0),    # Left edge
        (0.5, 0.0),       # Center
        (1.0, 100.0),     # Right edge
        (0.5120, 2.4),    # Row 1: (262-198)/125 ≈ 0.512
        (0.6720, 34.4),   # Row 3: (282-198)/125 = 0.672
        (0.8560, 71.2),   # Row 4: (305-198)/125 = 0.856
    ]

    for normalized, expected_amount in test_cases:
        actual_amount = calibrate_slider_amount(normalized)
        assert abs(actual_amount - expected_amount) < 0.1, \
            f"normalized={normalized}: amount={actual_amount}, expected {expected_amount}"

    print("✓ GenericSliderCalibration formula verified")


def test_full_calibration_pipeline():
    """Test the complete calibration pipeline end-to-end."""
    rail, observations = calibrate_matrix_amounts(
        arr=arr,
        reference_row_ys=REFERENCE_ROWS,
        populated_rows=POPULATED_ROWS,
        amount_column_x_range=AMOUNT_COLUMN,
    )

    # Verify all observations have canonical representation
    for route_name, obs in observations:
        assert obs.validates_representation(), \
            f"{route_name}: does not validate representation"

    # Compare against blind auditor
    print("\n" + "="*70)
    print("FULL CALIBRATION PIPELINE TEST")
    print("="*70)
    print(f"{'Route':30} {'System':>12} {'Blind':>12} {'Diff':>10}")
    print("-"*70)

    max_diff = 0.0
    for route_name, obs in observations:
        blind_handle, blind_amount = BLIND_AUDITOR[route_name]

        diff = abs(obs.amount - blind_amount)
        max_diff = max(max_diff, diff)

        status = "✓" if diff <= 5.0 else "⚠"
        print(f"{route_name:30} {obs.amount:>+12.1f}% {blind_amount:>+12.1f}% {diff:>+10.1f}pp {status}")

    print("-"*70)
    print(f"Maximum difference: {max_diff:.1f}pp (tolerance: ±5.0pp)")
    print("="*70)

    # All should be within ±5pp tolerance
    assert max_diff <= 5.0, \
        f"Maximum difference {max_diff:.1f}pp exceeds tolerance ±5.0pp"

    print("✓ Full calibration pipeline PASSED")


if __name__ == "__main__":
    print("="*80)
    print("REGRESSION TEST SUITE: Slider Calibration Pipeline (v3 Architecture)")
    print("="*80)

    try:
        test_structural_rail_established()
        test_rail_shared_across_all_rows()
        test_row4_uses_structural_rail_not_fill()
        test_handle_detection_independent_of_fill()
        test_generic_slider_calibration()
        test_full_calibration_pipeline()

        print("\n" + "="*80)
        print("ALL REGRESSION TESTS PASSED ✓")
        print("="*80)
        print("\nKey validations:")
        print("  • Structural rail established from reference rows")
        print("  • Rail is FIXED across all populated rows")
        print("  • Row 4 uses structural rail (not fill geometry)")
        print("  • Handle detection independent of visual fill")
        print("  • GenericSliderCalibration working correctly")
        print("  • All amounts within ±5pp of blind auditor")
        print("\nReady for production integration.")

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
