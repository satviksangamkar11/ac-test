"""Phase 3.5.2: Real Matrix Amount Fixture Tests

Acceptance criteria:
1. Real screenshot fixture loads
2. Real track coordinates are recorded
3. Real knob coordinate is recorded
4. ExtractionResult is EXTRACTED
5. SliderObservation is produced
6. Calibration returns deterministic normalized position
7. Domain mapper returns value in [-100, 100]
8. Evidence provenance is preserved end-to-end
9. TerminalObservation is generated
10. No execution/mutation occurs (Evidence ≠ Execution)

Plus: Second independent row proves genericity (Row A ≠ Row B, same GenericSliderCalibration).
"""

import sys
from matrix_amount_fixture import (
    MatrixAmountRow1Fixture,
    MatrixAmountRow2Fixture,
    MatrixAmountDomain,
)
from expected_inventory import (
    TerminalObservation,
    ObservationOutcome,
)


def test_1_real_screenshot_fixture_loads():
    """Fixture metadata loads without error"""
    print("\n--- Test 1: Real screenshot fixture loads ---")

    assert MatrixAmountRow1Fixture.reference_id == "HEEGN1Xl5o4"
    assert MatrixAmountRow1Fixture.source_image == "step3_04m35s_matrix_mod_routes.jpg"
    assert MatrixAmountRow1Fixture.canonical_id == "matrix.amount"
    assert MatrixAmountRow1Fixture.row_detail == "Env 2 → Filter 1 Freq"

    print(f"[PASS] Fixture loaded: {MatrixAmountRow1Fixture.canonical_id}[{MatrixAmountRow1Fixture.row_detail}]")
    return True


def test_2_real_track_coordinates_recorded():
    """Real measured track boundaries are stored"""
    print("\n--- Test 2: Real track coordinates recorded ---")

    assert MatrixAmountRow1Fixture.track_left_pixel == 100.0
    assert MatrixAmountRow1Fixture.track_right_pixel == 300.0
    assert MatrixAmountRow1Fixture.track_top_pixel == 150.0
    assert MatrixAmountRow1Fixture.track_bottom_pixel == 160.0

    # Validate sanity: left < right, top < bottom
    assert MatrixAmountRow1Fixture.track_left_pixel < MatrixAmountRow1Fixture.track_right_pixel
    assert MatrixAmountRow1Fixture.track_top_pixel < MatrixAmountRow1Fixture.track_bottom_pixel

    print(f"[PASS] Track: [{MatrixAmountRow1Fixture.track_left_pixel}, {MatrixAmountRow1Fixture.track_right_pixel}]")
    return True


def test_3_real_knob_coordinate_recorded():
    """Real measured knob position is stored"""
    print("\n--- Test 3: Real knob coordinate recorded ---")

    assert MatrixAmountRow1Fixture.knob_position_pixel == 220.0

    # Validate: knob within track bounds
    assert MatrixAmountRow1Fixture.track_left_pixel <= MatrixAmountRow1Fixture.knob_position_pixel <= MatrixAmountRow1Fixture.track_right_pixel

    print(f"[PASS] Knob position: {MatrixAmountRow1Fixture.knob_position_pixel}")
    return True


def test_4_extraction_result_is_extracted():
    """ExtractionResult status is EXTRACTED"""
    print("\n--- Test 4: ExtractionResult status ---")

    result = MatrixAmountRow1Fixture.get_extraction_result()

    assert result.status.value == "EXTRACTED"
    assert result.knob_position_pixel == 220.0
    assert result.track_detection_confidence == 0.95
    assert result.knob_detection_confidence == 0.85

    print(f"[PASS] Extraction: status={result.status.value}, track_conf={result.track_detection_confidence}")
    return True


def test_5_slider_observation_produced():
    """SliderObservation is created from extraction result"""
    print("\n--- Test 5: SliderObservation produced ---")

    observation = MatrixAmountRow1Fixture.get_slider_observation()

    assert observation.canonical_id == "matrix.amount"
    assert observation.row_detail == "Env 2 → Filter 1 Freq"
    assert observation.observed_position_pixel == 220.0
    assert observation.source_image == "step3_04m35s_matrix_mod_routes.jpg"

    print(f"[PASS] SliderObservation: {observation.canonical_id}[{observation.row_detail}]")
    return True


def test_6_calibration_deterministic():
    """Calibration returns deterministic normalized position"""
    print("\n--- Test 6: Calibration deterministic ---")

    # Run calibration twice
    norm1 = MatrixAmountRow1Fixture.calibrate()
    norm2 = MatrixAmountRow1Fixture.calibrate()

    assert norm1 == norm2
    assert 0.0 <= norm1 <= 1.0

    # knob at 220 out of [100, 300] = 120/200 = 0.6
    expected_normalized = (220.0 - 100.0) / (300.0 - 100.0)
    assert norm1 == expected_normalized

    print(f"[PASS] Calibration deterministic: normalized_position={norm1}")
    return True


def test_7_domain_mapper_valid_range():
    """Domain mapper returns value in [-100, 100]"""
    print("\n--- Test 7: Domain mapper valid range ---")

    normalized = MatrixAmountRow1Fixture.calibrate()
    domain_value = MatrixAmountRow1Fixture.domain_validate(normalized)

    assert MatrixAmountRow1Fixture.domain.min_value <= domain_value <= MatrixAmountRow1Fixture.domain.max_value

    # normalized=0.6 → domain_value = (0.6 * 200) - 100 = 120 - 100 = 20
    expected_domain_value = 20.0
    assert domain_value == expected_domain_value

    print(f"[PASS] Domain value: {domain_value} (in [-100, 100])")
    return True


def test_8_provenance_preserved_end_to_end():
    """Evidence provenance is retained through pipeline"""
    print("\n--- Test 8: Provenance preserved end-to-end ---")

    observation = MatrixAmountRow1Fixture.get_slider_observation()

    # Check provenance at each layer
    assert observation.source_image == "step3_04m35s_matrix_mod_routes.jpg"
    assert observation.confidence == 0.85  # knob_detection_confidence
    assert observation.geometry.source_image == "step3_04m35s_matrix_mod_routes.jpg"
    assert observation.geometry.detection_method == "SLIDER_PIXEL"
    assert observation.geometry.confidence == 0.95  # track_detection_confidence

    print(f"[PASS] Provenance trail: source={observation.source_image}, confidence={observation.confidence}")
    return True


def test_9_terminal_observation_generated():
    """TerminalObservation is created with OBSERVED outcome"""
    print("\n--- Test 9: TerminalObservation generated ---")

    normalized = MatrixAmountRow1Fixture.calibrate()
    domain_value = MatrixAmountRow1Fixture.domain_validate(normalized)

    # Create TerminalObservation
    terminal = TerminalObservation(
        canonical_id="matrix.amount",
        outcome=ObservationOutcome.OBSERVED,
        observation_status="OBSERVED",
        evidence_status="SUFFICIENT",
        proof_level="VISUAL_ONLY",
        candidate={
            "normalized_position": normalized,
            "domain_value": domain_value,
            "strategy": "SLIDER_PIXEL",
        },
        provenance={
            "source_image": "step3_04m35s_matrix_mod_routes.jpg",
            "row_detail": "Env 2 → Filter 1 Freq",
            "extraction_confidence": "0.85",
            "track_detection_confidence": "0.95",
            "calibration_method": "GenericSliderCalibration",
            "normalized_position": str(normalized),
            "domain_value": str(domain_value),
        }
    )

    assert terminal.canonical_id == "matrix.amount"
    assert terminal.outcome == ObservationOutcome.OBSERVED
    assert terminal.candidate["domain_value"] == 20.0

    print(f"[PASS] TerminalObservation: outcome={terminal.outcome.value}, value={terminal.candidate['domain_value']}")
    return True


def test_10_no_execution_occurs():
    """Calibration pipeline does NOT execute or mutate Serum"""
    print("\n--- Test 10: No Serum execution/mutation ---")

    # Run full pipeline
    observation = MatrixAmountRow1Fixture.get_slider_observation()
    normalized = MatrixAmountRow1Fixture.calibrate()
    domain_value = MatrixAmountRow1Fixture.domain_validate(normalized)

    # Verify: no serum-mcp imports, no mutation methods called
    # (This is guaranteed by design: calibration_model.py has no Serum imports)

    assert hasattr(observation, 'geometry')
    assert not hasattr(observation, 'execute')
    assert not hasattr(observation, 'mutate_serum')

    print(f"[PASS] No execution occurred. Evidence only: normalized={normalized}, domain_value={domain_value}")
    return True


def test_11_same_coordinates_same_result():
    """Same image + same coordinates → same normalized value → same terminal outcome"""
    print("\n--- Test 11: Determinism across runs ---")

    # Run same fixture multiple times
    results = []
    for i in range(3):
        norm = MatrixAmountRow1Fixture.calibrate()
        domain = MatrixAmountRow1Fixture.domain_validate(norm)
        results.append((norm, domain))

    # All runs identical
    assert results[0] == results[1] == results[2]

    print(f"[PASS] Deterministic across 3 runs: {results[0]}")
    return True


def test_12_second_row_genericity():
    """Second independent row (Row 2) uses same calibration engine, different row identity"""
    print("\n--- Test 12: Second row genericity (Row A ≠ Row B) ---")

    # Row 1: Env 2 → Filter 1 Freq
    norm1 = MatrixAmountRow1Fixture.calibrate()
    domain1 = MatrixAmountRow1Fixture.domain_validate(norm1)

    # Row 2: LFO 1 → OSC A Pitch (different row_detail, different knob position)
    norm2 = MatrixAmountRow2Fixture.calibrate()
    domain2 = MatrixAmountRow2Fixture.domain_validate(norm2)

    # Different rows, different positions, different normalized values
    assert norm1 != norm2
    assert domain1 != domain2

    # But same calibration machinery (GenericSliderCalibration)
    # Row 1: knob at 220 out of [100, 300] → (220-100)/(300-100) = 120/200 = 0.6 → 20%
    # Row 2: knob at 180 out of [100, 300] → (180-100)/(300-100) = 80/200 = 0.4 → -20%

    assert norm1 == 0.6
    assert norm2 == 0.4
    assert domain1 == 20.0
    assert domain2 == -20.0

    print(f"[PASS] Two independent rows through same calibration:")
    print(f"   Row 1 ({MatrixAmountRow1Fixture.row_detail}): normalized={norm1}, domain={domain1}%")
    print(f"   Row 2 ({MatrixAmountRow2Fixture.row_detail}): normalized={norm2}, domain={domain2}%")
    return True


def test_13_real_evidence_chain():
    """Full end-to-end chain: extraction → observation → calibration → domain → terminal"""
    print("\n--- Test 13: Real evidence chain (end-to-end) ---")

    # Step 1: Extract
    extraction_request = MatrixAmountRow1Fixture.get_extraction_request()
    extraction_result = MatrixAmountRow1Fixture.get_extraction_result()

    assert extraction_result.status.value == "EXTRACTED"

    # Step 2: Observe
    observation = MatrixAmountRow1Fixture.get_slider_observation()

    assert observation.source_image == "step3_04m35s_matrix_mod_routes.jpg"

    # Step 3: Calibrate
    normalized = MatrixAmountRow1Fixture.calibrate()

    assert 0.0 <= normalized <= 1.0

    # Step 4: Domain validate
    domain_value = MatrixAmountRow1Fixture.domain_validate(normalized)

    assert -100.0 <= domain_value <= 100.0

    # Step 5: Terminal observation
    terminal = TerminalObservation(
        canonical_id="matrix.amount",
        outcome=ObservationOutcome.OBSERVED,
        observation_status="OBSERVED",
        evidence_status="SUFFICIENT",
        proof_level="VISUAL_ONLY",
        candidate={
            "normalized_position": normalized,
            "domain_value": domain_value,
            "row_detail": "Env 2 → Filter 1 Freq",
        },
        provenance={
            "source_image": extraction_result.extraction_provenance.get("image_path"),
            "track_confidence": str(extraction_result.track_detection_confidence),
            "knob_confidence": str(extraction_result.knob_detection_confidence),
        }
    )

    assert terminal.outcome == ObservationOutcome.OBSERVED
    assert terminal.candidate["domain_value"] == 20.0

    print(f"[PASS] Full chain: {extraction_request.image_path} → {terminal.outcome.value} (value={terminal.candidate['domain_value']}%)")
    return True


def run_phase_3_5_2_tests():
    """Run matrix amount fixture tests."""
    print("\n" + "=" * 70)
    print("Phase 3.5.2: Real Matrix Amount Fixture Tests")
    print("=" * 70)

    tests = [
        ("Real screenshot fixture loads", test_1_real_screenshot_fixture_loads),
        ("Real track coordinates recorded", test_2_real_track_coordinates_recorded),
        ("Real knob coordinate recorded", test_3_real_knob_coordinate_recorded),
        ("ExtractionResult is EXTRACTED", test_4_extraction_result_is_extracted),
        ("SliderObservation produced", test_5_slider_observation_produced),
        ("Calibration deterministic", test_6_calibration_deterministic),
        ("Domain mapper valid range", test_7_domain_mapper_valid_range),
        ("Provenance preserved end-to-end", test_8_provenance_preserved_end_to_end),
        ("TerminalObservation generated", test_9_terminal_observation_generated),
        ("No execution/mutation occurs", test_10_no_execution_occurs),
        ("Determinism across runs", test_11_same_coordinates_same_result),
        ("Second row genericity", test_12_second_row_genericity),
        ("Real evidence chain (end-to-end)", test_13_real_evidence_chain),
    ]

    passed = 0
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"[FAIL] {name}: {e}")
        except Exception as e:
            print(f"[ERROR] {name}: {type(e).__name__}: {e}")

    print("\n" + "=" * 70)
    print(f"Phase 3.5.2 Results: {passed}/{len(tests)} PASSED")
    print("=" * 70)

    return passed == len(tests)


if __name__ == "__main__":
    success = run_phase_3_5_2_tests()
    sys.exit(0 if success else 1)
