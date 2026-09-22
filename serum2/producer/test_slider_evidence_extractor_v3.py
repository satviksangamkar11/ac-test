"""Test slider evidence extractor v3 production integration.

Verifies that the extractor can take raw requests and produce calibrated
observations ready for phase4_2_verified_state_adapter.
"""

import numpy as np
from PIL import Image
from slider_evidence_extractor_v3 import (
    SliderEvidenceExtractorV3,
    ExtractionRequest,
    ExtractionStatus,
    extraction_result_to_calibration_observation,
)

# Load test image
image_path = r"D:\ableton claude final best\video_screenshots\HEEGN1Xl5o4\step3_04m35s_matrix_mod_routes.jpg"
img = Image.open(image_path)
arr = np.array(img)

# Test configuration
REFERENCE_ROWS = [280]
AMOUNT_COLUMN = (198, 324)

TEST_ROWS = [
    ('LFO 1 → A Fine', 160),
    ('LFO 1 → B Fine', 184),
    ('Env 3 → Noise Level', 207),
    ('Env 2 → Filter 1 Freq', 232),
]

# Blind auditor expected values
BLIND_AUDITOR = {
    'LFO 1 → A Fine': (262, 1.6),
    'LFO 1 → B Fine': (262, 1.6),
    'Env 3 → Noise Level': (282, 33.3),
    'Env 2 → Filter 1 Freq': (305, 69.8),
}


def test_production_extraction():
    """Test end-to-end extraction pipeline."""

    extractor = SliderEvidenceExtractorV3()

    print("="*80)
    print("PRODUCTION EXTRACTION TEST: v3 Structural Rail Detector")
    print("="*80)

    results = {}
    max_diff = 0.0

    for route_name, row_y in TEST_ROWS:
        # Create extraction request
        request = ExtractionRequest(
            observation_id=f"obs_{route_name.replace(' → ', '_')}",
            canonical_id="matrix.amount",
            row_detail=str(row_y),
            image_path=image_path,
            expected_orientation="horizontal",
            extraction_method="SLIDER_PIXEL_V3",
        )

        # Extract
        result = extractor.extract(
            request,
            reference_row_ys=REFERENCE_ROWS,
            amount_column_x_range=AMOUNT_COLUMN,
        )

        results[route_name] = result

        # Verify success
        if result.status != ExtractionStatus.EXTRACTED:
            print(f"\n✗ {route_name}: FAILED")
            print(f"  Status: {result.status.value}")
            print(f"  Error: {result.error_message}")
            continue

        # Convert to calibration observation
        obs = extraction_result_to_calibration_observation(request, result)

        # Compare against blind auditor
        blind_handle, blind_amount = BLIND_AUDITOR[route_name]
        handle_diff = abs(result.handle_position_pixel - blind_handle)
        amount_diff = abs(result.calibrated_amount - blind_amount)
        max_diff = max(max_diff, amount_diff)

        status = "✓" if amount_diff <= 5.0 else "⚠"
        print(f"\n{status} {route_name}")
        print(f"  Handle:  {result.handle_position_pixel:.0f} (blind: {blind_handle}, diff: {handle_diff:.0f}px)")
        print(f"  Amount:  {result.calibrated_amount:+.1f}% (blind: {blind_amount:+.1f}%, diff: {amount_diff:+.1f}pp)")
        print(f"  Rail:    {result.left_pixel:.0f}–{result.right_pixel:.0f} "
              f"(confidence: {result.track_detection_confidence:.0%})")

    # Summary
    print("\n" + "="*80)
    print("PRODUCTION EXTRACTION SUMMARY")
    print("="*80)

    passed = sum(1 for r in results.values() if r.status == ExtractionStatus.EXTRACTED)
    print(f"Extractions: {passed}/{len(results)} successful")
    print(f"Maximum amount difference: {max_diff:.1f}pp (tolerance: ±5.0pp)")

    all_pass = (
        passed == len(results)
        and max_diff <= 5.0
    )

    if all_pass:
        print("\n✓ PRODUCTION EXTRACTION TEST PASSED")
        print("\nReady for integration into:")
        print("  • phase4_2_verified_state_adapter")
        print("  • VerifiedMatrixRoute creation")
        print("  • Full E2E test suite")
    else:
        print("\n✗ PRODUCTION EXTRACTION TEST FAILED")
        print(f"  Passed: {passed}/{len(results)}")
        print(f"  Max diff: {max_diff:.1f}pp")
        exit(1)

    print("="*80)


if __name__ == "__main__":
    test_production_extraction()
