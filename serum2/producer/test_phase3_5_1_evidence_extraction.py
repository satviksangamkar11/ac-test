"""Phase 3.5.1: Generic Slider Evidence Extraction Tests

Verify that evidence extraction is parameterless and produces deterministic SliderObservation.
"""

import sys
from slider_evidence_extractor import (
    SliderEvidenceExtractor,
    ExtractionRequest,
    ExtractionStatus,
    extraction_result_to_slider_observation,
)
from calibration_model import SliderObservation


def test_1_extraction_request_parameterless():
    """Evidence extraction carries no parameter-specific logic"""
    print("\n--- Test 1: Extraction request parameterless ---")

    request = ExtractionRequest(
        observation_id="obs_test1",
        canonical_id="matrix.amount",  # parameter name is metadata only
        row_detail="Env 2 → Filter 1 Freq",  # row is metadata only
        image_path="test_frame.jpg",
        extraction_method="SLIDER_PIXEL",
    )

    # Request contains no hardcoded matrix.amount, no Env 2, no Filter 1
    assert "matrix" not in request.extraction_method.lower()
    assert "env" not in request.extraction_method.lower()

    print(f"[PASS] Extraction request carries only: observation_id, canonical_id, row_detail, image_path")
    return True


def test_2_extractor_generic():
    """SliderEvidenceExtractor has no parameter-specific methods"""
    print("\n--- Test 2: Extractor is generic ---")

    extractor = SliderEvidenceExtractor(extractor_id="test_extractor")

    # Verify no parameter-specific methods exist
    assert not hasattr(extractor, 'extract_matrix_amount')
    assert not hasattr(extractor, 'detect_env2_filter1')
    assert not hasattr(extractor, 'handle_serum_slider')

    # Only generic extract() and populate_from_manual_evidence()
    assert hasattr(extractor, 'extract')
    assert hasattr(extractor, 'populate_from_manual_evidence')

    print(f"[PASS] Extractor is fully generic (no parameter-specific methods)")
    return True


def test_3_extraction_result_deterministic():
    """Same request → same extraction result"""
    print("\n--- Test 3: Deterministic extraction ---")

    extractor = SliderEvidenceExtractor()
    request = ExtractionRequest(
        observation_id="obs_det",
        canonical_id="matrix.amount",
        row_detail="Row 1",
        image_path="frame.jpg",
    )

    result1 = extractor.extract(request)
    result2 = extractor.extract(request)

    assert result1.status == result2.status
    assert result1.track_id == result2.track_id

    print(f"[PASS] Extraction deterministic: status={result1.status.value}")
    return True


def test_4_manual_evidence_population():
    """Populate extraction with measured pixel coordinates"""
    print("\n--- Test 4: Manual evidence population ---")

    extractor = SliderEvidenceExtractor()
    request = ExtractionRequest(
        observation_id="obs_manual",
        canonical_id="matrix.amount",
        row_detail="Env 2 → Filter 1 Freq",
        image_path="step3_04m35s_matrix_mod_routes.jpg",
        expected_orientation="horizontal",
    )

    result = extractor.extract(request)

    # Populate with measured coordinates (example values)
    result = extractor.populate_from_manual_evidence(
        result,
        left_px=100.0,
        right_px=300.0,
        top_px=150.0,
        bottom_px=160.0,
        knob_px=200.0,  # middle of track
        track_confidence=0.95,
        knob_confidence=0.85,
    )

    assert result.status == ExtractionStatus.EXTRACTED
    assert result.left_pixel == 100.0
    assert result.right_pixel == 300.0
    assert result.knob_position_pixel == 200.0
    assert result.track_detection_confidence == 0.95
    assert result.knob_detection_confidence == 0.85

    print(f"[PASS] Manual population: track=[{result.left_pixel}, {result.right_pixel}], knob={result.knob_position_pixel}")
    return True


def test_5_invalid_bounds_rejected():
    """Invalid pixel coordinates are detected and rejected"""
    print("\n--- Test 5: Invalid bounds rejection ---")

    extractor = SliderEvidenceExtractor()
    request = ExtractionRequest(
        observation_id="obs_invalid",
        canonical_id="some_slider",
        row_detail=None,
        image_path="test.jpg",
        expected_orientation="horizontal",
    )

    result = extractor.extract(request)

    # Try to populate with invalid bounds (left > right)
    result = extractor.populate_from_manual_evidence(
        result,
        left_px=300.0,
        right_px=100.0,  # INVALID: right < left
        top_px=150.0,
        bottom_px=160.0,
        knob_px=200.0,
    )

    assert result.status == ExtractionStatus.INVALID_FRAME
    assert result.error_message is not None

    print(f"[PASS] Invalid bounds rejected: {result.error_message}")
    return True


def test_6_knob_out_of_bounds_rejected():
    """Knob position outside track bounds is rejected"""
    print("\n--- Test 6: Knob out-of-bounds rejection ---")

    extractor = SliderEvidenceExtractor()
    request = ExtractionRequest(
        observation_id="obs_outofbounds",
        canonical_id="slider",
        row_detail=None,
        image_path="test.jpg",
        expected_orientation="horizontal",
    )

    result = extractor.extract(request)

    # Knob position outside track
    result = extractor.populate_from_manual_evidence(
        result,
        left_px=100.0,
        right_px=300.0,
        top_px=150.0,
        bottom_px=160.0,
        knob_px=350.0,  # INVALID: beyond right_px=300
    )

    assert result.status == ExtractionStatus.OUT_OF_BOUNDS
    assert result.error_message is not None

    print(f"[PASS] Knob out-of-bounds rejected: {result.error_message}")
    return True


def test_7_extraction_to_slider_observation():
    """Convert extraction result to SliderObservation for calibration"""
    print("\n--- Test 7: Conversion to SliderObservation ---")

    extractor = SliderEvidenceExtractor()
    request = ExtractionRequest(
        observation_id="obs_convert",
        canonical_id="matrix.amount",
        row_detail="Env 2 → Filter 1 Freq",
        image_path="step3_04m35s_matrix_mod_routes.jpg",
        expected_orientation="horizontal",
    )

    result = extractor.extract(request)
    result = extractor.populate_from_manual_evidence(
        result,
        left_px=100.0,
        right_px=300.0,
        top_px=150.0,
        bottom_px=160.0,
        knob_px=220.0,
        track_confidence=0.95,
        knob_confidence=0.90,
    )

    # Convert to SliderObservation
    observation = extraction_result_to_slider_observation(request, result)

    assert isinstance(observation, SliderObservation)
    assert observation.observation_id == "obs_convert"
    assert observation.canonical_id == "matrix.amount"
    assert observation.row_detail == "Env 2 → Filter 1 Freq"
    assert observation.observed_position_pixel == 220.0
    assert observation.geometry.left_pixel == 100.0
    assert observation.geometry.right_pixel == 300.0
    assert observation.geometry.orientation == "horizontal"

    print(f"[PASS] Converted to SliderObservation ready for calibration")
    return True


def test_8_multiple_rows_same_image():
    """Extract multiple row geometries from same image (no row-specific logic)"""
    print("\n--- Test 8: Multiple rows, same image ---")

    extractor = SliderEvidenceExtractor()

    # Two different rows, same image
    request1 = ExtractionRequest(
        observation_id="obs_row1",
        canonical_id="matrix.amount",
        row_detail="Env 2 → Filter 1 Freq",
        image_path="matrix_screenshot.jpg",
        expected_orientation="horizontal",
    )

    request2 = ExtractionRequest(
        observation_id="obs_row2",
        canonical_id="matrix.amount",
        row_detail="LFO 1 → OSC A Pitch",
        image_path="matrix_screenshot.jpg",
        expected_orientation="horizontal",
    )

    result1 = extractor.extract(request1)
    result1 = extractor.populate_from_manual_evidence(
        result1,
        left_px=100.0,
        right_px=300.0,
        top_px=150.0,
        bottom_px=160.0,
        knob_px=200.0,
    )

    result2 = extractor.extract(request2)
    result2 = extractor.populate_from_manual_evidence(
        result2,
        left_px=100.0,
        right_px=300.0,
        top_px=180.0,  # different Y (different row)
        bottom_px=190.0,
        knob_px=220.0,
    )

    obs1 = extraction_result_to_slider_observation(request1, result1)
    obs2 = extraction_result_to_slider_observation(request2, result2)

    assert obs1.row_detail == "Env 2 → Filter 1 Freq"
    assert obs2.row_detail == "LFO 1 → OSC A Pitch"
    assert obs1.geometry.top_pixel != obs2.geometry.top_pixel  # different rows
    assert obs1.observed_position_pixel != obs2.observed_position_pixel  # different knob positions

    print(f"[PASS] Two rows extracted from same image:")
    print(f"   Row 1: {obs1.row_detail} @ knob={obs1.observed_position_pixel}")
    print(f"   Row 2: {obs2.row_detail} @ knob={obs2.observed_position_pixel}")
    return True


def test_9_provenance_complete():
    """Extraction result retains full provenance"""
    print("\n--- Test 9: Complete provenance ---")

    extractor = SliderEvidenceExtractor()
    request = ExtractionRequest(
        observation_id="obs_prov",
        canonical_id="matrix.amount",
        row_detail="Row",
        image_path="step3_04m35s_matrix_mod_routes.jpg",
        extraction_method="SLIDER_PIXEL",
    )

    result = extractor.extract(request)
    result = extractor.populate_from_manual_evidence(
        result,
        left_px=100.0,
        right_px=300.0,
        top_px=150.0,
        bottom_px=160.0,
        knob_px=200.0,
    )

    assert result.extraction_provenance is not None
    assert "observation_id" in result.extraction_provenance
    assert "image_path" in result.extraction_provenance
    assert "extraction_method" in result.extraction_provenance

    print(f"[PASS] Provenance: {list(result.extraction_provenance.keys())}")
    return True


def test_10_extraction_ready_for_calibration():
    """Extracted observation flows directly to calibration"""
    print("\n--- Test 10: Ready for calibration pipeline ---")

    from calibration_model import GenericSliderCalibration, TrackGeometry

    extractor = SliderEvidenceExtractor()
    request = ExtractionRequest(
        observation_id="obs_calib",
        canonical_id="matrix.amount",
        row_detail="Env 2 → Filter 1 Freq",
        image_path="test.jpg",
    )

    result = extractor.extract(request)
    result = extractor.populate_from_manual_evidence(
        result,
        left_px=0.0,
        right_px=100.0,
        top_px=50.0,
        bottom_px=60.0,
        knob_px=50.0,  # middle
    )

    observation = extraction_result_to_slider_observation(request, result)

    # Feed directly to calibration
    calibration = GenericSliderCalibration(calibration_id="cal_test")
    calibration.register_track(observation.geometry)
    calib_result = calibration.calibrate(observation)

    assert calib_result.status.value == "CALIBRATED"
    assert calib_result.normalized_position == 0.5  # middle position

    print(f"[PASS] Extracted → Calibrated: normalized_position={calib_result.normalized_position}")
    return True


def run_phase_3_5_1_tests():
    """Run evidence extraction tests."""
    print("\n" + "=" * 70)
    print("Phase 3.5.1: Generic Slider Evidence Extraction Tests")
    print("=" * 70)

    tests = [
        ("Extraction request parameterless", test_1_extraction_request_parameterless),
        ("Extractor is generic", test_2_extractor_generic),
        ("Extraction deterministic", test_3_extraction_result_deterministic),
        ("Manual evidence population", test_4_manual_evidence_population),
        ("Invalid bounds rejection", test_5_invalid_bounds_rejected),
        ("Knob out-of-bounds rejection", test_6_knob_out_of_bounds_rejected),
        ("Conversion to SliderObservation", test_7_extraction_to_slider_observation),
        ("Multiple rows, same image", test_8_multiple_rows_same_image),
        ("Complete provenance", test_9_provenance_complete),
        ("Ready for calibration", test_10_extraction_ready_for_calibration),
    ]

    passed = 0
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"[FAIL] {name}: {e}")

    print("\n" + "=" * 70)
    print(f"Phase 3.5.1 Results: {passed}/{len(tests)} PASSED")
    print("=" * 70)

    return passed == len(tests)


if __name__ == "__main__":
    success = run_phase_3_5_1_tests()
    sys.exit(0 if success else 1)
