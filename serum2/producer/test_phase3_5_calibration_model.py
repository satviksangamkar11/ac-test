"""Phase 3.5: Generic Slider Calibration Model Tests

Acceptance criteria:
1. Track endpoints can be represented deterministically
2. Pixel position → normalized position is deterministic
3. Calibration is independent of parameter identity
4. Multiple rows can use the same calibration model
5. Out-of-track geometry is rejected, not clamped silently
6. Missing/ambiguous geometry produces explicit terminal failure
7. Calibration provenance is retained
8. Candidate value is validated against the Atlas/domain (prep for integration)
9. Calibration cannot directly execute or mutate Serum
10. Result feeds TerminalObservation, preserving Evidence ≠ Execution
"""

import sys
from calibration_model import (
    GenericSliderCalibration,
    TrackGeometry,
    SliderObservation,
    CalibrationStatus,
)


def test_1_track_endpoints_deterministic():
    """Criteria 1: Track endpoints can be represented deterministically"""
    print("\n--- Test 1: Deterministic track endpoints ---")

    track = TrackGeometry(
        track_id="matrix_row1_amount",
        left_pixel=100.0,
        right_pixel=300.0,
        top_pixel=150.0,
        bottom_pixel=160.0,
        orientation="horizontal",
        source_image="step3_04m35s.jpg",
        detection_method="ROI_CROP",
        confidence=0.95,
    )

    # Same track instantiated twice should be identical
    track2 = TrackGeometry(
        track_id="matrix_row1_amount",
        left_pixel=100.0,
        right_pixel=300.0,
        top_pixel=150.0,
        bottom_pixel=160.0,
        orientation="horizontal",
        source_image="step3_04m35s.jpg",
        detection_method="ROI_CROP",
        confidence=0.95,
    )

    assert track.left_pixel == track2.left_pixel
    assert track.right_pixel == track2.right_pixel
    assert track.orientation == track2.orientation
    print(f"[PASS] Track endpoints deterministic: {track.left_pixel}→{track.right_pixel}")
    return True


def test_2_pixel_to_normalized_deterministic():
    """Criteria 2: Pixel position → normalized position is deterministic"""
    print("\n--- Test 2: Deterministic pixel→normalized mapping ---")

    calibration = GenericSliderCalibration(calibration_id="cal_matrix_row1")
    track = TrackGeometry(
        track_id="matrix_row1_amount",
        left_pixel=100.0,
        right_pixel=300.0,
        top_pixel=150.0,
        bottom_pixel=160.0,
        orientation="horizontal",
        source_image="step3_04m35s.jpg",
        detection_method="ROI_CROP",
        confidence=0.95,
    )
    calibration.register_track(track)

    # Same observation, calibrated twice, should yield same result
    obs1 = SliderObservation(
        observation_id="obs1",
        canonical_id="matrix.amount",
        row_detail="Env 2 → Filter 1 Freq",
        geometry=track,
        observed_position_pixel=200.0,  # middle
        calibration_id="cal_matrix_row1",
        source_image="step3_04m35s.jpg",
        confidence=0.9,
    )

    result1 = calibration.calibrate(obs1)
    result2 = calibration.calibrate(obs1)

    assert result1.normalized_position == result2.normalized_position
    assert result1.status == result2.status
    print(f"[PASS] Pixel→normalized deterministic: {result1.normalized_position}")
    return True


def test_3_independent_of_parameter_identity():
    """Criteria 3: Calibration is independent of parameter identity"""
    print("\n--- Test 3: Parameter-identity independent ---")

    calibration = GenericSliderCalibration(calibration_id="cal_generic")
    track = TrackGeometry(
        track_id="generic_slider",
        left_pixel=0.0,
        right_pixel=100.0,
        top_pixel=50.0,
        bottom_pixel=60.0,
        orientation="horizontal",
        source_image="test.jpg",
        detection_method="ROI_CROP",
        confidence=0.9,
    )
    calibration.register_track(track)

    # Same position, different parameters
    obs_matrix = SliderObservation(
        observation_id="obs_matrix",
        canonical_id="matrix.amount",
        row_detail="Env 2 → Filter 1 Freq",
        geometry=track,
        observed_position_pixel=50.0,  # middle
        calibration_id="cal_generic",
        source_image="test.jpg",
    )

    obs_future = SliderObservation(
        observation_id="obs_future",
        canonical_id="some_future_slider",
        row_detail="row_detail_example",
        geometry=track,
        observed_position_pixel=50.0,  # same position
        calibration_id="cal_generic",
        source_image="test.jpg",
    )

    result_matrix = calibration.calibrate(obs_matrix)
    result_future = calibration.calibrate(obs_future)

    assert result_matrix.normalized_position == result_future.normalized_position
    print(f"[PASS] Calibration independent of parameter: {result_matrix.normalized_position}")
    return True


def test_4_multiple_rows_same_calibration():
    """Criteria 4: Multiple rows can use the same calibration model"""
    print("\n--- Test 4: Multiple rows, same calibration ---")

    calibration = GenericSliderCalibration(calibration_id="cal_matrix_all")
    track = TrackGeometry(
        track_id="matrix_all_rows",
        left_pixel=100.0,
        right_pixel=300.0,
        top_pixel=0.0,
        bottom_pixel=10.0,
        orientation="horizontal",
        source_image="matrix.jpg",
        detection_method="ROI_CROP",
        confidence=0.95,
    )
    calibration.register_track(track)

    # Row 1
    obs1 = SliderObservation(
        observation_id="obs_row1",
        canonical_id="matrix.amount",
        row_detail="Env 2 → Filter 1 Freq",
        geometry=track,
        observed_position_pixel=200.0,
        calibration_id="cal_matrix_all",
        source_image="matrix.jpg",
    )

    # Row 2
    obs2 = SliderObservation(
        observation_id="obs_row2",
        canonical_id="matrix.amount",
        row_detail="LFO 1 → OSC A Pitch",
        geometry=track,
        observed_position_pixel=150.0,
        calibration_id="cal_matrix_all",
        source_image="matrix.jpg",
    )

    result1 = calibration.calibrate(obs1)
    result2 = calibration.calibrate(obs2)

    assert result1.status == CalibrationStatus.CALIBRATED
    assert result2.status == CalibrationStatus.CALIBRATED
    assert result1.normalized_position != result2.normalized_position  # different positions
    print(f"[PASS] Multiple rows with same calibration:")
    print(f"   Row 1 (Env 2→Freq): {result1.normalized_position}")
    print(f"   Row 2 (LFO 1→Pitch): {result2.normalized_position}")
    return True


def test_5_out_of_track_rejected():
    """Criteria 5: Out-of-track geometry is rejected, not clamped silently"""
    print("\n--- Test 5: Out-of-track rejection (not clamped) ---")

    calibration = GenericSliderCalibration(calibration_id="cal_strict")
    track = TrackGeometry(
        track_id="strict_track",
        left_pixel=100.0,
        right_pixel=300.0,
        top_pixel=50.0,
        bottom_pixel=60.0,
        orientation="horizontal",
        source_image="test.jpg",
        detection_method="ROI_CROP",
        confidence=0.9,
    )
    calibration.register_track(track)

    # Position beyond right edge
    obs_beyond = SliderObservation(
        observation_id="obs_beyond",
        canonical_id="matrix.amount",
        row_detail=None,
        geometry=track,
        observed_position_pixel=350.0,  # beyond right_pixel=300
        calibration_id="cal_strict",
        source_image="test.jpg",
    )

    result = calibration.calibrate(obs_beyond)

    assert result.status == CalibrationStatus.OUT_OF_TRACK
    assert result.error_message is not None
    assert "outside track" in result.error_message
    print(f"[PASS] Out-of-track rejected: {result.error_message}")
    return True


def test_6_missing_geometry_explicit_failure():
    """Criteria 6: Missing/ambiguous geometry produces explicit terminal failure"""
    print("\n--- Test 6: Missing geometry → explicit failure ---")

    calibration = GenericSliderCalibration(calibration_id="cal_incomplete")
    # Do NOT register any tracks

    track = TrackGeometry(
        track_id="unregistered_track",
        left_pixel=0.0,
        right_pixel=100.0,
        top_pixel=50.0,
        bottom_pixel=60.0,
        orientation="horizontal",
        source_image="test.jpg",
        detection_method="ROI_CROP",
        confidence=0.9,
    )

    obs = SliderObservation(
        observation_id="obs1",
        canonical_id="matrix.amount",
        row_detail=None,
        geometry=track,
        observed_position_pixel=50.0,
        calibration_id="cal_incomplete",
        source_image="test.jpg",
    )

    result = calibration.calibrate(obs)

    assert result.status == CalibrationStatus.MISSING_GEOMETRY
    assert result.error_message is not None
    print(f"[PASS] Missing geometry explicit failure: {result.status.value}")
    return True


def test_7_provenance_retained():
    """Criteria 7: Calibration provenance is retained"""
    print("\n--- Test 7: Provenance retained in result ---")

    calibration = GenericSliderCalibration(calibration_id="cal_prov")
    track = TrackGeometry(
        track_id="track_prov",
        left_pixel=100.0,
        right_pixel=300.0,
        top_pixel=50.0,
        bottom_pixel=60.0,
        orientation="horizontal",
        source_image="step3_04m35s.jpg",
        detection_method="ROI_CROP",
        confidence=0.95,
    )
    calibration.register_track(track)

    obs = SliderObservation(
        observation_id="obs_prov",
        canonical_id="matrix.amount",
        row_detail="Env 2 → Filter 1 Freq",
        geometry=track,
        observed_position_pixel=200.0,
        calibration_id="cal_prov",
        source_image="step3_04m35s.jpg",
        confidence=0.92,
    )

    result = calibration.calibrate(obs)

    assert result.provenance["observation_id"] == "obs_prov"
    assert result.provenance["canonical_id"] == "matrix.amount"
    assert result.provenance["row_detail"] == "Env 2 → Filter 1 Freq"
    assert result.provenance["source_image"] == "step3_04m35s.jpg"
    assert result.provenance["track_detection_confidence"] == "0.95"
    print(f"[PASS] Provenance retained: {len(result.provenance)} fields")
    return True


def test_8_candidate_value_deterministic():
    """Criteria 8: Candidate value output (prep for domain validation)"""
    print("\n--- Test 8: Candidate value deterministic ---")

    # Normalized position is candidate_value (before domain validation)
    calibration = GenericSliderCalibration(calibration_id="cal_candidate")
    track = TrackGeometry(
        track_id="track_val",
        left_pixel=0.0,
        right_pixel=100.0,
        top_pixel=50.0,
        bottom_pixel=60.0,
        orientation="horizontal",
        source_image="test.jpg",
        detection_method="ROI_CROP",
        confidence=0.9,
    )
    calibration.register_track(track)

    obs = SliderObservation(
        observation_id="obs_val",
        canonical_id="matrix.amount",
        row_detail=None,
        geometry=track,
        observed_position_pixel=75.0,
        calibration_id="cal_candidate",
        source_image="test.jpg",
    )

    result = calibration.calibrate(obs)

    # normalized_position = 75/100 = 0.75
    assert result.normalized_position == 0.75
    print(f"[PASS] Candidate value deterministic: {result.normalized_position}")
    return True


def test_9_no_direct_serum_execution():
    """Criteria 9: Calibration cannot directly execute or mutate Serum"""
    print("\n--- Test 9: No Serum mutation capability ---")

    # This is a verification that the calibration model has no Serum imports,
    # no serum-mcp calls, no state mutation methods.
    # Proof: calibration_model.py does not import serum-mcp or have execute() methods.

    calibration = GenericSliderCalibration(calibration_id="cal_safe")

    # Verify no dangerous methods exist
    assert not hasattr(calibration, 'execute')
    assert not hasattr(calibration, 'set_value')
    assert not hasattr(calibration, 'mutate')

    print(f"[PASS] No Serum mutation capability in calibration model")
    return True


def test_10_feeds_terminal_observation():
    """Criteria 10: Result feeds TerminalObservation (Evidence ≠ Execution)"""
    print("\n--- Test 10: Result structure for TerminalObservation integration ---")

    calibration = GenericSliderCalibration(calibration_id="cal_terminal")
    track = TrackGeometry(
        track_id="track_term",
        left_pixel=0.0,
        right_pixel=100.0,
        top_pixel=50.0,
        bottom_pixel=60.0,
        orientation="horizontal",
        source_image="test.jpg",
        detection_method="ROI_CROP",
        confidence=0.9,
    )
    calibration.register_track(track)

    obs = SliderObservation(
        observation_id="obs_term",
        canonical_id="matrix.amount",
        row_detail="Env 2 → Filter 1 Freq",
        geometry=track,
        observed_position_pixel=50.0,
        calibration_id="cal_terminal",
        source_image="test.jpg",
    )

    result = calibration.calibrate(obs)

    # Result has all fields needed for TerminalObservation
    assert result.status is not None
    assert result.normalized_position is not None or result.status != CalibrationStatus.CALIBRATED
    assert result.provenance is not None
    assert result.error_message is None or result.status != CalibrationStatus.CALIBRATED

    print(f"[PASS] Result structure ready for TerminalObservation:")
    print(f"   Status: {result.status.value}")
    print(f"   Position: {result.normalized_position}")
    print(f"   Provenance fields: {len(result.provenance)}")
    return True


def run_phase_3_5_calibration_tests():
    """Run all acceptance criteria tests."""
    print("\n" + "=" * 70)
    print("Phase 3.5: Generic Slider Calibration Model Tests")
    print("=" * 70)

    tests = [
        ("Track endpoints deterministic", test_1_track_endpoints_deterministic),
        ("Pixel→normalized deterministic", test_2_pixel_to_normalized_deterministic),
        ("Parameter-identity independent", test_3_independent_of_parameter_identity),
        ("Multiple rows, same calibration", test_4_multiple_rows_same_calibration),
        ("Out-of-track rejection", test_5_out_of_track_rejected),
        ("Missing geometry failure", test_6_missing_geometry_explicit_failure),
        ("Provenance retained", test_7_provenance_retained),
        ("Candidate value deterministic", test_8_candidate_value_deterministic),
        ("No Serum mutation", test_9_no_direct_serum_execution),
        ("Feeds TerminalObservation", test_10_feeds_terminal_observation),
    ]

    passed = 0
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"[FAIL] {name}: {e}")

    print("\n" + "=" * 70)
    print(f"Phase 3.5 Calibration Results: {passed}/{len(tests)} PASSED")
    print("=" * 70)

    return passed == len(tests)


if __name__ == "__main__":
    success = run_phase_3_5_calibration_tests()
    sys.exit(0 if success else 1)
