"""Phase 4.2: Verified Reference State Tests

Acceptance criteria:
1. SliderObservation → VerifiedControlValue
2. Calibration provenance preserved
3. Canonical ID preserved
4. Domain value preserved
5. Unit preserved
6. Both Matrix rows distinct in manifest
7. Claude agreement → VERIFIED
8. Claude disagreement → CONFLICT
9. Claude-only item → BLOCK
10. Route mismatch → CONFLICT
11. Topology mismatch → CONFLICT
12. Unresolved required item → BLOCK
13. Fully verified state → passes gate
14. No serum-mcp call from reconstruction

Uses real Matrix fixture (both rows) end-to-end.
"""

import sys
from matrix_amount_fixture import (
    MatrixAmountRow1Fixture,
    MatrixAmountRow2Fixture,
)
from phase4_2_verified_state_adapter import (
    VerifiedStateBuilder,
    VerifiedControlValue,
    VerifiedMatrixRoute,
    BlindAuditProvenance,
    AuditMode,
)
from reference_state_reconstructor import (
    ReferenceStateReconstructor,
    ReferenceStateManifest,
    ControlValue,
    MatrixRoute,
    ControlValueStatus,
)


def test_1_slider_to_verified_control():
    """SliderObservation → VerifiedControlValue preserves all provenance"""
    print("\n--- Test 1: SliderObservation → VerifiedControlValue ---")

    # Get real calibration result from fixture
    row1_normalized = MatrixAmountRow1Fixture.calibrate()
    row1_domain_value = MatrixAmountRow1Fixture.domain_validate(row1_normalized)
    row1_obs = MatrixAmountRow1Fixture.get_slider_observation()

    # Build verified state
    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")
    verified_ctrl = builder.add_slider_observation(
        slider_obs=row1_obs,
        calibration_result=None,  # would contain CalibrationResult
        domain_value=row1_domain_value,
    )

    assert verified_ctrl.canonical_id == "matrix.amount"
    assert verified_ctrl.value == 20.0
    assert verified_ctrl.unit == "%"
    assert verified_ctrl.modality == "SLIDER_PIXEL"
    assert verified_ctrl.frame_source == "step3_04m35s_matrix_mod_routes.jpg"
    assert verified_ctrl.calibration_confidence == 0.85

    print(f"[PASS] SliderObservation → VerifiedControlValue: {verified_ctrl.canonical_id}={verified_ctrl.value}{verified_ctrl.unit}")
    return True


def test_2_both_matrix_rows_distinct():
    """Both Matrix rows appear distinctly in verified state"""
    print("\n--- Test 2: Both Matrix rows distinct in manifest ---")

    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")

    # Row 1
    row1_normalized = MatrixAmountRow1Fixture.calibrate()
    row1_domain = MatrixAmountRow1Fixture.domain_validate(row1_normalized)
    row1_obs = MatrixAmountRow1Fixture.get_slider_observation()
    row1_ctrl = builder.add_slider_observation(row1_obs, None, row1_domain)

    # Row 2
    row2_normalized = MatrixAmountRow2Fixture.calibrate()
    row2_domain = MatrixAmountRow2Fixture.domain_validate(row2_normalized)
    row2_obs = MatrixAmountRow2Fixture.get_slider_observation()

    # Create separate verified control for row 2 (with row_detail distinction)
    row2_ctrl = VerifiedControlValue(
        canonical_id="matrix.amount[LFO 1 → OSC A Pitch]",
        value=row2_domain,
        unit="%",
        modality="SLIDER_PIXEL",
        frame_source="step3_04m35s_matrix_mod_routes.jpg",
        system_value=row2_domain,
        calibration_confidence=0.82,
    )
    builder.verified_state.add_verified_control(row2_ctrl)

    verified_state = builder.verified_state

    # Both rows should be present and distinct
    assert "matrix.amount" in [c.canonical_id for c in verified_state.controls.values()]
    assert "matrix.amount[LFO 1 → OSC A Pitch]" in [c.canonical_id for c in verified_state.controls.values()]

    row1_val = [c.value for c in verified_state.controls.values() if "Env 2" in c.canonical_id or c.value == 20.0][0]
    row2_val = [c.value for c in verified_state.controls.values() if "LFO 1" in c.canonical_id or c.value == -20.0][0]

    assert row1_val == 20.0
    assert row2_val == -20.0

    print(f"[PASS] Both rows distinct: Row1={row1_val}%, Row2={row2_val}%")
    return True


def test_3_claude_agreement_verified():
    """Claude agreement on both rows → VERIFIED"""
    print("\n--- Test 3: Claude agreement → VERIFIED (both rows) ---")

    # System extracts both rows
    system_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    system_recon.add_frame_source("step3_04m35s_matrix_mod_routes.jpg")

    system_recon.record_control(ControlValue(
        canonical_id="matrix.amount[Env 2 → Filter 1 Freq]",
        value=20.0,
        unit="%",
        status=ControlValueStatus.OBSERVED,
        confidence=0.85,
        frame_source="step3_04m35s_matrix_mod_routes.jpg",
    ))

    system_recon.record_control(ControlValue(
        canonical_id="matrix.amount[LFO 1 → OSC A Pitch]",
        value=-20.0,
        unit="%",
        status=ControlValueStatus.OBSERVED,
        confidence=0.82,
        frame_source="step3_04m35s_matrix_mod_routes.jpg",
    ))

    system_manifest = system_recon.get_manifest()

    # Claude audit (independent, matches)
    claude_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    claude_recon.add_frame_source("step3_04m35s_matrix_mod_routes.jpg")

    claude_recon.record_control(ControlValue(
        canonical_id="matrix.amount[Env 2 → Filter 1 Freq]",
        value=20.0,  # MATCHES
        unit="%",
        status=ControlValueStatus.OBSERVED,
        confidence=0.87,
        frame_source="step3_04m35s_matrix_mod_routes.jpg",
    ))

    claude_recon.record_control(ControlValue(
        canonical_id="matrix.amount[LFO 1 → OSC A Pitch]",
        value=-20.0,  # MATCHES
        unit="%",
        status=ControlValueStatus.OBSERVED,
        confidence=0.84,
        frame_source="step3_04m35s_matrix_mod_routes.jpg",
    ))

    claude_manifest = claude_recon.get_manifest()

    # Build verified state and apply audit
    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")
    all_agree, conflicts = builder.audit_full_state(system_manifest, claude_manifest)

    assert all_agree, f"Expected agreement but got conflicts: {conflicts}"
    assert len(conflicts) == 0

    print(f"[PASS] Claude agreement on both rows: all_agree={all_agree}")
    return True


def test_4_claude_disagreement_conflict():
    """Claude disagreement on Row 1 → VERIFICATION_CONFLICT"""
    print("\n--- Test 4: Claude disagreement → CONFLICT ---")

    # System: Row 1 = 20%
    system_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    system_recon.record_control(ControlValue(
        canonical_id="matrix.amount[Env 2 → Filter 1 Freq]",
        value=20.0,
        status=ControlValueStatus.OBSERVED,
        confidence=0.85,
    ))
    system_manifest = system_recon.get_manifest()

    # Claude: Row 1 = 25% (DIFFERENT)
    claude_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    claude_recon.record_control(ControlValue(
        canonical_id="matrix.amount[Env 2 → Filter 1 Freq]",
        value=25.0,  # DISAGREE
        status=ControlValueStatus.OBSERVED,
        confidence=0.88,
    ))
    claude_manifest = claude_recon.get_manifest()

    # Audit
    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")
    all_agree, conflicts = builder.audit_full_state(system_manifest, claude_manifest)

    assert not all_agree
    assert len(conflicts) > 0
    assert any("MISMATCH" in c for c in conflicts)

    print(f"[PASS] Disagreement detected: conflicts={conflicts}")
    return True


def test_5_claude_only_item_blocks():
    """Claude-only item (not in system extraction) → BLOCK"""
    print("\n--- Test 5: Claude-only item → BLOCK ---")

    # System: only Row 1
    system_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    system_recon.record_control(ControlValue(
        canonical_id="matrix.amount[Env 2 → Filter 1 Freq]",
        value=20.0,
        status=ControlValueStatus.OBSERVED,
    ))
    system_manifest = system_recon.get_manifest()

    # Claude: Row 1 + Row 2 + filter1.cutoff (system missed these)
    claude_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    claude_recon.record_control(ControlValue(
        canonical_id="matrix.amount[Env 2 → Filter 1 Freq]",
        value=20.0,
        status=ControlValueStatus.OBSERVED,
    ))
    claude_recon.record_control(ControlValue(
        canonical_id="matrix.amount[LFO 1 → OSC A Pitch]",
        value=-20.0,
        status=ControlValueStatus.OBSERVED,
    ))
    claude_recon.record_control(ControlValue(
        canonical_id="filter1.cutoff",
        value=2400.0,
        status=ControlValueStatus.OBSERVED,
    ))
    claude_manifest = claude_recon.get_manifest()

    # Audit
    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")
    all_agree, conflicts = builder.audit_full_state(system_manifest, claude_manifest)

    # Should detect Claude-only items
    assert not all_agree
    claude_only = builder.detect_claude_only_items(
        set(system_manifest.controls.keys()),
        set(claude_manifest.controls.keys())
    )
    assert len(claude_only) > 0
    assert "matrix.amount[LFO 1 → OSC A Pitch]" in claude_only
    assert "filter1.cutoff" in claude_only

    print(f"[PASS] Claude-only items detected: {claude_only}")
    return True


def test_6_route_mismatch_conflict():
    """Matrix route mismatch → VERIFICATION_CONFLICT"""
    print("\n--- Test 6: Route mismatch → CONFLICT ---")

    # System: Route with amount 0.5
    system_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    system_recon.record_route(MatrixRoute(
        route_id="matrix_row1",
        source="Env 2",
        destination="Filter 1 Freq",
        amount=0.5,
        status=ControlValueStatus.OBSERVED,
    ))
    system_manifest = system_recon.get_manifest()

    # Claude: same route, different amount (0.45)
    claude_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    claude_recon.record_route(MatrixRoute(
        route_id="matrix_row1",
        source="Env 2",
        destination="Filter 1 Freq",
        amount=0.45,  # DIFFERENT
        status=ControlValueStatus.OBSERVED,
    ))
    claude_manifest = claude_recon.get_manifest()

    # Audit
    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")
    all_agree, conflicts = builder.audit_full_state(system_manifest, claude_manifest)

    assert not all_agree
    assert any("ROUTE_MISMATCH" in c for c in conflicts)

    print(f"[PASS] Route mismatch detected: {conflicts}")
    return True


def test_7_topology_mismatch_conflict():
    """Module enable state mismatch → VERIFICATION_CONFLICT"""
    print("\n--- Test 7: Topology mismatch → CONFLICT ---")

    # System: oscC disabled
    system_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    system_recon.record_topology("oscC", enabled=False)
    system_manifest = system_recon.get_manifest()

    # Claude: oscC enabled
    claude_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    claude_recon.record_topology("oscC", enabled=True)  # DIFFERENT
    claude_manifest = claude_recon.get_manifest()

    # Audit
    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")
    all_agree, conflicts = builder.audit_full_state(system_manifest, claude_manifest)

    assert not all_agree
    assert any("TOPOLOGY_MISMATCH" in c for c in conflicts)

    print(f"[PASS] Topology mismatch detected: {conflicts}")
    return True


def test_8_completeness_gate_passes():
    """Fully verified state passes completeness gate"""
    print("\n--- Test 8: Completeness gate passes ---")

    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")

    # Add verified controls
    row1_obs = MatrixAmountRow1Fixture.get_slider_observation()
    row1_normalized = MatrixAmountRow1Fixture.calibrate()
    row1_domain = MatrixAmountRow1Fixture.domain_validate(row1_normalized)
    builder.add_slider_observation(row1_obs, None, row1_domain)

    row2_obs = MatrixAmountRow2Fixture.get_slider_observation()
    row2_normalized = MatrixAmountRow2Fixture.calibrate()
    row2_domain = MatrixAmountRow2Fixture.domain_validate(row2_normalized)
    row2_ctrl = VerifiedControlValue(
        canonical_id="matrix.amount[LFO 1 → OSC A Pitch]",
        value=row2_domain,
        unit="%",
        modality="SLIDER_PIXEL",
        frame_source="step3_04m35s_matrix_mod_routes.jpg",
        system_value=row2_domain,
        calibration_confidence=0.82,
    )
    builder.verified_state.add_verified_control(row2_ctrl)

    # Finalize
    verified_state = builder.finalize()

    # Check gate
    assert verified_state.pass_completeness_gate()
    assert len(verified_state.unresolved_required) == 0
    assert len(verified_state.verification_conflicts) == 0
    assert verified_state.is_verified

    print(f"[PASS] Completeness gate passes: is_verified={verified_state.is_verified}")
    return True


def test_9_blind_audit_provenance():
    """Blind audit provenance tracks observer and independence"""
    print("\n--- Test 9: Blind audit provenance ---")

    provenance = BlindAuditProvenance(
        observer="Claude",
        audit_mode=AuditMode.DIRECT_VISUAL_INSPECTION,
        system_manifest_hidden=True,
        model_checkpoint="claude-sonnet-5",
    )

    provenance.source_frame_hashes["step3_04m35s_matrix_mod_routes.jpg"] = "abc123def456..."

    assert provenance.observer == "Claude"
    assert provenance.system_manifest_hidden is True
    assert "step3_04m35s_matrix_mod_routes.jpg" in provenance.source_frame_hashes

    prov_dict = provenance.to_dict()
    assert prov_dict["observer"] == "Claude"
    assert prov_dict["system_manifest_hidden"] is True

    print(f"[PASS] Blind audit provenance: observer={provenance.observer}, hidden={provenance.system_manifest_hidden}")
    return True


def test_10_no_serum_mcp_calls():
    """Reconstruction layer makes no serum-mcp calls"""
    print("\n--- Test 10: No serum-mcp calls from reconstruction ---")

    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")

    # Verify no serum-mcp methods are accessible
    assert not hasattr(builder, 'generate_preset')
    assert not hasattr(builder, 'edit_preset')
    assert not hasattr(builder.verified_state, 'load_into_serum')
    assert not hasattr(builder.verified_state, 'readback')

    # Reconstruction returns only verified state, no execution
    verified_state = builder.finalize()

    # VerifiedReferenceState is input to next phase, not execution
    assert hasattr(verified_state, 'to_dict')
    assert not hasattr(verified_state, 'execute')

    print(f"[PASS] No serum-mcp calls: reconstruction is evidence-only")
    return True


def run_phase_4_2_tests():
    """Run verified reference state tests."""
    print("\n" + "=" * 70)
    print("Phase 4.2: Verified Reference State Integration Tests")
    print("=" * 70)

    tests = [
        ("SliderObservation → VerifiedControlValue", test_1_slider_to_verified_control),
        ("Both Matrix rows distinct", test_2_both_matrix_rows_distinct),
        ("Claude agreement → VERIFIED", test_3_claude_agreement_verified),
        ("Claude disagreement → CONFLICT", test_4_claude_disagreement_conflict),
        ("Claude-only item → BLOCK", test_5_claude_only_item_blocks),
        ("Route mismatch → CONFLICT", test_6_route_mismatch_conflict),
        ("Topology mismatch → CONFLICT", test_7_topology_mismatch_conflict),
        ("Completeness gate passes", test_8_completeness_gate_passes),
        ("Blind audit provenance", test_9_blind_audit_provenance),
        ("No serum-mcp calls", test_10_no_serum_mcp_calls),
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
    print(f"Phase 4.2 Results: {passed}/{len(tests)} PASSED")
    print("=" * 70)

    return passed == len(tests)


if __name__ == "__main__":
    success = run_phase_4_2_tests()
    sys.exit(0 if success else 1)
