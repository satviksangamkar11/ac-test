"""Phase 4.1: Reference State Reconstructor Tests

Proof that:
1. Manifest structure captures complete state
2. Completeness validation blocks unresolved required items
3. Claude audit comparison detects agreement/conflict
4. Verification status flows through properly
5. End-to-end: evidence → manifest → verification gate
"""

import sys
from reference_state_reconstructor import (
    ReferenceStateReconstructor,
    ReferenceStateManifest,
    ControlValue,
    MatrixRoute,
    ControlValueStatus,
)


def test_1_manifest_captures_complete_state():
    """Manifest structure holds all required state components"""
    print("\n--- Test 1: Manifest captures complete state ---")

    reconstructor = ReferenceStateReconstructor(episode_id="test_episode")
    reconstructor.add_frame_source("frame1.jpg")
    reconstructor.add_frame_source("frame2.jpg")

    # Add controls
    ctrl1 = ControlValue(canonical_id="oscA.unison", value=7.0, unit="voices")
    ctrl2 = ControlValue(canonical_id="lfo1.shape", value_text="Lorenz")
    reconstructor.record_control(ctrl1)
    reconstructor.record_control(ctrl2)

    # Add route
    route = MatrixRoute(
        route_id="route_1",
        source="Env 2",
        destination="Filter 1 Freq",
        amount=0.5,
    )
    reconstructor.record_route(route)

    # Add topology
    reconstructor.record_topology("oscC", enabled=False)

    # Add unknown
    reconstructor.record_unknown("Some obscured control", "off-screen")

    manifest = reconstructor.get_manifest()

    assert len(manifest.frames) == 2
    assert len(manifest.controls) == 2
    assert len(manifest.matrix_routes) == 1
    assert len(manifest.topology) == 1
    assert len(manifest.unknown) == 1

    print(f"[PASS] Manifest captures: {len(manifest.controls)} controls, {len(manifest.matrix_routes)} routes, {len(manifest.topology)} topology, {len(manifest.unknown)} unknown")
    return True


def test_2_control_value_captures_evidence():
    """Control value retains extraction evidence and confidence"""
    print("\n--- Test 2: Control value captures evidence ---")

    control = ControlValue(
        canonical_id="matrix.amount",
        value=20.0,
        unit="%",
        modality="SLIDER_PIXEL",
        status=ControlValueStatus.OBSERVED,
        confidence=0.85,
        frame_source="step3_04m35s_matrix_mod_routes.jpg",
        roi_bbox={"x0": 100, "y0": 150, "x1": 300, "y1": 160},
    )

    assert control.canonical_id == "matrix.amount"
    assert control.value == 20.0
    assert control.confidence == 0.85
    assert control.frame_source == "step3_04m35s_matrix_mod_routes.jpg"
    assert control.roi_bbox is not None

    print(f"[PASS] Evidence captured: value={control.value}, confidence={control.confidence}, frame={control.frame_source}")
    return True


def test_3_completeness_validation_blocks_unresolved():
    """Completeness validation detects unresolved required items"""
    print("\n--- Test 3: Completeness validation blocks unresolved ---")

    reconstructor = ReferenceStateReconstructor(episode_id="test")

    # Add resolved control
    ctrl1 = ControlValue(
        canonical_id="oscA.unison",
        value=7.0,
        status=ControlValueStatus.OBSERVED,
    )
    reconstructor.record_control(ctrl1)

    # Add unresolved control (required but insufficient evidence)
    ctrl2 = ControlValue(
        canonical_id="env1.attack",
        value=None,
        status=ControlValueStatus.SOURCE_INSUFFICIENT,
    )
    reconstructor.record_control(ctrl2)

    is_complete, unresolved = reconstructor.validate_completeness()

    assert not is_complete
    assert "env1.attack" in unresolved

    print(f"[PASS] Validation blocked: {len(unresolved)} unresolved required items")
    return True


def test_4_verification_agreement():
    """Claude audit: agreement → VERIFIED"""
    print("\n--- Test 4: Claude audit agreement → VERIFIED ---")

    # System extraction
    system_reconstructor = ReferenceStateReconstructor(episode_id="test")
    system_ctrl = ControlValue(
        canonical_id="oscA.unison",
        value=7.0,
        status=ControlValueStatus.OBSERVED,
        confidence=0.90,
    )
    system_reconstructor.record_control(system_ctrl)
    system_manifest = system_reconstructor.get_manifest()

    # Claude audit (independent extraction)
    claude_reconstructor = ReferenceStateReconstructor(episode_id="test")
    claude_ctrl = ControlValue(
        canonical_id="oscA.unison",
        value=7.0,  # SAME VALUE
        status=ControlValueStatus.OBSERVED,
        confidence=0.92,
    )
    claude_reconstructor.record_control(claude_ctrl)
    claude_manifest = claude_reconstructor.get_manifest()

    # Apply audit
    system_reconstructor.apply_claude_audit(claude_manifest)
    final_manifest = system_reconstructor.get_manifest()

    ctrl = final_manifest.controls["oscA.unison"]
    assert ctrl.verification_status == ControlValueStatus.VERIFIED
    assert ctrl.claude_value == 7.0
    assert len(final_manifest.verification_conflicts) == 0

    print(f"[PASS] Agreement detected: system={system_ctrl.value}, claude={claude_ctrl.value} → VERIFIED")
    return True


def test_5_verification_conflict():
    """Claude audit: disagreement → VERIFICATION_CONFLICT"""
    print("\n--- Test 5: Claude audit disagreement → VERIFICATION_CONFLICT ---")

    # System extraction
    system_reconstructor = ReferenceStateReconstructor(episode_id="test")
    system_ctrl = ControlValue(
        canonical_id="filter1.frequency",
        value=2400.0,  # System says 2400 Hz
        status=ControlValueStatus.OBSERVED,
        confidence=0.70,
    )
    system_reconstructor.record_control(system_ctrl)
    system_manifest = system_reconstructor.get_manifest()

    # Claude audit (different value)
    claude_reconstructor = ReferenceStateReconstructor(episode_id="test")
    claude_ctrl = ControlValue(
        canonical_id="filter1.frequency",
        value=2350.0,  # Claude sees 2350 Hz
        status=ControlValueStatus.OBSERVED,
        confidence=0.88,
    )
    claude_reconstructor.record_control(claude_ctrl)
    claude_manifest = claude_reconstructor.get_manifest()

    # Apply audit
    system_reconstructor.apply_claude_audit(claude_manifest)
    final_manifest = system_reconstructor.get_manifest()

    ctrl = final_manifest.controls["filter1.frequency"]
    assert ctrl.verification_status == ControlValueStatus.VERIFICATION_CONFLICT
    assert ctrl.claude_value == 2350.0
    assert "filter1.frequency" in final_manifest.verification_conflicts
    assert final_manifest.verification_status == "CONFLICT"

    print(f"[PASS] Conflict detected: system={system_ctrl.value}, claude={claude_ctrl.value} → CONFLICT")
    return True


def test_6_text_value_verification():
    """Claude audit on text values (enums, labels)"""
    print("\n--- Test 6: Text value verification ---")

    # System extraction (text)
    system_reconstructor = ReferenceStateReconstructor(episode_id="test")
    system_ctrl = ControlValue(
        canonical_id="lfo1.shape",
        value_text="Lorenz",
        status=ControlValueStatus.OBSERVED,
        confidence=0.95,
    )
    system_reconstructor.record_control(system_ctrl)

    # Claude audit (same text, different case)
    claude_reconstructor = ReferenceStateReconstructor(episode_id="test")
    claude_ctrl = ControlValue(
        canonical_id="lfo1.shape",
        value_text="lorenz",  # lowercase, but same value
        status=ControlValueStatus.OBSERVED,
        confidence=0.93,
    )
    claude_reconstructor.record_control(claude_ctrl)
    claude_manifest = claude_reconstructor.get_manifest()

    # Apply audit
    system_reconstructor.apply_claude_audit(claude_manifest)
    final_manifest = system_reconstructor.get_manifest()

    ctrl = final_manifest.controls["lfo1.shape"]
    assert ctrl.verification_status == ControlValueStatus.VERIFIED

    print(f"[PASS] Text verification (case-insensitive): {system_ctrl.value_text} vs {claude_ctrl.value_text} → VERIFIED")
    return True


def test_7_matrix_route_structure():
    """Matrix route captures modulation connection"""
    print("\n--- Test 7: Matrix route structure ---")

    reconstructor = ReferenceStateReconstructor(episode_id="test")

    route1 = MatrixRoute(
        route_id="matrix_row1",
        source="Env 2",
        destination="Filter 1 Freq",
        amount=0.5,
        status=ControlValueStatus.OBSERVED,
        verification_status=ControlValueStatus.VERIFIED,
    )

    route2 = MatrixRoute(
        route_id="matrix_row2",
        source="LFO 1",
        destination="OSC A Pitch",
        amount=0.3,
        status=ControlValueStatus.OBSERVED,
        verification_status=ControlValueStatus.VERIFIED,
    )

    reconstructor.record_route(route1)
    reconstructor.record_route(route2)

    manifest = reconstructor.get_manifest()

    assert len(manifest.matrix_routes) == 2
    assert manifest.matrix_routes[0].source == "Env 2"
    assert manifest.matrix_routes[1].destination == "OSC A Pitch"

    print(f"[PASS] Matrix routes captured: {len(manifest.matrix_routes)} routes")
    return True


def test_8_topology_tracking():
    """Topology (module enable states) is tracked"""
    print("\n--- Test 8: Topology tracking ---")

    reconstructor = ReferenceStateReconstructor(episode_id="test")

    reconstructor.record_topology("oscA", enabled=True)
    reconstructor.record_topology("oscB", enabled=True)
    reconstructor.record_topology("oscC", enabled=False)

    manifest = reconstructor.get_manifest()

    assert manifest.topology["oscA"] is True
    assert manifest.topology["oscB"] is True
    assert manifest.topology["oscC"] is False

    print(f"[PASS] Topology tracked: {len(manifest.topology)} modules")
    return True


def test_9_completeness_gate_allows_verified():
    """Completeness validation allows all verified items"""
    print("\n--- Test 9: Completeness gate allows verified items ---")

    reconstructor = ReferenceStateReconstructor(episode_id="test")

    # Add verified controls
    for i in range(5):
        ctrl = ControlValue(
            canonical_id=f"control_{i}",
            value=float(i),
            status=ControlValueStatus.OBSERVED,
            verification_status=ControlValueStatus.VERIFIED,
        )
        reconstructor.record_control(ctrl)

    is_complete, unresolved = reconstructor.validate_completeness()

    assert is_complete
    assert len(unresolved) == 0

    print(f"[PASS] Completeness gate allows all verified: {len(reconstructor.get_manifest().controls)} verified items")
    return True


def test_10_end_to_end_reconstruction():
    """End-to-end: extraction → manifest → audit → verification"""
    print("\n--- Test 10: End-to-end reconstruction ---")

    # Step 1: Initial reconstruction (system extraction)
    system_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    system_recon.begin_reconstruction("Serum 2.0.21 tutorial, step 3")
    system_recon.add_frame_source("step3_04m35s_matrix_mod_routes.jpg")

    # Add extracted controls
    system_recon.record_control(ControlValue(
        canonical_id="oscA.unison",
        value=7.0,
        status=ControlValueStatus.OBSERVED,
        confidence=0.95,
        frame_source="step3_04m35s_matrix_mod_routes.jpg",
    ))

    system_recon.record_control(ControlValue(
        canonical_id="lfo1.shape",
        value_text="Lorenz",
        status=ControlValueStatus.OBSERVED,
        confidence=0.92,
        frame_source="step3_04m35s_matrix_mod_routes.jpg",
    ))

    system_recon.record_route(MatrixRoute(
        route_id="matrix_row1",
        source="Env 2",
        destination="Filter 1 Freq",
        amount=0.5,
        status=ControlValueStatus.OBSERVED,
    ))

    system_manifest = system_recon.get_manifest()

    # Step 2: Claude independent audit (same evidence)
    claude_recon = ReferenceStateReconstructor(episode_id="HEEGN1Xl5o4")
    claude_recon.add_frame_source("step3_04m35s_matrix_mod_routes.jpg")

    claude_recon.record_control(ControlValue(
        canonical_id="oscA.unison",
        value=7.0,  # MATCHES
        status=ControlValueStatus.OBSERVED,
        confidence=0.93,
        frame_source="step3_04m35s_matrix_mod_routes.jpg",
    ))

    claude_recon.record_control(ControlValue(
        canonical_id="lfo1.shape",
        value_text="Lorenz",  # MATCHES
        status=ControlValueStatus.OBSERVED,
        confidence=0.95,
        frame_source="step3_04m35s_matrix_mod_routes.jpg",
    ))

    claude_manifest = claude_recon.get_manifest()

    # Step 3: Apply audit
    system_recon.apply_claude_audit(claude_manifest)
    final_manifest = system_recon.get_manifest()

    # Verify
    assert final_manifest.verification_status == "VERIFIED"
    assert len(final_manifest.verification_conflicts) == 0
    assert final_manifest.controls["oscA.unison"].verification_status == ControlValueStatus.VERIFIED
    assert final_manifest.controls["lfo1.shape"].verification_status == ControlValueStatus.VERIFIED

    print(f"[PASS] End-to-end: extraction → audit → verification complete")
    return True


def run_phase_4_1_tests():
    """Run reference state reconstructor tests."""
    print("\n" + "=" * 70)
    print("Phase 4.1: Reference State Reconstructor Tests")
    print("=" * 70)

    tests = [
        ("Manifest captures complete state", test_1_manifest_captures_complete_state),
        ("Control value captures evidence", test_2_control_value_captures_evidence),
        ("Completeness validation blocks unresolved", test_3_completeness_validation_blocks_unresolved),
        ("Claude audit: agreement → VERIFIED", test_4_verification_agreement),
        ("Claude audit: disagreement → CONFLICT", test_5_verification_conflict),
        ("Text value verification", test_6_text_value_verification),
        ("Matrix route structure", test_7_matrix_route_structure),
        ("Topology tracking", test_8_topology_tracking),
        ("Completeness gate allows verified", test_9_completeness_gate_allows_verified),
        ("End-to-end reconstruction", test_10_end_to_end_reconstruction),
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
    print(f"Phase 4.1 Results: {passed}/{len(tests)} PASSED")
    print("=" * 70)

    return passed == len(tests)


if __name__ == "__main__":
    success = run_phase_4_1_tests()
    sys.exit(0 if success else 1)
