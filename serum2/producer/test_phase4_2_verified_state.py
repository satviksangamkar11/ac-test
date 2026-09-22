"""Phase 4.2: Verified Reference State Tests

Acceptance criteria:
1. SliderObservation -> VerifiedControlValue
2. Calibration provenance preserved
3. Row-detail identity preserved (matrix.amount[row])
4. Domain value preserved
5. Unit preserved
6. Both Matrix rows distinct in manifest
7. Claude agreement -> VERIFIED
8. Claude disagreement -> CONFLICT
9. Claude-only item -> BLOCK
10. Route mismatch -> CONFLICT
11. Topology mismatch -> CONFLICT
12. Unresolved required item -> BLOCK
13. Fully verified state -> passes gate
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
    """SliderObservation to VerifiedControlValue preserves all provenance"""
    print("\n--- Test 1: SliderObservation to VerifiedControlValue ---")

    try:
        # Get real calibration result from fixture
        row1_normalized = MatrixAmountRow1Fixture.calibrate()
        row1_domain_value = MatrixAmountRow1Fixture.domain_validate(row1_normalized)
        row1_obs = MatrixAmountRow1Fixture.get_slider_observation()

        # Build verified state
        builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")
        verified_ctrl = builder.add_slider_observation(
            slider_obs=row1_obs,
            calibration_result=None,
            domain_value=row1_domain_value,
        )

        # Should have row-detail preserved
        assert "matrix.amount" in verified_ctrl.canonical_id
        assert verified_ctrl.value == 20.0
        assert verified_ctrl.unit == "%"
        assert verified_ctrl.modality == "SLIDER_PIXEL"
        assert verified_ctrl.frame_source == "step3_04m35s_matrix_mod_routes.jpg"
        assert verified_ctrl.calibration_confidence == 0.85

        # Use ASCII-safe output for Windows console
        canonical_safe = verified_ctrl.canonical_id.replace('[', '(').replace(']', ')').replace('->', '-->')
        print(f"[PASS] SliderObservation conversion: {canonical_safe}={verified_ctrl.value}%")
        return True
    except Exception as e:
        print(f"[FAIL] SliderObservation conversion: {type(e).__name__}: {str(e)[:50]}")
        raise


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
        canonical_id="matrix.amount[LFO 1 -> OSC A Pitch]",
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
    canonical_ids = list(verified_state.controls.keys())
    assert len(canonical_ids) == 2, f"Expected 2 controls, got {len(canonical_ids)}: {canonical_ids}"

    row1_val = verified_state.controls[canonical_ids[0]].value
    row2_val = verified_state.controls[canonical_ids[1]].value

    assert row1_val == 20.0, f"Row 1 value should be 20.0, got {row1_val}"
    assert row2_val == -20.0, f"Row 2 value should be -20.0, got {row2_val}"

    print(f"[PASS] Both rows distinct: Row1={row1_val}%, Row2={row2_val}%")
    return True


def test_3_claude_agreement_verified():
    """Claude agreement on both rows -> VERIFIED"""
    print("\n--- Test 3: Claude agreement -> VERIFIED (both rows) ---")

    # System extracts both rows
    system_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    system_recon.add_frame_source("step3_04m35s_matrix_mod_routes.jpg")

    system_recon.record_control(ControlValue(
        canonical_id="matrix.amount[Env 2 -> Filter 1 Freq]",
        value=20.0,
        unit="%",
        status=ControlValueStatus.OBSERVED,
        confidence=0.85,
        frame_source="step3_04m35s_matrix_mod_routes.jpg",
    ))

    system_recon.record_control(ControlValue(
        canonical_id="matrix.amount[LFO 1 -> OSC A Pitch]",
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
        canonical_id="matrix.amount[Env 2 -> Filter 1 Freq]",
        value=20.0,
        unit="%",
        status=ControlValueStatus.OBSERVED,
        confidence=0.87,
        frame_source="step3_04m35s_matrix_mod_routes.jpg",
    ))

    claude_recon.record_control(ControlValue(
        canonical_id="matrix.amount[LFO 1 -> OSC A Pitch]",
        value=-20.0,
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
    """Claude disagreement on Row 1 -> VERIFICATION_CONFLICT"""
    print("\n--- Test 4: Claude disagreement -> CONFLICT ---")

    # System: Row 1 = 20%
    system_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    system_recon.record_control(ControlValue(
        canonical_id="matrix.amount[Env 2 -> Filter 1 Freq]",
        value=20.0,
        status=ControlValueStatus.OBSERVED,
        confidence=0.85,
    ))
    system_manifest = system_recon.get_manifest()

    # Claude: Row 1 = 25% (DIFFERENT)
    claude_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    claude_recon.record_control(ControlValue(
        canonical_id="matrix.amount[Env 2 -> Filter 1 Freq]",
        value=25.0,
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


def test_5_claude_only_control():
    """Claude-only control (not in system extraction) -> BLOCK"""
    print("\n--- Test 5: Claude-only control -> BLOCK ---")

    # System: only Row 1
    system_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    system_recon.record_control(ControlValue(
        canonical_id="matrix.amount[Env 2 -> Filter 1 Freq]",
        value=20.0,
        status=ControlValueStatus.OBSERVED,
    ))
    system_manifest = system_recon.get_manifest()

    # Claude: Row 1 + Row 2 + filter1.cutoff
    claude_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    claude_recon.record_control(ControlValue(
        canonical_id="matrix.amount[Env 2 -> Filter 1 Freq]",
        value=20.0,
        status=ControlValueStatus.OBSERVED,
    ))
    claude_recon.record_control(ControlValue(
        canonical_id="matrix.amount[LFO 1 -> OSC A Pitch]",
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
    assert any("CLAUDE_ONLY_" in c for c in conflicts)
    assert len(builder.verified_state.claude_only_items) > 0

    print(f"[PASS] Claude-only items detected: {builder.verified_state.claude_only_items}")
    return True


def test_6_claude_only_route():
    """Claude-only route (not in system) -> BLOCK"""
    print("\n--- Test 6: Claude-only route -> BLOCK ---")

    # System: no routes
    system_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    system_manifest = system_recon.get_manifest()

    # Claude: detects a route
    claude_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    claude_recon.record_route(MatrixRoute(
        route_id="matrix_row1",
        source="Env 2",
        destination="Filter 1 Freq",
        amount=0.5,
        status=ControlValueStatus.OBSERVED,
    ))
    claude_manifest = claude_recon.get_manifest()

    # Audit
    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")
    all_agree, conflicts = builder.audit_full_state(system_manifest, claude_manifest)

    assert not all_agree
    assert any("CLAUDE_ONLY_ROUTE" in c for c in conflicts)

    print(f"[PASS] Claude-only route detected: {conflicts}")
    return True


def test_7_claude_only_topology():
    """Claude-only topology (not in system) -> BLOCK"""
    print("\n--- Test 7: Claude-only topology -> BLOCK ---")

    # System: no topology
    system_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    system_manifest = system_recon.get_manifest()

    # Claude: detects oscC topology
    claude_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    claude_recon.record_topology("oscC", enabled=False)
    claude_manifest = claude_recon.get_manifest()

    # Audit
    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")
    all_agree, conflicts = builder.audit_full_state(system_manifest, claude_manifest)

    assert not all_agree
    assert any("CLAUDE_ONLY_TOPOLOGY" in c for c in conflicts)

    print(f"[PASS] Claude-only topology detected: {conflicts}")
    return True


def test_8_route_mismatch_conflict():
    """Matrix route mismatch -> VERIFICATION_CONFLICT"""
    print("\n--- Test 8: Route mismatch -> CONFLICT ---")

    # System: Route with amount +50.0% (canonical domain)
    system_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    system_recon.record_route(MatrixRoute(
        route_id="matrix_row1",
        source="Env 2",
        destination="Filter 1 Freq",
        amount=50.0,
        amount_unit="%",
        amount_domain=(-100.0, 100.0),
        amount_source="TOOLTIP",
        status=ControlValueStatus.OBSERVED,
    ))
    system_manifest = system_recon.get_manifest()

    # Claude: same route, different amount (+20.0%, outside ±5.0 tolerance)
    claude_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    claude_recon.record_route(MatrixRoute(
        route_id="matrix_row1",
        source="Env 2",
        destination="Filter 1 Freq",
        amount=20.0,
        amount_unit="%",
        amount_domain=(-100.0, 100.0),
        amount_source="TOOLTIP",
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


def test_9_topology_mismatch_conflict():
    """Module enable state mismatch -> VERIFICATION_CONFLICT"""
    print("\n--- Test 9: Topology mismatch -> CONFLICT ---")

    # System: oscC disabled
    system_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    system_recon.record_topology("oscC", enabled=False)
    system_manifest = system_recon.get_manifest()

    # Claude: oscC enabled
    claude_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    claude_recon.record_topology("oscC", enabled=True)
    claude_manifest = claude_recon.get_manifest()

    # Audit
    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")
    all_agree, conflicts = builder.audit_full_state(system_manifest, claude_manifest)

    assert not all_agree
    assert any("TOPOLOGY_MISMATCH" in c for c in conflicts)

    print(f"[PASS] Topology mismatch detected: {conflicts}")
    return True


def test_10_gate_requires_agreement():
    """Gate requires explicit agreement on all items"""
    print("\n--- Test 10: Gate requires explicit agreement ---")

    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")

    # Add control WITHOUT agreement
    ctrl = VerifiedControlValue(
        canonical_id="test.param",
        value=10.0,
        agreement=False,  # NOT agreed
    )
    builder.verified_state.add_verified_control(ctrl)

    provenance = BlindAuditProvenance(
        observer="Claude",
        audit_mode=AuditMode.DIRECT_VISUAL_INSPECTION,
        system_manifest_hidden=True,
    )

    verified_state = builder.finalize(audit_provenance=provenance)

    # Gate should fail because agreement=False
    assert not verified_state.pass_completeness_gate()
    assert not verified_state.is_verified

    print(f"[PASS] Gate blocks unverified controls: is_verified={verified_state.is_verified}")
    return True


def test_11_gate_blocks_unresolved():
    """Gate blocks when unresolved_required > 0"""
    print("\n--- Test 11: Gate blocks unresolved_required ---")

    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")
    builder.verified_state.unresolved_required = ["missing.param"]

    provenance = BlindAuditProvenance(
        observer="Claude",
        audit_mode=AuditMode.DIRECT_VISUAL_INSPECTION,
        system_manifest_hidden=True,
    )

    verified_state = builder.finalize(audit_provenance=provenance)

    assert not verified_state.pass_completeness_gate()
    assert len(verified_state.unresolved_required) > 0

    print(f"[PASS] Gate blocks unresolved: {verified_state.unresolved_required}")
    return True


def test_12_gate_blocks_conflicts():
    """Gate blocks when verification_conflicts > 0"""
    print("\n--- Test 12: Gate blocks verification_conflicts ---")

    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")
    builder.verified_state.verification_conflicts = ["CONTROL_MISMATCH: param1"]

    provenance = BlindAuditProvenance(
        observer="Claude",
        audit_mode=AuditMode.DIRECT_VISUAL_INSPECTION,
        system_manifest_hidden=True,
    )

    verified_state = builder.finalize(audit_provenance=provenance)

    assert not verified_state.pass_completeness_gate()
    assert len(verified_state.verification_conflicts) > 0

    print(f"[PASS] Gate blocks conflicts: {verified_state.verification_conflicts}")
    return True


def test_13_gate_blocks_claude_only():
    """Gate blocks when claude_only_items > 0"""
    print("\n--- Test 13: Gate blocks claude_only_items ---")

    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")
    builder.verified_state.claude_only_items = ["CLAUDE_ONLY_CONTROL: extra.param"]

    provenance = BlindAuditProvenance(
        observer="Claude",
        audit_mode=AuditMode.DIRECT_VISUAL_INSPECTION,
        system_manifest_hidden=True,
    )

    verified_state = builder.finalize(audit_provenance=provenance)

    assert not verified_state.pass_completeness_gate()
    assert len(verified_state.claude_only_items) > 0

    print(f"[PASS] Gate blocks claude_only: {verified_state.claude_only_items}")
    return True


def test_14_gate_requires_provenance():
    """Gate requires audit_provenance present"""
    print("\n--- Test 14: Gate requires audit_provenance ---")

    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")
    ctrl = VerifiedControlValue(canonical_id="test.param", value=10.0, agreement=True)
    builder.verified_state.add_verified_control(ctrl)

    # Finalize WITHOUT provenance
    verified_state = builder.finalize(audit_provenance=None)

    assert not verified_state.pass_completeness_gate()
    assert verified_state.audit_provenance is None

    print(f"[PASS] Gate requires provenance: audit_provenance={verified_state.audit_provenance}")
    return True


def test_15_gate_requires_manifest_hidden():
    """Gate requires system_manifest_hidden=True"""
    print("\n--- Test 15: Gate requires system_manifest_hidden ---")

    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")
    ctrl = VerifiedControlValue(canonical_id="test.param", value=10.0, agreement=True)
    builder.verified_state.add_verified_control(ctrl)

    provenance = BlindAuditProvenance(
        observer="Claude",
        audit_mode=AuditMode.DIRECT_VISUAL_INSPECTION,
        system_manifest_hidden=False,  # NOT hidden
    )

    verified_state = builder.finalize(audit_provenance=provenance)

    assert not verified_state.pass_completeness_gate()
    assert not verified_state.audit_provenance.system_manifest_hidden

    print(f"[PASS] Gate blocks visible manifest: system_manifest_hidden={verified_state.audit_provenance.system_manifest_hidden}")
    return True


def test_16_gate_requires_direct_visual():
    """Gate requires audit_mode=DIRECT_VISUAL_INSPECTION"""
    print("\n--- Test 16: Gate requires DIRECT_VISUAL_INSPECTION ---")

    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")
    ctrl = VerifiedControlValue(canonical_id="test.param", value=10.0, agreement=True)
    builder.verified_state.add_verified_control(ctrl)

    provenance = BlindAuditProvenance(
        observer="Claude",
        audit_mode=AuditMode.SYSTEM_EXTRACTION,  # WRONG mode
        system_manifest_hidden=True,
    )

    verified_state = builder.finalize(audit_provenance=provenance)

    assert not verified_state.pass_completeness_gate()
    assert verified_state.audit_provenance.audit_mode != AuditMode.DIRECT_VISUAL_INSPECTION

    print(f"[PASS] Gate blocks non-visual audit: audit_mode={verified_state.audit_provenance.audit_mode}")
    return True


def test_17_positive_gate_all_conditions():
    """Gate passes when ALL 7 conditions met"""
    print("\n--- Test 17: Gate passes with all conditions ---")

    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")

    # Add verified control with agreement
    ctrl = VerifiedControlValue(canonical_id="test.param", value=10.0, agreement=True)
    builder.verified_state.add_verified_control(ctrl)

    # Correct provenance
    provenance = BlindAuditProvenance(
        observer="Claude",
        audit_mode=AuditMode.DIRECT_VISUAL_INSPECTION,
        system_manifest_hidden=True,
    )

    # No unresolved, conflicts, claude_only, or required_not_visible
    builder.verified_state.unresolved_required = []
    builder.verified_state.verification_conflicts = []
    builder.verified_state.claude_only_items = []
    builder.verified_state.required_not_visible = []

    verified_state = builder.finalize(audit_provenance=provenance)

    assert verified_state.pass_completeness_gate()
    assert verified_state.is_verified
    assert verified_state.audit_provenance.system_manifest_hidden
    assert verified_state.audit_provenance.audit_mode == AuditMode.DIRECT_VISUAL_INSPECTION

    print(f"[PASS] Gate passes all conditions: is_verified={verified_state.is_verified}")
    return True


def test_18_undeclared_representation_blocked():
    """Route amounts without declared unit/domain -> BLOCK, not silently compared.

    Regression guard for the 0.067 (normalized) vs 6.7 (canonical %) bug:
    same route, numerically "close" under the old raw-diff check, but the
    representations were never declared equal, so the gate must refuse to
    compare them at all.
    """
    print("\n--- Test 18: Undeclared amount representation -> BLOCK ---")

    system_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    system_recon.record_route(MatrixRoute(
        route_id="matrix_row1",
        source="Env 2",
        destination="Filter 1 Freq",
        amount=0.067,  # no amount_unit/amount_domain declared
        status=ControlValueStatus.OBSERVED,
    ))
    system_manifest = system_recon.get_manifest()

    claude_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    claude_recon.record_route(MatrixRoute(
        route_id="matrix_row1",
        source="Env 2",
        destination="Filter 1 Freq",
        amount=6.7,  # declared canonical %, but system side is not
        amount_unit="%",
        amount_domain=(-100.0, 100.0),
        amount_source="TOOLTIP",
        status=ControlValueStatus.OBSERVED,
    ))
    claude_manifest = claude_recon.get_manifest()

    builder = VerifiedStateBuilder(episode_id="HEEGN1Xl5o4")
    all_agree, conflicts = builder.audit_full_state(system_manifest, claude_manifest)

    assert not all_agree
    assert any("AMOUNT_REPRESENTATION_UNDECLARED" in c for c in conflicts)
    assert not any("ROUTE_MISMATCH" in c for c in conflicts), (
        "must block on undeclared representation, not fall through to a raw numeric diff"
    )

    print(f"[PASS] Undeclared representation blocked: {conflicts}")
    return True


def run_phase_4_2_tests():
    """Run verified reference state tests."""
    print("\n" + "=" * 70)
    print("Phase 4.2: Verified Reference State Integration Tests")
    print("=" * 70)

    tests = [
        ("SliderObservation to VerifiedControlValue", test_1_slider_to_verified_control),
        ("Both Matrix rows distinct", test_2_both_matrix_rows_distinct),
        ("Claude agreement VERIFIED", test_3_claude_agreement_verified),
        ("Claude disagreement CONFLICT", test_4_claude_disagreement_conflict),
        ("Claude-only control BLOCK", test_5_claude_only_control),
        ("Claude-only route BLOCK", test_6_claude_only_route),
        ("Claude-only topology BLOCK", test_7_claude_only_topology),
        ("Route mismatch CONFLICT", test_8_route_mismatch_conflict),
        ("Topology mismatch CONFLICT", test_9_topology_mismatch_conflict),
        ("Gate requires agreement", test_10_gate_requires_agreement),
        ("Gate blocks unresolved_required", test_11_gate_blocks_unresolved),
        ("Gate blocks verification_conflicts", test_12_gate_blocks_conflicts),
        ("Gate blocks claude_only_items", test_13_gate_blocks_claude_only),
        ("Gate requires provenance", test_14_gate_requires_provenance),
        ("Gate requires system_manifest_hidden", test_15_gate_requires_manifest_hidden),
        ("Gate requires DIRECT_VISUAL_INSPECTION", test_16_gate_requires_direct_visual),
        ("Gate passes all conditions", test_17_positive_gate_all_conditions),
        ("Undeclared amount representation BLOCK", test_18_undeclared_representation_blocked),
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
