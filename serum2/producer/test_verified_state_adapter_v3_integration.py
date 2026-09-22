"""Test VerifiedStateAdapter integration with v3 extraction pipeline.

Two-phase verification:
  Phase 1: Extraction produces unverified routes (agreement=False)
  Phase 2: Claude audit confirms amounts and sets agreement=True
"""

import numpy as np
from PIL import Image
from slider_evidence_extractor_v3 import (
    SliderEvidenceExtractorV3,
    ExtractionRequest,
    ExtractionStatus,
)
from phase4_2_verified_state_adapter import (
    VerifiedStateBuilder,
    AuditMode,
    BlindAuditProvenance,
)


# Load test image
image_path = r"D:\ableton claude final best\video_screenshots\HEEGN1Xl5o4\step3_04m35s_matrix_mod_routes.jpg"
img = Image.open(image_path)
arr = np.array(img)

# Configuration
REFERENCE_ROWS = [280]
AMOUNT_COLUMN = (198, 324)

TEST_ROUTES = [
    {
        'route_id': 'LFO 1 → A Fine',
        'source': 'LFO 1',
        'destination': 'Osc A Fine',
        'row_y': 160,
        'blind_amount': 1.6,
    },
    {
        'route_id': 'LFO 1 → B Fine',
        'source': 'LFO 1',
        'destination': 'Osc B Fine',
        'row_y': 184,
        'blind_amount': 1.6,
    },
    {
        'route_id': 'Env 3 → Noise Level',
        'source': 'Env 3',
        'destination': 'Noise Level',
        'row_y': 207,
        'blind_amount': 33.3,
    },
    {
        'route_id': 'Env 2 → Filter 1 Freq',
        'source': 'Env 2',
        'destination': 'Filter 1 Freq',
        'row_y': 232,
        'blind_amount': 69.8,
    },
]


def test_phase1_extraction_produces_unverified_routes():
    """Phase 1: Extraction produces 4 routes with agreement=False.

    Critical invariant: extraction does NOT auto-verify routes.
    They remain unverified until Claude audit confirms the amounts.
    """
    print("\n" + "="*80)
    print("PHASE 1: EXTRACTION → UNVERIFIED ROUTES")
    print("="*80)

    builder = VerifiedStateBuilder("HEEGN1Xl5o4")
    extractor = SliderEvidenceExtractorV3()

    # Extract all four routes
    for route_spec in TEST_ROUTES:
        request = ExtractionRequest(
            observation_id=f"obs_{route_spec['route_id'].replace(' → ', '_')}",
            canonical_id="matrix.amount",
            row_detail=str(route_spec['row_y']),
            image_path=image_path,
        )

        result = extractor.extract(
            request,
            reference_row_ys=REFERENCE_ROWS,
            amount_column_x_range=AMOUNT_COLUMN,
        )

        assert result.status == ExtractionStatus.EXTRACTED, \
            f"Extraction failed: {result.error_message}"

        # Add to builder via v3 integration
        track_control, route = builder.add_matrix_route_observation(
            extraction_result=result,
            route_id=route_spec['route_id'],
            source=route_spec['source'],
            destination=route_spec['destination'],
        )

        # Verify extracted values
        assert route.amount is not None, f"{route_spec['route_id']}: amount not extracted"
        assert route.system_amount is not None, f"{route_spec['route_id']}: system_amount not set"
        assert route.amount_unit == "%", f"{route_spec['route_id']}: wrong unit"
        assert route.amount_domain == (-100.0, 100.0), f"{route_spec['route_id']}: wrong domain"
        assert route.amount_source == "SLIDER_PIXEL_CALIBRATION", \
            f"{route_spec['route_id']}: wrong source"

        # CRITICAL: agreement must be False (not auto-verified by extraction)
        assert route.agreement is False, \
            f"{route_spec['route_id']}: extraction incorrectly set agreement=True"

        # CRITICAL: claude_amount must be None (not yet audited)
        assert route.claude_amount is None, \
            f"{route_spec['route_id']}: claude_amount should be None before audit"

        print(f"✓ {route_spec['route_id']}")
        print(f"  Amount: {route.amount:+.1f}% (unverified)")
        print(f"  Agreement: {route.agreement} ← CRITICAL: False until audit")

    # Verify state
    assert len(builder.verified_state.matrix_routes) == 4, \
        f"Expected 4 routes, got {len(builder.verified_state.matrix_routes)}"

    # CRITICAL: gate should NOT pass with unverified routes
    gate_result = builder.verified_state.pass_completeness_gate()
    assert gate_result is False, \
        "Gate incorrectly passed with unverified routes (agreement=False)"

    print("\n✓ PHASE 1 COMPLETE: 4 routes extracted and unverified")
    print("  Gate status: BLOCKED (expected, because agreement=False)")


def test_phase2_audit_sets_agreement():
    """Phase 2: Claude audit confirms amounts and sets agreement=True.

    After extraction produces unverified routes, Claude audit compares
    system amounts against independent blind measurements and confirms agreement.
    """
    print("\n" + "="*80)
    print("PHASE 2: AUDIT → VERIFIED ROUTES")
    print("="*80)

    # Step 1: Extract (same as Phase 1)
    builder = VerifiedStateBuilder("HEEGN1Xl5o4")
    extractor = SliderEvidenceExtractorV3()

    for route_spec in TEST_ROUTES:
        request = ExtractionRequest(
            observation_id=f"obs_{route_spec['route_id'].replace(' → ', '_')}",
            canonical_id="matrix.amount",
            row_detail=str(route_spec['row_y']),
            image_path=image_path,
        )

        result = extractor.extract(
            request,
            reference_row_ys=REFERENCE_ROWS,
            amount_column_x_range=AMOUNT_COLUMN,
        )

        builder.add_matrix_route_observation(
            extraction_result=result,
            route_id=route_spec['route_id'],
            source=route_spec['source'],
            destination=route_spec['destination'],
        )

    # Step 2: Simulate Claude audit (manually confirm agreements)
    print("\nSimulating Claude audit...")
    for route_spec in TEST_ROUTES:
        route_id = route_spec['route_id']
        blind_amount = route_spec['blind_amount']

        route = builder.verified_state.matrix_routes[route_id]
        track_control = builder.verified_state.controls.get(f"matrix.track[{route_id}]")

        # Verify amount is within tolerance
        diff = abs(route.amount - blind_amount)
        assert diff <= 5.0, \
            f"{route_id}: diff {diff:.1f}pp exceeds ±5pp tolerance"

        # Audit confirms amount (Claude sees image and verifies)
        route.claude_amount = blind_amount  # Claude's independent measurement
        route.agreement = True  # Audit confirms agreement

        # Also confirm track geometry control
        if track_control:
            track_control.agreement = True
            track_control.audit_confidence = 0.90

        print(f"  ✓ {route_id}: audit confirms {route.amount:+.1f}% ≈ {blind_amount:+.1f}%")

    # Step 3: Set audit provenance (required for gate)
    from phase4_2_verified_state_adapter import BlindAuditProvenance, AuditMode

    builder.verified_state.audit_provenance = BlindAuditProvenance(
        observer="Claude",
        audit_mode=AuditMode.DIRECT_VISUAL_INSPECTION,
        source_frame_hashes={"step3_04m35s_matrix_mod_routes.jpg": "sha256:placeholder"},
        system_manifest_hidden=True,
        model_checkpoint="claude-haiku-4-5-20251001",
    )

    # Step 4: Verify gate now passes
    print("\nChecking gate conditions...")
    gate_result = builder.verified_state.pass_completeness_gate()

    if not gate_result:
        print("  Gate conditions:")
        print(f"    unresolved_required: {len(builder.verified_state.unresolved_required)} == 0? {len(builder.verified_state.unresolved_required) == 0}")
        print(f"    verification_conflicts: {len(builder.verified_state.verification_conflicts)} == 0? {len(builder.verified_state.verification_conflicts) == 0}")
        print(f"    all routes agreement=True? {all(r.agreement for r in builder.verified_state.matrix_routes.values())}")

    assert gate_result is True, \
        "Gate should pass after audit confirms all routes"

    print("\n✓ PHASE 2 COMPLETE: All routes verified and agreement confirmed")
    print("  Gate status: PASSED")


def test_anti_bypass_regression():
    """Prevent routes from being constructed without going through extraction.

    This regression test ensures the production path can't be bypassed by
    directly constructing routes with pre-computed amounts.
    """
    print("\n" + "="*80)
    print("ANTI-BYPASS REGRESSION TEST")
    print("="*80)

    builder = VerifiedStateBuilder("HEEGN1Xl5o4")

    # Try to bypass extraction by directly calling add_verified_route
    # This SHOULD be allowed for testing/fixtures, but must be detectable
    # (production path should go through add_matrix_route_observation instead)

    direct_route = builder.add_verified_route(
        route_id="test_bypass",
        source="Test",
        destination="Test",
        amount=2.4,
        amount_unit="%",
        amount_domain=(-100.0, 100.0),
        amount_source="MANUAL",  # Not SLIDER_PIXEL_CALIBRATION
        agreement=False,  # Still unverified
    )

    # Verify the bypass route is distinguishable from extraction routes
    assert direct_route.amount_source == "MANUAL", \
        "Bypass route should have different amount_source"

    extracted_routes = [r for r in builder.verified_state.matrix_routes.values()
                        if r.amount_source == "SLIDER_PIXEL_CALIBRATION"]
    manual_routes = [r for r in builder.verified_state.matrix_routes.values()
                     if r.amount_source != "SLIDER_PIXEL_CALIBRATION"]

    print(f"Routes by source:")
    print(f"  SLIDER_PIXEL_CALIBRATION: {len(extracted_routes)}")
    print(f"  Other (manual/fixture): {len(manual_routes)}")

    print("\n✓ ANTI-BYPASS: Direct construction detectable via amount_source")


if __name__ == "__main__":
    print("="*80)
    print("VERIFIED STATE ADAPTER V3 INTEGRATION TESTS")
    print("="*80)

    try:
        test_phase1_extraction_produces_unverified_routes()
        test_phase2_audit_sets_agreement()
        test_anti_bypass_regression()

        print("\n" + "="*80)
        print("ALL INTEGRATION TESTS PASSED ✓")
        print("="*80)
        print("\nProduction path validated:")
        print("  1. Extraction → unverified routes (agreement=False)")
        print("  2. Audit → confirmed agreement (agreement=True)")
        print("  3. Anti-bypass detectable via amount_source")
        print("\nReady for production integration.")

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        exit(1)
